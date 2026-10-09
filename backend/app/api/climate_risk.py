from __future__ import annotations

import json
import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.app.business.store import get_store
from backend.app.hazards.assessment import build_hazard_assessment
from backend.app.hazards.location import LocationInput
from backend.app.hazards.schemas import HazardAssessmentRequest
from backend.app.scoring.engine import calculate_climate_risk

load_dotenv()
router = APIRouter(prefix="/api/businesses", tags=["Climate Risk"])


class ClimateRiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    years: int = Field(default=10, ge=1, le=30)
    baseline_credit_score: int = Field(default=750, ge=300, le=900)
    hazard_types: list[str] = Field(
        default_factory=lambda: [
            "precipitation_extremes",
            "temperature_extremes",
            "wind_extremes",
        ]
    )



def _build_evidence_explanation(result: dict, baseline: int, penalty: int | None, adjusted: int | None) -> dict:
    """Explain only structured evidence; fall back to deterministic text if OpenAI is unavailable."""
    dimensions = result.get("dimensions", {})
    evidence = {
        "data_quality": result.get("data_quality", {}),
        "risk_indicator": result.get("experimental_climate_risk_indicator"),
        "dimensions": {
            name: {"score": value.get("score"), "status": value.get("status"),
                   "explanation": value.get("explanation"), "sources": value.get("sources", [])}
            for name, value in dimensions.items()
        },
        "observed_hazard_evidence": result.get("evidence_items", []),
        "supplier_context": result.get("supplier_context", []),
        "missing_inputs": result.get("missing_inputs", []),
        "warnings": result.get("warnings", []),
        "baseline_score": baseline,
        "adjustment_points": penalty,
        "adjusted_score": adjusted,
    }
    fallback = {
        "summary": (
            f"{result.get('data_quality', {}).get('summary', 'Data quality was not assessed.')} "
            f"The climate indicator is {evidence['risk_indicator']}/100. "
            f"The demo applies an adjustment of {penalty:+d} points to baseline {baseline}, resulting in {adjusted}."
            if adjusted is not None else "There is not enough scored evidence to calculate an adjusted score."
        ),
        "positive_factors": [
            f"{name.replace('_', ' ').title()} score is {value['score']}/100."
            for name, value in dimensions.items()
            if value.get("score") is not None and float(value["score"]) < 35
        ],
        "risk_factors": [
            f"{name.replace('_', ' ').title()} score is {value['score']}/100."
            for name, value in dimensions.items()
            if value.get("score") is not None and float(value["score"]) >= 35
        ] + [
            item.get("plain_explanation", "Supplier rainfall may disrupt critical material supply.")
            for item in result.get("evidence_items", [])
            if item.get("label") == "Supplier rainfall exposure"
        ],
        "business_problem": (
            next((item.get("plain_explanation") for item in result.get("evidence_items", [])
                  if item.get("label") == "Supplier rainfall exposure"), None)
            or "No validated business-specific problem can be confirmed until the data quality checks and available evidence are reviewed."
        ),
        "data_quality_issues": [
            item.get("detail", item.get("check", "Data quality issue"))
            for item in result.get("data_quality", {}).get("checks", [])
            if item.get("status") != "passed"
        ],
        "evidence_limitations": list(result.get("missing_inputs", [])) + list(result.get("warnings", [])),
        "generated_by": "rule_based_fallback",
    }
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback
    try:
        response = requests.post(
            os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": (
                        "You are TerraCred's plain-language business climate-risk explainer. FIRST inspect data_quality and its checks. "
                        "If any checks failed or warnings exist, clearly say what information is missing, invalid, or unverified before discussing risk. "
                        "Then explain in simple non-technical language what could disrupt this business, which exact observations support that concern, "
                        "and what evidence is not available. For a furniture maker buying wood from a supplier with high observed rainfall, explain the plausible chain: "
                        "rain or wet storage can make timber harder to dry and keep dry; high wood moisture can encourage mould/fungal decay and cause swelling, warping, "
                        "or cracking; rain can also disrupt roads, timber handling, and deliveries, delaying furniture production. A single daily maximum does not by itself prove an area is rain-prone. Present these as possible mechanisms, "
                        "not confirmed damage. Say that rainfall alone does not prove the wood got wet, the supplier was flooded, or deliveries were disrupted; those need "
                        "storage, humidity/moisture, flood, transport, or supplier records. Use the supplied material and location evidence; do not assume the business sells furniture "
                        "unless the input supports it. Do not call weather data a flood or damage proof. "
                        "Never invent facts, sources, readings, causes, financial history, or recommendations unsupported by the input. "
                        "Missing evidence means unknown, not safe. Do not calculate or change the score. "
                        "Return JSON with keys: summary (2-4 simple sentences), business_problem (one plain-language sentence), "
                        "positive_factors (array of short simple strings), risk_factors (array of short simple strings), "
                        "data_quality_issues (array of short strings), evidence_limitations (array of short strings). "
                        "When supplier rainfall evidence and wood/timber material are present, explicitly connect the observed rainfall to the plausible wood and delivery impacts in plain language. "
                        "Mention the score adjustment is only a demo heuristic, not a validated credit model."
                    )},
                    {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)},
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        explanation = json.loads(response.json()["choices"][0]["message"]["content"])
        explanation["generated_by"] = "openai"
        return explanation
    except Exception:
        return fallback


@router.post("/{business_id}/climate-risk-assessment")
def assess_climate_risk(business_id: str, payload: ClimateRiskRequest):
    store = get_store()
    business = store.get_business(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    suppliers = store.list_suppliers(business_id)
    vulnerability = store.get_operational_vulnerability(business_id)
    hazard_rows = []
    hazard_warning = None

    location = business.business_location
    if location is not None and location.latitude is not None and location.longitude is not None:
        request = HazardAssessmentRequest(
            location=LocationInput(
                latitude=location.latitude,
                longitude=location.longitude,
                place_name=location.place_name,
                admin_area=location.admin_area,
            ),
            hazard_types=payload.hazard_types,
            years=payload.years,
            include_unavailable=True,
        )
        try:
            hazard_result = build_hazard_assessment(request)
            hazard_rows = [item.model_dump(mode="json") for item in hazard_result.hazards]
        except Exception as exc:
            hazard_warning = f"Live hazard retrieval failed: {type(exc).__name__}"
    else:
        hazard_warning = "Business location is missing or incomplete; live hazard assessment was skipped."

    result = calculate_climate_risk(
        business=business.model_dump(mode="json"),
        suppliers=[item.model_dump(mode="json") for item in suppliers],
        vulnerability=vulnerability.model_dump(mode="json") if vulnerability else None,
        hazards=hazard_rows,
    )
    if hazard_warning:
        result["warnings"].append(hazard_warning)

    # Retrieve rainfall evidence at each supplier's location separately from the MSME's location.
    # This avoids incorrectly treating the business address as the supplier's climate exposure.
    supplier_context = []
    supplier_rain_signals = []
    for supplier in suppliers:
        supplier_data = supplier.model_dump(mode="json")
        supplier_location = supplier_data.get("supplier_location") or {}
        material = (supplier_data.get("material_supplied") or "").strip()
        context = {
            "supplier_name": supplier_data.get("supplier_name") or "Unnamed supplier",
            "material_supplied": material or "Not specified",
            "procurement_share_pct": supplier_data.get("procurement_share"),
            "critical_to_operations": supplier_data.get("critical_to_operations"),
            "alternative_supplier_available": supplier_data.get("alternative_supplier_available"),
            "location": supplier_location.get("place_name") or supplier_location.get("admin_area"),
            "location_verification": supplier_location.get("verification_status", "unknown"),
            "rainfall_evidence_status": "not_assessed",
        }
        lat, lon = supplier_location.get("latitude"), supplier_location.get("longitude")
        if lat is not None and lon is not None:
            try:
                supplier_request = HazardAssessmentRequest(
                    location=LocationInput(
                        latitude=lat, longitude=lon,
                        place_name=supplier_location.get("place_name"),
                        admin_area=supplier_location.get("admin_area"),
                    ),
                    hazard_types=["precipitation_extremes"],
                    years=payload.years,
                    include_unavailable=True,
                )
                supplier_assessment = build_hazard_assessment(supplier_request)
                rain_row = next(
                    (h.model_dump(mode="json") for h in supplier_assessment.hazards
                     if h.hazard_type == "precipitation_extremes"),
                    None,
                )
                if rain_row and rain_row.get("status") == "available":
                    rain_data = rain_row.get("evidence") or {}
                    rain_mm = rain_data.get("max_daily_precipitation_mm")
                    if isinstance(rain_mm, (int, float)) and not isinstance(rain_mm, bool) and 0 <= rain_mm <= 2000:
                        signal = round(min(100.0, float(rain_mm)), 2)
                        supplier_rain_signals.append(signal)
                        context["rainfall_evidence_status"] = "available"
                        context["max_daily_rainfall_mm"] = round(float(rain_mm), 2)
                        context["data_period"] = rain_row.get("data_period")
                        context["source"] = rain_row.get("source")
                        context["source_url"] = rain_row.get("source_url")
                        material_lower = material.lower()
                        wood_related = any(term in material_lower for term in ("wood", "timber", "lumber", "plywood", "veneer"))
                        if wood_related:
                            explanation = (
                                f"The supplier's weather data records a maximum daily rainfall of {rain_mm} mm "
                                f"at {context['location'] or 'the entered supplier location'} during the retrieved period. "
                                f"Because this supplier provides {material}, rain can make timber storage, drying, and transport harder to manage "
                                "when storage or transport is exposed. If wood stays damp, "
                                "it may develop mould or fungal decay, swell, warp, or crack; rain-related road or handling disruption "
                                "can also delay deliveries and interrupt furniture production. These are plausible risks, not proof that "
                                "this supplier's wood was wet, damaged, flooded, or delivered late."
                            )
                        else:
                            explanation = (
                                f"The supplier's weather data records a maximum daily rainfall of {rain_mm} mm at "
                                f"{context['location'] or 'the entered supplier location'}. Rain may disrupt this supplier's "
                                f"handling or transport of {material or 'the supplied material'}, but the available rainfall record "
                                "does not prove actual damage or a delivery delay."
                            )
                        result["evidence_items"].append({
                            "dimension": "supplier_climate_exposure",
                            "hazard_type": "precipitation_extremes",
                            "label": "Supplier rainfall exposure",
                            "observed_value": round(float(rain_mm), 2),
                            "unit": "mm in one day",
                            "plain_explanation": explanation,
                            "source": rain_row.get("source"),
                            "source_url": rain_row.get("source_url"),
                            "data_period": rain_row.get("data_period"),
                            "prototype_signal_score": signal,
                            "limitations": [
                                "Rainfall at the supplier location is not proof of flooding, timber moisture, mould, damage, or a delivery delay.",
                                "Wood condition, covered storage, kiln drying, road access, and supplier continuity records were not measured.",
                            ],
                        })
                else:
                    context["rainfall_evidence_status"] = "unavailable"
            except Exception as exc:
                context["rainfall_evidence_status"] = "unavailable"
                context["rainfall_error"] = type(exc).__name__
        else:
            context["rainfall_evidence_status"] = "missing_supplier_coordinates"
        supplier_context.append(context)

    result["supplier_context"] = supplier_context
    if supplier_rain_signals:
        supplier_climate_score = round(sum(supplier_rain_signals) / len(supplier_rain_signals), 2)
        result["dimensions"]["supplier_climate_exposure"] = {
            "score": supplier_climate_score,
            "status": "available",
            "signals_used": len(supplier_rain_signals),
            "explanation": (
                "Mean of maximum daily rainfall observations at supplier locations. This is an illustrative exposure proxy, "
                "not a flood probability, timber moisture measurement, or confirmed supply disruption."
            ),
        }
        base_dimensions = [
            value["score"] for name, value in result["dimensions"].items()
            if name in {"hazard_evidence", "operational_vulnerability", "supplier_dependency"}
            and value.get("score") is not None
        ]
        result["experimental_climate_risk_indicator"] = round(
            sum(base_dimensions + [supplier_climate_score]) / (len(base_dimensions) + 1), 2
        )
        result["warnings"].append(
            "Supplier rainfall exposure is included as an illustrative proxy only; it is not evidence of actual timber damage or delivery loss."
        )
    elif suppliers:
        result["warnings"].append(
            "Supplier-specific rainfall was not scored because supplier coordinates or valid rainfall observations were unavailable; missing data is not treated as safe."
        )

    # Demo-only translation of the climate indicator into a familiar 300–900 score range.
    # The baseline is an assumed demo input, not extracted from a Udyam certificate.
    climate_risk = result.get("experimental_climate_risk_indicator")
    if climate_risk is None:
        result["baseline_credit_score"] = payload.baseline_credit_score
        result["climate_penalty_points"] = None
        result["climate_adjusted_credit_score"] = None
        result["credit_score_band"] = "Insufficient evidence"
    else:
        # Small, symmetric demo adjustment around a neutral indicator of 50.
        # Higher-than-neutral risk lowers the score; lower-than-neutral risk raises it.
        adjustment = max(-25, min(25, round((float(climate_risk) - 50.0) * 0.5)))
        adjusted = max(300, min(900, payload.baseline_credit_score - adjustment))
        result["baseline_credit_score"] = payload.baseline_credit_score
        result["climate_adjustment_points"] = adjustment
        result["climate_penalty_points"] = max(0, adjustment)
        result["climate_uplift_points"] = max(0, -adjustment)
        result["climate_adjusted_credit_score"] = adjusted
        if adjusted < 550:
            band = "Poor"
        elif adjusted < 650:
            band = "Fair"
        elif adjusted < 750:
            band = "Good"
        else:
            band = "Excellent"
        result["credit_score_band"] = band
    result["credit_score_methodology"] = (
        "Demo-only mapping: adjustment = rounded (climate indicator − 50) × 0.5, bounded to −25..+25; "
        "adjusted score = baseline score − adjustment, bounded to 300–900. Indicators below 50 can raise the score; "
        "indicators above 50 can lower it. "
        "The baseline score is assumed for demonstration and is not supplied by Udyam. "
        "This range mapping is illustrative, not a validated lending model."
    )
    result["evidence_explanation"] = _build_evidence_explanation(
        result, payload.baseline_credit_score,
        result.get("climate_adjustment_points"), result.get("climate_adjusted_credit_score"),
    )
    return result

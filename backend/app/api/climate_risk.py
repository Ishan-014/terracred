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
        "risk_indicator": result.get("experimental_climate_risk_indicator"),
        "dimensions": {
            name: {"score": value.get("score"), "status": value.get("status"),
                   "explanation": value.get("explanation"), "sources": value.get("sources", [])}
            for name, value in dimensions.items()
        },
        "observed_hazard_evidence": result.get("evidence_items", []),
        "missing_inputs": result.get("missing_inputs", []),
        "warnings": result.get("warnings", []),
        "baseline_score": baseline,
        "penalty_points": penalty,
        "adjusted_score": adjusted,
    }
    fallback = {
        "summary": (
            f"The illustrative climate indicator is {evidence['risk_indicator']}/100. "
            f"The demo applies a {penalty}-point adjustment to baseline {baseline}, resulting in {adjusted}."
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
                        "You are TerraCred's evidence explainer. Explain only supplied structured evidence. "
                        "Never invent facts, sources, weather readings, causes, or credit history. "
                        "Distinguish measured evidence from illustrative prototype signals. Missing evidence is unknown, not safe. "
                        "Return JSON with keys summary (string), positive_factors (array), risk_factors (array), "
                        "evidence_limitations (array). State the adjustment is a demo heuristic, not a validated credit model."
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

    # Demo-only translation of the climate indicator into a familiar 300–900 score range.
    # The baseline is an assumed demo input, not extracted from a Udyam certificate.
    climate_risk = result.get("experimental_climate_risk_indicator")
    if climate_risk is None:
        result["baseline_credit_score"] = payload.baseline_credit_score
        result["climate_penalty_points"] = None
        result["climate_adjusted_credit_score"] = None
        result["credit_score_band"] = "Insufficient evidence"
    else:
        penalty = min(40, round(max(0.0, min(100.0, float(climate_risk))) * 0.5))
        adjusted = max(300, min(900, payload.baseline_credit_score - penalty))
        result["baseline_credit_score"] = payload.baseline_credit_score
        result["climate_penalty_points"] = penalty
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
        "Demo-only mapping: climate penalty = rounded climate indicator × 0.5 points, capped at 40; "
        "adjusted score = baseline score − penalty, bounded to 300–900. "
        "The baseline score is assumed for demonstration and is not supplied by Udyam. "
        "This range mapping is illustrative, not a validated lending model."
    )
    result["evidence_explanation"] = _build_evidence_explanation(
        result, payload.baseline_credit_score,
        result.get("climate_penalty_points"), result.get("climate_adjusted_credit_score"),
    )
    return result

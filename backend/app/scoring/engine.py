from __future__ import annotations

from typing import Any

MODEL_VERSION = "terracred-prototype-0.1"
METHODOLOGY = (
    "Experimental, rule-based prototype for demonstration only. Thresholds and equal "
    "dimension weighting are illustrative, not calibrated or scientifically validated. "
    "The result is not a conventional credit score or a lending recommendation."
)


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def _clamp_percent(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)


def calculate_climate_risk(
    business: dict[str, Any],
    suppliers: list[dict[str, Any]],
    vulnerability: dict[str, Any] | None,
    hazards: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build an explainable prototype indicator from existing evidence.

    Unknown or unsupported evidence is omitted from numeric calculations and reported.
    Weather-derived values are not interpreted as flood/property damage evidence.
    """
    warnings: list[str] = []
    missing: list[str] = []
    dimensions: dict[str, dict[str, Any]] = {}
    data_quality_checks: list[dict[str, Any]] = []

    def quality_check(name: str, passed: bool, detail: str, severity: str = "warning") -> None:
        data_quality_checks.append({
            "check": name,
            "status": "passed" if passed else severity,
            "detail": detail,
        })

    location = business.get("business_location") or {}
    lat = location.get("latitude")
    lon = location.get("longitude")
    valid_coordinates = (
        isinstance(lat, (int, float)) and not isinstance(lat, bool) and -90 <= lat <= 90
        and isinstance(lon, (int, float)) and not isinstance(lon, bool) and -180 <= lon <= 180
    )
    quality_check(
        "Business coordinates",
        valid_coordinates,
        "Coordinates are present and within valid latitude/longitude ranges."
        if valid_coordinates else "Missing or invalid coordinates; local weather evidence may be unavailable.",
        "blocking",
    )
    quality_check(
        "Business profile verification",
        business.get("verification_status") == "verified",
        "Business profile is marked verified." if business.get("verification_status") == "verified"
        else "Business profile is unverified; entered or extracted details may be incorrect.",
    )

    # Hazard dimension: only connected, available weather indicators contribute.
    hazard_signals: list[float] = []
    hazard_sources: list[dict[str, Any]] = []
    evidence_items: list[dict[str, Any]] = []
    for hazard in hazards:
        if hazard.get("status") != "available":
            warnings.append(
                f"{hazard.get('hazard_type', 'hazard')}: evidence status is "
                f"{hazard.get('status', 'unknown')}; not scored."
            )
            continue
        evidence = hazard.get("evidence") or {}
        kind = hazard.get("hazard_type")
        signal = None
        label = kind or "Weather evidence"
        observed_value = None
        unit = None
        plain_explanation = None
        try:
            if kind == "precipitation_extremes":
                value = evidence.get("max_daily_precipitation_mm")
                if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 2000:
                    observed_value, unit = round(float(value), 2), "mm in one day"
                    signal = _clamp_percent(float(value))
                    label = "Heavy rainfall"
                    plain_explanation = f"The highest recorded daily rainfall was {observed_value} mm. This can indicate heavy-rain exposure, but it does not prove flooding at the business."
            elif kind == "temperature_extremes":
                hot_days = evidence.get("hot_days_above_35c")
                observed = evidence.get("days_with_observations")
                if (isinstance(hot_days, (int, float)) and not isinstance(hot_days, bool)
                    and isinstance(observed, (int, float)) and not isinstance(observed, bool)
                    and observed > 0 and 0 <= hot_days <= observed):
                    observed_value = f"{int(hot_days)} of {int(observed)} observed days"
                    unit = "days"
                    signal = _clamp_percent(float(hot_days) / float(observed) * 100)
                    label = "Extreme heat"
                    plain_explanation = f"Temperatures exceeded 35°C on {int(hot_days)} of {int(observed)} observed days. This is a heat-stress signal, not a direct estimate of business loss."
            elif kind == "wind_extremes":
                value = evidence.get("max_daily_wind_speed_kmh")
                if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 500:
                    observed_value, unit = round(float(value), 2), "km/h"
                    signal = _clamp_percent(float(value))
                    label = "Strong wind"
                    plain_explanation = f"The highest recorded daily wind speed was {observed_value} km/h. Actual damage depends on the building and local conditions."
        except (TypeError, ValueError, OverflowError):
            signal = None

        if signal is None:
            quality_check(
                f"{kind or 'Hazard'} evidence",
                False,
                "Evidence is missing or outside expected numeric ranges, so it was excluded from scoring.",
            )
            warnings.append(f"{kind or 'Hazard'}: missing or invalid values; not scored.")
            continue

        quality_check(
            f"{kind} evidence",
            True,
            "Required observation is present and passed basic range checks.",
        )
        hazard_signals.append(signal)
        evidence_items.append({
            "dimension": "hazard_evidence",
            "hazard_type": kind,
            "label": label,
            "observed_value": observed_value,
            "unit": unit,
            "plain_explanation": plain_explanation,
            "source": hazard.get("source"),
            "source_url": hazard.get("source_url"),
            "data_period": hazard.get("data_period"),
            "prototype_signal_score": signal,
            "limitations": hazard.get("limitations", []),
        })
        hazard_sources.append({
                "hazard_type": kind,
                "source": hazard.get("source"),
                "source_url": hazard.get("source_url"),
                "data_period": hazard.get("data_period"),
                "units": hazard.get("units"),
                "matching_method": hazard.get("matching_method"),
            })
    hazard_score = _mean(hazard_signals)
    dimensions["hazard_evidence"] = {
        "score": hazard_score,
        "status": "available" if hazard_score is not None else "insufficient_evidence",
        "signals_used": len(hazard_signals),
        "explanation": (
            "Mean of available weather-derived prototype signals; this is not a flood map "
            "or property-damage probability."
            if hazard_score is not None else
            "No supported, available weather indicators could be scored."
        ),
        "sources": hazard_sources,
    }
    if hazard_score is None:
        missing.append("No supported hazard evidence was available for numeric scoring.")
    quality_check(
        "Climate evidence availability",
        hazard_score is not None,
        "At least one valid weather indicator was available." if hazard_score is not None
        else "No valid weather indicator was available; local climate evidence is missing.",
    )

    # Operational vulnerability: score only known answers, with transparent ratios.
    vulnerability_signals: list[float] = []
    if vulnerability:
        operations = vulnerability.get("critical_operations") or []
        inputs = vulnerability.get("critical_inputs") or []
        known_fallback = [x for x in operations if x.get("fallback_available") is not None]
        if known_fallback:
            vulnerability_signals.append(
                sum(1 for x in known_fallback if x.get("fallback_available") is False)
                / len(known_fallback) * 100
            )
        known_substitute = [x for x in inputs if x.get("substitute_available") is not None]
        if known_substitute:
            vulnerability_signals.append(
                sum(1 for x in known_substitute if x.get("substitute_available") is False)
                / len(known_substitute) * 100
            )
        if not operations:
            missing.append("No critical operations are documented.")
        if not inputs:
            missing.append("No critical inputs are documented.")
    else:
        missing.append("No operational vulnerability record exists.")
    vulnerability_score = _mean(vulnerability_signals)
    dimensions["operational_vulnerability"] = {
        "score": vulnerability_score,
        "status": "available" if vulnerability_score is not None else "insufficient_evidence",
        "signals_used": len(vulnerability_signals),
        "explanation": (
            "Share of documented operations without fallback and critical inputs without substitutes."
            if vulnerability_score is not None else
            "Not enough known fallback/substitution answers to calculate this dimension."
        ),
    }

    # Supplier dependency: use known procurement shares and known lack of alternatives.
    supplier_signals: list[float] = []
    known_shares = [
        float(s["procurement_share"]) for s in suppliers
        if isinstance(s.get("procurement_share"), (int, float))
        and 0 <= float(s["procurement_share"]) <= 100
    ]
    if known_shares:
        supplier_signals.append(max(known_shares))
    known_critical = [
        s for s in suppliers
        if s.get("critical_to_operations") is True
        and s.get("alternative_supplier_available") is not None
    ]
    if known_critical:
        supplier_signals.append(
            sum(1 for s in known_critical if s.get("alternative_supplier_available") is False)
            / len(known_critical) * 100
        )
    supplier_score = _mean(supplier_signals)
    dimensions["supplier_dependency"] = {
        "score": supplier_score,
        "status": "available" if supplier_score is not None else "insufficient_evidence",
        "signals_used": len(supplier_signals),
        "supplier_count": len(suppliers),
        "unverified_or_unknown_suppliers": sum(
            1 for s in suppliers if s.get("verification_status") != "verified"
        ),
        "explanation": (
            "Mean of the largest recorded procurement share and the known share of critical "
            "suppliers without alternatives. This does not establish a supplier's climate exposure."
            if supplier_score is not None else
            "Supplier concentration or alternative-supplier evidence is not sufficiently documented."
        ),
    }
    if not suppliers:
        missing.append("No supplier relationships are recorded.")
    elif any(s.get("verification_status") != "verified" for s in suppliers):
        warnings.append("Some supplier relationships are unverified or have unknown verification status.")
    quality_check(
        "Supplier information",
        bool(suppliers) and all(s.get("verification_status") == "verified" for s in suppliers),
        "Supplier records are present and verified." if suppliers and all(s.get("verification_status") == "verified" for s in suppliers)
        else "Supplier details are missing or unverified; supplier findings are provisional.",
    )

    # Evidence quality is reported separately and is not treated as a risk score.
    verification_values = []
    business_verification = business.get("verification_status")
    if business_verification is not None:
        verification_values.append(1.0 if business_verification == "verified" else 0.0)
    location = business.get("business_location") or {}
    if location:
        verification_values.append(1.0 if location.get("verification_status") == "verified" else 0.0)
    for supplier in suppliers:
        verification_values.append(1.0 if supplier.get("verification_status") == "verified" else 0.0)
    data_quality_pct = round(sum(verification_values) / len(verification_values) * 100, 2) if verification_values else None
    dimensions["evidence_quality"] = {
        "score": None,
        "verification_coverage_pct": data_quality_pct,
        "status": "available" if data_quality_pct is not None else "insufficient_evidence",
        "explanation": "Verification coverage is a data-quality indicator, not a risk score.",
    }

    available_scores = [
        item["score"] for key, item in dimensions.items()
        if key in {"hazard_evidence", "operational_vulnerability", "supplier_dependency"}
        and item.get("score") is not None
    ]
    overall_score = _mean(available_scores)
    overall_status = "experimental_indicator" if overall_score is not None else "insufficient_evidence"
    if overall_score is not None and len(available_scores) < 3:
        warnings.append("Overall indicator uses only available dimensions; missing dimensions were not assumed safe.")
    if overall_score is not None and (hazard_score is None or not valid_coordinates):
        warnings.append("The overall indicator is provisional because valid location-based climate evidence is missing.")
    warnings.append("Prototype weights and thresholds are illustrative and have not been scientifically validated.")
    warnings.append("Climate-risk output must not replace conventional credit assessment or automatically decide lending.")

    return {
        "business_id": business.get("business_id"),
        "business_name": business.get("business_name"),
        "model_version": MODEL_VERSION,
        "methodology": METHODOLOGY,
        "status": overall_status,
        "experimental_climate_risk_indicator": overall_score,
        "dimensions": dimensions,
        "evidence_items": evidence_items,
        "data_quality": {
            "status": "needs_review" if any(item["status"] in {"warning", "blocking"} for item in data_quality_checks) else "passed",
            "checks": data_quality_checks,
            "issue_count": sum(1 for item in data_quality_checks if item["status"] in {"warning", "blocking"}),
            "summary": (
                "Some information is missing, invalid, or unverified. Treat this result as provisional."
                if any(item["status"] in {"warning", "blocking"} for item in data_quality_checks)
                else "Basic data checks passed. The model is still an experimental prototype."
            ),
        },
        "missing_inputs": sorted(set(missing)),
        "warnings": warnings,
        "conventional_credit_score": None,
        "lending_decision": None,
    }

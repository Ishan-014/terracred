from backend.app.scoring.engine import calculate_climate_risk


def test_missing_evidence_does_not_become_low_risk():
    result = calculate_climate_risk(
        business={"business_id": "synthetic-1", "business_name": "Synthetic Example", "verification_status": "unknown"},
        suppliers=[],
        vulnerability=None,
        hazards=[],
    )
    assert result["status"] == "insufficient_evidence"
    assert result["experimental_climate_risk_indicator"] is None
    assert result["dimensions"]["hazard_evidence"]["score"] is None
    assert result["dimensions"]["operational_vulnerability"]["score"] is None
    assert result["dimensions"]["supplier_dependency"]["score"] is None
    assert result["conventional_credit_score"] is None
    assert result["lending_decision"] is None


def test_scoring_is_deterministic_and_explained():
    business = {
        "business_id": "synthetic-2",
        "business_name": "Synthetic Example",
        "verification_status": "verified",
        "business_location": {"verification_status": "verified"},
    }
    suppliers = [{
        "supplier_name": "Synthetic Supplier",
        "procurement_share": 60,
        "critical_to_operations": True,
        "alternative_supplier_available": False,
        "verification_status": "unverified",
    }]
    vulnerability = {
        "critical_operations": [{"fallback_available": False}],
        "critical_inputs": [{"substitute_available": False}],
    }
    hazards = [{
        "hazard_type": "precipitation_extremes",
        "status": "available",
        "source": "Synthetic test fixture",
        "source_url": None,
        "data_period": None,
        "units": {"precipitation_sum": "mm"},
        "matching_method": "test_fixture",
        "evidence": {"max_daily_precipitation_mm": 40},
    }]
    first = calculate_climate_risk(business, suppliers, vulnerability, hazards)
    second = calculate_climate_risk(business, suppliers, vulnerability, hazards)
    assert first == second
    assert first["status"] == "experimental_indicator"
    assert first["experimental_climate_risk_indicator"] is not None
    assert first["dimensions"]["operational_vulnerability"]["score"] == 100
    assert first["dimensions"]["supplier_dependency"]["score"] == 80
    assert first["conventional_credit_score"] is None
    assert first["lending_decision"] is None


def test_unavailable_hazard_is_not_scored():
    result = calculate_climate_risk(
        business={"business_id": "synthetic-3", "verification_status": "unknown"},
        suppliers=[],
        vulnerability=None,
        hazards=[{"hazard_type": "flood_hazard", "status": "not_supported", "evidence": {}}],
    )
    assert result["dimensions"]["hazard_evidence"]["score"] is None
    assert any("not_supported" in warning for warning in result["warnings"])

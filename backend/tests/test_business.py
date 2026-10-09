from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend.app.business.models import BusinessProfile
from backend.app.business.store import get_store
from backend.app.main import app

client = TestClient(app)


def test_create_and_read_business_profile():
    payload = {
        "business_name": "GreenRiver Foods",
        "industry": "Food processing",
        "business_activity": "Rice milling and packaging",
        "business_location": {
            "latitude": 12.5,
            "longitude": 77.5,
            "place_name": "Bengaluru",
            "verification_status": "verified",
        },
        "main_activities": ["rice milling", "packing"],
        "critical_raw_materials": ["rice", "packaging film"],
        "operational_dependencies": ["power", "water supply"],
        "evidence": [
            {
                "title": "Owner-provided business details",
                "source": "user_input",
                "verification_status": "verified",
            }
        ],
        "verification_status": "verified",
    }

    created = client.post("/api/businesses", json=payload)
    assert created.status_code == 201
    created_json = created.json()
    assert created_json["business_name"] == "GreenRiver Foods"
    assert created_json["business_id"]

    profile = client.get(f"/api/businesses/{created_json['business_id']}")
    assert profile.status_code == 200
    assert profile.json()["industry"] == "Food processing"


def test_business_profile_validation_and_invalid_coordinates():
    invalid_lat = client.post(
        "/api/businesses",
        json={
            "business_name": "Bad Location",
            "industry": "Textiles",
            "business_location": {"latitude": 91, "longitude": 77.5},
        },
    )
    assert invalid_lat.status_code == 422

    validation = client.post(
        "/api/businesses/validate",
        json={
            "business_name": "",
            "industry": "",
            "business_location": {"latitude": 12.5, "longitude": 77.5},
        },
    )
    assert validation.status_code == 200
    body = validation.json()
    assert body["valid"] is False
    assert "business_name" in body["missing_fields"]
    assert "industry" in body["missing_fields"]


def test_business_supplier_creation_and_dependency_summary():
    business = client.post(
        "/api/businesses",
        json={
            "business_name": "Supply Test Ltd.",
            "industry": "Food distribution",
            "business_location": {"latitude": 11.0, "longitude": 76.0},
            "main_activities": ["distribution"],
            "critical_raw_materials": ["rice"],
            "operational_dependencies": ["cold storage"],
            "verification_status": "unverified",
        },
    )
    business_id = business.json()["business_id"]

    supplier = client.post(
        f"/api/businesses/{business_id}/suppliers",
        json={
            "supplier_name": "North Agro Traders",
            "supplier_location": {
                "latitude": 13.0,
                "longitude": 78.0,
                "verification_status": "verified",
            },
            "material_supplied": "rice",
            "critical_to_operations": True,
            "procurement_share": 60,
            "alternative_supplier_available": False,
            "substitution_time_days": 14,
            "verification_status": "verified",
        },
    )
    assert supplier.status_code == 201

    suppliers = client.get(f"/api/businesses/{business_id}/suppliers")
    assert suppliers.status_code == 200
    assert len(suppliers.json()["suppliers"]) == 1

    summary = client.get(f"/api/businesses/{business_id}/dependencies")
    assert summary.status_code == 200
    body = summary.json()
    assert body["total_known_suppliers"] == 1
    assert body["critical_material_count"] == 1
    assert body["critical_materials_without_alternative"] == 1
    assert body["largest_supplier_share_of_total_pct"] == 100.0


def test_update_business_profile_and_supplier_share_validation():
    created = client.post(
        "/api/businesses",
        json={
            "business_name": "Update Test",
            "industry": "Textiles",
            "business_location": {"latitude": 10.0, "longitude": 72.0},
            "verification_status": "unknown",
        },
    )
    business_id = created.json()["business_id"]

    updated = client.put(
        f"/api/businesses/{business_id}",
        json={"business_name": "Update Test Revised", "verification_status": "verified"},
    )
    assert updated.status_code == 200
    assert updated.json()["business_name"] == "Update Test Revised"

    bad_supplier = client.post(
        f"/api/businesses/{business_id}/suppliers",
        json={
            "supplier_name": "Bad Share",
            "material_supplied": "cotton",
            "procurement_share": 150,
        },
    )
    assert bad_supplier.status_code == 400
    assert "procurement_share" in bad_supplier.json()["detail"]


def test_missing_information_is_reported_without_score_creation():
    business = client.post(
        "/api/businesses",
        json={
            "business_name": "Sparse Data Co.",
            "industry": "Agriculture",
            "main_activities": ["farming"],
        },
    )
    assert business.status_code == 201
    profile = business.json()

    dependency_summary = client.get(f"/api/businesses/{profile['business_id']}/dependencies")
    assert dependency_summary.status_code == 200
    summary = dependency_summary.json()
    assert summary["total_known_suppliers"] == 0
    assert summary["critical_materials_without_alternative"] == 0


def test_business_store_persists_across_store_reinitialization(tmp_path, monkeypatch):
    database_path = tmp_path / "terracred-persist.db"
    monkeypatch.setenv("TERRACRED_DB_PATH", str(database_path))
    store = get_store(refresh=True)

    business = store.create_business(
        BusinessProfile(
            business_id="persist-business",
            business_name="Persisted Co.",
            industry="Manufacturing",
            business_location={"latitude": 11.0, "longitude": 78.0},
            main_activities=["assembly"],
            critical_raw_materials=["steel"],
            operational_dependencies=["power"],
            evidence=[],
            verification_status="verified",
        )
    )
    assert store.get_business("persist-business") is not None

    store_2 = get_store(refresh=True)
    restored = store_2.get_business("persist-business")
    assert restored is not None
    assert restored.business_name == "Persisted Co."

    business_client = client.post(
        "/api/businesses",
        json={
            "business_name": "Transient Co.",
            "industry": "Textiles",
            "business_location": {"latitude": 20.0, "longitude": 75.0},
            "verification_status": "unverified",
        },
    )
    assert business_client.status_code == 201


def test_operational_vulnerability_summary_and_hazard_assessment():
    from unittest.mock import patch

    business = client.post(
        "/api/businesses",
        json={
            "business_name": "Ops Vulnerability Co.",
            "industry": "Food processing",
            "business_location": {"latitude": 12.0, "longitude": 77.0},
            "main_activities": ["milling"],
            "critical_raw_materials": ["rice"],
            "operational_dependencies": ["power"],
            "verification_status": "verified",
        },
    )
    business_id = business.json()["business_id"]

    vulnerability = client.post(
        f"/api/businesses/{business_id}/operational-vulnerability",
        json={
            "critical_operations": [
                {
                    "operation_name": "Rice milling",
                    "fallback_available": False,
                    "recovery_time_days": 7,
                    "verification_status": "verified",
                }
            ],
            "critical_inputs": [
                {
                    "material_or_service": "rice",
                    "critical_to_operations": True,
                    "inventory_days": 12,
                    "substitute_available": False,
                    "verification_status": "verified",
                }
            ],
            "continuity_measures": ["generator backup"],
            "historical_disruptions": [
                {"event_type": "power outage", "days_lost": 3, "verification_status": "verified"}
            ],
            "evidence": [{"title": "Utility check", "source": "user_input", "verification_status": "verified"}],
        },
    )
    assert vulnerability.status_code == 201

    summary = client.get(f"/api/businesses/{business_id}/operational-vulnerability/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["critical_operations_without_fallback"] == 1
    assert body["critical_inputs_without_substitute"] == 1
    assert body["known_inventory_entries"] == 1
    assert body["recovery_time_coverage_pct"] == 100.0

    with patch("backend.app.hazards.providers.get_climate_history") as mock_get_climate_history:
        mock_get_climate_history.return_value = {
            "source": "mocked",
            "latitude": 12.0,
            "longitude": 77.0,
            "timezone": "UTC",
            "units": {
                "precipitation_sum": "mm",
                "temperature_2m_max": "°C",
                "temperature_2m_min": "°C",
                "wind_speed_10m_max": "km/h",
            },
            "daily": {
                "time": ["2024-01-01", "2024-01-02"],
                "precipitation_sum": [5.0, 7.0],
                "temperature_2m_max": [30.0, 33.0],
                "temperature_2m_min": [18.0, 15.0],
                "wind_speed_10m_max": [30.0, 24.0],
            },
            "period": {"start": "2024-01-01", "end": "2024-01-02", "requested_years": 1, "days_returned": 2},
        }
        hazard = client.post(
            f"/api/businesses/{business_id}/hazard-assessment",
            json={"hazard_types": ["temperature_extremes"], "years": 5, "include_unavailable": True},
        )

    assert hazard.status_code == 200
    payload = hazard.json()
    assert payload["requested_location"]["latitude"] == 12.0
    assert any(item["hazard_type"] == "temperature_extremes" for item in payload["hazards"])

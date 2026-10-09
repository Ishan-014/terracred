from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.hazards.assessment import build_hazard_assessment
from backend.app.hazards.location import LocationInput
from backend.app.hazards.schemas import HazardAssessmentRequest
from backend.app.main import app

client = TestClient(app)


@pytest.fixture
def sample_historical_weather():
    return {
        "source": "Open-Meteo Historical Archive API",
        "latitude": 12.5,
        "longitude": 77.5,
        "timezone": "UTC",
        "units": {
            "precipitation_sum": "mm",
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "wind_speed_10m_max": "km/h",
        },
        "daily": {
            "time": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "precipitation_sum": [10.0, 25.0, 12.0],
            "temperature_2m_max": [30.0, 38.0, 32.0],
            "temperature_2m_min": [18.0, 4.0, 12.0],
            "wind_speed_10m_max": [20.0, 42.0, 38.0],
        },
        "period": {
            "start": "2024-01-01",
            "end": "2024-01-03",
            "requested_years": 1,
            "days_returned": 3,
        },
    }


def test_location_validation():
    valid = LocationInput(latitude=12.5, longitude=77.5)
    assert valid.latitude == 12.5

    with pytest.raises(ValidationError):
        LocationInput(latitude=91, longitude=77.5)

    with pytest.raises(ValidationError):
        LocationInput(latitude=12.5, longitude=181)


def test_build_hazard_assessment_for_open_meteo_provider(sample_historical_weather):
    with patch("backend.app.hazards.providers.get_climate_history") as mock_get_climate_history:
        mock_get_climate_history.return_value = sample_historical_weather

        request = HazardAssessmentRequest(
            location=LocationInput(latitude=12.5, longitude=77.5),
            hazard_types=["precipitation_extremes", "temperature_extremes", "wind_extremes"],
            years=1,
        )

        result = build_hazard_assessment(request)

    assert result.assessment_status == "complete"
    assert result.hazards[0].hazard_type == "precipitation_extremes"
    assert result.hazards[0].status == "available"
    assert result.hazards[0].evidence["max_daily_precipitation_mm"] == 25.0
    assert result.hazards[1].evidence["hot_days_above_35c"] == 1
    assert result.hazards[2].evidence["max_daily_wind_speed_kmh"] == 42.0


def test_unknown_or_unavailable_hazard_types_are_handled():
    request = HazardAssessmentRequest(
        location=LocationInput(latitude=12.5, longitude=77.5),
        hazard_types=["nonexistent_hazard"],
    )

    result = build_hazard_assessment(request)
    assert result.hazards[0].status == "not_supported"

    request_2 = HazardAssessmentRequest(
        location=LocationInput(latitude=12.5, longitude=77.5),
        hazard_types=["flood_hazard"],
    )

    result_2 = build_hazard_assessment(request_2)
    assert result_2.hazards[0].status == "unavailable"


def test_hazard_assessment_endpoint_with_mocked_provider():
    with patch("backend.app.hazards.providers.get_climate_history") as mock_get_climate_history:
        mock_get_climate_history.return_value = {
            "source": "Open-Meteo Historical Archive API",
            "latitude": 12.5,
            "longitude": 77.5,
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
            "period": {
                "start": "2024-01-01",
                "end": "2024-01-02",
                "requested_years": 1,
                "days_returned": 2,
            },
        }

        response = client.post(
            "/api/hazards/assess",
            json={
                "location": {"latitude": 12.5, "longitude": 77.5},
                "hazard_types": ["precipitation_extremes"],
                "years": 1,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["hazards"][0]["hazard_type"] == "precipitation_extremes"
    assert payload["hazards"][0]["status"] == "available"


def test_provider_timeout_and_malformed_data_are_reported_cleanly():
    with patch("backend.app.hazards.providers.get_climate_history", side_effect=TimeoutError("timed out")):
        request = HazardAssessmentRequest(
            location=LocationInput(latitude=12.5, longitude=77.5),
            hazard_types=["precipitation_extremes"],
        )
        result = build_hazard_assessment(request)

    assert result.hazards[0].status == "unavailable"
    assert "timed out" in result.hazards[0].limitations[0]

    with patch("backend.app.hazards.providers.get_climate_history", return_value={"daily": "bad"}):
        request = HazardAssessmentRequest(
            location=LocationInput(latitude=12.5, longitude=77.5),
            hazard_types=["wind_extremes"],
        )
        result_b = build_hazard_assessment(request)

    assert result_b.hazards[0].status == "unavailable"


def test_list_hazard_types_endpoint():
    response = client.get("/api/hazards")
    assert response.status_code == 200
    payload = response.json()
    assert "precipitation_extremes" in payload["hazard_types"]
    assert "flood_hazard" in payload["hazard_types"]

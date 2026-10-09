from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.data.open_meteo import get_climate_history, get_weather
from backend.app.data.weather_features import calculate_weather_features
from backend.app.main import app

client = TestClient(app)


@pytest.fixture
def sample_weather_payload():
    return {
        "source": "Open-Meteo Forecast API",
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
            "precipitation_sum": [1.0, 2.5, None],
            "temperature_2m_max": [20.0, 22.0, 18.5],
            "temperature_2m_min": [10.0, 11.5, None],
            "wind_speed_10m_max": [30.0, 28.0, 35.5],
        },
    }


def test_root_and_health_endpoints():
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["status"] == "running"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "healthy"


def test_weather_forecast_route_schema(sample_weather_payload):
    with patch("backend.app.api.weather.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = sample_weather_payload
        mock_get.return_value = mock_response

        response = client.get("/api/weather/forecast?latitude=12.5&longitude=77.5&days=3")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "Open-Meteo Forecast API"
    assert payload["daily"]["time"] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert payload["timezone"] == "UTC"


def test_climate_history_route_schema_and_period(sample_weather_payload):
    with patch("backend.app.api.weather.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = sample_weather_payload

        response = client.get("/api/weather/climate-history?latitude=12.5&longitude=77.5&years=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "Open-Meteo Historical Archive API"
    assert "period" in payload
    assert payload["period"]["requested_years"] == 2
    assert payload["period"]["days_returned"] == 3


def test_weather_feature_climate_history_route(sample_weather_payload):
    with patch("backend.app.api.weather_features.requests.get") as mock_get:
        mock_get.return_value.raise_for_status.return_value = None
        mock_get.return_value.json.return_value = sample_weather_payload

        response = client.get("/api/weather-features/climate-history?latitude=12.5&longitude=77.5&years=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["features"]["maximum_daily_temperature"]["value"] == 22.0


def test_invalid_coordinates_and_periods():
    with pytest.raises(ValueError, match="Latitude"):
        get_weather(91, 0, 3)

    with pytest.raises(ValueError, match="Longitude"):
        get_weather(0, 181, 3)

    with pytest.raises(ValueError, match="Forecast days"):
        get_weather(20, 20, 0)

    with pytest.raises(ValueError, match="Years"):
        get_climate_history(20, 20, 0)

    with pytest.raises(ValueError, match="Years"):
        get_climate_history(20, 20, 31)


def test_calculate_weather_features_known_values(sample_weather_payload):
    summary = calculate_weather_features(sample_weather_payload)

    assert summary["features"]["total_precipitation"]["value"] == 3.5
    assert summary["features"]["maximum_daily_temperature"]["value"] == 22.0
    assert summary["features"]["minimum_daily_temperature"]["value"] == 10.0
    assert summary["features"]["maximum_daily_wind_speed"]["value"] == 35.5
    assert summary["features"]["total_precipitation"]["valid_days"] == 2
    assert summary["period"]["days_returned"] == 3


def test_missing_daily_fields_are_handled():
    empty_weather = {
        "source": "Open-Meteo Historical Archive API",
        "latitude": 1.0,
        "longitude": 2.0,
        "timezone": "UTC",
        "units": {},
        "daily": {"time": []},
    }

    with pytest.raises(ValueError, match="no daily dates"):
        calculate_weather_features(empty_weather)


def test_http_errors_and_malformed_responses():
    with patch("backend.app.data.open_meteo.requests.get", side_effect=TimeoutError("timed out")):
        with pytest.raises(TimeoutError):
            get_weather(10, 20, 3)

    with patch("backend.app.data.open_meteo.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = RuntimeError("server error")
        mock_get.return_value = mock_response
        with pytest.raises(RuntimeError):
            get_weather(10, 20, 3)

    with patch("backend.app.data.open_meteo.requests.get") as mock_get:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"daily": "bad payload"}
        mock_get.return_value = mock_response
        result = get_weather(10, 20, 3)
        assert result["daily"] == {}


def test_leap_year_range_handling():
    end_date = date(2024, 3, 1)
    start_date = end_date.replace(year=end_date.year - 1)
    assert start_date == date(2023, 3, 1)

    leap_end = date(2024, 2, 29)
    with pytest.raises(ValueError):
        leap_end.replace(year=leap_end.year - 1)

    start_before_leap = leap_end.replace(year=leap_end.year - 1, day=28)
    assert start_before_leap == date(2023, 2, 28)


def test_api_route_rejects_invalid_query_values():
    invalid_lat = client.get("/api/weather/forecast?latitude=91&longitude=20&days=3")
    invalid_days = client.get("/api/weather/forecast?latitude=20&longitude=20&days=8")
    invalid_years = client.get("/api/weather/climate-history?latitude=20&longitude=20&years=31")

    assert invalid_lat.status_code == 422
    assert invalid_days.status_code == 422
    assert invalid_years.status_code == 422

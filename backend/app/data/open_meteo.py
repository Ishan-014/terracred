
from datetime import date, timedelta
from typing import Any

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARIABLES = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
]


def _validate_coordinates(latitude: float, longitude: float) -> None:
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")


def _normalise_daily_payload(data: Any) -> dict[str, Any]:
    daily = data.get("daily") if isinstance(data, dict) else {}
    if not isinstance(daily, dict):
        return {}
    return daily


def _fetch_archive(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
) -> dict:
    """Fetch daily weather observations for an explicit date range."""

    if start_date > end_date:
        raise ValueError("Start date must not be after end date.")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY_VARIABLES,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "UTC",
    }

    response = requests.get(
        ARCHIVE_URL,
        params=params,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    daily = _normalise_daily_payload(data)

    return {
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "units": data.get("daily_units", {}),
        "daily": daily,
    }


def get_weather(
    latitude: float,
    longitude: float,
    days: int = 7,
) -> dict:
    """Fetch forecast data for a business or supplier location."""

    _validate_coordinates(latitude, longitude)

    if not 1 <= days <= 7:
        raise ValueError("Forecast days must be between 1 and 7.")

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY_VARIABLES,
        "forecast_days": days,
        "timezone": "UTC",
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    daily = _normalise_daily_payload(data)

    return {
        "source": "Open-Meteo Forecast API",
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "timezone": data.get("timezone"),
        "units": data.get("daily_units", {}),
        "daily": daily,
    }


def get_historical_weather(
    latitude: float,
    longitude: float,
    days: int = 30,
) -> dict:
    """Fetch recent historical weather observations."""

    _validate_coordinates(latitude, longitude)

    if not 1 <= days <= 365:
        raise ValueError("Historical days must be between 1 and 365.")

    # Leave a five-day buffer for archive data availability.
    end_date = date.today() - timedelta(days=5)
    start_date = end_date - timedelta(days=days - 1)

    result = _fetch_archive(
        latitude,
        longitude,
        start_date,
        end_date,
    )

    return {
        "source": "Open-Meteo Historical Archive API",
        **result,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    }


def get_climate_history(
    latitude: float,
    longitude: float,
    years: int = 10,
) -> dict:
    """
    Fetch multiple years of daily historical weather observations.

    This provides historical context, not a validated climate normal.
    """

    _validate_coordinates(latitude, longitude)

    if not 1 <= years <= 30:
        raise ValueError("Years must be between 1 and 30.")

    end_date = date.today() - timedelta(days=5)

    try:
        start_date = end_date.replace(year=end_date.year - years)
    except ValueError:
        start_date = end_date.replace(
            year=end_date.year - years,
            day=28,
        )

    result = _fetch_archive(
        latitude,
        longitude,
        start_date,
        end_date,
    )

    daily = result.get("daily", {})
    dates = daily.get("time", []) if isinstance(daily, dict) else []

    return {
        "source": "Open-Meteo Historical Archive API",
        **result,
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "requested_years": years,
            "days_returned": len(dates),
        },
        "limitations": [
            "Historical observations are not automatically validated climate normals.",
            "Archive coverage and completeness must be checked before scoring.",
            "Weather observations alone do not establish property-level flood damage.",
        ],
    }


from typing import Any


def calculate_weather_features(weather: dict[str, Any]) -> dict[str, Any]:
    """Convert Open-Meteo daily observations into transparent summary features."""

    daily = weather.get("daily", {})
    units = weather.get("units", {})

    dates = daily.get("time", [])
    rainfall = daily.get("precipitation_sum", [])
    max_temp = daily.get("temperature_2m_max", [])
    min_temp = daily.get("temperature_2m_min", [])
    max_wind = daily.get("wind_speed_10m_max", [])

    if not dates:
        raise ValueError("Weather response contains no daily dates.")

    def valid_values(values):
        return [
            float(value)
            for value in values
            if value is not None
        ]

    rain_values = valid_values(rainfall)
    high_temps = valid_values(max_temp)
    low_temps = valid_values(min_temp)
    wind_values = valid_values(max_wind)

    return {
        "source": weather.get("source", "Unknown"),
        "location": {
            "latitude": weather.get("latitude"),
            "longitude": weather.get("longitude"),
        },
        "period": {
            "start": dates[0],
            "end": dates[-1],
            "days_returned": len(dates),
        },
        "features": {
            "total_precipitation": {
                "value": round(sum(rain_values), 2) if rain_values else None,
                "unit": units.get("precipitation_sum"),
                "valid_days": len(rain_values),
            },
            "maximum_daily_temperature": {
                "value": max(high_temps) if high_temps else None,
                "unit": units.get("temperature_2m_max"),
                "valid_days": len(high_temps),
            },
            "minimum_daily_temperature": {
                "value": min(low_temps) if low_temps else None,
                "unit": units.get("temperature_2m_min"),
                "valid_days": len(low_temps),
            },
            "maximum_daily_wind_speed": {
                "value": max(wind_values) if wind_values else None,
                "unit": units.get("wind_speed_10m_max"),
                "valid_days": len(wind_values),
            },
        },
        "limitations": [
            "Weather summaries are not equivalent to a validated climate-risk score.",
            "Missing observations are excluded and reported through valid_days.",
            "Location-level weather data does not prove that a specific property was flooded or damaged.",
        ],
    }

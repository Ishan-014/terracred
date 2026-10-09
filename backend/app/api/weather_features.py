
from fastapi import APIRouter, HTTPException, Query
import requests

from backend.app.data.open_meteo import (
    get_climate_history,
    get_historical_weather,
    get_weather,
)
from backend.app.data.weather_features import calculate_weather_features

router = APIRouter(
    prefix="/api/weather-features",
    tags=["Weather Features"],
)


@router.get("/forecast")
def forecast_features(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days: int = Query(7, ge=1, le=7),
):
    try:
        weather = get_weather(latitude, longitude, days)
        return calculate_weather_features(weather)
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to process forecast data: {exc}",
        ) from exc


@router.get("/historical")
def historical_features(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days: int = Query(30, ge=1, le=365),
):
    try:
        weather = get_historical_weather(latitude, longitude, days)
        return calculate_weather_features(weather)
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to process historical data: {exc}",
        ) from exc


@router.get("/climate-history")
def climate_history_features(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    years: int = Query(10, ge=1, le=30),
):
    try:
        weather = get_climate_history(latitude, longitude, years)
        return calculate_weather_features(weather)
    except (requests.RequestException, ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to process climate history data: {exc}",
        ) from exc


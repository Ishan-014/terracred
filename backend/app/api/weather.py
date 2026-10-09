
from fastapi import APIRouter, HTTPException, Query
import requests

from backend.app.data.open_meteo import (
    get_climate_history,
    get_historical_weather,
    get_weather,
)

router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.get("/forecast")
def weather_forecast(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days: int = Query(7, ge=1, le=7),
):
    try:
        return get_weather(latitude, longitude, days)
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/historical")
def historical_weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    days: int = Query(30, ge=1, le=365),
):
    try:
        return get_historical_weather(latitude, longitude, days)
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/climate-history")
def climate_history_weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    years: int = Query(10, ge=1, le=30),
):
    try:
        return get_climate_history(latitude, longitude, years)
    except (requests.RequestException, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.hazards.assessment import build_hazard_assessment
from backend.app.hazards.schemas import HazardAssessmentRequest

router = APIRouter(prefix="/api/hazards", tags=["Hazards"])


@router.get("")
def list_hazard_types():
    return {
        "hazard_types": [
            "precipitation_extremes",
            "temperature_extremes",
            "wind_extremes",
            "flood_hazard",
            "inundation_hazard",
            "population_flood_exposure",
            "flood_exposure",
        ],
        "note": "Open-Meteo weather-derived indicators are connected; flood hazard map providers are documented but not yet connected to a live geospatial lookup.",
    }


@router.post("/assess")
def assess_hazards(request: HazardAssessmentRequest):
    try:
        return build_hazard_assessment(request).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=500,
            detail=f"Hazard assessment failed: {exc}",
        ) from exc

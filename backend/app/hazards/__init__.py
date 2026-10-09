"""Hazard evidence modules for TerraCred."""

from backend.app.hazards.assessment import build_hazard_assessment
from backend.app.hazards.location import LocationInput
from backend.app.hazards.schemas import HazardAssessmentRequest, HazardAssessmentResponse, HazardEvidence

__all__ = [
    "HazardAssessmentRequest",
    "HazardAssessmentResponse",
    "HazardEvidence",
    "LocationInput",
    "build_hazard_assessment",
]

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.hazards.location import LocationInput, ResolvedLocation


class HazardEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hazard_type: str
    status: str = "available"
    source: str
    source_url: str | None = None
    retrieval_time: str
    coordinates: dict[str, float]
    spatial_resolution: str | None = None
    temporal_resolution: str | None = None
    data_period: dict[str, str | None] | None = None
    units: dict[str, str] | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    interpretation: str | None = None
    completeness: str = "partial"
    confidence: str = "medium"
    matching_method: str = "point_lookup"
    limitations: list[str] = Field(default_factory=list)
    suitable_for_downstream_scoring: bool = False


class HazardAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location: LocationInput
    hazard_types: list[str] = Field(
        default_factory=lambda: [
            "precipitation_extremes",
            "temperature_extremes",
            "wind_extremes",
        ]
    )
    years: int = Field(default=10, ge=1, le=30)
    include_unavailable: bool = True


class HazardAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requested_location: LocationInput
    resolved_location: ResolvedLocation
    hazards: list[HazardEvidence]
    assessment_status: str = "complete"
    warnings: list[str] = Field(default_factory=list)
    note: str = (
        "Weather-derived hazard evidence is not a validated flood map, property-damage estimate, or lending recommendation."
    )

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    place_name: str | None = None
    admin_area: str | None = None


class ResolvedLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float
    longitude: float
    matching_method: str = "requested_coordinates"
    resolution: str | None = None
    snapped_to_dataset: bool = False
    source: str | None = None

from __future__ import annotations

from datetime import datetime, timezone

from backend.app.hazards.location import LocationInput, ResolvedLocation
from backend.app.hazards.providers import get_provider_for_hazard
from backend.app.hazards.schemas import HazardAssessmentRequest, HazardAssessmentResponse, HazardEvidence


def build_hazard_assessment(request: HazardAssessmentRequest) -> HazardAssessmentResponse:
    hazards: list[HazardEvidence] = []
    warnings: list[str] = []

    resolved = ResolvedLocation(
        latitude=request.location.latitude,
        longitude=request.location.longitude,
        matching_method="requested_coordinates",
        resolution="none",
        snapped_to_dataset=False,
        source="user_input",
    )

    for hazard_type in request.hazard_types:
        normalized = hazard_type.strip().lower()
        provider = get_provider_for_hazard(normalized)

        if provider is None:
            record = HazardEvidence(
                hazard_type=normalized,
                status="not_supported",
                source="TerraCred hazard catalog",
                source_url=None,
                retrieval_time=datetime.now(timezone.utc).isoformat(),
                coordinates={
                    "latitude": request.location.latitude,
                    "longitude": request.location.longitude,
                },
                interpretation="No connected hazard provider is available for this hazard type.",
                completeness="incomplete",
                confidence="low",
                matching_method="not_supported",
                limitations=[
                    "The requested hazard type is not connected to a tested provider in the current project.",
                    "Missing hazard evidence must not be treated as low risk.",
                ],
                suitable_for_downstream_scoring=False,
            )
            hazards.append(record)
            warnings.append(f"{normalized}: no connected provider")
            continue

        record = provider.assess(request.location, normalized, request.years)
        hazards.append(record)

        if record.status != "available":
            warnings.append(f"{normalized}: {record.status}")

    if not hazards:
        warnings.append("No hazard types were requested.")

    return HazardAssessmentResponse(
        requested_location=request.location,
        resolved_location=resolved,
        hazards=hazards if request.include_unavailable else [h for h in hazards if h.status == "available"],
        assessment_status="complete" if hazards else "no_data",
        warnings=warnings,
    )

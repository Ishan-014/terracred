from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from backend.app.business.indicators import calculate_dependency_summary
from backend.app.business.models import (
    BusinessProfile,
    BusinessProfileCreate,
    BusinessProfileUpdate,
    OperationalVulnerability,
    OperationalVulnerabilityCreate,
    SupplierRelationship,
    SupplierRelationshipCreate,
)
from backend.app.business.store import get_store
from backend.app.business.vulnerability import calculate_operational_vulnerability_summary
from backend.app.hazards.assessment import build_hazard_assessment
from backend.app.hazards.location import LocationInput
from backend.app.hazards.schemas import HazardAssessmentRequest

router = APIRouter(prefix="/api/businesses", tags=["Business"])


class BusinessHazardAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    location_scope: Literal["business", "supplier"] = "business"
    supplier_id: str | None = None
    hazard_types: list[str] = Field(
        default_factory=lambda: [
            "precipitation_extremes",
            "temperature_extremes",
            "wind_extremes",
        ]
    )
    years: int = Field(default=10, ge=1, le=30)
    include_unavailable: bool = True


def _profile_validation_report(profile: BusinessProfileCreate | BusinessProfile) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []

    if profile.business_name is None or not str(profile.business_name).strip():
        missing.append("business_name")
    if profile.industry is None or not str(profile.industry).strip():
        missing.append("industry")
    if not profile.business_activity:
        warnings.append("business_activity is missing; operational detail is incomplete")
    if profile.business_location is None:
        warnings.append("business_location is not provided")
    elif profile.business_location.latitude is None or profile.business_location.longitude is None:
        errors.append("business_location must include both latitude and longitude when provided")

    if not profile.main_activities:
        warnings.append("main_activities is empty")
    if not profile.critical_raw_materials:
        warnings.append("critical_raw_materials is empty")
    if not profile.operational_dependencies:
        warnings.append("operational_dependencies is empty")

    return {
        "valid": not errors and not missing,
        "errors": errors,
        "warnings": warnings,
        "missing_fields": missing,
    }


@router.get("")
def list_business_profiles():
    return {"businesses": get_store().list_businesses()}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_business_profile(payload: BusinessProfileCreate):
    validation = _profile_validation_report(payload)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation)

    profile = BusinessProfile(
        business_id=get_store().create_business_id(),
        **payload.model_dump(exclude_none=True),
    )
    stored = get_store().create_business(profile)
    return stored


@router.get("/{business_id}")
def get_business_profile(business_id: str):
    profile = get_store().get_business(business_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    return profile


@router.put("/{business_id}")
def update_business_profile(business_id: str, payload: BusinessProfileUpdate):
    existing = get_store().get_business(business_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not update_data:
        return existing

    updated = get_store().update_business(business_id, update_data)
    if updated is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    return updated


@router.post("/{business_id}/suppliers", status_code=status.HTTP_201_CREATED)
def add_supplier_relationship(business_id: str, payload: SupplierRelationshipCreate):
    business = get_store().get_business(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    if payload.procurement_share is not None and not 0 <= payload.procurement_share <= 100:
        raise HTTPException(status_code=400, detail="procurement_share must be between 0 and 100.")

    supplier = SupplierRelationship(
        supplier_id=get_store().create_business_id(),
        business_id=business_id,
        **payload.model_dump(exclude_none=True),
    )
    stored = get_store().add_supplier(business_id, supplier)
    return stored


@router.get("/{business_id}/suppliers")
def list_supplier_relationships(business_id: str):
    if get_store().get_business(business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    return {"suppliers": get_store().list_suppliers(business_id)}


@router.get("/{business_id}/dependencies")
def get_supplier_dependency_summary(business_id: str):
    if get_store().get_business(business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    supplier_rows = [
        supplier.model_dump(mode="json")
        for supplier in get_store().list_suppliers(business_id)
    ]
    summary = calculate_dependency_summary(supplier_rows)
    summary["business_id"] = business_id
    return summary


@router.post("/{business_id}/operational-vulnerability", status_code=status.HTTP_201_CREATED)
@router.post("/{business_id}/vulnerability", status_code=status.HTTP_201_CREATED)
def create_operational_vulnerability(business_id: str, payload: OperationalVulnerabilityCreate):
    if get_store().get_business(business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    vulnerability = OperationalVulnerability(
        business_id=business_id,
        vulnerability_id=get_store().create_business_id(),
        **payload.model_dump(exclude_none=True),
    )
    stored = get_store().create_operational_vulnerability(business_id, vulnerability)
    return stored


@router.get("/{business_id}/operational-vulnerability")
@router.get("/{business_id}/vulnerability")
def get_operational_vulnerability(business_id: str):
    if get_store().get_business(business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    vulnerability = get_store().get_operational_vulnerability(business_id)
    if vulnerability is None:
        raise HTTPException(status_code=404, detail="Operational vulnerability record not found.")
    return vulnerability


@router.get("/{business_id}/operational-vulnerability/summary")
@router.get("/{business_id}/vulnerability/summary")
def get_operational_vulnerability_summary(business_id: str):
    if get_store().get_business(business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    vulnerability = get_store().get_operational_vulnerability(business_id)
    if vulnerability is None:
        return {
            "business_id": business_id,
            "critical_operations_without_fallback": 0,
            "critical_inputs_without_substitute": 0,
            "inventory_coverage_days": 0,
            "average_inventory_days": 0.0,
            "recovery_time_coverage_pct": 0.0,
            "verified_vulnerability_fields_pct": 0.0,
            "missing_evidence_warnings": ["No operational vulnerability record has been created for this business."],
            "known_inventory_entries": 0,
        }
    return {"business_id": business_id, **calculate_operational_vulnerability_summary(vulnerability)}


@router.post("/{business_id}/hazard-assessment")
def assess_business_hazard(business_id: str, payload: BusinessHazardAssessmentRequest):
    business = get_store().get_business(business_id)
    if business is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")

    location = business.business_location
    if payload.location_scope == "supplier":
        if payload.supplier_id is None:
            raise HTTPException(status_code=400, detail="supplier_id is required when location_scope='supplier'.")
        supplier = get_store().get_supplier(business_id, payload.supplier_id)
        if supplier is None:
            raise HTTPException(status_code=404, detail="Supplier not found for this business.")
        location = supplier.supplier_location

    if location is None or location.latitude is None or location.longitude is None:
        raise HTTPException(
            status_code=400,
            detail="No usable business or supplier location is available for hazard assessment.",
        )

    request = HazardAssessmentRequest(
        location=LocationInput(
            latitude=location.latitude,
            longitude=location.longitude,
            place_name=location.place_name,
            admin_area=location.admin_area,
        ),
        hazard_types=payload.hazard_types,
        years=payload.years,
        include_unavailable=payload.include_unavailable,
    )
    return build_hazard_assessment(request).model_dump(mode="json")


@router.post("/{business_id}/suppliers/{supplier_id}/hazard-assessment")
def assess_supplier_hazard(business_id: str, supplier_id: str, payload: BusinessHazardAssessmentRequest):
    if get_store().get_business(business_id) is None:
        raise HTTPException(status_code=404, detail="Business profile not found.")
    supplier = get_store().get_supplier(business_id, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found for this business.")
    if supplier.supplier_location is None or supplier.supplier_location.latitude is None or supplier.supplier_location.longitude is None:
        raise HTTPException(status_code=400, detail="Supplier location is incomplete or unavailable.")

    request = HazardAssessmentRequest(
        location=LocationInput(
            latitude=supplier.supplier_location.latitude,
            longitude=supplier.supplier_location.longitude,
            place_name=supplier.supplier_location.place_name,
            admin_area=supplier.supplier_location.admin_area,
        ),
        hazard_types=payload.hazard_types,
        years=payload.years,
        include_unavailable=payload.include_unavailable,
    )
    return build_hazard_assessment(request).model_dump(mode="json")


@router.post("/validate")
def validate_business_profile(payload: BusinessProfileCreate):
    return _profile_validation_report(payload)

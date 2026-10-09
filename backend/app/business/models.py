from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BusinessLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    place_name: str | None = None
    admin_area: str | None = None
    source: str | None = None
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"

    @property
    def is_complete(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class SupplierLocation(BusinessLocation):
    model_config = ConfigDict(extra="forbid")


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    source: str
    url: str | None = None
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class BusinessProfileBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_name: str | None = None
    industry: str | None = None
    business_activity: str | None = None
    business_location: BusinessLocation | None = None
    main_activities: list[str] = Field(default_factory=list)
    critical_raw_materials: list[str] = Field(default_factory=list)
    operational_dependencies: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class BusinessProfileCreate(BusinessProfileBase):
    business_name: str | None = None


class BusinessProfileUpdate(BusinessProfileBase):
    business_name: str | None = None
    business_location: BusinessLocation | None = None
    main_activities: list[str] | None = None
    critical_raw_materials: list[str] | None = None
    operational_dependencies: list[str] | None = None
    evidence: list[EvidenceReference] | None = None
    verification_status: Literal["verified", "unverified", "unknown"] | None = None


class BusinessProfile(BusinessProfileBase):
    business_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("main_activities", "critical_raw_materials", "operational_dependencies", mode="before")
    @classmethod
    def normalize_list(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)


class SupplierRelationshipBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_name: str | None = None
    supplier_location: SupplierLocation | None = None
    material_supplied: str | None = None
    critical_to_operations: bool | None = None
    procurement_share: float | None = None
    alternative_supplier_available: bool | None = None
    substitution_time_days: int | None = Field(default=None, ge=0)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class SupplierRelationshipCreate(SupplierRelationshipBase):
    pass


class SupplierRelationship(SupplierRelationshipBase):
    supplier_id: str
    business_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CriticalOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_name: str | None = None
    dependency_type: str | None = None
    fallback_available: bool | None = None
    recovery_time_days: int | None = Field(default=None, ge=0)
    continuity_measure: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class CriticalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_or_service: str | None = None
    critical_to_operations: bool | None = None
    inventory_days: int | None = Field(default=None, ge=0)
    substitute_available: bool | None = None
    substitute_time_days: int | None = Field(default=None, ge=0)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class HistoricalDisruption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: str | None = None
    description: str | None = None
    impacted_operation: str | None = None
    days_lost: int | None = Field(default=None, ge=0)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class OperationalVulnerabilityBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    critical_operations: list[CriticalOperation] = Field(default_factory=list)
    critical_inputs: list[CriticalInput] = Field(default_factory=list)
    continuity_measures: list[str] = Field(default_factory=list)
    historical_disruptions: list[HistoricalDisruption] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    verification_status: Literal["verified", "unverified", "unknown"] = "unknown"


class OperationalVulnerabilityCreate(OperationalVulnerabilityBase):
    pass


class OperationalVulnerability(OperationalVulnerabilityBase):
    business_id: str
    vulnerability_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

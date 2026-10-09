from __future__ import annotations

from typing import Any


def calculate_dependency_summary(suppliers: list[dict[str, Any]]) -> dict[str, Any]:
    """Return descriptive dependency indicators without creating a risk score."""

    total_suppliers = len(suppliers)
    critical_materials = [
        s for s in suppliers if s.get("critical_to_operations") is True
    ]
    critical_material_count = len({s.get("material_supplied") for s in critical_materials if s.get("material_supplied")})

    shares = [
        float(s.get("procurement_share"))
        for s in suppliers
        if isinstance(s.get("procurement_share"), (int, float)) and 0 <= float(s.get("procurement_share")) <= 100
    ]
    if shares:
        largest_share = max(shares)
        total_share = sum(shares)
        largest_supplier_share_pct = round((largest_share / total_share) * 100, 2) if total_share > 0 else None
    else:
        largest_share = None
        largest_supplier_share_pct = None

    no_alternative = sum(
        1
        for s in suppliers
        if s.get("critical_to_operations") is True and s.get("alternative_supplier_available") is False
    )

    unknown_or_unverified = sum(
        1
        for s in suppliers
        if not s.get("supplier_location") or s.get("verification_status") != "verified"
    )

    completeness_scores = []
    for supplier in suppliers:
        fields = [
            supplier.get("supplier_name"),
            supplier.get("material_supplied"),
            supplier.get("supplier_location"),
            supplier.get("verification_status"),
            supplier.get("procurement_share") is not None,
        ]
        completeness_scores.append(sum(1 for value in fields if value not in (None, "", False)))

    completeness_pct = None
    if suppliers:
        completeness_pct = round((sum(completeness_scores) / (len(suppliers) * 5)) * 100, 2)

    verification_coverage = None
    if suppliers:
        verified = sum(
            1 for s in suppliers if s.get("verification_status") == "verified"
        )
        verification_coverage = round((verified / len(suppliers)) * 100, 2)

    return {
        "total_known_suppliers": total_suppliers,
        "critical_material_count": critical_material_count,
        "procurement_concentration_pct": round(float(largest_share), 2) if largest_share is not None else None,
        "largest_supplier_share_of_total_pct": largest_supplier_share_pct,
        "critical_materials_without_alternative": no_alternative,
        "supplier_locations_unknown_or_unverified": unknown_or_unverified,
        "data_completeness_pct": completeness_pct,
        "verification_coverage_pct": verification_coverage,
        "notes": [
            "Descriptive dependency indicators are not a validated climate-risk or credit score.",
            "Unknown or unverified supplier information must not be treated as safe.",
        ],
    }

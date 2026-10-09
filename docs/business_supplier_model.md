# Business and supplier intelligence model

## Purpose
This module captures structured MSME business and supplier information for climate-risk context. It is designed to supplement conventional credit assessment, not replace it and not automatically approve or reject a loan.

## Business profile fields
A business profile stores the following fields:

- `business_id`: internal identifier for this record.
- `business_name`: optional business name, when supplied by the user.
- `industry`: sector or category for the business.
- `business_activity`: short description of the business activity.
- `business_location`: optional coordinates and place metadata.
- `main_activities`: operational tasks such as milling, processing, packaging, logistics, or fabrication.
- `critical_raw_materials`: materials essential to ongoing operations.
- `operational_dependencies`: utility or service dependencies such as water, power, transport, or cold storage.
- `evidence`: list of evidence references with source and verification status.
- `verification_status`: explicit status such as verified, unverified, or unknown.
- `created_at` and `updated_at`: timestamps for provenance and auditability.

## Supplier relationship fields
A supplier relationship stores:

- `supplier_id`: internal supplier identifier.
- `supplier_name`: optional supplier name.
- `supplier_location`: optional location and verification status.
- `material_supplied`: material or service supplied.
- `critical_to_operations`: whether the supplied input is essential to output or continuity.
- `procurement_share`: percentage of procurement represented by the supplier, when known.
- `alternative_supplier_available`: whether a viable substitution path is known.
- `substitution_time_days`: expected time to swap suppliers if relevant.
- `evidence`: evidence supporting the relationship.
- `verification_status`: verified, unverified, or unknown.

## Data provenance and verification status
The model preserves explicit provenance and never invents supplier relationships. A relationship is only as solid as the evidence and verification status recorded. Unknown values remain unknown and are not interpreted as safe or risky.

## Dependency indicator definitions
The backend currently computes descriptive indicators only. These are intentionally not climate-risk scores.

- `total_known_suppliers`: number of supplier records known for the business.
- `critical_material_count`: count of unique critical materials supplied.
- `procurement_concentration_pct`: largest single supplier share when valid shares are present.
- `largest_supplier_share_of_total_pct`: percentage of procurement represented by the largest supplier, if total shares are calculable and consistent.
- `critical_materials_without_alternative`: number of critical materials with no known alternative supplier.
- `supplier_locations_unknown_or_unverified`: count of supplier locations that are missing or not verified.
- `data_completeness_pct`: percentage of key supplier fields populated with usable values.
- `verification_coverage_pct`: percentage of supplier records with explicit verification status = verified.

These metrics are descriptive only and must be treated as supporting context for later climate and operational-risk assessments.

## Missing-data handling
Missing and incomplete records are reported transparently.

- Missing coordinates are not automatically treated as safe.
- Unknown supplier relationships are not treated as risk-free.
- Unknown values remain `unknown` and do not get replaced with arbitrary defaults.
- Incomplete procurement share data is excluded from aggregation instead of being silently inferred.

## Persistence approach
This phase uses SQLite-backed persistence through the standard library `sqlite3` interface. The database path is configured through the `TERRACRED_DB_PATH` environment variable, with a default file in the repository `data/` directory. This keeps the solution lightweight, local, and durable without requiring paid infrastructure or remote services. Records persist across restarts and are isolated per environment. A future PostgreSQL migration path is straightforward because the API layer uses explicit record objects and JSON payload storage; the primary changes would be schema-aligned SQL syntax and connection configuration.

## API endpoints
The current business and supplier intelligence module exposes:

- `GET /api/businesses`: list business profiles
- `POST /api/businesses`: create a business profile
- `GET /api/businesses/{business_id}`: retrieve a profile
- `PUT /api/businesses/{business_id}`: update a profile
- `POST /api/businesses/{business_id}/suppliers`: add a supplier relationship
- `GET /api/businesses/{business_id}/suppliers`: list suppliers
- `GET /api/businesses/{business_id}/dependencies`: calculate dependency indicator summary
- `POST /api/businesses/validate`: validate profile input structure and missing fields

## Limitations and next integration points
- This module records business context and supplier dependency evidence, but does not calculate a final climate-risk score.
- It is ready for later integration with hazard evidence, operational vulnerability, and climate-disruption scenario analysis.
- Supplier relationship details must remain separate from conventional credit scoring and any later lending decision logic.

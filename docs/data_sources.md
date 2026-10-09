# Data sources and evidence status

## Confirmed access and use

### A. Open-Meteo weather and historical archive
- Source: https://open-meteo.com/
- Historical API doc: https://open-meteo.com/en/docs/historical-weather-api
- Forecast API doc: https://open-meteo.com/en/docs
- Access status: Confirmed and currently used by the backend for forecast, recent historical weather, and multi-year archive requests.
- Variables used: `temperature_2m_max`, `temperature_2m_min`, `precipitation_sum`, and `wind_speed_10m_max`.
- Time coverage: Daily historical archive coverage is available for many global locations, but the exact period and completeness depend on the queried coordinates and archive availability; completeness should be checked before scoring or risk interpretation.
- Units: Daily temperature values are typically in °C, precipitation in mm, and wind speeds in km/h or the API-selected units.
- Spatial resolution: Point-based API requests at coordinates; not a property parcel or building-level dataset.
- Update frequency: Forecast data is near real-time and refreshed according to Open-Meteo availability; historical archive data is retrospective and can be queried by date range.
- Limitations: Weather observations are not climate-normal validation, do not prove flood damage, and are insufficient for property-level hazard confirmation without additional geospatial evidence.

### B. World Bank Climate Change Knowledge Portal (CCKP)
- Source: https://climateknowledgeportal.worldbank.org/
- Access status: Research-only source for long-term historical climate baselines and future climate projections; not yet wired into the backend API.
- Use case: Baseline or context analysis for long-run climate trends, not a substitute for point-level weather observations.
- Limitations: Availability and indicator coverage vary by country and region. It is useful for contextual climate exposure analysis but not enough alone to determine a business site’s flood or heat risk.

### C. Flood hazard and exposure data
- Source examples:
  - Bhuvan Flood Hazard Zones: https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood_hz/flood_hz.php
  - National Flood Vulnerability Assessment System: https://bhuvan-app1.nrsc.gov.in/nfvas/
  - World Bank Global Flood Exposure Dataset: https://datacatalog.worldbank.org/search/dataset/0062763/global-flood-exposure-gridded-exposure-headcounts-by-country
  - NASA/USGS/UN environment geospatial hazard products and local national flood datasets where available.
- Access status: Bhuvan provides official flood layers for review, but no dependable machine-readable API or bulk download path was identified for automated integration in this project phase. The World Bank dataset is catalogued and documented, but it represents population exposure during a defined flood scenario and is not a property-level flood-risk model.
- Why it matters: Flood hazard maps are useful for exposure assessment, but population exposure or coarse geospatial layers are not equivalent to property-level flood probability or damage estimates.
- Limitation: Without verified site coordinates and the correct hazard layer, a flood signal is not enough to infer actual business damage or disruption.

### D. Other relevant sources
- Historical extreme precipitation and temperature records: National meteorological services, World Bank climate portals, and authoritative climate datasets where country-specific data is available.
- Heat stress and drought indicators: National meteorological agencies and global climate research products such as ERA5/CMIP-derived analyses when licensed and processed appropriately.
- Geographic boundary and location matching: Official administrative boundary datasets from national statistics offices and geospatial agencies; needed for matching business locations to region or district-level context.
- MSME classification and document fields: Udyam registration fields and official government documentation for business identity and activity type; useful for onboarding but not a substitute for a conventional credit score or supplier verification.

## Proposed or unavailable sources

- Property-level flood damage models and local hazard scoring products are not yet available as a standard, open source API for this project and would require additional licensing and validation.
- High-resolution supplier risk datasets are not yet in scope for the current backend milestone.
- Production-grade climate risk scoring should not be implemented until hazard exposure, business vulnerability, and supplier dependency data are all documented and validated.

## Data governance notes
- All weather and climate indicators must preserve source, units, validity coverage, time range, and methodology.
- Missing or incomplete weather data must not be silently treated as safe.
- Any future risk score must remain separate from a baseline credit score and must include explicit model versioning and confidence metadata.

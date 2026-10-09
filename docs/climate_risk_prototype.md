# TerraCred climate-risk prototype

## Prototype workflow

1. Create a business profile.
2. Record supplier relationships and operational vulnerability.
3. Request `POST /api/businesses/{business_id}/climate-risk-assessment`.
4. Review the experimental indicator, each dimension, evidence sources, missing inputs, and warnings.

## Interpretation

The response is an explainable **prototype indicator**, not a validated probability of loss, conventional credit score, or lending decision. The current weather provider supplies historical weather-derived indicators only. Heavy rainfall is not proof of flooding; the prototype does not currently connect a property-level flood map or damage model.

## Prototype calculation

- Hazard evidence: mean of available connected weather indicators. For the demonstration only, maximum daily precipitation in mm and maximum daily wind speed in km/h are capped at 100; the percentage of observed days above 35°C is used for the heat indicator.
- Operational vulnerability: mean of available known shares of critical operations without a fallback and critical inputs without a substitute.
- Supplier dependency: mean of the largest recorded procurement share and the known share of critical suppliers without an alternative.
- Experimental overall indicator: arithmetic mean of whichever of the three dimensions have numeric evidence. Missing dimensions are excluded, never assumed safe. The response warns when fewer than three dimensions are available.
- Evidence quality: verification coverage is reported separately and is not mixed into the risk indicator.

These choices are deliberately simple, transparent, and **illustrative rather than scientifically calibrated**. The output must not replace conventional credit assessment or automatically approve/reject lending.

## Data quality

Unknown, unsupported, unavailable, and unverified information is returned as warnings or missing inputs. Weather-derived indicators are not flood evidence. The API returns model version and source metadata for the weather evidence used.

## Not included in this fast prototype

No ML training, claimed predictive accuracy, GST/Udyam-based supplier verification, property-damage probability, automatic lending decision, or production-grade multi-user deployment.


## Climate-adjusted score demo

The streamlined frontend starts with a Udyam certificate upload. The upload endpoint extracts embedded PDF text or uses OCR for scanned PDFs/images to suggest fields; users must review them, and this does not verify certificate authenticity. The form collects business coordinates and separate supplier coordinates so the system does not mistake weather at the shop for weather at the supplier.

For the visual demonstration, the API accepts an assumed baseline score in the 300–900 range (default 750). If the existing climate-risk engine returns a numeric indicator, the demo applies:

- Signed climate adjustment = rounded (climate-risk indicator − 50) × 0.5, bounded to −25..+25 points. Values above 50 lower the score; values below 50 raise it.
- Climate-adjusted score = baseline score − climate penalty, bounded to 300–900.
- Display bands: 300–549 Poor, 550–649 Fair, 650–749 Good, and 750–900 Excellent.

This is an illustrative presentation mapping, not an established MSME credit-risk formula or validated credit score. A Udyam certificate does not itself provide the baseline credit score. The score must not be used to make real lending decisions. For a production system, the climate adjustment would need a justified, calibrated methodology and independently sourced conventional credit data.


## Evidence explanation layer

The assessment response includes raw observed weather evidence used for the hazard signals, source metadata, risk dimensions, missing inputs, and warnings. If `OPENAI_API_KEY` is configured, the backend sends this structured evidence to the OpenAI Chat Completions API (default model `gpt-4o-mini`) to produce a plain-language summary, risk factors, lower-risk signals, and evidence limitations. The model is instructed not to invent evidence; if the API key is absent or the request fails, a deterministic rule-based explanation is returned instead. Configure `OPENAI_API_KEY` in the repository-root `.env` file; never expose this key in frontend code. OpenAI explains the engine's result and does not calculate or alter the score.


The current demonstration score adjustment is deliberately small and symmetric: `adjustment = clamp(round((risk_indicator - 50) * 0.5), -25, 25)` and `adjusted_score = baseline - adjustment`. OpenAI explains the returned evidence but does not determine or change the score.


## Data quality and plain-language evidence

Before interpreting the score, the engine performs basic checks on business coordinates, business verification status, supplier verification status, and supported weather measurements. Weather values outside broad expected ranges or missing required values are excluded from numeric scoring and surfaced as data-quality issues. The API labels the result provisional when climate evidence or valid coordinates are missing. This is a basic validation layer, not a full statistical or geospatial validation.

The evidence response now contains short labels, observed values, source, period, and a plain-language explanation instead of requiring the frontend to show raw JSON. The OpenAI explainer is instructed to review data-quality checks first, then explain the possible business disruption in simple language using only the supplied observations. OpenAI does not calculate or alter the score; a rule-based explanation is used if the API is not configured or fails.


## Supplier rainfall and wood-based businesses

For each supplier with coordinates, the climate-risk endpoint separately retrieves historical precipitation evidence at the supplier location. When the supplied material text indicates wood, timber, lumber, plywood, or veneer, the explanation layer can describe the plausible pathway in plain language: rain-exposed storage or transport can make it harder to keep timber dry; damp wood may develop mould/fungal decay or swell, warp, or crack; rain-related road/handling disruptions may delay deliveries and interrupt furniture production.

These are possible mechanisms, not proof of actual timber moisture, mould, damage, flooding, or a late delivery. The API records the observed maximum daily rainfall and source/period, and explicitly notes that a single daily maximum does not by itself establish that an area is rain-prone. The supplier rainfall proxy is included in the prototype's illustrative indicator only when valid supplier-location rainfall observations are available; missing supplier coordinates/data are not treated as safe. The score is still experimental and not a lending decision.

## Business/material-to-hazard relevance

The scoring path now applies explicit prototype relevance rules before a weather indicator can contribute to the score. Business-location rainfall, heat, and wind observations are excluded when the recorded business activity/materials do not match a configured disruption pathway; the response explains that exclusion rather than treating the hazard as safe. Supplier rainfall is separately matched to the supplied material. The current illustrative rainfall weights are 1.0 for wood/timber/lumber/plywood/veneer, 0.8 for paper/cardboard/packaging/cotton/textiles, 0.7 for grain/crops/seeds/fertilizer, 0.6 for common construction materials, and 0.5 for food/perishables/dairy/medicine/pharma. Unmatched materials remain visible as context but do not contribute to the numeric score.

For example, rainfall at a timber supplier can contribute to the furniture shop's prototype indicator, and the explanation describes possible moisture-related swelling/warping/mould and delivery interruption. Wind at the same location is not scored unless the business/material rules identify a relevant pathway. These rules and weights are transparent demonstration assumptions, not validated physical-damage or credit-risk coefficients. The weather provider's maximum daily rainfall is only a point-weather proxy; it does not establish long-term rain-proneness, flooding, actual wood moisture, damage, or delivery loss.

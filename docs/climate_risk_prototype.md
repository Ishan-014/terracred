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

The streamlined frontend starts with a Udyam certificate upload, then collects a small set of business and supplier details. The upload endpoint stores the file locally but does not extract or verify its contents; details are manually entered.

For the visual demonstration, the API accepts an assumed baseline score in the 300–900 range (default 750). If the existing climate-risk engine returns a numeric indicator, the demo applies:

- Climate penalty = rounded climate-risk indicator × 3 points.
- Climate-adjusted score = baseline score − climate penalty, bounded to 300–900.
- Display bands: 300–549 Poor, 550–649 Fair, 650–749 Good, and 750–900 Excellent.

This is an illustrative presentation mapping, not an established MSME credit-risk formula or validated credit score. A Udyam certificate does not itself provide the baseline credit score. The score must not be used to make real lending decisions. For a production system, the climate adjustment would need a justified, calibrated methodology and independently sourced conventional credit data.

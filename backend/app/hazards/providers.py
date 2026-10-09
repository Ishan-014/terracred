from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from backend.app.data.open_meteo import get_climate_history
from backend.app.hazards.location import LocationInput
from backend.app.hazards.schemas import HazardEvidence


class BaseHazardProvider(ABC):
    provider_name: str = "Unknown provider"
    source_url: str | None = None
    supported_hazard_types: tuple[str, ...] = ()

    def supports(self, hazard_type: str) -> bool:
        return hazard_type in self.supported_hazard_types

    @abstractmethod
    def assess(
        self,
        location: LocationInput,
        hazard_type: str,
        years: int = 10,
    ) -> HazardEvidence:
        raise NotImplementedError


class OpenMeteoHazardProvider(BaseHazardProvider):
    provider_name = "Open-Meteo Historical Weather Archive"
    source_url = "https://open-meteo.com/en/docs/historical-weather-api"
    supported_hazard_types = (
        "precipitation_extremes",
        "temperature_extremes",
        "wind_extremes",
    )

    def assess(
        self,
        location: LocationInput,
        hazard_type: str,
        years: int = 10,
    ) -> HazardEvidence:
        try:
            weather = get_climate_history(
                latitude=location.latitude,
                longitude=location.longitude,
                years=years,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            return HazardEvidence(
                hazard_type=hazard_type,
                status="unavailable",
                source=self.provider_name,
                source_url=self.source_url,
                retrieval_time=datetime.now(timezone.utc).isoformat(),
                coordinates={
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                },
                interpretation="Historical weather retrieval for hazard evidence failed.",
                completeness="incomplete",
                confidence="low",
                limitations=[f"Provider access failed: {exc}"],
                suitable_for_downstream_scoring=False,
            )

        daily = weather.get("daily", {}) if isinstance(weather, dict) else {}
        period = weather.get("period", {}) if isinstance(weather, dict) else {}
        units = weather.get("units", {}) if isinstance(weather, dict) else {}
        dates = daily.get("time", []) if isinstance(daily, dict) else []

        if not isinstance(daily, dict):
            return HazardEvidence(
                hazard_type=hazard_type,
                status="unavailable",
                source=self.provider_name,
                source_url=self.source_url,
                retrieval_time=datetime.now(timezone.utc).isoformat(),
                coordinates={
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                },
                interpretation="The provider returned malformed weather data and no valid daily observations.",
                completeness="incomplete",
                confidence="low",
                matching_method="point_lookup",
                limitations=[
                    "Daily weather data was missing or malformed, so no hazard evidence could be computed.",
                    "Missing or malformed data must not be treated as low risk.",
                ],
                suitable_for_downstream_scoring=False,
            )

        if hazard_type == "precipitation_extremes":
            values = [float(value) for value in daily.get("precipitation_sum", []) if value is not None]
            evidence = {
                "max_daily_precipitation_mm": round(max(values), 2) if values else None,
                "total_precipitation_mm": round(sum(values), 2) if values else None,
                "days_with_observations": len(values),
            }
            interpretation = (
                "Maximum observed daily precipitation within the requested historical window. "
                "This is weather evidence and not a flood-hazard map or property-damage estimate."
            )
            limits = [
                "Daily precipitation is not equivalent to a flood inundation map.",
                "Heavy rainfall at a point does not prove a property was flooded.",
            ]
            suitable = False
        elif hazard_type == "temperature_extremes":
            max_values = [float(value) for value in daily.get("temperature_2m_max", []) if value is not None]
            min_values = [float(value) for value in daily.get("temperature_2m_min", []) if value is not None]
            evidence = {
                "max_daily_temperature_c": round(max(max_values), 2) if max_values else None,
                "min_daily_temperature_c": round(min(min_values), 2) if min_values else None,
                "hot_days_above_35c": sum(1 for value in max_values if value > 35.0),
                "cold_days_below_0c": sum(1 for value in min_values if value < 0.0),
                "days_with_observations": len(max_values),
            }
            interpretation = (
                "Temperature extremes are a proxy for heat or cold stress risk and should be paired with local exposure context."
            )
            limits = [
                "Weather-derived temperature extremes do not define site-specific heat exposure.",
                "Data quality depends on availability and reporting completeness over the period.",
            ]
            suitable = False
        elif hazard_type == "wind_extremes":
            values = [float(value) for value in daily.get("wind_speed_10m_max", []) if value is not None]
            evidence = {
                "max_daily_wind_speed_kmh": round(max(values), 2) if values else None,
                "days_with_observations": len(values),
            }
            interpretation = (
                "Daily maximum wind speeds provide an indicator of localized wind stress and disruption risk."
            )
            limits = [
                "Wind-speed observations are not a property-level hazard map.",
                "Damage risk depends on building type, materials, and local topography.",
            ]
            suitable = False
        else:
            raise ValueError(f"Unsupported hazard type: {hazard_type}")

        return HazardEvidence(
            hazard_type=hazard_type,
            status="available" if dates else "unavailable",
            source=self.provider_name,
            source_url=self.source_url,
            retrieval_time=datetime.now(timezone.utc).isoformat(),
            coordinates={
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            spatial_resolution="point_weather_grid",
            temporal_resolution="daily",
            data_period={
                "start": period.get("start"),
                "end": period.get("end"),
            },
            units={
                "precipitation_sum": units.get("precipitation_sum", "mm"),
                "temperature_2m_max": units.get("temperature_2m_max", "°C"),
                "temperature_2m_min": units.get("temperature_2m_min", "°C"),
                "wind_speed_10m_max": units.get("wind_speed_10m_max", "km/h"),
            },
            evidence=evidence,
            interpretation=interpretation,
            completeness="complete" if dates else "incomplete",
            confidence="medium",
            matching_method="point_lookup",
            limitations=[
                "Weather observations do not confirm flood inundation, property loss, or asset-level damage.",
                *(limits or []),
            ],
            suitable_for_downstream_scoring=suitable,
        )


class FloodHazardMapProvider(BaseHazardProvider):
    provider_name = "Bhuvan Flood Hazard Map (not connected)"
    source_url = "https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/flood_hz/flood_hz.php"
    supported_hazard_types = ("flood_hazard", "inundation_hazard")

    def assess(
        self,
        location: LocationInput,
        hazard_type: str,
        years: int = 10,
    ) -> HazardEvidence:
        return HazardEvidence(
            hazard_type=hazard_type,
            status="unavailable",
            source=self.provider_name,
            source_url=self.source_url,
            retrieval_time=datetime.now(timezone.utc).isoformat(),
            coordinates={
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            spatial_resolution=None,
            temporal_resolution=None,
            interpretation="Bhuvan flood-zone layers are not currently connected to an automated geospatial lookup in this project.",
            completeness="incomplete",
            confidence="low",
            matching_method="unavailable",
            limitations=[
                "Official flood maps are available but no dependable machine-readable, programmatic API was implemented in this phase.",
                "Satellite-derived flood extents can miss minor, flash, or peak flood events.",
            ],
            suitable_for_downstream_scoring=False,
        )


class PopulationFloodExposureProvider(BaseHazardProvider):
    provider_name = "World Bank Global Flood Exposure"
    source_url = "https://datacatalog.worldbank.org/search/dataset/0062763/global-flood-exposure-gridded-exposure-headcounts-by-country"
    supported_hazard_types = ("population_flood_exposure", "flood_exposure")

    def assess(
        self,
        location: LocationInput,
        hazard_type: str,
        years: int = 10,
    ) -> HazardEvidence:
        return HazardEvidence(
            hazard_type=hazard_type,
            status="unavailable",
            source=self.provider_name,
            source_url=self.source_url,
            retrieval_time=datetime.now(timezone.utc).isoformat(),
            coordinates={
                "latitude": location.latitude,
                "longitude": location.longitude,
            },
            spatial_resolution="3 arc-second raster",
            temporal_resolution="event-based",
            interpretation=(
                "This dataset reflects population exposure to inundation depth during a defined flood scenario; "
                "it is not a property-level flood probability or damage estimate."
            ),
            completeness="incomplete",
            confidence="low",
            matching_method="not_connected",
            limitations=[
                "Population exposure is not equivalent to business or asset-level flood risk.",
                "This dataset does not estimate probability of flooding at a specific MSME property.",
            ],
            suitable_for_downstream_scoring=False,
        )


PROVIDERS: tuple[BaseHazardProvider, ...] = (
    OpenMeteoHazardProvider(),
    FloodHazardMapProvider(),
    PopulationFloodExposureProvider(),
)


def get_provider_for_hazard(hazard_type: str) -> BaseHazardProvider | None:
    for provider in PROVIDERS:
        if provider.supports(hazard_type):
            return provider
    return None

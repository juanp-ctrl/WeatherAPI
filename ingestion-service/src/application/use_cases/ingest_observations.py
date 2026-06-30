from __future__ import annotations

import logging

from ...domain.ports.weather_data_source import WeatherDataSource
from ...domain.repositories.location_repository import LocationRepository
from ...domain.repositories.raw_observation_repository import RawObservationRepository
from ..dtos.observation_dto import IngestResultDTO

logger = logging.getLogger(__name__)


class IngestObservationsUseCase:
    def __init__(
        self,
        location_repository: LocationRepository,
        observation_repository: RawObservationRepository,
        weather_source: WeatherDataSource,
    ) -> None:
        self._locations = location_repository
        self._observations = observation_repository
        self._weather_source = weather_source

    async def execute(self) -> IngestResultDTO:
        locations = await self._locations.list_all(active_only=True)
        locations_processed = 0
        total_stored = 0
        errors: list[str] = []

        for location in locations:
            try:
                observations = await self._weather_source.fetch_current(location)
                if observations:
                    stored = await self._observations.save_many(observations)
                    total_stored += stored
                locations_processed += 1
                logger.info(
                    "Ingested %d observation(s) for location '%s'",
                    len(observations),
                    location.name,
                )
            except Exception as exc:
                msg = f"Failed to ingest location '{location.name}': {exc}"
                logger.error(msg)
                errors.append(msg)

        logger.info(
            "Ingestion cycle complete: %d locations processed, %d observations stored, %d errors",
            locations_processed,
            total_stored,
            len(errors),
        )
        return IngestResultDTO(
            locations_processed=locations_processed,
            observations_stored=total_stored,
            errors=errors,
        )

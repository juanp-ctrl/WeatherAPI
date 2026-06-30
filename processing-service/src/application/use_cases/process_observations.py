from __future__ import annotations

import logging
from datetime import datetime, timezone

from ...domain.entities.alert import Alert
from ...domain.entities.processed_observation import ProcessedObservation
from ...domain.entities.watermark import Watermark
from ...domain.ports.ingestion_client import IngestionClient
from ...domain.repositories.alert_repository import AlertRepository
from ...domain.repositories.processed_observation_repository import (
    ProcessedObservationRepository,
)
from ...domain.repositories.processing_rule_repository import ProcessingRuleRepository
from ...domain.repositories.watermark_repository import WatermarkRepository
from ...domain.services.metrics import (
    compute_feels_like,
    compute_heat_index,
    compute_severity_score,
    compute_wind_chill,
)
from ...domain.services.rule_engine import evaluate_rules
from ..dtos.processed_observation_dto import ProcessResultDTO

logger = logging.getLogger(__name__)

_WATERMARK_SOURCE = "ingestion"


class ProcessObservationsUseCase:
    def __init__(
        self,
        ingestion_client: IngestionClient,
        obs_repo: ProcessedObservationRepository,
        alert_repo: AlertRepository,
        rule_repo: ProcessingRuleRepository,
        watermark_repo: WatermarkRepository,
    ) -> None:
        self._ingestion = ingestion_client
        self._obs_repo = obs_repo
        self._alert_repo = alert_repo
        self._rule_repo = rule_repo
        self._watermark_repo = watermark_repo

    async def execute(self) -> ProcessResultDTO:
        watermark = await self._watermark_repo.get(_WATERMARK_SOURCE)
        since = watermark.last_ingested_at if watermark else None

        raw_observations = await self._ingestion.get_observations(since=since, limit=100)
        if not raw_observations:
            logger.info("Processing cycle: no new observations to process")
            return ProcessResultDTO(observations_processed=0, alerts_generated=0)

        active_rules = await self._rule_repo.list_active()
        total_alerts = 0
        errors: list[str] = []
        new_watermark_ts: datetime | None = None

        for raw_obs in raw_observations:
            try:
                heat_index = compute_heat_index(raw_obs.temperature_c, raw_obs.humidity_pct)
                wind_chill = compute_wind_chill(raw_obs.temperature_c, raw_obs.wind_speed_kmh)
                feels_like = compute_feels_like(raw_obs.temperature_c, heat_index, wind_chill)

                obs_data = {
                    "temperature_c": raw_obs.temperature_c,
                    "humidity_pct": raw_obs.humidity_pct,
                    "wind_speed_kmh": raw_obs.wind_speed_kmh,
                    "precipitation_mm": raw_obs.precipitation_mm,
                    "weather_code": raw_obs.weather_code,
                    "heat_index_c": heat_index,
                    "wind_chill_c": wind_chill,
                    "feels_like_c": feels_like,
                }
                matches = evaluate_rules(obs_data, active_rules)
                severity_score = compute_severity_score([m.severity for m in matches])

                processed = await self._obs_repo.save(
                    ProcessedObservation(
                        raw_observation_id=raw_obs.id,
                        location_id=raw_obs.location_id,
                        observed_at=raw_obs.observed_at,
                        temperature_c=raw_obs.temperature_c,
                        humidity_pct=raw_obs.humidity_pct,
                        wind_speed_kmh=raw_obs.wind_speed_kmh,
                        precipitation_mm=raw_obs.precipitation_mm,
                        weather_code=raw_obs.weather_code,
                        heat_index_c=heat_index,
                        wind_chill_c=wind_chill,
                        feels_like_c=feels_like,
                        severity_score=severity_score,
                    )
                )

                for match in matches:
                    await self._alert_repo.save(
                        Alert(
                            processed_observation_id=processed.id,
                            rule_id=match.rule_id,
                            alert_type=match.alert_type,
                            severity=match.severity,
                            message=match.message,
                        )
                    )
                total_alerts += len(matches)

                if new_watermark_ts is None or raw_obs.ingested_at > new_watermark_ts:
                    new_watermark_ts = raw_obs.ingested_at

            except Exception as exc:
                msg = f"Failed to process observation {raw_obs.id}: {exc}"
                logger.error(msg)
                errors.append(msg)

        if new_watermark_ts:
            await self._watermark_repo.upsert(
                Watermark(source=_WATERMARK_SOURCE, last_ingested_at=new_watermark_ts)
            )

        logger.info(
            "Processing cycle complete: %d observations processed, %d alerts generated",
            len(raw_observations),
            total_alerts,
        )
        return ProcessResultDTO(
            observations_processed=len(raw_observations),
            alerts_generated=total_alerts,
            errors=errors,
        )

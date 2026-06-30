from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.processed_observation import ProcessedObservation
from .models import ProcessedObservationModel


def _to_entity(model: ProcessedObservationModel) -> ProcessedObservation:
    return ProcessedObservation(
        id=model.id,
        raw_observation_id=model.raw_observation_id,
        location_id=model.location_id,
        temperature_c=model.temperature_c,
        humidity_pct=model.humidity_pct,
        wind_speed_kmh=model.wind_speed_kmh,
        precipitation_mm=model.precipitation_mm,
        weather_code=model.weather_code,
        heat_index_c=model.heat_index_c,
        wind_chill_c=model.wind_chill_c,
        feels_like_c=model.feels_like_c,
        severity_score=model.severity_score,
        observed_at=model.observed_at,
        processed_at=model.processed_at,
    )


class SQLAlchemyProcessedObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, observation_id: UUID) -> ProcessedObservation | None:
        result = await self._session.execute(
            select(ProcessedObservationModel).where(
                ProcessedObservationModel.id == observation_id
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list(
        self,
        location_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProcessedObservation]:
        stmt = select(ProcessedObservationModel).order_by(
            ProcessedObservationModel.processed_at.desc()
        )
        if location_id is not None:
            stmt = stmt.where(ProcessedObservationModel.location_id == location_id)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def count(self, location_id: UUID | None = None) -> int:
        stmt = select(func.count()).select_from(ProcessedObservationModel)
        if location_id is not None:
            stmt = stmt.where(ProcessedObservationModel.location_id == location_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def save(self, observation: ProcessedObservation) -> ProcessedObservation:
        model = ProcessedObservationModel(
            id=observation.id,
            raw_observation_id=observation.raw_observation_id,
            location_id=observation.location_id,
            temperature_c=observation.temperature_c,
            humidity_pct=observation.humidity_pct,
            wind_speed_kmh=observation.wind_speed_kmh,
            precipitation_mm=observation.precipitation_mm,
            weather_code=observation.weather_code,
            heat_index_c=observation.heat_index_c,
            wind_chill_c=observation.wind_chill_c,
            feels_like_c=observation.feels_like_c,
            severity_score=observation.severity_score,
            observed_at=observation.observed_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

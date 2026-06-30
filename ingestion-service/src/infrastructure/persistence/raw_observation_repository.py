from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.raw_observation import RawObservation
from .models import RawObservationModel


def _to_entity(model: RawObservationModel) -> RawObservation:
    return RawObservation(
        id=model.id,
        location_id=model.location_id,
        temperature_c=model.temperature_c,
        humidity_pct=model.humidity_pct,
        wind_speed_kmh=model.wind_speed_kmh,
        precipitation_mm=model.precipitation_mm,
        weather_code=model.weather_code,
        observed_at=model.observed_at,
        ingested_at=model.ingested_at,
    )


class SQLAlchemyRawObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, observation_id: UUID) -> RawObservation | None:
        result = await self._session.execute(
            select(RawObservationModel).where(RawObservationModel.id == observation_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list(
        self,
        location_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RawObservation]:
        stmt = select(RawObservationModel).order_by(
            RawObservationModel.ingested_at.asc()
        )
        if location_id is not None:
            stmt = stmt.where(RawObservationModel.location_id == location_id)
        if since is not None:
            stmt = stmt.where(RawObservationModel.ingested_at > since)
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        location_id: UUID | None = None,
        since: datetime | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(RawObservationModel)
        if location_id is not None:
            stmt = stmt.where(RawObservationModel.location_id == location_id)
        if since is not None:
            stmt = stmt.where(RawObservationModel.ingested_at > since)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def save_many(self, observations: list[RawObservation]) -> int:
        if not observations:
            return 0
        values = [
            {
                "id": obs.id,
                "location_id": obs.location_id,
                "temperature_c": obs.temperature_c,
                "humidity_pct": obs.humidity_pct,
                "wind_speed_kmh": obs.wind_speed_kmh,
                "precipitation_mm": obs.precipitation_mm,
                "weather_code": obs.weather_code,
                "observed_at": obs.observed_at,
            }
            for obs in observations
        ]
        stmt = pg_insert(RawObservationModel).values(values)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["location_id", "observed_at"]
        )
        result = await self._session.execute(stmt)
        return result.rowcount

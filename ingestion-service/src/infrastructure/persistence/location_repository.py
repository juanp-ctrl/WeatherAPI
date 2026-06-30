from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.location import Location
from .models import LocationModel


def _to_entity(model: LocationModel) -> Location:
    return Location(
        id=model.id,
        name=model.name,
        latitude=model.latitude,
        longitude=model.longitude,
        timezone=model.timezone,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyLocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, location_id: UUID) -> Location | None:
        result = await self._session.execute(
            select(LocationModel).where(LocationModel.id == location_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_all(self, active_only: bool = False) -> list[Location]:
        stmt = select(LocationModel)
        if active_only:
            stmt = stmt.where(LocationModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def save(self, location: Location) -> Location:
        model = LocationModel(
            id=location.id,
            name=location.name,
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            is_active=location.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, location: Location) -> Location:
        result = await self._session.execute(
            select(LocationModel).where(LocationModel.id == location.id)
        )
        model = result.scalar_one()
        model.name = location.name
        model.latitude = location.latitude
        model.longitude = location.longitude
        model.timezone = location.timezone
        model.is_active = location.is_active
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def soft_delete(self, location_id: UUID) -> bool:
        result = await self._session.execute(
            select(LocationModel).where(LocationModel.id == location_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        model.is_active = False
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        return True

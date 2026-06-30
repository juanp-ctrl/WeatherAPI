from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.watermark import Watermark
from .models import WatermarkModel


def _to_entity(model: WatermarkModel) -> Watermark:
    return Watermark(
        id=model.id,
        source=model.source,
        last_ingested_at=model.last_ingested_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyWatermarkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, source: str) -> Watermark | None:
        result = await self._session.execute(
            select(WatermarkModel).where(WatermarkModel.source == source)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def upsert(self, watermark: Watermark) -> Watermark:
        now = datetime.now(timezone.utc)
        stmt = (
            pg_insert(WatermarkModel)
            .values(
                id=watermark.id,
                source=watermark.source,
                last_ingested_at=watermark.last_ingested_at,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["source"],
                set_={
                    "last_ingested_at": watermark.last_ingested_at,
                    "updated_at": now,
                },
            )
            .returning(WatermarkModel)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one()
        return _to_entity(model)

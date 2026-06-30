from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.alert import Alert
from .models import AlertModel


def _to_entity(model: AlertModel) -> Alert:
    return Alert(
        id=model.id,
        processed_observation_id=model.processed_observation_id,
        rule_id=model.rule_id,
        alert_type=model.alert_type,
        severity=model.severity,
        message=model.message,
        acknowledged=model.acknowledged,
        created_at=model.created_at,
        acknowledged_at=model.acknowledged_at,
    )


class SQLAlchemyAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, alert_id: UUID) -> Alert | None:
        result = await self._session.execute(
            select(AlertModel).where(AlertModel.id == alert_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list(
        self,
        severity: str | None = None,
        acknowledged: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        stmt = select(AlertModel).order_by(AlertModel.created_at.desc())
        if severity is not None:
            stmt = stmt.where(AlertModel.severity == severity.upper())
        if acknowledged is not None:
            stmt = stmt.where(AlertModel.acknowledged.is_(acknowledged))
        stmt = stmt.limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [_to_entity(m) for m in result.scalars().all()]

    async def count(
        self,
        severity: str | None = None,
        acknowledged: bool | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(AlertModel)
        if severity is not None:
            stmt = stmt.where(AlertModel.severity == severity.upper())
        if acknowledged is not None:
            stmt = stmt.where(AlertModel.acknowledged.is_(acknowledged))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def save(self, alert: Alert) -> Alert:
        model = AlertModel(
            id=alert.id,
            processed_observation_id=alert.processed_observation_id,
            rule_id=alert.rule_id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            acknowledged=alert.acknowledged,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def acknowledge(self, alert_id: UUID) -> Alert | None:
        result = await self._session.execute(
            select(AlertModel).where(AlertModel.id == alert_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return None
        model.acknowledged = True
        model.acknowledged_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.processing_rule import ProcessingRule
from .models import ProcessingRuleModel


def _to_entity(model: ProcessingRuleModel) -> ProcessingRule:
    return ProcessingRule(
        id=model.id,
        metric=model.metric,
        operator=model.operator,
        threshold=model.threshold,
        severity=model.severity,
        alert_type=model.alert_type,
        message_template=model.message_template,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SQLAlchemyProcessingRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, rule_id: UUID) -> ProcessingRule | None:
        result = await self._session.execute(
            select(ProcessingRuleModel).where(ProcessingRuleModel.id == rule_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def list_active(self) -> list[ProcessingRule]:
        result = await self._session.execute(
            select(ProcessingRuleModel).where(
                ProcessingRuleModel.is_active.is_(True)
            )
        )
        return [_to_entity(m) for m in result.scalars().all()]

    async def list_all(self) -> list[ProcessingRule]:
        result = await self._session.execute(select(ProcessingRuleModel))
        return [_to_entity(m) for m in result.scalars().all()]

    async def save(self, rule: ProcessingRule) -> ProcessingRule:
        model = ProcessingRuleModel(
            id=rule.id,
            metric=rule.metric,
            operator=rule.operator,
            threshold=rule.threshold,
            severity=rule.severity,
            alert_type=rule.alert_type,
            message_template=rule.message_template,
            is_active=rule.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def update(self, rule: ProcessingRule) -> ProcessingRule:
        result = await self._session.execute(
            select(ProcessingRuleModel).where(ProcessingRuleModel.id == rule.id)
        )
        model = result.scalar_one()
        model.metric = rule.metric
        model.operator = rule.operator
        model.threshold = rule.threshold
        model.severity = rule.severity
        model.alert_type = rule.alert_type
        model.message_template = rule.message_template
        model.is_active = rule.is_active
        model.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(model)
        return _to_entity(model)

    async def delete(self, rule_id: UUID) -> bool:
        result = await self._session.execute(
            select(ProcessingRuleModel).where(ProcessingRuleModel.id == rule_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

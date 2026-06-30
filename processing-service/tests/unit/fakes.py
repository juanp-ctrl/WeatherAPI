"""In-memory fakes implementing repository and port protocols."""
from datetime import datetime
from uuid import UUID, uuid4

from src.domain.entities.alert import Alert
from src.domain.entities.processed_observation import ProcessedObservation
from src.domain.entities.processing_rule import ProcessingRule
from src.domain.entities.watermark import Watermark
from src.domain.ports.ingestion_client import RawObservationData


class FakeProcessedObservationRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, ProcessedObservation] = {}

    async def get_by_id(self, observation_id: UUID) -> ProcessedObservation | None:
        return self._store.get(observation_id)

    async def list(
        self,
        location_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ProcessedObservation]:
        items = list(self._store.values())
        if location_id:
            items = [o for o in items if o.location_id == location_id]
        return items[offset: offset + limit]

    async def count(self, location_id: UUID | None = None) -> int:
        items = list(self._store.values())
        if location_id:
            items = [o for o in items if o.location_id == location_id]
        return len(items)

    async def save(self, observation: ProcessedObservation) -> ProcessedObservation:
        self._store[observation.id] = observation
        return observation


class FakeAlertRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Alert] = {}

    async def get_by_id(self, alert_id: UUID) -> Alert | None:
        return self._store.get(alert_id)

    async def list(
        self,
        severity: str | None = None,
        acknowledged: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]:
        items = list(self._store.values())
        if severity:
            items = [a for a in items if a.severity == severity.upper()]
        if acknowledged is not None:
            items = [a for a in items if a.acknowledged == acknowledged]
        return items[offset: offset + limit]

    async def count(
        self,
        severity: str | None = None,
        acknowledged: bool | None = None,
    ) -> int:
        items = list(self._store.values())
        if severity:
            items = [a for a in items if a.severity == severity.upper()]
        if acknowledged is not None:
            items = [a for a in items if a.acknowledged == acknowledged]
        return len(items)

    async def save(self, alert: Alert) -> Alert:
        self._store[alert.id] = alert
        return alert

    async def acknowledge(self, alert_id: UUID) -> Alert | None:
        alert = self._store.get(alert_id)
        if alert is None:
            return None
        alert.acknowledged = True
        return alert


class FakeProcessingRuleRepository:
    def __init__(self, rules: list[ProcessingRule] | None = None) -> None:
        self._store: dict[UUID, ProcessingRule] = {r.id: r for r in (rules or [])}

    async def get_by_id(self, rule_id: UUID) -> ProcessingRule | None:
        return self._store.get(rule_id)

    async def list_active(self) -> list[ProcessingRule]:
        return [r for r in self._store.values() if r.is_active]

    async def list_all(self) -> list[ProcessingRule]:
        return list(self._store.values())

    async def save(self, rule: ProcessingRule) -> ProcessingRule:
        self._store[rule.id] = rule
        return rule

    async def update(self, rule: ProcessingRule) -> ProcessingRule:
        self._store[rule.id] = rule
        return rule

    async def delete(self, rule_id: UUID) -> bool:
        if rule_id not in self._store:
            return False
        del self._store[rule_id]
        return True


class FakeWatermarkRepository:
    def __init__(self) -> None:
        self._store: dict[str, Watermark] = {}

    async def get(self, source: str) -> Watermark | None:
        return self._store.get(source)

    async def upsert(self, watermark: Watermark) -> Watermark:
        self._store[watermark.source] = watermark
        return watermark


class FakeIngestionClient:
    def __init__(self, observations: list[RawObservationData] | None = None) -> None:
        self._observations = observations or []

    async def get_observations(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[RawObservationData]:
        if since is None:
            return self._observations[:limit]
        return [o for o in self._observations if o.ingested_at > since][:limit]

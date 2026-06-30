from __future__ import annotations

from typing import Protocol
from uuid import UUID

from ..entities.alert import Alert


class AlertRepository(Protocol):
    async def get_by_id(self, alert_id: UUID) -> Alert | None: ...
    async def list(
        self,
        severity: str | None = None,
        acknowledged: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Alert]: ...
    async def count(
        self,
        severity: str | None = None,
        acknowledged: bool | None = None,
    ) -> int: ...
    async def save(self, alert: Alert) -> Alert: ...
    async def acknowledge(self, alert_id: UUID) -> Alert | None: ...

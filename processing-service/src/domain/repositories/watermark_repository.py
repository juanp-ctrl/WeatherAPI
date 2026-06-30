from __future__ import annotations

from typing import Protocol

from ..entities.watermark import Watermark


class WatermarkRepository(Protocol):
    async def get(self, source: str) -> Watermark | None: ...
    async def upsert(self, watermark: Watermark) -> Watermark: ...

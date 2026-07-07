from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

import httpx

from ...domain.ports.ingestion_client import IngestionClient, RawObservationData

logger = logging.getLogger(__name__)


class HttpIngestionClient:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def get_observations(
        self,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[RawObservationData]:
        params: dict = {"limit": limit, "offset": 0}
        if since is not None:
            params["since"] = since.isoformat()

        url = f"{self._base_url}/api/v1/observations"
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch observations from ingestion-service: %s", exc)
            return []

        payload = response.json()
        items = payload.get("items", [])
        result: list[RawObservationData] = []

        for item in items:
            try:
                result.append(
                    RawObservationData(
                        id=UUID(item["id"]),
                        location_id=UUID(item["location_id"]),
                        observed_at=datetime.fromisoformat(item["observed_at"]),
                        ingested_at=datetime.fromisoformat(item["ingested_at"]),
                        temperature_c=item.get("temperature_c"),
                        humidity_pct=item.get("humidity_pct"),
                        wind_speed_kmh=item.get("wind_speed_kmh"),
                        precipitation_mm=item.get("precipitation_mm"),
                        weather_code=item.get("weather_code"),
                    )
                )
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed observation from ingestion-service: %s", exc)

        return result

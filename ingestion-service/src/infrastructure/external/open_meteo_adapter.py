from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from ...domain.entities.location import Location
from ...domain.entities.raw_observation import RawObservation

logger = logging.getLogger(__name__)

_CURRENT_VARIABLES = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation",
    "weather_code",
])


class OpenMeteoAdapter:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def fetch_current(self, location: Location) -> list[RawObservation]:
        url = f"{self._base_url}/v1/forecast"
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": _CURRENT_VARIABLES,
            "timezone": location.timezone,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Open-Meteo request failed for '%s': %s", location.name, exc)
            return []

        data = response.json()
        current = data.get("current")
        if not current:
            logger.warning("No 'current' block in Open-Meteo response for '%s'", location.name)
            return []

        try:
            observed_at = datetime.fromisoformat(current["time"]).replace(
                tzinfo=timezone.utc
            )
        except (KeyError, ValueError) as exc:
            logger.error("Invalid timestamp from Open-Meteo for '%s': %s", location.name, exc)
            return []

        observation = RawObservation(
            location_id=location.id,
            observed_at=observed_at,
            temperature_c=current.get("temperature_2m"),
            humidity_pct=current.get("relative_humidity_2m"),
            wind_speed_kmh=current.get("wind_speed_10m"),
            precipitation_mm=current.get("precipitation"),
            weather_code=current.get("weather_code"),
        )
        return [observation]

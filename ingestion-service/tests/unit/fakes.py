"""In-memory fakes implementing the repository and port protocols."""
from datetime import datetime
from uuid import UUID

from src.domain.entities.location import Location
from src.domain.entities.raw_observation import RawObservation


class FakeLocationRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, Location] = {}

    async def get_by_id(self, location_id: UUID) -> Location | None:
        return self._store.get(location_id)

    async def list_all(self, active_only: bool = False) -> list[Location]:
        locations = list(self._store.values())
        if active_only:
            locations = [loc for loc in locations if loc.is_active]
        return locations

    async def save(self, location: Location) -> Location:
        self._store[location.id] = location
        return location

    async def update(self, location: Location) -> Location:
        self._store[location.id] = location
        return location

    async def soft_delete(self, location_id: UUID) -> bool:
        location = self._store.get(location_id)
        if location is None:
            return False
        location.is_active = False
        return True


class FakeRawObservationRepository:
    def __init__(self) -> None:
        self._store: list[RawObservation] = []

    async def get_by_id(self, observation_id: UUID) -> RawObservation | None:
        return next((o for o in self._store if o.id == observation_id), None)

    async def list(
        self,
        location_id: UUID | None = None,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RawObservation]:
        results = self._store
        if location_id is not None:
            results = [o for o in results if o.location_id == location_id]
        if since is not None and all(o.ingested_at is not None for o in results):
            results = [o for o in results if o.ingested_at > since]
        return results[offset: offset + limit]

    async def count(
        self,
        location_id: UUID | None = None,
        since: datetime | None = None,
    ) -> int:
        results = self._store
        if location_id is not None:
            results = [o for o in results if o.location_id == location_id]
        if since is not None:
            results = [o for o in results if o.ingested_at and o.ingested_at > since]
        return len(results)

    async def save_many(self, observations: list[RawObservation]) -> int:
        stored = 0
        seen = {(o.location_id, o.observed_at) for o in self._store}
        for obs in observations:
            key = (obs.location_id, obs.observed_at)
            if key not in seen:
                self._store.append(obs)
                seen.add(key)
                stored += 1
        return stored


class FakeWeatherDataSource:
    def __init__(self, responses: dict | None = None) -> None:
        self._responses: dict[UUID, list[RawObservation]] = responses or {}

    async def fetch_current(self, location: Location) -> list[RawObservation]:
        return self._responses.get(location.id, [])

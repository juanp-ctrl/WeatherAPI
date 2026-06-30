from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.use_cases.list_observations import ListObservationsUseCase
from src.domain.entities.raw_observation import RawObservation
from .fakes import FakeRawObservationRepository


_counter = 0


def _make_obs(location_id=None, ingested_at=None):
    global _counter
    _counter += 1
    return RawObservation(
        location_id=location_id or uuid4(),
        observed_at=datetime(2026, 6, 30, _counter % 24, _counter % 60, tzinfo=timezone.utc),
        temperature_c=22.0,
        ingested_at=ingested_at or datetime(2026, 6, 30, 12, 5, tzinfo=timezone.utc),
    )


async def test_list_returns_all_observations():
    repo = FakeRawObservationRepository()
    for _ in range(3):
        await repo.save_many([_make_obs()])

    uc = ListObservationsUseCase(repo)
    result = await uc.execute()

    assert result.total == 3
    assert len(result.items) == 3


async def test_list_pagination():
    repo = FakeRawObservationRepository()
    for _ in range(5):
        await repo.save_many([_make_obs()])

    uc = ListObservationsUseCase(repo)
    result = await uc.execute(limit=2, offset=0)

    assert result.limit == 2
    assert result.offset == 0
    assert len(result.items) == 2
    assert result.total == 5


async def test_list_filter_by_location():
    repo = FakeRawObservationRepository()
    loc_a = uuid4()
    loc_b = uuid4()
    await repo.save_many([_make_obs(loc_a)])
    await repo.save_many([_make_obs(loc_a)])
    await repo.save_many([_make_obs(loc_b)])

    uc = ListObservationsUseCase(repo)
    result = await uc.execute(location_id=loc_a)

    assert result.total == 2
    assert all(str(item.location_id) == str(loc_a) for item in result.items)


async def test_list_filter_since():
    repo = FakeRawObservationRepository()
    early = datetime(2026, 6, 29, tzinfo=timezone.utc)
    late = datetime(2026, 6, 30, tzinfo=timezone.utc)

    obs_early = _make_obs(ingested_at=early)
    obs_late = _make_obs(ingested_at=late)
    await repo.save_many([obs_early, obs_late])

    uc = ListObservationsUseCase(repo)
    since = datetime(2026, 6, 29, 12, 0, tzinfo=timezone.utc)
    result = await uc.execute(since=since)

    assert result.total == 1
    assert len(result.items) == 1

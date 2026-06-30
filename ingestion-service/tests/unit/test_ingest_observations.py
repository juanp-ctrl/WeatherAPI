from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.use_cases.ingest_observations import IngestObservationsUseCase
from src.domain.entities.location import Location
from src.domain.entities.raw_observation import RawObservation
from .fakes import FakeLocationRepository, FakeRawObservationRepository, FakeWeatherDataSource


def _make_location(active: bool = True) -> Location:
    return Location(
        id=uuid4(),
        name="Test City",
        latitude=0.0,
        longitude=0.0,
        is_active=active,
    )


def _make_observation(location_id) -> RawObservation:
    return RawObservation(
        location_id=location_id,
        observed_at=datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc),
        temperature_c=28.5,
        humidity_pct=70.0,
        wind_speed_kmh=10.0,
        precipitation_mm=0.0,
        weather_code=1,
    )


async def test_ingest_fetches_only_active_locations():
    loc_repo = FakeLocationRepository()
    active_loc = _make_location(active=True)
    inactive_loc = _make_location(active=False)
    await loc_repo.save(active_loc)
    await loc_repo.save(inactive_loc)

    obs_data = {active_loc.id: [_make_observation(active_loc.id)]}
    weather_source = FakeWeatherDataSource(obs_data)
    obs_repo = FakeRawObservationRepository()

    uc = IngestObservationsUseCase(loc_repo, obs_repo, weather_source)
    result = await uc.execute()

    assert result.locations_processed == 1
    assert result.observations_stored == 1
    assert result.errors == []


async def test_ingest_stores_observations():
    loc_repo = FakeLocationRepository()
    loc = _make_location()
    await loc_repo.save(loc)

    obs = _make_observation(loc.id)
    weather_source = FakeWeatherDataSource({loc.id: [obs]})
    obs_repo = FakeRawObservationRepository()

    uc = IngestObservationsUseCase(loc_repo, obs_repo, weather_source)
    await uc.execute()

    all_obs = await obs_repo.list()
    assert len(all_obs) == 1
    assert all_obs[0].temperature_c == 28.5


async def test_ingest_idempotent_duplicate_ignored():
    loc_repo = FakeLocationRepository()
    loc = _make_location()
    await loc_repo.save(loc)

    obs = _make_observation(loc.id)
    weather_source = FakeWeatherDataSource({loc.id: [obs]})
    obs_repo = FakeRawObservationRepository()

    uc = IngestObservationsUseCase(loc_repo, obs_repo, weather_source)
    await uc.execute()
    result = await uc.execute()

    assert result.observations_stored == 0
    assert len(await obs_repo.list()) == 1


async def test_ingest_no_active_locations():
    loc_repo = FakeLocationRepository()
    obs_repo = FakeRawObservationRepository()
    weather_source = FakeWeatherDataSource()

    uc = IngestObservationsUseCase(loc_repo, obs_repo, weather_source)
    result = await uc.execute()

    assert result.locations_processed == 0
    assert result.observations_stored == 0


async def test_ingest_weather_source_error_recorded():
    class ErrorSource:
        async def fetch_current(self, location):
            raise RuntimeError("API down")

    loc_repo = FakeLocationRepository()
    loc = _make_location()
    await loc_repo.save(loc)

    obs_repo = FakeRawObservationRepository()

    uc = IngestObservationsUseCase(loc_repo, obs_repo, ErrorSource())
    result = await uc.execute()

    assert result.errors != []
    assert result.observations_stored == 0

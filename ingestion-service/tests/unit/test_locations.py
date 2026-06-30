from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.dtos.location_dto import LocationUpdateDTO
from src.application.use_cases.delete_location import DeleteLocationUseCase
from src.application.use_cases.get_location import GetLocationUseCase
from src.application.use_cases.list_locations import ListLocationsUseCase
from src.application.use_cases.update_location import UpdateLocationUseCase
from src.domain.entities.location import Location
from .fakes import FakeLocationRepository


async def test_get_location_found():
    repo = FakeLocationRepository()
    loc = Location(name="Miami", latitude=25.76, longitude=-80.19)
    await repo.save(loc)

    uc = GetLocationUseCase(repo)
    result = await uc.execute(loc.id)

    assert result.id == loc.id
    assert result.name == "Miami"


async def test_get_location_not_found():
    repo = FakeLocationRepository()
    uc = GetLocationUseCase(repo)

    with pytest.raises(HTTPException) as exc_info:
        await uc.execute(uuid4())

    assert exc_info.value.status_code == 404


async def test_list_locations_active_only():
    repo = FakeLocationRepository()
    active = Location(name="Active", latitude=0, longitude=0, is_active=True)
    inactive = Location(name="Inactive", latitude=0, longitude=0, is_active=False)
    await repo.save(active)
    await repo.save(inactive)

    uc = ListLocationsUseCase(repo)
    all_locs = await uc.execute(active_only=False)
    active_locs = await uc.execute(active_only=True)

    assert len(all_locs) == 2
    assert len(active_locs) == 1


async def test_update_location():
    repo = FakeLocationRepository()
    loc = Location(name="Old Name", latitude=0, longitude=0)
    await repo.save(loc)

    uc = UpdateLocationUseCase(repo)
    result = await uc.execute(loc.id, LocationUpdateDTO(name="New Name"))

    assert result.name == "New Name"


async def test_update_location_not_found():
    repo = FakeLocationRepository()
    uc = UpdateLocationUseCase(repo)

    with pytest.raises(HTTPException) as exc_info:
        await uc.execute(uuid4(), LocationUpdateDTO(name="X"))

    assert exc_info.value.status_code == 404


async def test_delete_location_soft_deletes():
    repo = FakeLocationRepository()
    loc = Location(name="City", latitude=0, longitude=0)
    await repo.save(loc)

    uc = DeleteLocationUseCase(repo)
    await uc.execute(loc.id)

    stored = await repo.get_by_id(loc.id)
    assert stored is not None
    assert stored.is_active is False

import pytest

from src.application.dtos.location_dto import LocationCreateDTO
from src.application.use_cases.register_location import RegisterLocationUseCase
from .fakes import FakeLocationRepository


@pytest.fixture
def repo():
    return FakeLocationRepository()


async def test_register_location_creates_and_returns_dto(repo):
    uc = RegisterLocationUseCase(repo)
    dto = LocationCreateDTO(name="Miami, FL", latitude=25.76, longitude=-80.19)
    result = await uc.execute(dto)

    assert result.name == "Miami, FL"
    assert result.latitude == 25.76
    assert result.longitude == -80.19
    assert result.timezone == "UTC"
    assert result.is_active is True
    assert result.id is not None


async def test_register_location_persists_in_repo(repo):
    uc = RegisterLocationUseCase(repo)
    dto = LocationCreateDTO(name="New York", latitude=40.71, longitude=-74.01)
    result = await uc.execute(dto)

    stored = await repo.get_by_id(result.id)
    assert stored is not None
    assert stored.name == "New York"


async def test_register_location_custom_timezone(repo):
    uc = RegisterLocationUseCase(repo)
    dto = LocationCreateDTO(
        name="Tokyo", latitude=35.68, longitude=139.69, timezone="Asia/Tokyo"
    )
    result = await uc.execute(dto)
    assert result.timezone == "Asia/Tokyo"

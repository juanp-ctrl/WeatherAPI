from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from ..application.use_cases.delete_location import DeleteLocationUseCase
from ..application.use_cases.get_location import GetLocationUseCase
from ..application.use_cases.get_observation import GetObservationUseCase
from ..application.use_cases.ingest_observations import IngestObservationsUseCase
from ..application.use_cases.list_locations import ListLocationsUseCase
from ..application.use_cases.list_observations import ListObservationsUseCase
from ..application.use_cases.register_location import RegisterLocationUseCase
from ..application.use_cases.update_location import UpdateLocationUseCase
from ..infrastructure.config.settings import get_settings
from ..infrastructure.external.open_meteo_adapter import OpenMeteoAdapter
from ..infrastructure.persistence.database import get_db_session
from ..infrastructure.persistence.location_repository import SQLAlchemyLocationRepository
from ..infrastructure.persistence.raw_observation_repository import (
    SQLAlchemyRawObservationRepository,
)

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    settings = get_settings()
    if not api_key or api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_location_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyLocationRepository(session)


def get_observation_repo(session: AsyncSession = Depends(get_session)):
    return SQLAlchemyRawObservationRepository(session)


def get_weather_source():
    settings = get_settings()
    return OpenMeteoAdapter(base_url=settings.open_meteo_base_url)


def get_register_location_uc(
    repo=Depends(get_location_repo),
) -> RegisterLocationUseCase:
    return RegisterLocationUseCase(repo)


def get_get_location_uc(repo=Depends(get_location_repo)) -> GetLocationUseCase:
    return GetLocationUseCase(repo)


def get_list_locations_uc(repo=Depends(get_location_repo)) -> ListLocationsUseCase:
    return ListLocationsUseCase(repo)


def get_update_location_uc(repo=Depends(get_location_repo)) -> UpdateLocationUseCase:
    return UpdateLocationUseCase(repo)


def get_delete_location_uc(repo=Depends(get_location_repo)) -> DeleteLocationUseCase:
    return DeleteLocationUseCase(repo)


def get_ingest_uc(
    loc_repo=Depends(get_location_repo),
    obs_repo=Depends(get_observation_repo),
    weather_source=Depends(get_weather_source),
) -> IngestObservationsUseCase:
    return IngestObservationsUseCase(loc_repo, obs_repo, weather_source)


def get_list_observations_uc(
    repo=Depends(get_observation_repo),
) -> ListObservationsUseCase:
    return ListObservationsUseCase(repo)


def get_get_observation_uc(
    repo=Depends(get_observation_repo),
) -> GetObservationUseCase:
    return GetObservationUseCase(repo)

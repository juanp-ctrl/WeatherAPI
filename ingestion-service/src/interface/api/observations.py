from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ...application.dtos.observation_dto import (
    IngestResultDTO,
    ObservationListResponseDTO,
    ObservationResponseDTO,
)
from ..dependencies import (
    GetObservationUCDep,
    IngestObservationsUCDep,
    ListObservationsUCDep,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/observations", tags=["observations"])


@router.get("", response_model=ObservationListResponseDTO)
async def list_observations(
    uc: ListObservationsUCDep,
    location_id: Annotated[UUID | None, Query()] = None,
    since: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ObservationListResponseDTO:
    return await uc.execute(
        location_id=location_id, since=since, limit=limit, offset=offset
    )


@router.get("/{observation_id}", response_model=ObservationResponseDTO)
async def get_observation(
    observation_id: UUID,
    uc: GetObservationUCDep,
) -> ObservationResponseDTO:
    return await uc.execute(observation_id)


@router.post(
    "/ingest",
    response_model=IngestResultDTO,
    dependencies=[Depends(require_api_key)],
)
async def trigger_ingestion(
    uc: IngestObservationsUCDep,
) -> IngestResultDTO:
    return await uc.execute()

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ...application.dtos.processed_observation_dto import (
    ProcessResultDTO,
    ProcessedObservationListDTO,
    ProcessedObservationResponseDTO,
)
from ..dependencies import (
    GetObsUseCaseDep,
    ListObsUseCaseDep,
    ProcessUseCaseDep,
    require_api_key,
)

router = APIRouter(tags=["processed-observations"])


@router.get("/api/v1/processed")
async def list_processed(
    uc: ListObsUseCaseDep,
    location_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProcessedObservationListDTO:
    return await uc.execute(location_id=location_id, limit=limit, offset=offset)


@router.get("/api/v1/processed/{observation_id}")
async def get_processed(
    observation_id: UUID,
    uc: GetObsUseCaseDep,
) -> ProcessedObservationResponseDTO:
    return await uc.execute(observation_id)


@router.post(
    "/api/v1/process",
    dependencies=[Depends(require_api_key)],
)
async def trigger_processing(uc: ProcessUseCaseDep) -> ProcessResultDTO:
    return await uc.execute()

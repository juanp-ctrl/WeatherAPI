from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ...application.dtos.alert_dto import AlertListDTO, AlertResponseDTO
from ..dependencies import (
    AckAlertUseCaseDep,
    GetAlertUseCaseDep,
    ListAlertsUseCaseDep,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    uc: ListAlertsUseCaseDep,
    severity: Annotated[str | None, Query()] = None,
    acknowledged: Annotated[bool | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AlertListDTO:
    return await uc.execute(
        severity=severity, acknowledged=acknowledged, limit=limit, offset=offset
    )


@router.get("/{alert_id}")
async def get_alert(alert_id: UUID, uc: GetAlertUseCaseDep) -> AlertResponseDTO:
    return await uc.execute(alert_id)


@router.patch(
    "/{alert_id}/acknowledge",
    dependencies=[Depends(require_api_key)],
)
async def acknowledge_alert(
    alert_id: UUID,
    uc: AckAlertUseCaseDep,
) -> AlertResponseDTO:
    return await uc.execute(alert_id)

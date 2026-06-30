from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from ...application.dtos.alert_dto import AlertListDTO, AlertResponseDTO
from ...application.use_cases.acknowledge_alert import AcknowledgeAlertUseCase
from ...application.use_cases.list_alerts import GetAlertUseCase, ListAlertsUseCase
from ..dependencies import (
    get_ack_alert_uc,
    get_get_alert_uc,
    get_list_alerts_uc,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=AlertListDTO)
async def list_alerts(
    severity: str | None = Query(None),
    acknowledged: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    uc: ListAlertsUseCase = Depends(get_list_alerts_uc),
) -> AlertListDTO:
    return await uc.execute(
        severity=severity, acknowledged=acknowledged, limit=limit, offset=offset
    )


@router.get("/{alert_id}", response_model=AlertResponseDTO)
async def get_alert(
    alert_id: UUID,
    uc: GetAlertUseCase = Depends(get_get_alert_uc),
) -> AlertResponseDTO:
    return await uc.execute(alert_id)


@router.patch(
    "/{alert_id}/acknowledge",
    response_model=AlertResponseDTO,
    dependencies=[Depends(require_api_key)],
)
async def acknowledge_alert(
    alert_id: UUID,
    uc: AcknowledgeAlertUseCase = Depends(get_ack_alert_uc),
) -> AlertResponseDTO:
    return await uc.execute(alert_id)

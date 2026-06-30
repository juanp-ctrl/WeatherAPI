from __future__ import annotations

from fastapi import HTTPException, status
from uuid import UUID

from ...domain.repositories.alert_repository import AlertRepository
from ..dtos.alert_dto import AlertListDTO, AlertResponseDTO


class ListAlertsUseCase:
    def __init__(self, repository: AlertRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        severity: str | None = None,
        acknowledged: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AlertListDTO:
        items = await self._repository.list(
            severity=severity, acknowledged=acknowledged, limit=limit, offset=offset
        )
        total = await self._repository.count(severity=severity, acknowledged=acknowledged)
        return AlertListDTO(
            items=[AlertResponseDTO.model_validate(a) for a in items],
            total=total,
            limit=limit,
            offset=offset,
        )


class GetAlertUseCase:
    def __init__(self, repository: AlertRepository) -> None:
        self._repository = repository

    async def execute(self, alert_id: UUID) -> AlertResponseDTO:
        alert = await self._repository.get_by_id(alert_id)
        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )
        return AlertResponseDTO.model_validate(alert)

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from ...domain.repositories.alert_repository import AlertRepository
from ..dtos.alert_dto import AlertResponseDTO


class AcknowledgeAlertUseCase:
    def __init__(self, repository: AlertRepository) -> None:
        self._repository = repository

    async def execute(self, alert_id: UUID) -> AlertResponseDTO:
        alert = await self._repository.acknowledge(alert_id)
        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found",
            )
        return AlertResponseDTO.model_validate(alert)

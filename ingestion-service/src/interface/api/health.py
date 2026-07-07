from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponseDTO(BaseModel):
    status: str
    service: str


@router.get("/health")
async def health_check() -> HealthResponseDTO:
    return HealthResponseDTO(status="ok", service="ingestion-service")

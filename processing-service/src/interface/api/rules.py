from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...application.dtos.rule_dto import RuleCreateDTO, RuleResponseDTO, RuleUpdateDTO
from ..dependencies import (
    CreateRuleUseCaseDep,
    DeleteRuleUseCaseDep,
    GetRuleUseCaseDep,
    ListRulesUseCaseDep,
    UpdateRuleUseCaseDep,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("")
async def list_rules(uc: ListRulesUseCaseDep) -> list[RuleResponseDTO]:
    return await uc.execute()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def create_rule(dto: RuleCreateDTO, uc: CreateRuleUseCaseDep) -> RuleResponseDTO:
    return await uc.execute(dto)


@router.get("/{rule_id}")
async def get_rule(rule_id: UUID, uc: GetRuleUseCaseDep) -> RuleResponseDTO:
    return await uc.execute(rule_id)


@router.put(
    "/{rule_id}",
    dependencies=[Depends(require_api_key)],
)
async def update_rule(
    rule_id: UUID,
    dto: RuleUpdateDTO,
    uc: UpdateRuleUseCaseDep,
) -> RuleResponseDTO:
    return await uc.execute(rule_id, dto)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
async def delete_rule(rule_id: UUID, uc: DeleteRuleUseCaseDep) -> None:
    await uc.execute(rule_id)

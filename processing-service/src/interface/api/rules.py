from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status

from ...application.dtos.rule_dto import RuleCreateDTO, RuleResponseDTO, RuleUpdateDTO
from ...application.use_cases.crud_rules import (
    CreateRuleUseCase,
    DeleteRuleUseCase,
    GetRuleUseCase,
    ListRulesUseCase,
    UpdateRuleUseCase,
)
from ..dependencies import (
    get_create_rule_uc,
    get_delete_rule_uc,
    get_get_rule_uc,
    get_list_rules_uc,
    get_update_rule_uc,
    require_api_key,
)

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("", response_model=list[RuleResponseDTO])
async def list_rules(
    uc: ListRulesUseCase = Depends(get_list_rules_uc),
) -> list[RuleResponseDTO]:
    return await uc.execute()


@router.post(
    "",
    response_model=RuleResponseDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def create_rule(
    dto: RuleCreateDTO,
    uc: CreateRuleUseCase = Depends(get_create_rule_uc),
) -> RuleResponseDTO:
    return await uc.execute(dto)


@router.get("/{rule_id}", response_model=RuleResponseDTO)
async def get_rule(
    rule_id: UUID,
    uc: GetRuleUseCase = Depends(get_get_rule_uc),
) -> RuleResponseDTO:
    return await uc.execute(rule_id)


@router.put(
    "/{rule_id}",
    response_model=RuleResponseDTO,
    dependencies=[Depends(require_api_key)],
)
async def update_rule(
    rule_id: UUID,
    dto: RuleUpdateDTO,
    uc: UpdateRuleUseCase = Depends(get_update_rule_uc),
) -> RuleResponseDTO:
    return await uc.execute(rule_id, dto)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_api_key)],
)
async def delete_rule(
    rule_id: UUID,
    uc: DeleteRuleUseCase = Depends(get_delete_rule_uc),
) -> None:
    await uc.execute(rule_id)

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from ...domain.entities.processing_rule import ProcessingRule
from ...domain.repositories.processing_rule_repository import ProcessingRuleRepository
from ..dtos.rule_dto import RuleCreateDTO, RuleResponseDTO, RuleUpdateDTO


class CreateRuleUseCase:
    def __init__(self, repository: ProcessingRuleRepository) -> None:
        self._repository = repository

    async def execute(self, dto: RuleCreateDTO) -> RuleResponseDTO:
        rule = ProcessingRule(
            metric=dto.metric,
            operator=dto.operator,
            threshold=dto.threshold,
            severity=dto.severity,
            alert_type=dto.alert_type,
            message_template=dto.message_template,
            is_active=dto.is_active,
        )
        saved = await self._repository.save(rule)
        return RuleResponseDTO.model_validate(saved)


class GetRuleUseCase:
    def __init__(self, repository: ProcessingRuleRepository) -> None:
        self._repository = repository

    async def execute(self, rule_id: UUID) -> RuleResponseDTO:
        rule = await self._repository.get_by_id(rule_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found",
            )
        return RuleResponseDTO.model_validate(rule)


class ListRulesUseCase:
    def __init__(self, repository: ProcessingRuleRepository) -> None:
        self._repository = repository

    async def execute(self) -> list[RuleResponseDTO]:
        rules = await self._repository.list_all()
        return [RuleResponseDTO.model_validate(r) for r in rules]


class UpdateRuleUseCase:
    def __init__(self, repository: ProcessingRuleRepository) -> None:
        self._repository = repository

    async def execute(self, rule_id: UUID, dto: RuleUpdateDTO) -> RuleResponseDTO:
        rule = await self._repository.get_by_id(rule_id)
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found",
            )
        if dto.metric is not None:
            rule.metric = dto.metric
        if dto.operator is not None:
            rule.operator = dto.operator
        if dto.threshold is not None:
            rule.threshold = dto.threshold
        if dto.severity is not None:
            rule.severity = dto.severity
        if dto.alert_type is not None:
            rule.alert_type = dto.alert_type
        if dto.message_template is not None:
            rule.message_template = dto.message_template
        if dto.is_active is not None:
            rule.is_active = dto.is_active

        updated = await self._repository.update(rule)
        return RuleResponseDTO.model_validate(updated)


class DeleteRuleUseCase:
    def __init__(self, repository: ProcessingRuleRepository) -> None:
        self._repository = repository

    async def execute(self, rule_id: UUID) -> None:
        deleted = await self._repository.delete(rule_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found",
            )

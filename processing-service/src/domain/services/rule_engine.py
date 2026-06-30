from __future__ import annotations

"""Pure domain function for evaluating processing rules against an observation."""
from dataclasses import dataclass
from uuid import UUID

from ..entities.processing_rule import ProcessingRule


@dataclass
class RuleMatch:
    rule_id: UUID
    alert_type: str
    severity: str
    message: str


def _evaluate_operator(value: float, operator: str, threshold: float) -> bool:
    match operator:
        case ">":
            return value > threshold
        case ">=":
            return value >= threshold
        case "<":
            return value < threshold
        case "<=":
            return value <= threshold
        case "==":
            return value == threshold
        case _:
            return False


def evaluate_rules(obs_data: dict, rules: list[ProcessingRule]) -> list[RuleMatch]:
    """Return a list of RuleMatch for every active rule whose threshold is breached.

    obs_data keys: temperature_c, humidity_pct, wind_speed_kmh, precipitation_mm,
                   weather_code, heat_index_c, wind_chill_c, feels_like_c
    """
    matches: list[RuleMatch] = []
    for rule in rules:
        if not rule.is_active:
            continue
        value = obs_data.get(rule.metric)
        if value is None:
            continue
        if not isinstance(value, (int, float)):
            continue
        if _evaluate_operator(float(value), rule.operator, rule.threshold):
            message = (
                rule.message_template
                .replace("{value}", str(round(float(value), 2)))
                .replace("{threshold}", str(rule.threshold))
            )
            matches.append(
                RuleMatch(
                    rule_id=rule.id,
                    alert_type=rule.alert_type,
                    severity=rule.severity,
                    message=message,
                )
            )
    return matches

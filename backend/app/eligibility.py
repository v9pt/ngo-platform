"""Eligibility rules as data. Pure functions: no I/O, so every outcome is testable.

Each rule is {"field", "op", "value"}. A rule is met, not_met, or unknown (the person did not
answer that question). Any not_met rule excludes; all met matches; otherwise it is possible.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

Outcome = Literal["met", "not_met", "unknown"]
Status = Literal["match", "possible", "excluded"]


@dataclass(frozen=True)
class RuleResult:
    field: str
    op: str
    value: Any
    outcome: Outcome


@dataclass(frozen=True)
class Evaluation:
    status: Status
    rules: list[RuleResult]


def _is_number(x: Any) -> bool:
    return isinstance(x, int | float) and not isinstance(x, bool)


def _eq(answer: Any, value: Any) -> bool:
    # Strict about bools: 1 must not satisfy True.
    if isinstance(value, bool) or isinstance(answer, bool):
        return isinstance(answer, bool) and isinstance(value, bool) and answer == value
    return bool(answer == value)


def _in(answer: Any, value: Any) -> bool:
    return answer in value


def _between(answer: Any, value: Any) -> bool:
    return _is_number(answer) and value[0] <= answer <= value[1]


def _gte(answer: Any, value: Any) -> bool:
    return _is_number(answer) and answer >= value


_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "eq": _eq,
    "in": _in,
    "between": _between,
    "gte": _gte,
}


def evaluate(rules: Sequence[Mapping[str, Any]], answers: Mapping[str, Any]) -> Evaluation:
    results: list[RuleResult] = []
    for rule in rules:
        field, op, value = rule["field"], rule["op"], rule["value"]
        check = _OPS.get(op)
        if check is None:
            raise ValueError(f"unsupported operator: {op!r}")
        answer = answers.get(field)
        if answer is None:
            outcome: Outcome = "unknown"
        else:
            outcome = "met" if check(answer, value) else "not_met"
        results.append(RuleResult(field, op, value, outcome))

    outcomes = {r.outcome for r in results}
    status: Status
    if "not_met" in outcomes:
        status = "excluded"
    elif "unknown" in outcomes:
        status = "possible"
    else:
        status = "match"
    return Evaluation(status, results)


# What each answer field accepts, so a mistyped rule is refused when it is saved, not at check time.
_BOOL_FIELDS = (
    "has_bpl_card",
    "pregnant",
    "first_child",
    "shg_member",
    "has_school_age_girl",
    "owns_pucca_house",
)
MARITAL_STATUSES = ("single", "married", "widow", "divorced", "separated")
RULE_FIELDS = ("age", "marital_status", "district", *_BOOL_FIELDS)


def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def rule_problem(rule: Mapping[str, Any]) -> str | None:
    """Explain why a rule cannot be saved, or return None when it is valid."""
    field, op = rule.get("field"), rule.get("op")
    value: Any = rule.get("value")
    if field not in RULE_FIELDS:
        return f"Unknown question: {field!r}."
    if field == "age":
        if op == "gte" and _is_int(value) and 0 <= value <= 120:
            return None
        if op == "between" and isinstance(value, list) and len(value) == 2:
            low, high = value
            if _is_int(low) and _is_int(high) and 0 <= low <= high <= 120:
                return None
        return "Age needs a minimum, or a minimum and maximum, between 0 and 120."
    if field in _BOOL_FIELDS:
        if op == "eq" and isinstance(value, bool):
            return None
        return f"{field} must be yes or no."
    allowed = MARITAL_STATUSES if field == "marital_status" else None
    items = value if op == "in" and isinstance(value, list) else [value] if op == "eq" else None
    if not items or not all(isinstance(x, str) and x for x in items):
        return f"{field} needs at least one value."
    if allowed and any(x not in allowed for x in items):
        return "Marital status has an unknown value."
    return None

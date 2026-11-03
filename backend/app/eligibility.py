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

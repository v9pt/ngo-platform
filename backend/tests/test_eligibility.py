"""Eligibility engine: pure rule evaluation with per-rule explanations."""

from typing import Any

import pytest

from app.eligibility import evaluate

WIDOW_RULES: list[dict[str, Any]] = [
    {"field": "marital_status", "op": "eq", "value": "widow"},
    {"field": "age", "op": "between", "value": [18, 79]},
    {"field": "has_bpl_card", "op": "eq", "value": True},
]


def test_all_rules_met_is_a_match_and_each_rule_is_shown() -> None:
    r = evaluate(WIDOW_RULES, {"marital_status": "widow", "age": 40, "has_bpl_card": True})
    assert r.status == "match"
    assert [x.outcome for x in r.rules] == ["met", "met", "met"]
    assert r.rules[1].field == "age" and r.rules[1].op == "between"


def test_any_rule_failed_is_excluded_even_if_others_are_unknown() -> None:
    r = evaluate(WIDOW_RULES, {"marital_status": "married"})
    assert r.status == "excluded"
    assert [x.outcome for x in r.rules] == ["not_met", "unknown", "unknown"]


def test_missing_answers_without_failures_is_possible() -> None:
    r = evaluate(WIDOW_RULES, {"marital_status": "widow", "age": 40})
    assert r.status == "possible"


def test_between_is_inclusive_and_gte_and_in_work() -> None:
    assert (
        evaluate([{"field": "age", "op": "between", "value": [18, 45]}], {"age": 45}).status
        == "match"
    )
    assert (
        evaluate([{"field": "age", "op": "between", "value": [18, 45]}], {"age": 46}).status
        == "excluded"
    )
    assert evaluate([{"field": "age", "op": "gte", "value": 30}], {"age": 30}).status == "match"
    rule = [{"field": "district", "op": "in", "value": ["Bhopal", "Sehore"]}]
    assert evaluate(rule, {"district": "Sehore"}).status == "match"
    assert evaluate(rule, {"district": "Indore"}).status == "excluded"


def test_a_scheme_with_no_rules_matches_everyone() -> None:
    assert evaluate([], {}).status == "match"


def test_bool_rule_does_not_accept_truthy_non_bool() -> None:
    rule = [{"field": "has_bpl_card", "op": "eq", "value": True}]
    assert evaluate(rule, {"has_bpl_card": 1}).status == "excluded"


def test_unknown_operator_is_a_loud_error_not_a_silent_pass() -> None:
    with pytest.raises(ValueError, match="operator"):
        evaluate([{"field": "age", "op": "regex", "value": "."}], {"age": 5})

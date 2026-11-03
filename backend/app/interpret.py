"""Turns a typed question into suggested finder answers. It never decides eligibility.

The person sees every suggestion, can change it, and only then does the rule engine run. Two
readers: keyword rules that always work, and Claude when a key is set. Where they disagree the
field is left blank and marked unsure, because a wrong pre-filled answer would be worse than
asking the question.
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol

from pydantic import ValidationError

from app.schemas import EligibilityAnswers, InterpretOut

DISTRICT_NAMES: dict[str, str] = {
    "bhopal": "Bhopal",
    "भोपाल": "Bhopal",
    "sehore": "Sehore",
    "सीहोर": "Sehore",
    "vidisha": "Vidisha",
    "विदिशा": "Vidisha",
    "raisen": "Raisen",
    "रायसेन": "Raisen",
    "rajgarh": "Rajgarh",
    "राजगढ़": "Rajgarh",
    "indore": "Indore",
    "इंदौर": "Indore",
    "dewas": "Dewas",
    "देवास": "Dewas",
    "ujjain": "Ujjain",
    "उज्जैन": "Ujjain",
    "narmadapuram": "Narmadapuram",
    "नर्मदापुरम": "Narmadapuram",
    "होशंगाबाद": "Narmadapuram",
}

_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NEGATION_AFTER = re.compile(r"^[^।.,;!?]{0,24}(नहीं|नही|ना\b|no\b|not\b)", re.IGNORECASE)
_NEGATION_BEFORE = re.compile(r"(\bno|\bnot|\bwithout|don't|do not|बिना)\s+(\w+\s+){0,3}$", re.I)
_AGE_PATTERNS = (
    re.compile(r"(\d{1,3})\s*(?:साल|वर्ष|बरस|years?|yrs?)", re.IGNORECASE),
    re.compile(r"(?:उम्र|आयु|age)\D{0,12}(\d{1,3})", re.IGNORECASE),
)
# Order matters: "अविवाहित" contains "विवाहित", so the longer word is tried first.
_MARITAL: tuple[tuple[str, str], ...] = (
    (r"विधवा|widow|पति (?:का|की) (?:निधन|मृत्यु)|पति नहीं रहे|पति गुज़र", "widow"),
    (r"तलाक|divorce", "divorced"),
    (r"अलग रह|separated", "separated"),
    (r"अविवाहित|कुँवारी|कुंवारी|unmarried|\bsingle\b", "single"),
    (r"विवाहित|शादीशुदा|\bmarried\b", "married"),
)
_YES_NO: tuple[tuple[str, str], ...] = (
    (r"बीपीएल|गरीबी रेखा|\bbpl\b", "has_bpl_card"),
    (r"गर्भवती|गर्भ से|pregnant", "pregnant"),
    (r"पहला बच्चा|पहली संतान|पहले बच्चे|first (?:child|baby)", "first_child"),
    (r"स्वयं सहायता|स्व-सहायता|स्वसहायता|समूह की सदस्य|\bshg\b|self[- ]help", "shg_member"),
    (r"(?:बेटी|बच्ची|बालिका|daughter|girl).{0,24}(?:स्कूल|पढ़|school)", "has_school_age_girl"),
    (r"(?:स्कूल|school).{0,24}(?:बेटी|बच्ची|बालिका|daughter|girl)", "has_school_age_girl"),
    (r"पक्का (?:मकान|घर)|pucca", "owns_pucca_house"),
)


def read_with_rules(text: str) -> dict[str, Any]:
    """Keyword reader for Hindi and English. Reports only what the text plainly says."""
    t = text.translate(_DIGITS)
    found: dict[str, Any] = {}
    for pattern in _AGE_PATTERNS:
        m = pattern.search(t)
        if m and int(m.group(1)) <= 120:
            found["age"] = int(m.group(1))
            break
    for pattern_text, status in _MARITAL:
        if re.search(pattern_text, t, re.IGNORECASE):
            found["marital_status"] = status
            break
    for pattern_text, field in _YES_NO:
        m = re.search(pattern_text, t, re.IGNORECASE)
        if m:
            negated = _NEGATION_AFTER.search(t[m.end() :]) or _NEGATION_BEFORE.search(
                t[: m.start()]
            )
            found[field] = not negated
    if re.search(r"कच्चा (?:मकान|घर)|kutcha|kachha", t, re.IGNORECASE):
        found["owns_pucca_house"] = False
    lowered = t.lower()
    for name, district in DISTRICT_NAMES.items():
        if name in lowered:
            found["district"] = district
            break
    return found


class AnswerReader(Protocol):
    async def read(self, text: str) -> dict[str, Any]: ...


def clean_model_answers(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep only values the finder accepts. One bad field must not lose the good ones."""
    kept: dict[str, Any] = {}
    for field, value in raw.items():
        if value is None or field not in EligibilityAnswers.model_fields:
            continue
        if field == "district" and value not in set(DISTRICT_NAMES.values()):
            continue
        try:
            EligibilityAnswers.model_validate({field: value})
        except ValidationError:
            continue
        kept[field] = value
    return kept


async def interpret(text: str, reader: AnswerReader | None) -> InterpretOut:
    """Combine both readers. Any failure of the model falls back to the keyword reader."""
    from_rules = read_with_rules(text)
    if reader is None:
        return InterpretOut(answers=from_rules, unsure=[], source="rules")
    try:
        from_model = clean_model_answers(await reader.read(text))
    except Exception:  # network, quota, refusal, malformed reply: the keyword reader still works
        return InterpretOut(answers=from_rules, unsure=[], source="rules")
    unsure = sorted(
        f for f in from_rules.keys() & from_model.keys() if from_rules[f] != from_model[f]
    )
    # The model can only add an age if the text holds a number or spells one out; a number it
    # invented would silently change results, so an age with no digit in the text goes to unsure.
    if (
        "age" in from_model
        and "age" not in from_rules
        and not re.search(r"\d", text.translate(_DIGITS))
    ):
        unsure.append("age")
    merged = {**from_rules, **from_model}
    return InterpretOut(
        answers={k: v for k, v in merged.items() if k not in unsure},
        unsure=sorted(set(unsure)),
        source="ai",
    )


def parse_model_json(raw: str) -> dict[str, Any]:
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("expected a JSON object")
    return parsed

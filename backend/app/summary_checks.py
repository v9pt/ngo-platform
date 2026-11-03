"""Deterministic checks for AI-drafted Hindi summaries: mostly Devanagari, bounded length, and
every number in the summary must also appear in the source notice. Pure functions."""

from __future__ import annotations

import re
from typing import Any

MIN_LEN, MAX_LEN = 40, 600
MIN_DEVANAGARI = 0.6

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?(?:\s*(?:लाख|lakh|lakhs))?", re.IGNORECASE)


def _numbers(text: str) -> set[int | float]:
    found: set[int | float] = set()
    for m in _NUMBER.finditer(text.translate(_DEVANAGARI_DIGITS)):
        raw = m.group(0)
        scale = 100_000 if re.search(r"लाख|lakh", raw, re.IGNORECASE) else 1
        digits = re.match(r"\d[\d,]*(?:\.\d+)?", raw)
        if digits is None:  # pragma: no cover - the pattern always starts with a digit
            continue
        value = float(digits.group(0).replace(",", "")) * scale
        found.add(int(value) if value == int(value) else value)
    return found


def _devanagari_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    return sum("ऀ" <= ch <= "ॿ" for ch in letters) / len(letters)


def run_checks(summary: str, source: str) -> dict[str, Any]:
    ratio = _devanagari_ratio(summary)
    unmatched = sorted(_numbers(summary) - _numbers(source))
    length_ok = MIN_LEN <= len(summary.strip()) <= MAX_LEN
    devanagari_ok = ratio >= MIN_DEVANAGARI
    numbers_ok = not unmatched
    return {
        "devanagari_ratio": round(ratio, 2),
        "devanagari_ok": devanagari_ok,
        "length_ok": length_ok,
        "numbers_match_source": numbers_ok,
        "unmatched_numbers": unmatched,
        "needs_attention": not (devanagari_ok and length_ok and numbers_ok),
    }

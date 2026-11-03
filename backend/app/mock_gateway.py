"""Test-mode card outcomes. Pure, so every path is unit-tested without a network.

Only published test numbers are accepted. Anything else is refused outright, which stops a
visitor from typing a real card into a demo. Foreign cards are blocked before any charge
(assumption A6: the trust holds no FCRA registration in this build).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Outcome = Literal["succeeded", "declined", "insufficient_funds", "foreign_card"]

TEST_CARDS: dict[str, Outcome] = {
    "4242424242424242": "succeeded",
    "4000000000000002": "declined",
    "4000000000009995": "insufficient_funds",
    "4000000000000101": "foreign_card",
}


class NotATestCard(ValueError):
    """The number is not one of the published test cards."""


@dataclass(frozen=True)
class Charge:
    outcome: Outcome

    @property
    def paid(self) -> bool:
        return self.outcome == "succeeded"


def normalize_card(raw: str) -> str:
    return "".join(ch for ch in raw if ch.isdigit())


def charge(card_number: str, issuing_country: str) -> Charge:
    """Decide what the gateway would do. The foreign block wins over every other outcome."""
    outcome = TEST_CARDS.get(normalize_card(card_number))
    if outcome is None:
        raise NotATestCard
    if issuing_country.upper() != "IN":
        return Charge("foreign_card")
    return Charge(outcome)

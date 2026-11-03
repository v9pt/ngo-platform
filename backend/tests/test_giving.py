"""Test-card payments, 80G certificates and monthly giving, through the API."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.mandates import add_month, charge_due_mandates
from app.mock_gateway import NotATestCard, charge
from app.pdf import rupees_in_words
from tests.test_donations_api import _donate, _live_campaign, _signed_in

GOOD = {"card_number": "4242 4242 4242 4242", "issuing_country": "IN"}


async def _pay(client: AsyncClient, donation_id: str, **card: str) -> Any:
    return await client.post(f"/v1/donations/{donation_id}/test-charge", json={**GOOD, **card})


def test_each_test_card_has_its_outcome() -> None:
    assert charge("4242424242424242", "IN").paid
    assert charge("4000000000000002", "IN").outcome == "declined"
    assert charge("4000-0000-0000-9995", "in").outcome == "insufficient_funds"
    assert charge("4000000000000101", "IN").outcome == "foreign_card"


def test_foreign_country_is_blocked_even_on_a_good_card() -> None:
    assert charge("4242424242424242", "US").outcome == "foreign_card"


def test_a_number_that_is_not_a_test_card_is_refused() -> None:
    with pytest.raises(NotATestCard):
        charge("5500005555555559", "IN")


@pytest.mark.parametrize(
    ("paise", "words"),
    [
        (10_000, "Rupees One Hundred only"),
        (75_100, "Rupees Seven Hundred Fifty One only"),
        (2_500_000, "Rupees Twenty Five Thousand only"),
        (
            12_345_650,
            "Rupees One Lakh Twenty Three Thousand Four Hundred Fifty Six and Fifty Paise only",
        ),
        (1_000_000_000, "Rupees One Crore only"),
    ],
)
def test_amount_in_words_uses_indian_grouping(paise: int, words: str) -> None:
    assert rupees_in_words(paise) == words


def test_add_month_clamps_to_the_end_of_a_short_month() -> None:
    assert add_month(date(2027, 1, 31)) == date(2027, 2, 28)
    assert add_month(date(2026, 12, 15)) == date(2027, 1, 15)


async def test_good_card_issues_a_receipt_straight_away(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client))).json()
    paid = await _pay(client, donation["id"])
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert paid.json()["receipt_number"].startswith("RCPT/")


async def test_paying_twice_returns_the_same_receipt(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client))).json()
    first = (await _pay(client, donation["id"])).json()
    second = (await _pay(client, donation["id"])).json()
    assert first["receipt_number"] == second["receipt_number"]


async def test_foreign_card_is_blocked_with_a_reason_and_no_receipt(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client))).json()
    out = (await _pay(client, donation["id"], issuing_country="GB")).json()
    assert out["status"] == "failed"
    assert out["failure_reason"] == "foreign_card"
    assert out["receipt_number"] is None


async def test_a_declined_payment_can_be_retried_and_clears_the_reason(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client))).json()
    declined = (await _pay(client, donation["id"], card_number="4000000000000002")).json()
    assert declined["status"] == "failed"
    retried = (await _pay(client, donation["id"])).json()
    assert retried["status"] == "paid"
    assert retried["failure_reason"] is None


async def test_real_looking_card_is_rejected_without_echoing_it(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client))).json()
    r = await _pay(client, donation["id"], card_number="5500005555555559")
    assert r.status_code == 422
    assert "5500" not in r.text


async def test_another_donors_donation_cannot_be_charged(client: AsyncClient) -> None:
    await _signed_in(client, "first@example.org")
    donation = (await _donate(client, await _live_campaign(client))).json()
    client.cookies.clear()
    await _signed_in(client, "second@example.org")
    assert (await _pay(client, donation["id"])).status_code == 404


async def test_pan_is_validated_masked_and_never_returned_whole(client: AsyncClient) -> None:
    await _signed_in(client)
    bad = await client.put("/v1/auth/me/pan", json={"pan": "ABCDE12345"})
    assert bad.status_code == 422
    ok = await client.put("/v1/auth/me/pan", json={"pan": "abcde1234f"})
    assert ok.status_code == 200
    assert "ABCDE1234F" not in ok.text
    assert ok.json()["pan_masked"]


async def test_pan_at_rest_is_encrypted(client: AsyncClient, app: Any) -> None:
    await _signed_in(client)
    await client.put("/v1/auth/me/pan", json={"pan": "ABCDE1234F"})
    async with app.state.engine.connect() as conn:
        stored = (await conn.execute(text("SELECT pan_ciphertext FROM users"))).scalar_one()
    assert "ABCDE1234F" not in stored


async def test_with_a_pan_the_receipt_is_an_80g_certificate(client: AsyncClient) -> None:
    await _signed_in(client)
    await client.put("/v1/auth/me/pan", json={"pan": "ABCDE1234F"})
    donation = (await _donate(client, await _live_campaign(client))).json()
    assert (await _pay(client, donation["id"])).json()["has_80g"] is True


async def test_without_a_pan_the_receipt_is_plain(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client))).json()
    assert (await _pay(client, donation["id"])).json()["has_80g"] is False


async def _due_mandate(client: AsyncClient, app: Any) -> str:
    donation = (await _donate(client, await _live_campaign(client), kind="monthly")).json()
    await _pay(client, donation["id"])
    mandates = (await client.get("/v1/mandates")).json()
    assert len(mandates) == 1
    async with app.state.engine.begin() as conn:
        await conn.execute(text("UPDATE mandates SET next_charge_on = '2026-01-01'"))
    return str(mandates[0]["id"])


async def test_one_time_gift_opens_no_mandate(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client))).json()
    await _pay(client, donation["id"])
    assert (await client.get("/v1/mandates")).json() == []


async def test_replaying_a_monthly_payment_opens_one_mandate_only(client: AsyncClient) -> None:
    await _signed_in(client)
    donation = (await _donate(client, await _live_campaign(client), kind="monthly")).json()
    await _pay(client, donation["id"])
    await _pay(client, donation["id"])
    assert len((await client.get("/v1/mandates")).json()) == 1


async def test_running_charges_twice_in_one_month_charges_once(
    client: AsyncClient, app: Any
) -> None:
    await _signed_in(client)
    await _due_mandate(client, app)
    now = datetime(2026, 1, 15, 6, 0, tzinfo=UTC)
    async with app.state.sessionmaker() as session, session.begin():
        assert await charge_due_mandates(session, app.state.config, now) == (1, 0)
    # Force the same mandate due again in the same month, as an overlapping run would see it.
    async with app.state.engine.begin() as conn:
        await conn.execute(text("UPDATE mandates SET next_charge_on = '2026-01-01'"))
    async with app.state.sessionmaker() as session, session.begin():
        assert await charge_due_mandates(session, app.state.config, now) == (0, 1)
    history = (await client.get("/v1/donations")).json()
    assert len(history) == 2
    assert all(d["receipt_number"] for d in history)


async def test_cancelled_mandate_is_not_charged(client: AsyncClient, app: Any) -> None:
    await _signed_in(client)
    mandate_id = await _due_mandate(client, app)
    cancelled = await client.post(f"/v1/mandates/{mandate_id}/cancel")
    assert cancelled.json()["status"] == "cancelled"
    now = datetime.now(UTC)
    async with app.state.sessionmaker() as session, session.begin():
        assert await charge_due_mandates(session, app.state.config, now) == (0, 0)


async def test_only_the_owner_can_cancel_a_mandate(client: AsyncClient, app: Any) -> None:
    await _signed_in(client, "first@example.org")
    mandate_id = await _due_mandate(client, app)
    client.cookies.clear()
    await _signed_in(client, "second@example.org")
    assert (await client.post(f"/v1/mandates/{mandate_id}/cancel")).status_code == 404
    assert (await client.post(f"/v1/mandates/{uuid.uuid4()}/cancel")).status_code == 404

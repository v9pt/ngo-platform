"""Donation creation (account required, idempotent) and the signed payment webhook."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from httpx import AsyncClient, Response
from sqlalchemy import text

from tests.conftest import make_config

DONOR = {"email": "asha@example.org", "password": "a-long-password-1", "full_name": "Asha Verma"}
WEBHOOK = "/v1/webhooks/mock-gateway"


async def _live_campaign(client: AsyncClient, status: str = "live") -> str:
    slug = f"camp-{uuid.uuid4().hex[:6]}"
    async with client._transport.app.state.engine.begin() as conn:  # type: ignore[attr-defined]
        await conn.execute(
            text(
                "INSERT INTO campaigns (slug, title_en, title_hi, status) "
                "VALUES (:s, 'Girls schooling', 'x', :st)"
            ),
            {"s": slug, "st": status},
        )
    return slug


async def _donate(
    client: AsyncClient,
    slug: str,
    amount: int = 50_000,
    key: str | None = None,
    kind: str = "one_time",
) -> Response:
    return await client.post(
        "/v1/donations",
        json={"campaign_slug": slug, "amount_paise": amount, "kind": kind},
        headers={"Idempotency-Key": key or uuid.uuid4().hex},
    )


def _signed(payload: dict[str, str], secret: str | None = None) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode()
    key = (secret or make_config().gateway_webhook_secret).encode()
    sig = hmac.new(key, body, hashlib.sha256).hexdigest()
    return body, {"X-Signature": sig, "Content-Type": "application/json"}


async def _signed_in(client: AsyncClient, email: str = DONOR["email"]) -> None:
    r = await client.post("/v1/auth/register", json={**DONOR, "email": email})
    assert r.status_code == 201


async def test_donating_requires_an_account(client: AsyncClient) -> None:
    slug = await _live_campaign(client)
    assert (await _donate(client, slug)).status_code == 401


async def test_create_donation_returns_pending_with_gateway_ref(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    r = await _donate(client, slug)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending" and body["amount_paise"] == 50_000
    assert body["gateway_ref"].startswith("mock_") and body["receipt_number"] is None


async def test_same_idempotency_key_returns_the_same_donation(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    first = await _donate(client, slug, key="idem-key-0001")
    again = await _donate(client, slug, key="idem-key-0001")
    assert again.status_code == 200
    assert again.json()["id"] == first.json()["id"]


async def test_amount_below_minimum_is_rejected(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    assert (await _donate(client, slug, amount=9_999)).status_code == 422


async def test_closed_or_unknown_campaign_is_rejected(client: AsyncClient) -> None:
    await _signed_in(client)
    closed = await _live_campaign(client, status="closed")
    assert (await _donate(client, closed)).status_code == 404
    assert (await _donate(client, "nope")).status_code == 404


async def test_missing_idempotency_key_is_rejected(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    r = await client.post(
        "/v1/donations", json={"campaign_slug": slug, "amount_paise": 50_000, "kind": "one_time"}
    )
    assert r.status_code == 422


async def test_signed_success_webhook_issues_receipt_and_replay_is_safe(
    client: AsyncClient,
) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    d = (await _donate(client, slug)).json()
    body, headers = _signed({"gateway_ref": d["gateway_ref"], "event": "payment.succeeded"})

    first = await client.post(WEBHOOK, content=body, headers=headers)
    replay = await client.post(WEBHOOK, content=body, headers=headers)

    assert first.status_code == 200 and replay.status_code == 200
    assert first.json()["receipt_number"] == replay.json()["receipt_number"]
    assert first.json()["receipt_number"].startswith("RCPT/")
    mine = (await client.get(f"/v1/donations/{d['id']}")).json()
    assert mine["status"] == "paid" and mine["receipt_number"] == first.json()["receipt_number"]


async def test_webhook_with_bad_or_missing_signature_changes_nothing(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    d = (await _donate(client, slug)).json()
    payload = {"gateway_ref": d["gateway_ref"], "event": "payment.succeeded"}
    body, headers = _signed(payload, secret="w" * 40)

    wrong = await client.post(WEBHOOK, content=body, headers=headers)
    missing = await client.post(WEBHOOK, content=body)

    assert wrong.status_code == 401 and missing.status_code == 401
    assert (await client.get(f"/v1/donations/{d['id']}")).json()["status"] == "pending"


async def test_failed_event_marks_pending_donation_failed_but_never_a_paid_one(
    client: AsyncClient,
) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    failed = (await _donate(client, slug)).json()
    paid = (await _donate(client, slug)).json()
    for d, event in ((failed, "payment.failed"), (paid, "payment.succeeded")):
        body, headers = _signed({"gateway_ref": d["gateway_ref"], "event": event})
        assert (await client.post(WEBHOOK, content=body, headers=headers)).status_code == 200
    body, headers = _signed({"gateway_ref": paid["gateway_ref"], "event": "payment.failed"})
    await client.post(WEBHOOK, content=body, headers=headers)

    assert (await client.get(f"/v1/donations/{failed['id']}")).json()["status"] == "failed"
    assert (await client.get(f"/v1/donations/{paid['id']}")).json()["status"] == "paid"


async def test_unknown_gateway_ref_in_signed_webhook_is_404(client: AsyncClient) -> None:
    body, headers = _signed({"gateway_ref": "mock_nope", "event": "payment.succeeded"})
    assert (await client.post(WEBHOOK, content=body, headers=headers)).status_code == 404


async def test_a_donor_cannot_read_someone_elses_donation(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    d = (await _donate(client, slug)).json()
    client.cookies.clear()
    await _signed_in(client, email="other@example.org")
    assert (await client.get(f"/v1/donations/{d['id']}")).status_code == 404

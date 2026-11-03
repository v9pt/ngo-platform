"""Receipt PDF: rendered from the immutable receipt snapshot, owner-only."""

from __future__ import annotations

from datetime import UTC, datetime

from httpx import AsyncClient

from app.models import Receipt
from app.pdf import receipt_html
from app.security import PanCipher
from tests.conftest import make_config
from tests.test_donations_api import (
    WEBHOOK,
    _donate,
    _live_campaign,
    _signed,
    _signed_in,
)


def _receipt(**over: object) -> Receipt:
    cipher = PanCipher(make_config().pan_encryption_key)
    fields: dict[str, object] = {
        "number": "RCPT/2026-27/000042",
        "issued_at": datetime(2026, 11, 3, 10, 0, tzinfo=UTC),
        "donor_name": "Asha Devi",
        "donor_email": "a@x.example",
        "donor_pan_ciphertext": cipher.encrypt("ABCDE1234F"),
        "amount_paise": 123_450,
        "campaign_title": "Girls' schooling",
        "trust_snapshot": {"name": "Demo Trust", "pan": "AAAAA0000A", "reg_80g": "DEMO/80G/1"},
    }
    fields.update(over)
    return Receipt(**fields)


def test_html_shows_number_rupees_and_masked_pan_only() -> None:
    html = receipt_html(_receipt(), PanCipher(make_config().pan_encryption_key))
    assert "RCPT/2026-27/000042" in html
    assert "1,234.50" in html
    assert "AB*******F" in html
    assert "1234F" not in html


def test_html_escapes_donor_supplied_text() -> None:
    html = receipt_html(
        _receipt(donor_name="<script>alert(1)</script>"),
        PanCipher(make_config().pan_encryption_key),
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


async def test_owner_downloads_pdf_after_payment(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    d = (await _donate(client, slug)).json()
    body, headers = _signed({"gateway_ref": d["gateway_ref"], "event": "payment.succeeded"})
    await client.post(WEBHOOK, content=body, headers=headers)

    r = await client.get(f"/v1/donations/{d['id']}/receipt.pdf")

    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


async def test_unpaid_donation_has_no_receipt_pdf(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    d = (await _donate(client, slug)).json()
    assert (await client.get(f"/v1/donations/{d['id']}/receipt.pdf")).status_code == 404


async def test_other_donor_cannot_download_receipt_pdf(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    d = (await _donate(client, slug)).json()
    body, headers = _signed({"gateway_ref": d["gateway_ref"], "event": "payment.succeeded"})
    await client.post(WEBHOOK, content=body, headers=headers)
    client.cookies.clear()
    await _signed_in(client, email="other@example.org")
    assert (await client.get(f"/v1/donations/{d['id']}/receipt.pdf")).status_code == 404

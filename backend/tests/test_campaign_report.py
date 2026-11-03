"""Admin campaign report and 10BD-style CSV export (assumption A5: common columns only)."""

from __future__ import annotations

import csv
import io
from typing import Any

from httpx import AsyncClient
from sqlalchemy import text

from app.seed import run_seed
from tests.conftest import TEST_DB_URL
from tests.test_donations_api import WEBHOOK, _donate, _live_campaign, _signed, _signed_in


async def _pay(client: AsyncClient, slug: str, amount: int) -> None:
    d = (await _donate(client, slug, amount=amount)).json()
    body, headers = _signed({"gateway_ref": d["gateway_ref"], "event": "payment.succeeded"})
    await client.post(WEBHOOK, content=body, headers=headers)


async def _as_admin(client: AsyncClient) -> None:
    run_seed(TEST_DB_URL, "DemoPass#2026")
    client.cookies.clear()
    await client.post(
        "/v1/auth/login", json={"email": "admin@demo.example", "password": "DemoPass#2026"}
    )


async def test_report_totals_paid_donations_only(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    await _pay(client, slug, 50_000)
    await _pay(client, slug, 25_000)
    await _donate(client, slug, amount=99_000)  # pending, excluded
    await _as_admin(client)
    r = (await client.get(f"/v1/admin/campaigns/{slug}/report")).json()
    assert r["paid_count"] == 2 and r["paid_paise"] == 75_000 and r["pending_count"] == 1


async def test_csv_has_one_row_per_receipt_and_masks_pan(client: AsyncClient, app: Any) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    await _pay(client, slug, 50_000)
    await _as_admin(client)
    r = await client.get(f"/v1/admin/campaigns/{slug}/donations.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 1
    assert rows[0]["receipt_number"].startswith("RCPT/") and rows[0]["amount_rupees"] == "500.00"
    assert set(rows[0]) >= {"receipt_date", "donor_name", "donor_pan", "amount_rupees"}


async def test_csv_neutralises_spreadsheet_formulas_in_names(client: AsyncClient, app: Any) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    await _pay(client, slug, 50_000)
    async with app.state.engine.begin() as conn:
        # Receipts are immutable; edit the user, then issue a fresh receipt via a new donation.
        await conn.execute(text("UPDATE users SET full_name = '=HYPERLINK(\"http://x\")'"))
    await _pay(client, slug, 20_000)
    await _as_admin(client)
    rows = list(
        csv.DictReader(
            io.StringIO((await client.get(f"/v1/admin/campaigns/{slug}/donations.csv")).text)
        )
    )
    assert any(r["donor_name"].startswith("'=") for r in rows)
    assert not any(r["donor_name"].startswith("=") for r in rows)


async def test_report_and_csv_are_admin_only_not_editor(client: AsyncClient) -> None:
    slug = await _live_campaign(client)
    run_seed(TEST_DB_URL, "DemoPass#2026")
    await client.post(
        "/v1/auth/login", json={"email": "editor@demo.example", "password": "DemoPass#2026"}
    )
    assert (await client.get(f"/v1/admin/campaigns/{slug}/report")).status_code == 403
    assert (await client.get(f"/v1/admin/campaigns/{slug}/donations.csv")).status_code == 403


async def test_unknown_campaign_is_404(client: AsyncClient) -> None:
    await _as_admin(client)
    assert (await client.get("/v1/admin/campaigns/nope/report")).status_code == 404

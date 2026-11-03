"""Public campaign list: only live campaigns, with money raised so far from paid donations."""

from httpx import AsyncClient
from sqlalchemy import text

from tests.test_donations_api import (
    WEBHOOK,
    _donate,
    _live_campaign,
    _signed,
    _signed_in,
)


async def test_lists_only_live_campaigns(client: AsyncClient) -> None:
    live = await _live_campaign(client)
    await _live_campaign(client, status="draft")
    await _live_campaign(client, status="closed")
    rows = (await client.get("/v1/campaigns")).json()
    assert [r["slug"] for r in rows] == [live]
    assert rows[0]["raised_paise"] == 0


async def test_raised_counts_paid_donations_only(client: AsyncClient) -> None:
    await _signed_in(client)
    slug = await _live_campaign(client)
    paid = (await _donate(client, slug, amount=50_000)).json()
    await _donate(client, slug, amount=70_000)  # still pending
    body, headers = _signed({"gateway_ref": paid["gateway_ref"], "event": "payment.succeeded"})
    await client.post(WEBHOOK, content=body, headers=headers)
    rows = (await client.get("/v1/campaigns")).json()
    assert rows[0]["raised_paise"] == 50_000


async def test_goal_is_reported_when_set(client: AsyncClient) -> None:
    slug = await _live_campaign(client)
    async with client._transport.app.state.engine.begin() as conn:  # type: ignore[attr-defined]
        await conn.execute(
            text("UPDATE campaigns SET goal_paise = 1000000 WHERE slug = :s"), {"s": slug}
        )
    assert (await client.get("/v1/campaigns")).json()[0]["goal_paise"] == 1_000_000

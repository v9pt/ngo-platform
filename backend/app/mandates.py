"""Monthly giving in test mode: open a mandate on the first payment, then charge when due.

Each run is safe to repeat. The idempotency key includes the month, so a mandate cannot be
charged twice for the same month even if two runs overlap.
"""

from __future__ import annotations

import calendar
import secrets
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.models import Donation, Mandate
from app.receipts import IST, issue_receipt


def add_month(d: date) -> date:
    """Same day next month, clamped: 31 Jan becomes 28 or 29 Feb."""
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


async def open_mandate_if_monthly(session: AsyncSession, donation: Donation, now: datetime) -> None:
    """Called after a successful payment. Replays find the existing row and do nothing."""
    if donation.kind != "monthly":
        return
    # Renewals carry a mandate-prefixed key and must not open a mandate of their own.
    if donation.idempotency_key.startswith("mandate:"):
        return
    existing = await session.scalar(
        select(Mandate.id).where(Mandate.first_donation_id == donation.id)
    )
    if existing is None:
        session.add(
            Mandate(
                donor_id=donation.donor_id,
                campaign_id=donation.campaign_id,
                first_donation_id=donation.id,
                amount_paise=donation.amount_paise,
                next_charge_on=add_month(now.astimezone(IST).date()),
            )
        )
        await session.flush()


async def charge_due_mandates(
    session: AsyncSession, config: Config, now: datetime
) -> tuple[int, int]:
    """Charge every active mandate that is due. Returns (charged, skipped as already charged)."""
    today = now.astimezone(IST).date()
    due = await session.scalars(
        select(Mandate)
        .where(Mandate.status == "active", Mandate.next_charge_on <= today)
        .order_by(Mandate.next_charge_on, Mandate.id)
        .with_for_update(skip_locked=True)
    )
    charged = skipped = 0
    for mandate in due.all():
        key = f"mandate:{mandate.id}:{mandate.next_charge_on:%Y-%m}"
        already = await session.scalar(
            select(Donation.id).where(
                Donation.donor_id == mandate.donor_id, Donation.idempotency_key == key
            )
        )
        if already is None:
            donation = Donation(
                donor_id=mandate.donor_id,
                campaign_id=mandate.campaign_id,
                amount_paise=mandate.amount_paise,
                kind="monthly",
                gateway_ref=f"mock_{secrets.token_hex(16)}",
                idempotency_key=key,
            )
            session.add(donation)
            await session.flush()
            await issue_receipt(session, donation.gateway_ref, config, now)
            charged += 1
        else:
            skipped += 1
        mandate.next_charge_on = add_month(mandate.next_charge_on)
    await session.flush()
    return charged, skipped

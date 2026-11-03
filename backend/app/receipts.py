"""Receipt issuing: one transaction, fixed lock order, exactly one receipt per donation.

Lock order is donation row, then the financial-year counter row. The counter row stays locked
until commit, so numbers are gapless: a rolled-back transaction never consumes a number.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.models import Campaign, Donation, Receipt, User
from app.seed import current_fy

IST = ZoneInfo("Asia/Kolkata")


class DonationNotFound(LookupError):
    pass


async def issue_receipt(
    session: AsyncSession, gateway_ref: str, config: Config, now: datetime
) -> Receipt:
    """Mark the donation paid and issue its receipt. Replays return the existing receipt.

    Must run inside the caller's transaction; the caller commits.
    """
    donation = await session.scalar(
        select(Donation).where(Donation.gateway_ref == gateway_ref).with_for_update()
    )
    if donation is None:
        raise DonationNotFound(gateway_ref)

    existing = await session.scalar(select(Receipt).where(Receipt.donation_id == donation.id))
    if existing is not None:
        return existing

    fy = current_fy(now.astimezone(IST).date())
    seq = await session.scalar(
        text(
            "INSERT INTO receipt_counters (fy, last_seq) VALUES (:fy, 1) "
            "ON CONFLICT (fy) DO UPDATE SET last_seq = receipt_counters.last_seq + 1 "
            "RETURNING last_seq"
        ),
        {"fy": fy},
    )
    if seq is None:  # pragma: no cover - RETURNING always yields a row
        raise RuntimeError("receipt counter returned no row")

    donor = await session.get(User, donation.donor_id)
    campaign = await session.get(Campaign, donation.campaign_id)
    if donor is None or campaign is None:  # pragma: no cover - FKs guarantee both
        raise RuntimeError("donation references a missing donor or campaign")

    receipt = Receipt(
        donation_id=donation.id,
        fy=fy,
        seq=seq,
        number=f"RCPT/{fy}/{seq:06d}",
        issued_at=now,
        donor_name=donor.full_name,
        donor_email=donor.email,
        donor_pan_ciphertext=donor.pan_ciphertext,
        amount_paise=donation.amount_paise,
        campaign_title=campaign.title_en,
        trust_snapshot={
            "name": config.trust_name,
            "pan": config.trust_pan,
            "reg_80g": config.trust_80g_reg,
        },
    )
    session.add(receipt)
    donation.status = "paid"
    donation.paid_at = now
    await session.flush()
    return receipt

"""Receipt issuing: sequential numbers per financial year, exactly once per donation."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Config
from app.models import Campaign, Donation, Receipt, User
from app.receipts import DonationNotFound, issue_receipt
from app.security import PanCipher
from tests.conftest import make_config

PAID_AT = datetime(2026, 11, 3, 10, 0, tzinfo=UTC)


async def _make_donations(
    maker: async_sessionmaker[AsyncSession], count: int, pan: str | None = None
) -> list[str]:
    config = make_config()
    async with maker() as s, s.begin():
        user = User(
            email=f"d{uuid.uuid4().hex[:8]}@x.example",
            password_hash="x",
            full_name="Asha Devi",
            pan_ciphertext=PanCipher(config.pan_encryption_key).encrypt(pan) if pan else None,
        )
        campaign = Campaign(
            slug=f"c{uuid.uuid4().hex[:8]}", title_en="Girls' schooling", title_hi="x"
        )
        s.add_all([user, campaign])
        await s.flush()
        refs = [f"mock_{uuid.uuid4().hex}" for _ in range(count)]
        s.add_all(
            Donation(
                donor_id=user.id,
                campaign_id=campaign.id,
                amount_paise=50_000,
                kind="one_time",
                gateway_ref=r,
                idempotency_key=uuid.uuid4().hex,
            )
            for r in refs
        )
    return refs


async def _issue(maker: async_sessionmaker[AsyncSession], ref: str, config: Config) -> Receipt:
    async with maker() as s, s.begin():
        return await issue_receipt(s, ref, config, now=PAID_AT)


async def test_issue_assigns_first_number_and_snapshots_donation(app: object) -> None:
    maker = app.state.sessionmaker  # type: ignore[attr-defined]
    config = make_config()
    (ref,) = await _make_donations(maker, 1, pan="ABCDE1234F")

    receipt = await _issue(maker, ref, config)

    assert receipt.number == "RCPT/2026-27/000001"
    assert (receipt.fy, receipt.seq, receipt.amount_paise) == ("2026-27", 1, 50_000)
    assert receipt.donor_name == "Asha Devi"
    assert receipt.campaign_title == "Girls' schooling"
    assert receipt.trust_snapshot["name"] == config.trust_name
    assert receipt.donor_pan_ciphertext is not None
    assert "ABCDE1234F" not in receipt.donor_pan_ciphertext
    async with maker() as s:
        donation = await s.scalar(select(Donation).where(Donation.gateway_ref == ref))
        assert donation is not None
        assert donation.status == "paid" and donation.paid_at == PAID_AT


async def test_replayed_payment_returns_same_receipt_without_advancing_counter(
    app: object,
) -> None:
    maker = app.state.sessionmaker  # type: ignore[attr-defined]
    (ref,) = await _make_donations(maker, 1)

    first = await _issue(maker, ref, make_config())
    again = await _issue(maker, ref, make_config())

    assert again.id == first.id and again.number == first.number
    async with maker() as s:
        last = await s.scalar(text("SELECT last_seq FROM receipt_counters WHERE fy='2026-27'"))
    assert last == 1


async def test_unknown_gateway_ref_is_rejected(app: object) -> None:
    maker = app.state.sessionmaker  # type: ignore[attr-defined]
    with pytest.raises(DonationNotFound):
        await _issue(maker, "mock_does_not_exist", make_config())


async def test_april_starts_a_new_financial_year_at_one(app: object) -> None:
    maker = app.state.sessionmaker  # type: ignore[attr-defined]
    march, april = await _make_donations(maker, 2)
    async with maker() as s, s.begin():
        r1 = await issue_receipt(
            s, march, make_config(), now=datetime(2027, 3, 31, 18, 29, tzinfo=UTC)
        )  # 23:59 IST, still FY 2026-27
    async with maker() as s, s.begin():
        r2 = await issue_receipt(
            s, april, make_config(), now=datetime(2027, 3, 31, 18, 31, tzinfo=UTC)
        )  # 00:01 IST on 1 April
    assert r1.number == "RCPT/2026-27/000001"
    assert r2.number == "RCPT/2027-28/000001"


async def test_200_parallel_payments_get_unique_gapless_numbers(app: object) -> None:
    maker = app.state.sessionmaker  # type: ignore[attr-defined]
    refs = await _make_donations(maker, 200)
    config = make_config()

    # Every ref is paid twice at once (webhook retry) to exercise replay under contention.
    results = await asyncio.gather(*(_issue(maker, r, config) for r in refs * 2))

    by_ref: dict[str, set[str]] = {}
    for ref, rec in zip(refs * 2, results, strict=True):
        by_ref.setdefault(ref, set()).add(rec.number)
    assert all(len(numbers) == 1 for numbers in by_ref.values())
    async with maker() as s:
        seqs = sorted((await s.scalars(select(Receipt.seq))).all())
    assert seqs == list(range(1, 201))

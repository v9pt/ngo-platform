"""Invariants that must hold in the database itself, whatever the application does."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError


async def _seed_donation(conn: object) -> str:
    await conn.execute(  # type: ignore[attr-defined]
        text("INSERT INTO users (email, password_hash, full_name) VALUES ('d@example.org','x','D')")
    )
    await conn.execute(  # type: ignore[attr-defined]
        text("INSERT INTO campaigns (slug, title_en, title_hi) VALUES ('c1','C','सी')")
    )
    row = await conn.execute(  # type: ignore[attr-defined]
        text(
            "INSERT INTO donations (donor_id, campaign_id, amount_paise, kind, gateway_ref, "
            "idempotency_key) SELECT u.id, c.id, 50000, 'one_time', 'gw_1', 'k1' "
            "FROM users u, campaigns c RETURNING id"
        )
    )
    return str(row.scalar_one())


async def test_receipts_cannot_be_updated_or_deleted(app: object) -> None:
    async with app.state.engine.begin() as conn:  # type: ignore[attr-defined]
        donation_id = await _seed_donation(conn)
        await conn.execute(
            text(
                "INSERT INTO receipts (donation_id, fy, seq, number, donor_name, donor_email, "
                "amount_paise, campaign_title, trust_snapshot) VALUES "
                "(:d, '2026-27', 1, 'R/2026-27/000001', 'D', 'd@example.org', 50000, 'C', '{}')"
            ),
            {"d": donation_id},
        )
    for stmt in ("UPDATE receipts SET donor_name='X'", "DELETE FROM receipts"):
        with pytest.raises(DBAPIError, match="immutable"):
            async with app.state.engine.begin() as conn:  # type: ignore[attr-defined]
                await conn.execute(text(stmt))


async def test_receipt_sequence_is_unique_per_financial_year(app: object) -> None:
    async with app.state.engine.begin() as conn:  # type: ignore[attr-defined]
        donation_id = await _seed_donation(conn)
        await conn.execute(
            text(
                "INSERT INTO donations (donor_id, campaign_id, amount_paise, kind, gateway_ref, "
                "idempotency_key) SELECT donor_id, campaign_id, 50000, 'one_time', 'gw_2', 'k2' "
                "FROM donations LIMIT 1"
            )
        )
        second = (
            await conn.execute(text("SELECT id FROM donations WHERE gateway_ref='gw_2'"))
        ).scalar_one()
        insert = (
            "INSERT INTO receipts (donation_id, fy, seq, number, donor_name, donor_email, "
            "amount_paise, campaign_title, trust_snapshot) VALUES "
            "(:d, '2026-27', 1, :n, 'D', 'd@example.org', 50000, 'C', '{}')"
        )
        await conn.execute(text(insert), {"d": donation_id, "n": "A"})
    with pytest.raises(IntegrityError):
        async with app.state.engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.execute(text(insert), {"d": str(second), "n": "B"})


@pytest.mark.parametrize("amount", [0, -100, 9999])
async def test_donation_below_minimum_is_rejected(app: object, amount: int) -> None:
    with pytest.raises(IntegrityError):
        async with app.state.engine.begin() as conn:  # type: ignore[attr-defined]
            await _seed_donation(conn)
            await conn.execute(text("UPDATE donations SET amount_paise = :a"), {"a": amount})


async def test_duplicate_idempotency_key_for_same_donor_is_rejected(app: object) -> None:
    with pytest.raises(IntegrityError):
        async with app.state.engine.begin() as conn:  # type: ignore[attr-defined]
            await _seed_donation(conn)
            await conn.execute(
                text(
                    "INSERT INTO donations (donor_id, campaign_id, amount_paise, kind, gateway_ref, "
                    "idempotency_key) SELECT donor_id, campaign_id, 50000, 'one_time', 'gw_x', 'k1' "
                    "FROM donations LIMIT 1"
                )
            )


async def test_approved_summary_must_record_who_approved(app: object) -> None:
    with pytest.raises(IntegrityError):
        async with app.state.engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.execute(
                text(
                    "INSERT INTO schemes (code, title_en, title_hi, need, benefit_en, who_can_apply_en, "
                    "source_url, last_checked) VALUES ('S1','t','ट','pension','b','w','https://x.gov.in',"
                    "'2026-09-01')"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO scheme_summaries (scheme_id, hindi_text, source, status) "
                    "SELECT id, 'सार', 'ai', 'approved' FROM schemes"
                )
            )

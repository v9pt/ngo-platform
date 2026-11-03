"""Donation creation, lookup, and the signed (mock) payment-gateway webhook."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.db import db_session
from app.deps import current_user, get_config
from app.mandates import open_mandate_if_monthly
from app.mock_gateway import NotATestCard, charge
from app.models import Campaign, Donation, Mandate, Receipt, User
from app.pdf import render_receipt_pdf
from app.receipts import DonationNotFound, issue_receipt
from app.schemas import DonationCreate, DonationOut, MandateOut, TestCharge, WebhookEvent

router = APIRouter(tags=["donations"])


def _out(d: Donation, campaign: Campaign, receipt: Receipt | None) -> DonationOut:
    return DonationOut(
        id=d.id,
        campaign_slug=campaign.slug,
        campaign_title_en=campaign.title_en,
        campaign_title_hi=campaign.title_hi,
        amount_paise=d.amount_paise,
        kind=d.kind,
        status=d.status,
        gateway_ref=d.gateway_ref,
        receipt_number=receipt.number if receipt else None,
        has_80g=bool(receipt and receipt.donor_pan_ciphertext),
        failure_reason=d.failure_reason,
        created_at=d.created_at,
    )


@router.post("/v1/donations", status_code=201, response_model=DonationOut)
async def create_donation(
    body: DonationCreate,
    response: Response,
    idempotency_key: str = Header(min_length=8, max_length=80),
    user: User = Depends(current_user),
    session: AsyncSession = db_session,
) -> DonationOut:
    campaign = await session.scalar(
        select(Campaign).where(Campaign.slug == body.campaign_slug, Campaign.status == "live")
    )
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

    existing = await session.scalar(
        select(Donation).where(
            Donation.donor_id == user.id, Donation.idempotency_key == idempotency_key
        )
    )
    if existing is None:
        donation = Donation(
            donor_id=user.id,
            campaign_id=campaign.id,
            amount_paise=body.amount_paise,
            kind=body.kind,
            gateway_ref=f"mock_{secrets.token_hex(16)}",
            idempotency_key=idempotency_key,
        )
        session.add(donation)
        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:  # concurrent retry with the same key won the race
            existing = await session.scalar(
                select(Donation).where(
                    Donation.donor_id == user.id, Donation.idempotency_key == idempotency_key
                )
            )
        else:
            await session.refresh(donation, ["created_at"])
            return _out(donation, campaign, None)

    if existing is None:  # pragma: no cover - conflict implies the row exists
        raise HTTPException(status_code=409, detail="Please retry.")
    response.status_code = 200
    return await _load_out(session, existing)


async def _load_out(session: AsyncSession, d: Donation) -> DonationOut:
    campaign = await session.get(Campaign, d.campaign_id)
    if campaign is None:  # pragma: no cover - FK guarantees it
        raise HTTPException(status_code=404, detail="Campaign not found.")
    receipt = await session.scalar(select(Receipt).where(Receipt.donation_id == d.id))
    await session.refresh(d, ["created_at"])
    return _out(d, campaign, receipt)


@router.get("/v1/donations", response_model=list[DonationOut])
async def list_my_donations(
    user: User = Depends(current_user),
    session: AsyncSession = db_session,
) -> list[DonationOut]:
    rows = await session.execute(
        select(Donation, Campaign, Receipt)
        .join(Campaign, Campaign.id == Donation.campaign_id)
        .outerjoin(Receipt, Receipt.donation_id == Donation.id)
        .where(Donation.donor_id == user.id)
        .order_by(Donation.created_at.desc(), Donation.id)
        .limit(200)
    )
    return [_out(d, campaign, receipt) for d, campaign, receipt in rows.all()]


@router.get("/v1/donations/{donation_id}", response_model=DonationOut)
async def get_donation(
    donation_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = db_session,
) -> DonationOut:
    donation = await session.get(Donation, donation_id)
    # 404, not 403, so ids of other donors' donations are not confirmable.
    if donation is None or donation.donor_id != user.id:
        raise HTTPException(status_code=404, detail="Donation not found.")
    return await _load_out(session, donation)


@router.get("/v1/donations/{donation_id}/receipt.pdf")
async def receipt_pdf(
    donation_id: uuid.UUID,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = db_session,
) -> Response:
    receipt = await session.scalar(
        select(Receipt)
        .join(Donation, Donation.id == Receipt.donation_id)
        .where(Donation.id == donation_id, Donation.donor_id == user.id)
    )
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found.")
    pdf = await render_receipt_pdf(receipt, request.app.state.pan_cipher)
    number = receipt.number.replace("/", "-")
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'},
    )


@router.post("/v1/donations/{donation_id}/test-charge", response_model=DonationOut)
async def test_charge(
    donation_id: uuid.UUID,
    body: TestCharge,
    user: User = Depends(current_user),
    session: AsyncSession = db_session,
    config: Config = Depends(get_config),
) -> DonationOut:
    """The test-mode stand-in for a hosted payment page. A failed attempt can be retried on the
    same donation; once paid, a further call returns the existing receipt."""
    if config.gateway_mode != "test":
        raise HTTPException(status_code=404, detail="Not found.")
    donation = await session.get(Donation, donation_id)
    if donation is None or donation.donor_id != user.id:
        raise HTTPException(status_code=404, detail="Donation not found.")
    if donation.status == "paid":
        return await _load_out(session, donation)
    try:
        result = charge(body.card_number, body.issuing_country)
    except NotATestCard as exc:
        raise HTTPException(status_code=422, detail="Use one of the listed test cards.") from exc
    await _apply_payment(session, config, donation.gateway_ref, result.paid, result.outcome)
    await session.refresh(donation)
    return await _load_out(session, donation)


async def _apply_payment(
    session: AsyncSession, config: Config, gateway_ref: str, paid: bool, reason: str | None
) -> Donation:
    """One path for the webhook and the test charge, so both obey the same rules."""
    now = datetime.now(UTC)
    if paid:
        try:
            receipt = await issue_receipt(session, gateway_ref, config, now)
        except DonationNotFound as exc:
            raise HTTPException(status_code=404, detail="Unknown payment.") from exc
        donation = await session.get(Donation, receipt.donation_id)
        if donation is None:  # pragma: no cover - FK guarantees it
            raise HTTPException(status_code=404, detail="Unknown payment.")
        donation.failure_reason = None
        await session.flush()
        await open_mandate_if_monthly(session, donation, now)
        return donation
    donation = await session.scalar(
        select(Donation).where(Donation.gateway_ref == gateway_ref).with_for_update()
    )
    if donation is None:
        raise HTTPException(status_code=404, detail="Unknown payment.")
    if donation.status != "paid":  # a paid donation is never downgraded
        donation.status = "failed"
        donation.failure_reason = reason
    await session.flush()
    return donation


def _signature_ok(secret: str, raw: bytes, header: str | None) -> bool:
    if not header:
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.strip().lower())


@router.post("/v1/webhooks/mock-gateway", response_model=DonationOut)
async def gateway_webhook(
    request: Request,
    session: AsyncSession = db_session,
    config: Config = Depends(get_config),
    x_signature: str | None = Header(default=None),
) -> DonationOut:
    """Fails closed: nothing is parsed or touched until the HMAC over the raw body verifies."""
    raw = await request.body()
    if not _signature_ok(config.gateway_webhook_secret, raw, x_signature):
        raise HTTPException(status_code=401, detail="Invalid signature.")
    try:
        event = WebhookEvent.model_validate(json.loads(raw))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail="Malformed event.") from exc

    paid = event.event == "payment.succeeded"
    donation = await _apply_payment(
        session, config, event.gateway_ref, paid, None if paid else "declined"
    )
    return await _load_out(session, donation)


@router.get("/v1/mandates", response_model=list[MandateOut])
async def list_my_mandates(
    user: User = Depends(current_user), session: AsyncSession = db_session
) -> list[MandateOut]:
    rows = await session.execute(
        select(Mandate, Campaign)
        .join(Campaign, Campaign.id == Mandate.campaign_id)
        .where(Mandate.donor_id == user.id)
        .order_by(Mandate.created_at.desc())
    )
    return [_mandate_out(m, c) for m, c in rows.all()]


@router.post("/v1/mandates/{mandate_id}/cancel", response_model=MandateOut)
async def cancel_mandate(
    mandate_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = db_session,
) -> MandateOut:
    mandate = await session.get(Mandate, mandate_id, with_for_update=True)
    if mandate is None or mandate.donor_id != user.id:
        raise HTTPException(status_code=404, detail="Mandate not found.")
    mandate.status = "cancelled"
    campaign = await session.get(Campaign, mandate.campaign_id)
    if campaign is None:  # pragma: no cover - FK guarantees it
        raise HTTPException(status_code=404, detail="Campaign not found.")
    await session.flush()
    return _mandate_out(mandate, campaign)


def _mandate_out(m: Mandate, c: Campaign) -> MandateOut:
    return MandateOut(
        id=m.id,
        campaign_title_en=c.title_en,
        campaign_title_hi=c.title_hi,
        amount_paise=m.amount_paise,
        status=m.status,
        next_charge_on=m.next_charge_on,
    )

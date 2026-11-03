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
from app.db import get_session
from app.deps import current_user, get_config
from app.models import Campaign, Donation, Receipt, User
from app.pdf import render_receipt_pdf
from app.receipts import DonationNotFound, issue_receipt
from app.schemas import DonationCreate, DonationOut, WebhookEvent

router = APIRouter(tags=["donations"])


def _out(d: Donation, slug: str, receipt_number: str | None) -> DonationOut:
    return DonationOut(
        id=d.id,
        campaign_slug=slug,
        amount_paise=d.amount_paise,
        kind=d.kind,
        status=d.status,
        gateway_ref=d.gateway_ref,
        receipt_number=receipt_number,
    )


@router.post("/v1/donations", status_code=201, response_model=DonationOut)
async def create_donation(
    body: DonationCreate,
    response: Response,
    idempotency_key: str = Header(min_length=8, max_length=80),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
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
            return _out(donation, campaign.slug, None)

    if existing is None:  # pragma: no cover - conflict implies the row exists
        raise HTTPException(status_code=409, detail="Please retry.")
    response.status_code = 200
    return await _load_out(session, existing)


async def _load_out(session: AsyncSession, d: Donation) -> DonationOut:
    slug = await session.scalar(select(Campaign.slug).where(Campaign.id == d.campaign_id))
    number = await session.scalar(select(Receipt.number).where(Receipt.donation_id == d.id))
    return _out(d, slug or "", number)


@router.get("/v1/donations", response_model=list[DonationOut])
async def list_my_donations(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[DonationOut]:
    rows = await session.execute(
        select(Donation, Campaign.slug, Receipt.number)
        .join(Campaign, Campaign.id == Donation.campaign_id)
        .outerjoin(Receipt, Receipt.donation_id == Donation.id)
        .where(Donation.donor_id == user.id)
        .order_by(Donation.created_at.desc(), Donation.id)
        .limit(200)
    )
    return [_out(d, slug, number) for d, slug, number in rows.all()]


@router.get("/v1/donations/{donation_id}", response_model=DonationOut)
async def get_donation(
    donation_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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


def _signature_ok(secret: str, raw: bytes, header: str | None) -> bool:
    if not header:
        return False
    expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.strip().lower())


@router.post("/v1/webhooks/mock-gateway", response_model=DonationOut)
async def gateway_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
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

    now = datetime.now(UTC)
    if event.event == "payment.succeeded":
        try:
            receipt = await issue_receipt(session, event.gateway_ref, config, now)
        except DonationNotFound as exc:
            raise HTTPException(status_code=404, detail="Unknown payment.") from exc
        donation = await session.get(Donation, receipt.donation_id)
    else:
        donation = await session.scalar(
            select(Donation).where(Donation.gateway_ref == event.gateway_ref).with_for_update()
        )
        if donation is None:
            raise HTTPException(status_code=404, detail="Unknown payment.")
        if donation.status == "pending":  # a paid donation is never downgraded
            donation.status = "failed"
    if donation is None:  # pragma: no cover
        raise HTTPException(status_code=404, detail="Unknown payment.")
    return await _load_out(session, donation)

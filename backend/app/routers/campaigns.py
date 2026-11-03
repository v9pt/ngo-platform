"""Public list of live campaigns with the amount raised so far (paid donations only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Campaign, Donation
from app.schemas import CampaignOut

router = APIRouter(prefix="/v1/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(session: AsyncSession = Depends(get_session)) -> list[CampaignOut]:
    raised = func.coalesce(func.sum(Donation.amount_paise), 0)
    rows = await session.execute(
        select(Campaign, raised)
        .outerjoin(Donation, (Donation.campaign_id == Campaign.id) & (Donation.status == "paid"))
        .where(Campaign.status == "live")
        .group_by(Campaign.id)
        .order_by(Campaign.created_at, Campaign.slug)
    )
    return [
        CampaignOut(
            slug=c.slug,
            title_en=c.title_en,
            title_hi=c.title_hi,
            description_en=c.description_en,
            description_hi=c.description_hi,
            goal_paise=c.goal_paise,
            raised_paise=int(total),
        )
        for c, total in rows.all()
    ]

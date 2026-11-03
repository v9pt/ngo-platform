"""Editorial CMS API. Editors and admins only; the role is read from the DB row.

Scheme workflow: draft -> in_review (editor or admin) -> published (admin only). A published
scheme is immutable until an admin moves it back to draft. Every transition is audit-logged.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.db import get_session
from app.deps import get_config, require_roles
from app.eligibility import rule_problem
from app.mandates import charge_due_mandates
from app.models import (
    AuditLog,
    CallbackRequest,
    Campaign,
    Donation,
    Receipt,
    Scheme,
    SchemeSummary,
    User,
)
from app.schemas import (
    AdminSchemeDetail,
    AdminSchemeRow,
    AuditEntry,
    CallbackOut,
    CampaignReport,
    MandateRunOut,
    SchemeCreate,
    SchemeEdit,
    SummaryCreate,
    SummaryEdit,
    SummaryOut,
    Transition,
)
from app.security import mask_pan
from app.summary_checks import run_checks

router = APIRouter(prefix="/v1/admin", tags=["admin"])

_staff = require_roles("editor", "admin")

# (from, to) -> roles allowed to perform it
_TRANSITIONS: dict[tuple[str, str], tuple[str, ...]] = {
    ("draft", "in_review"): ("editor", "admin"),
    ("in_review", "draft"): ("admin",),
    ("in_review", "published"): ("admin",),
    ("published", "draft"): ("admin",),
}


def _row(s: Scheme) -> AdminSchemeRow:
    return AdminSchemeRow(
        code=s.code,
        title_en=s.title_en,
        title_hi=s.title_hi,
        status=s.status,
        notice_text=s.notice_text,
        benefit_hi=s.benefit_hi,
    )


def _detail(s: Scheme) -> AdminSchemeDetail:
    return AdminSchemeDetail.model_validate(s, from_attributes=True)


def _publish_blockers(s: Scheme) -> list[str]:
    """What must be true before the public can see a scheme. A scheme with no rules would match
    every woman who uses the finder, so it cannot be sent for review or published."""
    blockers: list[str] = []
    if not s.rules:
        blockers.append("Add at least one eligibility rule.")
    if not s.benefit_en.strip():
        blockers.append("Add the benefit.")
    if not s.who_can_apply_en.strip():
        blockers.append("Add who can apply.")
    if "example.invalid" in s.source_url:
        blockers.append("Add the official source link.")
    return blockers


async def _scheme(session: AsyncSession, code: str, lock: bool = False) -> Scheme:
    q = select(Scheme).where(Scheme.code == code)
    scheme = await session.scalar(q.with_for_update() if lock else q)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return scheme


def _audit(
    session: AsyncSession,
    actor: User,
    action: str,
    entity: str,
    entity_id: str,
    detail: dict[str, Any],
) -> None:
    session.add(
        AuditLog(
            actor_id=actor.id, action=action, entity=entity, entity_id=entity_id, detail=detail
        )
    )


async def _summary_out(session: AsyncSession, s: SchemeSummary) -> SummaryOut:
    code = await session.scalar(select(Scheme.code).where(Scheme.id == s.scheme_id))
    return SummaryOut(
        id=s.id,
        scheme_code=code or "",
        hindi_text=s.hindi_text,
        source=s.source,
        status=s.status,
        checks=s.checks,
        approved_by=s.approved_by,
    )


@router.get("/schemes", response_model=list[AdminSchemeRow])
async def list_all(
    _: User = Depends(_staff), session: AsyncSession = Depends(get_session)
) -> list[AdminSchemeRow]:
    return [_row(s) for s in (await session.scalars(select(Scheme).order_by(Scheme.code))).all()]


@router.post("/schemes", response_model=AdminSchemeDetail, status_code=201)
async def create_scheme(
    body: SchemeCreate,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> AdminSchemeDetail:
    """Starts as an empty draft. The code is assigned here so editors never have to pick one."""
    codes = await session.scalars(select(Scheme.code))
    numbers = [int(c[4:]) for c in codes.all() if c[:4] == "SCH-" and c[4:].isdigit()]
    scheme = Scheme(
        code=f"SCH-{max(numbers, default=0) + 10:03d}",
        title_en=body.title_en.strip(),
        title_hi=body.title_hi.strip(),
        need=body.need,
        benefit_en="",
        who_can_apply_en="",
        source_url="https://example.invalid/add-the-official-link",
        last_checked=datetime.now(UTC).date(),
    )
    session.add(scheme)
    try:
        await session.flush()
    except IntegrityError as exc:  # two editors created one at the same moment
        raise HTTPException(status_code=409, detail="Please try again.") from exc
    _audit(session, actor, "scheme.create", "scheme", scheme.code, {})
    await session.refresh(scheme)
    return _detail(scheme)


@router.get("/schemes/{code}", response_model=AdminSchemeDetail)
async def get_scheme(
    code: str, _: User = Depends(_staff), session: AsyncSession = Depends(get_session)
) -> AdminSchemeDetail:
    return _detail(await _scheme(session, code))


@router.get("/schemes/{code}/history", response_model=list[AuditEntry])
async def scheme_history(
    code: str, _: User = Depends(_staff), session: AsyncSession = Depends(get_session)
) -> list[AuditEntry]:
    rows = await session.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_id)
        .where(AuditLog.entity == "scheme", AuditLog.entity_id == code)
        .order_by(AuditLog.id.desc())
        .limit(30)
    )
    return [
        AuditEntry(action=a.action, actor_name=name, detail=a.detail, created_at=a.created_at)
        for a, name in rows.all()
    ]


@router.patch("/schemes/{code}", response_model=AdminSchemeRow)
async def edit_scheme(
    code: str,
    body: SchemeEdit,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> AdminSchemeRow:
    scheme = await _scheme(session, code, lock=True)
    if scheme.status == "published":
        raise HTTPException(status_code=409, detail="Move the scheme back to draft to edit it.")
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    for rule in changes.get("rules", []):
        problem = rule_problem(rule)
        if problem:
            raise HTTPException(status_code=422, detail=problem)
    for field, value in changes.items():
        setattr(scheme, field, value)
    _audit(session, actor, "scheme.edit", "scheme", scheme.code, {"fields": sorted(changes)})
    await session.flush()
    return _row(scheme)


@router.post("/schemes/{code}/transition", response_model=AdminSchemeRow)
async def transition(
    code: str,
    body: Transition,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> AdminSchemeRow:
    scheme = await _scheme(session, code, lock=True)
    allowed = _TRANSITIONS.get((scheme.status, body.to))
    if allowed is None:
        raise HTTPException(
            status_code=409, detail=f"Cannot move a {scheme.status} scheme to {body.to}."
        )
    if actor.role not in allowed:
        raise HTTPException(status_code=403, detail="You do not have access to this.")
    if body.to in ("in_review", "published"):
        blockers = _publish_blockers(scheme)
        if blockers:
            raise HTTPException(status_code=409, detail=" ".join(blockers))
    _audit(
        session,
        actor,
        "scheme.transition",
        "scheme",
        scheme.code,
        {"from": scheme.status, "to": body.to},
    )
    scheme.status = body.to
    await session.flush()
    return _row(scheme)


@router.get("/schemes/{code}/summaries", response_model=list[SummaryOut])
async def list_summaries(
    code: str, _: User = Depends(_staff), session: AsyncSession = Depends(get_session)
) -> list[SummaryOut]:
    scheme = await _scheme(session, code)
    rows = await session.scalars(
        select(SchemeSummary)
        .where(SchemeSummary.scheme_id == scheme.id)
        .order_by(SchemeSummary.created_at.desc(), SchemeSummary.id)
    )
    return [await _summary_out(session, s) for s in rows.all()]


@router.post("/schemes/{code}/summary-draft", response_model=SummaryOut, status_code=201)
async def draft_summary(
    code: str,
    request: Request,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> SummaryOut:
    generator = getattr(request.app.state, "summary_generator", None)
    if generator is None:
        raise HTTPException(status_code=503, detail="AI drafting is not configured.")
    scheme = await _scheme(session, code)
    if not scheme.notice_text.strip():
        raise HTTPException(status_code=409, detail="Add the official notice text first.")
    try:
        text = await generator.generate(scheme.notice_text)
    except Exception as exc:  # network, quota, malformed reply: never leak provider details
        raise HTTPException(status_code=503, detail="AI drafting failed. Try again.") from exc
    summary = SchemeSummary(
        scheme_id=scheme.id,
        hindi_text=text,
        source="ai",
        status="draft",
        checks=run_checks(text, scheme.notice_text),
        created_by=actor.id,
    )
    session.add(summary)
    await session.flush()
    _audit(session, actor, "summary.draft", "scheme", scheme.code, {"summary_id": str(summary.id)})
    return await _summary_out(session, summary)


@router.post("/schemes/{code}/summaries", response_model=SummaryOut, status_code=201)
async def write_summary(
    code: str,
    body: SummaryCreate,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> SummaryOut:
    """A summary written by a person: the path when the model is off, failing or wrong. It passes
    through the same checks and the same approval as an AI draft."""
    scheme = await _scheme(session, code)
    text = body.hindi_text.strip()
    summary = SchemeSummary(
        scheme_id=scheme.id,
        hindi_text=text,
        source="human",
        status="draft",
        checks=run_checks(text, scheme.notice_text),
        created_by=actor.id,
    )
    session.add(summary)
    await session.flush()
    _audit(session, actor, "summary.write", "scheme", scheme.code, {"summary_id": str(summary.id)})
    return await _summary_out(session, summary)


async def _draft(session: AsyncSession, summary_id: uuid.UUID) -> tuple[SchemeSummary, Scheme]:
    summary = await session.scalar(
        select(SchemeSummary).where(SchemeSummary.id == summary_id).with_for_update()
    )
    if summary is None:
        raise HTTPException(status_code=404, detail="Summary not found.")
    scheme = await session.get(Scheme, summary.scheme_id)
    if scheme is None:  # pragma: no cover - FK guarantees it
        raise HTTPException(status_code=404, detail="Scheme not found.")
    if summary.status != "draft":
        raise HTTPException(status_code=409, detail="Only drafts can be changed.")
    return summary, scheme


@router.patch("/summaries/{summary_id}", response_model=SummaryOut)
async def edit_summary(
    summary_id: uuid.UUID,
    body: SummaryEdit,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> SummaryOut:
    summary, scheme = await _draft(session, summary_id)
    summary.hindi_text = body.hindi_text.strip()
    summary.checks = run_checks(summary.hindi_text, scheme.notice_text)  # re-run on every edit
    _audit(session, actor, "summary.edit", "scheme", scheme.code, {"summary_id": str(summary.id)})
    await session.flush()
    return await _summary_out(session, summary)


@router.post("/summaries/{summary_id}/approve", response_model=SummaryOut)
async def approve_summary(
    summary_id: uuid.UUID,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> SummaryOut:
    summary, scheme = await _draft(session, summary_id)
    # Re-run now so a stale stored result can never let a bad summary through.
    checks = run_checks(summary.hindi_text, scheme.notice_text)
    summary.checks = checks
    if checks["needs_attention"]:
        raise HTTPException(status_code=409, detail="Fix the flagged problems before approving.")
    summary.status = "approved"
    summary.approved_by = actor.id
    summary.approved_at = datetime.now(UTC)
    # At most one approved summary per scheme: retire the previous one.
    for other in (
        await session.scalars(
            select(SchemeSummary).where(
                SchemeSummary.scheme_id == scheme.id,
                SchemeSummary.status == "approved",
                SchemeSummary.id != summary.id,
            )
        )
    ).all():
        other.status = "rejected"
    _audit(
        session, actor, "summary.approve", "scheme", scheme.code, {"summary_id": str(summary.id)}
    )
    await session.flush()
    return await _summary_out(session, summary)


@router.post("/summaries/{summary_id}/reject", response_model=SummaryOut)
async def reject_summary(
    summary_id: uuid.UUID,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> SummaryOut:
    summary, scheme = await _draft(session, summary_id)
    summary.status = "rejected"
    _audit(session, actor, "summary.reject", "scheme", scheme.code, {"summary_id": str(summary.id)})
    await session.flush()
    return await _summary_out(session, summary)


_admin_only = require_roles("admin")


async def _campaign(session: AsyncSession, slug: str) -> Campaign:
    campaign = await session.scalar(select(Campaign).where(Campaign.slug == slug))
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


def _report(campaign: Campaign, by_status: dict[str, tuple[int, int]]) -> CampaignReport:
    return CampaignReport(
        slug=campaign.slug,
        title_en=campaign.title_en,
        status=campaign.status,
        goal_paise=campaign.goal_paise,
        paid_count=by_status.get("paid", (0, 0))[0],
        paid_paise=by_status.get("paid", (0, 0))[1],
        pending_count=by_status.get("pending", (0, 0))[0],
        failed_count=by_status.get("failed", (0, 0))[0],
    )


@router.get("/campaigns", response_model=list[CampaignReport])
async def all_campaign_reports(
    _: User = Depends(_admin_only), session: AsyncSession = Depends(get_session)
) -> list[CampaignReport]:
    rows = await session.execute(
        select(
            Donation.campaign_id,
            Donation.status,
            func.count(),
            func.coalesce(func.sum(Donation.amount_paise), 0),
        ).group_by(Donation.campaign_id, Donation.status)
    )
    totals: dict[uuid.UUID, dict[str, tuple[int, int]]] = {}
    for campaign_id, status, count, total in rows.all():
        totals.setdefault(campaign_id, {})[status] = (count, int(total))
    campaigns = await session.scalars(select(Campaign).order_by(Campaign.created_at, Campaign.slug))
    return [_report(c, totals.get(c.id, {})) for c in campaigns.all()]


@router.get("/campaigns/{slug}/report", response_model=CampaignReport)
async def campaign_report(
    slug: str, _: User = Depends(_admin_only), session: AsyncSession = Depends(get_session)
) -> CampaignReport:
    campaign = await _campaign(session, slug)
    rows = await session.execute(
        select(Donation.status, func.count(), func.coalesce(func.sum(Donation.amount_paise), 0))
        .where(Donation.campaign_id == campaign.id)
        .group_by(Donation.status)
    )
    return _report(campaign, {status: (n, int(total)) for status, n, total in rows.all()})


def _csv_safe(value: str) -> str:
    """Stop spreadsheet apps from running a donor-chosen name as a formula."""
    return f"'{value}" if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


@router.get("/campaigns/{slug}/donations.csv")
async def campaign_donations_csv(
    slug: str,
    request: Request,
    actor: User = Depends(_admin_only),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """One row per issued receipt. PAN is masked: the full value never leaves the database
    (assumption A5: not the official 10BD utility format)."""
    campaign = await _campaign(session, slug)
    cipher = request.app.state.pan_cipher
    receipts = await session.scalars(
        select(Receipt)
        .join(Donation, Donation.id == Receipt.donation_id)
        .where(Donation.campaign_id == campaign.id)
        .order_by(Receipt.fy, Receipt.seq)
    )
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "receipt_number",
            "receipt_date",
            "donor_name",
            "donor_email",
            "donor_pan",
            "amount_rupees",
        ]
    )
    for r in receipts.all():
        pan = mask_pan(cipher.decrypt(r.donor_pan_ciphertext)) if r.donor_pan_ciphertext else ""
        paise = r.amount_paise
        writer.writerow(
            [
                r.number,
                r.issued_at.date().isoformat(),
                _csv_safe(r.donor_name),
                _csv_safe(r.donor_email),
                pan,
                f"{paise // 100}.{paise % 100:02d}",
            ]
        )
    _audit(session, actor, "campaign.export", "campaign", slug, {})
    return Response(
        out.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{slug}-donations.csv"'},
    )


@router.post("/mandates/run", response_model=MandateRunOut)
async def run_monthly_charges(
    actor: User = Depends(_admin_only),
    session: AsyncSession = Depends(get_session),
    config: Config = Depends(get_config),
) -> MandateRunOut:
    """The test-mode scheduler. A real deployment would call this from cron."""
    if config.gateway_mode != "test":
        raise HTTPException(status_code=404, detail="Not found.")
    charged, skipped = await charge_due_mandates(session, config, datetime.now(UTC))
    _audit(session, actor, "mandates.run", "mandate", "all", {"charged": charged})
    return MandateRunOut(charged=charged, skipped=skipped)


@router.get("/callbacks", response_model=list[CallbackOut])
async def list_callbacks(
    _: User = Depends(_staff), session: AsyncSession = Depends(get_session)
) -> list[CallbackOut]:
    rows = await session.scalars(
        select(CallbackRequest)
        .order_by(CallbackRequest.status.desc(), CallbackRequest.created_at.desc())
        .limit(100)
    )
    return [CallbackOut.model_validate(r, from_attributes=True) for r in rows.all()]


@router.post("/callbacks/{callback_id}/done", response_model=CallbackOut)
async def finish_callback(
    callback_id: uuid.UUID,
    actor: User = Depends(_staff),
    session: AsyncSession = Depends(get_session),
) -> CallbackOut:
    callback = await session.get(CallbackRequest, callback_id, with_for_update=True)
    if callback is None:
        raise HTTPException(status_code=404, detail="Request not found.")
    callback.status = "done"
    _audit(session, actor, "callback.done", "callback", str(callback.id), {})
    await session.flush()
    return CallbackOut.model_validate(callback, from_attributes=True)

"""Public scheme catalogue and the eligibility check. Only published schemes are visible."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import db_session
from app.eligibility import evaluate
from app.interpret import interpret
from app.models import CallbackRequest, Scheme, SchemeSummary
from app.ratelimit import RateLimiter
from app.schemas import (
    CallbackCreate,
    EligibilityAnswers,
    InterpretOut,
    InterpretRequest,
    RuleResultOut,
    SchemeCheckOut,
    SchemeDetailOut,
    SchemeSummaryOut,
)

router = APIRouter(prefix="/v1/schemes", tags=["schemes"])

_RANK = {"match": 0, "possible": 1, "excluded": 2}


def _rules_with_area(scheme: Scheme) -> list[dict[str, Any]]:
    """A scheme limited to some districts is limited in the check too, even if an editor set the
    districts but forgot the rule. Otherwise browse and finder could disagree."""
    has_rule = any(r["field"] == "district" for r in scheme.rules)
    if scheme.districts and not has_rule:
        return [*scheme.rules, {"field": "district", "op": "in", "value": scheme.districts}]
    return scheme.rules


@router.get("", response_model=list[SchemeSummaryOut])
async def list_schemes(
    need: str | None = None,
    district: str | None = None,
    session: AsyncSession = db_session,
) -> list[SchemeSummaryOut]:
    q = select(Scheme).where(Scheme.status == "published").order_by(Scheme.code)
    if need:
        q = q.where(Scheme.need == need)
    if district:  # an empty district list means the scheme runs everywhere
        q = q.where(
            or_(func.cardinality(Scheme.districts) == 0, Scheme.districts.contains([district]))
        )
    rows = (await session.scalars(q)).all()
    return [SchemeSummaryOut.model_validate(r, from_attributes=True) for r in rows]


# 30 readings a minute per client: each one may cost a model call, so the limit caps spend too.
interpret_limiter = RateLimiter(max_events=30, window_seconds=60)
callback_limiter = RateLimiter(max_events=5, window_seconds=3600)


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# Declared before "/{code}" so these paths are never read as a scheme code. The text and phone
# number below are personal data: neither is logged, and the text is not stored at all.
@router.post("/interpret", response_model=InterpretOut)
async def interpret_question(body: InterpretRequest, request: Request) -> InterpretOut:
    interpret_limiter.check(_client_key(request))
    return await interpret(body.text, getattr(request.app.state, "answer_reader", None))


@router.post("/callbacks", status_code=201)
async def request_callback(
    body: CallbackCreate, request: Request, session: AsyncSession = db_session
) -> dict[str, str]:
    callback_limiter.check(_client_key(request))
    session.add(
        CallbackRequest(
            phone=body.phone,
            name=body.name.strip(),
            scheme_code=body.scheme_code,
            language=body.language,
        )
    )
    await session.flush()
    return {"status": "received"}


@router.post("/check", response_model=list[SchemeCheckOut])
async def check_eligibility(
    answers: EligibilityAnswers, session: AsyncSession = db_session
) -> list[SchemeCheckOut]:
    given = answers.model_dump(exclude_none=True)
    rows = (
        await session.scalars(
            select(Scheme).where(Scheme.status == "published").order_by(Scheme.code)
        )
    ).all()
    out: list[SchemeCheckOut] = []
    for s in rows:
        ev = evaluate(_rules_with_area(s), given)
        out.append(
            SchemeCheckOut(
                code=s.code,
                title_en=s.title_en,
                title_hi=s.title_hi,
                need=s.need,
                benefit_en=s.benefit_en,
                benefit_hi=s.benefit_hi,
                status=ev.status,
                rules=[RuleResultOut(**vars(r)) for r in ev.rules],
            )
        )
    out.sort(key=lambda x: _RANK[x.status])  # stable: ties stay in code order
    return out


@router.get("/{code}", response_model=SchemeDetailOut)
async def get_scheme(code: str, session: AsyncSession = db_session) -> SchemeDetailOut:
    scheme = await session.scalar(
        select(Scheme).where(Scheme.code == code, Scheme.status == "published")
    )
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    summary = await session.scalar(
        select(SchemeSummary.hindi_text)
        .where(SchemeSummary.scheme_id == scheme.id, SchemeSummary.status == "approved")
        .order_by(SchemeSummary.approved_at.desc())
        .limit(1)
    )
    detail = SchemeDetailOut.model_validate(scheme, from_attributes=True)
    detail.summary_hi = summary
    return detail

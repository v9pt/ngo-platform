"""Public scheme catalogue and the eligibility check. Only published schemes are visible."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.eligibility import evaluate
from app.models import Scheme
from app.schemas import (
    EligibilityAnswers,
    RuleResultOut,
    SchemeCheckOut,
    SchemeDetailOut,
    SchemeSummaryOut,
)

router = APIRouter(prefix="/v1/schemes", tags=["schemes"])

_RANK = {"match": 0, "possible": 1, "excluded": 2}


@router.get("", response_model=list[SchemeSummaryOut])
async def list_schemes(
    need: str | None = None, session: AsyncSession = Depends(get_session)
) -> list[SchemeSummaryOut]:
    q = select(Scheme).where(Scheme.status == "published").order_by(Scheme.code)
    if need:
        q = q.where(Scheme.need == need)
    rows = (await session.scalars(q)).all()
    return [SchemeSummaryOut.model_validate(r, from_attributes=True) for r in rows]


# Declared before "/{code}" so "check" is never read as a scheme code.
@router.post("/check", response_model=list[SchemeCheckOut])
async def check_eligibility(
    answers: EligibilityAnswers, session: AsyncSession = Depends(get_session)
) -> list[SchemeCheckOut]:
    given = answers.model_dump(exclude_none=True)
    rows = (
        await session.scalars(
            select(Scheme).where(Scheme.status == "published").order_by(Scheme.code)
        )
    ).all()
    out: list[SchemeCheckOut] = []
    for s in rows:
        ev = evaluate(s.rules, given)
        out.append(
            SchemeCheckOut(
                code=s.code,
                title_en=s.title_en,
                title_hi=s.title_hi,
                status=ev.status,
                rules=[RuleResultOut(**vars(r)) for r in ev.rules],
            )
        )
    out.sort(key=lambda x: _RANK[x.status])  # stable: ties stay in code order
    return out


@router.get("/{code}", response_model=SchemeDetailOut)
async def get_scheme(code: str, session: AsyncSession = Depends(get_session)) -> SchemeDetailOut:
    scheme = await session.scalar(
        select(Scheme).where(Scheme.code == code, Scheme.status == "published")
    )
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found.")
    return SchemeDetailOut.model_validate(scheme, from_attributes=True)

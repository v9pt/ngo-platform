"""Idempotent demo data. Run with:  python -m app.seed

Everything here is illustrative sample data (assumption A1 in the TDD): the scheme values come
from the brief's sample rows plus a few invented schemes, the trust and donors are fictional,
and the demo accounts use a documented public password that must never be reused.
Re-running updates rows in place and never duplicates them.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models import Campaign, ReceiptCounter, Scheme, SchemeSummary, User
from app.security import hash_password

DEMO_PASSWORD_DEFAULT = "DemoPass#2026"  # noqa: S105  # public demo credential, see deployment.md

# Nine Madhya Pradesh districts used as the trust's area (assumption A2: the brief names none).
DISTRICTS = [
    "Bhopal",
    "Sehore",
    "Vidisha",
    "Raisen",
    "Rajgarh",
    "Indore",
    "Dewas",
    "Ujjain",
    "Narmadapuram",
]

DEMO_USERS: list[dict[str, str]] = [
    {"email": "admin@demo.example", "full_name": "Meera Admin", "role": "admin"},
    {"email": "editor@demo.example", "full_name": "Ravi Editor", "role": "editor"},
    {"email": "donor@demo.example", "full_name": "Asha Verma", "role": "donor"},
]

SCHEMES: list[dict[str, Any]] = [
    {
        "code": "SCH-014",
        "title_en": "State widow pension",
        "title_hi": "राज्य विधवा पेंशन",
        "need": "pension",
        "districts": [],
        "benefit_en": "Rs 600 a month",
        "benefit_hi": "₹600 प्रति माह",
        "who_can_apply_en": "Widow aged 18-79 with a BPL card",
        "documents": ["Husband's death certificate", "BPL card", "Aadhaar-linked bank passbook"],
        "how_to_apply_en": "Apply at the Gram Panchayat or ward office with the documents.",
        "help_centre": "Block social welfare office",
        "source_url": "https://example.org/notices/sch-014",
        "last_checked": date(2026, 9, 12),
        "rules": [
            {"field": "marital_status", "op": "eq", "value": "widow"},
            {"field": "age", "op": "between", "value": [18, 79]},
            {"field": "has_bpl_card", "op": "eq", "value": True},
        ],
        "notice_text": (
            "Illustrative notice. Widows aged between 18 and 79 years who hold a BPL card are "
            "eligible for a monthly pension of Rs 600. Apply with the death certificate of the "
            "husband, the BPL card and a bank passbook."
        ),
        "status": "published",
    },
    {
        "code": "SCH-022",
        "title_en": "Self-help group loan support",
        "title_hi": "स्व-सहायता समूह ऋण सहायता",
        "need": "livelihood",
        "districts": [],
        "benefit_en": "Loan up to Rs 3 lakh at lower interest",
        "benefit_hi": "₹3 लाख तक का ऋण, कम ब्याज पर",
        "who_can_apply_en": "Member of a registered SHG",
        "documents": ["SHG registration proof", "Member list", "Bank passbook of the group"],
        "how_to_apply_en": "Apply through your SHG federation or the nearest bank branch.",
        "help_centre": "District livelihood mission office",
        "source_url": "https://example.org/notices/sch-022",
        "last_checked": date(2026, 8, 30),
        "rules": [{"field": "shg_member", "op": "eq", "value": True}],
        "notice_text": (
            "Illustrative notice. Members of a registered self-help group can get loan support "
            "of up to Rs 3 lakh at a lower rate of interest through the group's bank account."
        ),
        "status": "published",
    },
    {
        "code": "SCH-031",
        "title_en": "Maternity cash benefit",
        "title_hi": "मातृत्व नकद सहायता",
        "need": "health",
        "districts": [],
        "benefit_en": "Rs 5,000 in instalments",
        "benefit_hi": "₹5,000 किस्तों में",
        "who_can_apply_en": "Pregnant woman, first child",
        "documents": ["Pregnancy registration (MCP card)", "Bank passbook"],
        "how_to_apply_en": "Register at the Anganwadi centre or health sub-centre.",
        "help_centre": "Anganwadi centre",
        "source_url": "https://example.org/notices/sch-031",
        "last_checked": date(2026, 10, 5),
        "rules": [
            {"field": "pregnant", "op": "eq", "value": True},
            {"field": "first_child", "op": "eq", "value": True},
        ],
        "notice_text": (
            "Illustrative notice. A pregnant woman expecting her first child receives Rs 5,000 "
            "in instalments after registering her pregnancy at the Anganwadi centre."
        ),
        "status": "published",
    },
    {
        "code": "SCH-040",
        "title_en": "Girl child education scholarship",
        "title_hi": "बालिका शिक्षा छात्रवृत्ति",
        "need": "education",
        "districts": ["Bhopal", "Sehore", "Vidisha", "Raisen"],
        "benefit_en": "Rs 1,200 a year per girl",
        "benefit_hi": "प्रति बालिका ₹1,200 प्रति वर्ष",
        "who_can_apply_en": "Family with a school-going girl and a BPL card",
        "documents": ["School enrolment proof", "BPL card"],
        "how_to_apply_en": "Apply through the school principal.",
        "help_centre": "District education office",
        "source_url": "https://example.org/notices/sch-040",
        "last_checked": date(2026, 9, 20),
        "rules": [
            {"field": "has_school_age_girl", "op": "eq", "value": True},
            {"field": "has_bpl_card", "op": "eq", "value": True},
            {"field": "district", "op": "in", "value": ["Bhopal", "Sehore", "Vidisha", "Raisen"]},
        ],
        "notice_text": (
            "Illustrative notice. Families holding a BPL card with a girl studying in school get "
            "Rs 1,200 per year per girl in the districts of Bhopal, Sehore, Vidisha and Raisen."
        ),
        "status": "published",
    },
    {
        "code": "SCH-045",
        "title_en": "Skill training stipend",
        "title_hi": "कौशल प्रशिक्षण वृत्ति",
        "need": "livelihood",
        "districts": [],
        "benefit_en": "Free training and Rs 2,000 monthly stipend",
        "benefit_hi": "निःशुल्क प्रशिक्षण और ₹2,000 मासिक वृत्ति",
        "who_can_apply_en": "Women aged 18-45",
        "documents": ["Age proof", "Bank passbook"],
        "how_to_apply_en": "Register at the nearest skill centre.",
        "help_centre": "District skill centre",
        "source_url": "https://example.org/notices/sch-045",
        "last_checked": date(2026, 10, 12),
        "rules": [{"field": "age", "op": "between", "value": [18, 45]}],
        "notice_text": (
            "Illustrative notice. Women aged 18 to 45 may join free skill training and receive "
            "a stipend of Rs 2,000 per month while they train."
        ),
        "status": "published",
    },
    {
        "code": "SCH-050",
        "title_en": "Women's health check-up camp",
        "title_hi": "महिला स्वास्थ्य जाँच शिविर",
        "need": "health",
        "districts": [],
        "benefit_en": "Free yearly health check-up",
        "benefit_hi": "निःशुल्क वार्षिक स्वास्थ्य जाँच",
        "who_can_apply_en": "Women aged 30 and above",
        "documents": ["Any photo ID"],
        "how_to_apply_en": "Walk in at the camp. Dates are announced at the health centre.",
        "help_centre": "Community health centre",
        "source_url": "https://example.org/notices/sch-050",
        "last_checked": date(2026, 10, 1),
        "rules": [{"field": "age", "op": "gte", "value": 30}],
        "notice_text": (
            "Illustrative notice. Women aged 30 years and above can get a free health check-up "
            "once a year at the camps held by the community health centre."
        ),
        "status": "published",
    },
    {
        "code": "SCH-060",
        "title_en": "Rural housing support",
        "title_hi": "ग्रामीण आवास सहायता",
        "need": "housing",
        "districts": [],
        "benefit_en": "Rs 1.2 lakh for building a house",
        "benefit_hi": "घर बनाने के लिए ₹1.2 लाख",
        "who_can_apply_en": "BPL family without a pucca house",
        "documents": ["BPL card", "Land document"],
        "how_to_apply_en": "Apply at the Gram Panchayat.",
        "help_centre": "Gram Panchayat",
        "source_url": "https://example.org/notices/sch-060",
        "last_checked": date(2026, 9, 2),
        "rules": [
            {"field": "has_bpl_card", "op": "eq", "value": True},
            {"field": "owns_pucca_house", "op": "eq", "value": False},
        ],
        "notice_text": (
            "Illustrative notice. BPL families without a pucca house get Rs 1.2 lakh to build "
            "one. Apply at the Gram Panchayat with the BPL card and land document."
        ),
        # Left in review to demo the editor workflow in the admin CMS.
        "status": "in_review",
    },
]

CAMPAIGNS: list[dict[str, Any]] = [
    {
        "slug": "womens-livelihood-fund",
        "title_en": "Women's Livelihood Fund",
        "title_hi": "महिला आजीविका कोष",
        "description_en": "Seed money for women's self-help groups to start small businesses.",
        "description_hi": "महिला स्व-सहायता समूहों को छोटे व्यवसाय शुरू करने के लिए आरंभिक पूँजी।",
        "goal_paise": 500_000_00,
        "status": "live",
    },
    {
        "slug": "safe-motherhood",
        "title_en": "Safe Motherhood Drive",
        "title_hi": "सुरक्षित मातृत्व अभियान",
        "description_en": "Health check-ups and nutrition kits for expecting mothers.",
        "description_hi": "गर्भवती महिलाओं के लिए स्वास्थ्य जाँच और पोषण किट।",
        "goal_paise": 300_000_00,
        "status": "live",
    },
    {
        "slug": "winter-warmth-2026",
        "title_en": "Winter Warmth 2026",
        "title_hi": "शीतकालीन सहायता 2026",
        "description_en": "Blankets for families in our nine districts.",
        "description_hi": "हमारे नौ ज़िलों के परिवारों के लिए कंबल।",
        "goal_paise": 150_000_00,
        "status": "draft",
    },
]

AI_DRAFT_CHECKS: dict[str, Any] = {
    "devanagari_ratio": 0.82,
    "length_ok": True,
    "numbers_match_source": True,
    "needs_attention": False,
}


def current_fy(today: date | None = None) -> str:
    """Indian financial year label (April to March), e.g. 2026-27."""
    d = today or date.today()
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def run_seed(database_url: str, demo_password: str) -> dict[str, int]:
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        users = _seed_users(session, demo_password)
        _seed_by_key(session, Scheme, SCHEMES, "code")
        _seed_by_key(session, Campaign, CAMPAIGNS, "slug")
        _seed_summaries(session, users)
        if session.get(ReceiptCounter, current_fy()) is None:
            session.add(ReceiptCounter(fy=current_fy(), last_seq=0))
        counts = {
            "users": session.scalar(select(func.count()).select_from(User)) or 0,
            "schemes": session.scalar(select(func.count()).select_from(Scheme)) or 0,
            "campaigns": session.scalar(select(func.count()).select_from(Campaign)) or 0,
            "summaries": session.scalar(select(func.count()).select_from(SchemeSummary)) or 0,
        }
    engine.dispose()
    return counts


def _seed_users(session: Session, password: str) -> dict[str, User]:
    out: dict[str, User] = {}
    for spec in DEMO_USERS:
        user = session.scalar(select(User).where(func.lower(User.email) == spec["email"]))
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(password),
                **{k: v for k, v in spec.items() if k != "email"},
            )
            session.add(user)
        out[spec["role"]] = user
    session.flush()
    return out


def _seed_by_key(
    session: Session, model: type[Scheme] | type[Campaign], rows: list[dict[str, Any]], key: str
) -> None:
    for row in rows:
        existing = session.scalar(select(model).where(getattr(model, key) == row[key]))
        if existing is None:
            session.add(model(**row))
        else:
            for k, v in row.items():
                setattr(existing, k, v)
    session.flush()


def _seed_summaries(session: Session, users: dict[str, User]) -> None:
    """One approved human summary and one pending AI draft, so both states are visible."""
    if session.scalar(select(func.count()).select_from(SchemeSummary)):
        return
    widow = session.scalar(select(Scheme).where(Scheme.code == "SCH-014"))
    shg = session.scalar(select(Scheme).where(Scheme.code == "SCH-022"))
    assert widow is not None and shg is not None  # noqa: S101  # seeded just above
    session.add(
        SchemeSummary(
            scheme_id=widow.id,
            hindi_text=(
                "यह योजना 18 से 79 वर्ष की उन विधवा महिलाओं के लिए है जिनके पास बीपीएल कार्ड है। "
                "उन्हें हर महीने ₹600 पेंशन मिलती है। आवेदन ग्राम पंचायत में करें।"
            ),
            source="human",
            status="approved",
            created_by=users["editor"].id,
            approved_by=users["admin"].id,
            approved_at=datetime.now(UTC),
        )
    )
    session.add(
        SchemeSummary(
            scheme_id=shg.id,
            hindi_text=(
                "पंजीकृत स्व-सहायता समूह की सदस्य महिलाएँ समूह के बैंक खाते के माध्यम से "
                "₹3 लाख तक का ऋण कम ब्याज पर पा सकती हैं।"
            ),
            source="ai",
            status="draft",
            checks=AI_DRAFT_CHECKS,
            created_by=users["editor"].id,
        )
    )
    session.flush()


def main() -> None:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise SystemExit("DATABASE_URL is required")
    password = os.environ.get("SEED_DEMO_PASSWORD", DEMO_PASSWORD_DEFAULT)
    counts = run_seed(url, password)
    print(f"seeded: {counts}")  # noqa: T201  # CLI output


if __name__ == "__main__":
    main()

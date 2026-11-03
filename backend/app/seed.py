"""Idempotent demo data. Run with:  python -m app.seed

Everything here is illustrative sample data (assumption A1 in the TDD): the scheme values come
from the brief's sample rows plus a few invented schemes, the trust and donors are fictional,
and the demo accounts use a documented public password that must never be reused.
Re-running updates rows in place and never duplicates them.
"""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.config import Config
from app.models import (
    AuditLog,
    CallbackRequest,
    Campaign,
    Donation,
    Mandate,
    Receipt,
    ReceiptCounter,
    Scheme,
    SchemeSummary,
    User,
)
from app.security import PanCipher, hash_password, mask_pan

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

# Fictional donors, so the campaign report and raised totals are not empty on first run.
SAMPLE_DONORS: list[tuple[str, str, str | None]] = [
    ("Farida Khan", "farida@demo.example", "AAAPK1234Q"),
    ("Sunita Rajput", "sunita@demo.example", "AAAPR5678L"),
    ("Prakash Malviya", "prakash@demo.example", None),
    ("रेखा तिवारी", "rekha@demo.example", "AAAPT4321M"),
    ("Imran Qureshi", "imran@demo.example", None),
    ("Kavita Jain", "kavita@demo.example", "AAAPJ8765H"),
]
# (donor index, campaign index, rupees, days after 1 April 2026). Asha's own rows come first.
SAMPLE_PAID: list[tuple[int, int, int, int]] = [
    (0, 0, 2500, 40),
    (0, 1, 1000, 120),
    (1, 0, 25000, 9),
    (2, 0, 5000, 26),
    (3, 1, 1100, 33),
    (4, 0, 11000, 51),
    (5, 1, 500, 62),
    (6, 0, 15000, 70),
    (1, 1, 5000, 88),
    (2, 1, 2100, 96),
    (3, 0, 751, 104),
    (4, 1, 3000, 131),
    (5, 0, 1500, 145),
    (6, 1, 7500, 158),
    (1, 0, 21000, 172),
    (3, 0, 2000, 181),
    (5, 1, 1000, 190),
    (2, 0, 3500, 196),
]
SAMPLE_CALLBACKS: list[tuple[str, str, str | None]] = [
    ("9000000011", "रुखसाना", "SCH-014"),
    ("9000000022", "Geeta", "SCH-031"),
    ("9000000033", "", None),
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
        "who_can_apply_hi": "18 से 79 वर्ष की विधवा महिला जिसके पास बीपीएल कार्ड हो",
        "documents_hi": ["पति का मृत्यु प्रमाण पत्र", "बीपीएल कार्ड", "आधार से जुड़ी बैंक पासबुक"],
        "how_to_apply_hi": "दस्तावेज़ों के साथ ग्राम पंचायत या वार्ड कार्यालय में आवेदन करें।",
        "help_centre_hi": "ब्लॉक सामाजिक कल्याण कार्यालय",
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
        "who_can_apply_hi": "पंजीकृत स्व-सहायता समूह की सदस्य",
        "documents_hi": ["समूह के पंजीकरण का प्रमाण", "सदस्यों की सूची", "समूह की बैंक पासबुक"],
        "how_to_apply_hi": "अपने समूह संघ या नज़दीकी बैंक शाखा के ज़रिए आवेदन करें।",
        "help_centre_hi": "ज़िला आजीविका मिशन कार्यालय",
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
        "who_can_apply_hi": "गर्भवती महिला, पहला बच्चा",
        "documents_hi": ["गर्भावस्था पंजीकरण (एमसीपी कार्ड)", "बैंक पासबुक"],
        "how_to_apply_hi": "आँगनवाड़ी केंद्र या स्वास्थ्य उप-केंद्र में पंजीकरण कराएँ।",
        "help_centre_hi": "आँगनवाड़ी केंद्र",
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
        "who_can_apply_hi": "स्कूल जाने वाली बेटी और बीपीएल कार्ड वाला परिवार",
        "documents_hi": ["स्कूल में दाखिले का प्रमाण", "बीपीएल कार्ड"],
        "how_to_apply_hi": "स्कूल के प्रधानाचार्य के ज़रिए आवेदन करें।",
        "help_centre_hi": "ज़िला शिक्षा कार्यालय",
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
        "who_can_apply_hi": "18 से 45 वर्ष की महिलाएँ",
        "documents_hi": ["उम्र का प्रमाण", "बैंक पासबुक"],
        "how_to_apply_hi": "नज़दीकी कौशल केंद्र में पंजीकरण कराएँ।",
        "help_centre_hi": "ज़िला कौशल केंद्र",
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
        "who_can_apply_hi": "30 वर्ष और उससे अधिक उम्र की महिलाएँ",
        "documents_hi": ["कोई भी फ़ोटो पहचान पत्र"],
        "how_to_apply_hi": "शिविर में सीधे आएँ। तारीखें स्वास्थ्य केंद्र पर बताई जाती हैं।",
        "help_centre_hi": "सामुदायिक स्वास्थ्य केंद्र",
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
        "who_can_apply_hi": "बीपीएल परिवार जिसके पास पक्का मकान नहीं है",
        "documents_hi": ["बीपीएल कार्ड", "ज़मीन का दस्तावेज़"],
        "how_to_apply_hi": "ग्राम पंचायत में आवेदन करें।",
        "help_centre_hi": "ग्राम पंचायत",
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
    {
        "code": "SCH-070",
        "title_en": "One-stop support for women facing violence",
        "title_hi": "हिंसा से पीड़ित महिलाओं के लिए एक-स्थान सहायता",
        "need": "safety",
        "districts": ["Bhopal", "Indore", "Ujjain"],
        "benefit_en": "Free legal aid, counselling and up to 5 days of shelter",
        "benefit_hi": "निःशुल्क कानूनी मदद, परामर्श और 5 दिन तक आश्रय",
        "who_can_apply_en": "Any woman aged 18 or above facing violence at home or outside",
        "who_can_apply_hi": "घर या बाहर हिंसा झेल रही 18 वर्ष या उससे अधिक उम्र की कोई भी महिला",
        "documents": ["No documents needed to ask for help"],
        "documents_hi": ["मदद माँगने के लिए कोई दस्तावेज़ ज़रूरी नहीं"],
        "how_to_apply_en": "Walk in at the centre or ask the helpline to connect you.",
        "how_to_apply_hi": "केंद्र पर सीधे जाएँ या हेल्पलाइन से जुड़वाने के लिए कहें।",
        "help_centre": "District one-stop centre",
        "help_centre_hi": "ज़िला वन-स्टॉप केंद्र",
        "source_url": "https://example.org/notices/sch-070",
        "last_checked": date(2026, 10, 18),
        "rules": [
            {"field": "age", "op": "gte", "value": 18},
            {"field": "district", "op": "in", "value": ["Bhopal", "Indore", "Ujjain"]},
        ],
        "notice_text": (
            "Illustrative notice. Women aged 18 or above facing violence get free legal aid, "
            "counselling and shelter for up to 5 days at the one-stop centres in Bhopal, Indore "
            "and Ujjain."
        ),
        "status": "published",
    },
    {
        "code": "SCH-080",
        "title_en": "Tailoring machine grant",
        "title_hi": "सिलाई मशीन अनुदान",
        "need": "livelihood",
        "districts": [],
        "benefit_en": "Rs 7,500 towards a sewing machine",
        "benefit_hi": "सिलाई मशीन के लिए ₹7,500",
        "who_can_apply_en": "Women aged 20-55 with a BPL card",
        "who_can_apply_hi": "20 से 55 वर्ष की महिलाएँ जिनके पास बीपीएल कार्ड हो",
        "documents": ["BPL card", "Age proof", "Bank passbook"],
        "documents_hi": ["बीपीएल कार्ड", "उम्र का प्रमाण", "बैंक पासबुक"],
        "how_to_apply_en": "Apply at the district industries centre.",
        "how_to_apply_hi": "ज़िला उद्योग केंद्र में आवेदन करें।",
        "help_centre": "District industries centre",
        "help_centre_hi": "ज़िला उद्योग केंद्र",
        "source_url": "https://example.org/notices/sch-080",
        "last_checked": date(2026, 9, 28),
        "rules": [
            {"field": "age", "op": "between", "value": [20, 55]},
            {"field": "has_bpl_card", "op": "eq", "value": True},
        ],
        "notice_text": (
            "Illustrative notice. Women aged 20 to 55 who hold a BPL card can get Rs 7,500 "
            "towards a sewing machine through the district industries centre."
        ),
        "status": "published",
    },
    {
        "code": "SCH-090",
        "title_en": "Widow remarriage support",
        "title_hi": "विधवा पुनर्विवाह सहायता",
        "need": "pension",
        "districts": [],
        "benefit_en": "One-time Rs 2 lakh",
        "benefit_hi": "एक बार ₹2 लाख",
        "who_can_apply_en": "Widow aged 18-45",
        "who_can_apply_hi": "18 से 45 वर्ष की विधवा",
        "documents": ["Husband's death certificate", "Marriage certificate"],
        "documents_hi": ["पति का मृत्यु प्रमाण पत्र", "विवाह प्रमाण पत्र"],
        "how_to_apply_en": "Apply at the district women and child office.",
        "how_to_apply_hi": "ज़िला महिला एवं बाल विकास कार्यालय में आवेदन करें।",
        "help_centre": "District women and child office",
        "help_centre_hi": "ज़िला महिला एवं बाल विकास कार्यालय",
        "source_url": "https://example.org/notices/sch-090",
        "last_checked": date(2026, 8, 11),
        "rules": [
            {"field": "marital_status", "op": "eq", "value": "widow"},
            {"field": "age", "op": "between", "value": [18, 45]},
        ],
        "notice_text": (
            "Illustrative notice. Widows aged 18 to 45 who remarry may receive a one-time grant "
            "of Rs 2 lakh."
        ),
        # A draft, to show the editor workflow from the very first step.
        "status": "draft",
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


FY_SAMPLE = "2026-27"


def current_fy(today: date | None = None) -> str:
    """Indian financial year label (April to March), e.g. 2026-27."""
    d = today or date.today()
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def run_seed(database_url: str, demo_password: str, config: Config | None = None) -> dict[str, int]:
    """config supplies the trust details and PAN key for sample receipts. Without it, or with
    no PAN key in the environment, schemes and campaigns are seeded with no giving history."""
    engine = create_engine(database_url)
    with Session(engine) as session, session.begin():
        users = _seed_users(session, demo_password)
        _seed_by_key(session, Scheme, SCHEMES, "code")
        _seed_by_key(session, Campaign, CAMPAIGNS, "slug")
        _seed_summaries(session, users)
        if session.get(ReceiptCounter, current_fy()) is None:
            session.add(ReceiptCounter(fy=current_fy(), last_seq=0))
        session.flush()
        if config is not None:
            _seed_giving(session, users, config, demo_password)
        counts = {
            "users": session.scalar(select(func.count()).select_from(User)) or 0,
            "schemes": session.scalar(select(func.count()).select_from(Scheme)) or 0,
            "campaigns": session.scalar(select(func.count()).select_from(Campaign)) or 0,
            "summaries": session.scalar(select(func.count()).select_from(SchemeSummary)) or 0,
        }
    engine.dispose()
    return counts


def _seed_giving(session: Session, users: dict[str, User], config: Config, password: str) -> None:
    """Paid donations with real receipts, one due mandate and open call-backs. Runs once: receipts
    are immutable and numbered, so a re-run must not add to them."""
    if session.scalar(select(func.count()).select_from(Donation)):
        return
    cipher = PanCipher(config.pan_encryption_key)
    password_hash = hash_password(password)
    donors = [users["donor"]]
    users["donor"].pan_ciphertext = cipher.encrypt("AAAPV1234K")
    users["donor"].pan_masked = mask_pan("AAAPV1234K")
    for name, email, pan in SAMPLE_DONORS:
        donor = session.scalar(select(User).where(User.email == email))
        if donor is None:
            donor = User(
                email=email,
                password_hash=password_hash,
                full_name=name,
                role="donor",
                pan_ciphertext=cipher.encrypt(pan) if pan else None,
                pan_masked=mask_pan(pan) if pan else None,
            )
            session.add(donor)
        donors.append(donor)
    session.flush()
    campaigns = list(
        session.scalars(
            select(Campaign).where(Campaign.status == "live").order_by(Campaign.slug.desc())
        )
    )
    trust = {"name": config.trust_name, "pan": config.trust_pan, "reg_80g": config.trust_80g_reg}
    counter = session.get(ReceiptCounter, FY_SAMPLE) or ReceiptCounter(fy=FY_SAMPLE, last_seq=0)
    session.add(counter)
    start = datetime(2026, 4, 1, 11, 30, tzinfo=UTC)
    for i, (who, where, rupees, days) in enumerate(SAMPLE_PAID):
        donor, campaign, when = donors[who], campaigns[where], start + timedelta(days=days)
        donation = Donation(
            donor_id=donor.id,
            campaign_id=campaign.id,
            amount_paise=rupees * 100,
            kind="one_time",
            status="paid",
            gateway_ref=f"mock_seed_{i:04d}",
            idempotency_key=f"seed-{i:04d}",
            created_at=when,
            paid_at=when,
        )
        session.add(donation)
        session.flush()
        counter.last_seq += 1
        session.add(
            Receipt(
                donation_id=donation.id,
                fy=FY_SAMPLE,
                seq=counter.last_seq,
                number=f"RCPT/{FY_SAMPLE}/{counter.last_seq:06d}",
                issued_at=when,
                donor_name=donor.full_name,
                donor_email=donor.email,
                donor_pan_ciphertext=donor.pan_ciphertext,
                amount_paise=donation.amount_paise,
                campaign_title=campaign.title_en,
                trust_snapshot=trust,
            )
        )
    _seed_monthly(session, users["donor"], campaigns[1], start, counter, trust)
    session.add(
        Donation(
            donor_id=users["donor"].id,
            campaign_id=campaigns[0].id,
            amount_paise=75_000,
            kind="one_time",
            status="failed",
            failure_reason="declined",
            gateway_ref="mock_seed_failed",
            idempotency_key="seed-failed",
        )
    )
    for phone, name, code in SAMPLE_CALLBACKS:
        session.add(CallbackRequest(phone=phone, name=name, scheme_code=code))
    session.add(
        AuditLog(
            actor_id=users["admin"].id,
            action="scheme.transition",
            entity="scheme",
            entity_id="SCH-014",
            detail={"from": "in_review", "to": "published"},
        )
    )
    session.flush()


def _seed_monthly(
    session: Session,
    donor: User,
    campaign: Campaign,
    start: datetime,
    counter: ReceiptCounter,
    trust: dict[str, str],
) -> None:
    """Asha gives monthly, and a charge is due today, so the scheduler has work on a fresh demo."""
    when = start + timedelta(days=150)
    first = Donation(
        donor_id=donor.id,
        campaign_id=campaign.id,
        amount_paise=50_000,
        kind="monthly",
        status="paid",
        gateway_ref="mock_seed_monthly",
        idempotency_key="seed-monthly",
        created_at=when,
        paid_at=when,
    )
    session.add(first)
    session.flush()
    counter.last_seq += 1
    session.add(
        Receipt(
            donation_id=first.id,
            fy=FY_SAMPLE,
            seq=counter.last_seq,
            number=f"RCPT/{FY_SAMPLE}/{counter.last_seq:06d}",
            issued_at=when,
            donor_name=donor.full_name,
            donor_email=donor.email,
            donor_pan_ciphertext=donor.pan_ciphertext,
            amount_paise=first.amount_paise,
            campaign_title=campaign.title_en,
            trust_snapshot=trust,
        )
    )
    session.add(
        Mandate(
            donor_id=donor.id,
            campaign_id=campaign.id,
            first_donation_id=first.id,
            amount_paise=first.amount_paise,
            next_charge_on=date.today(),
        )
    )


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
    # Sample receipts need the PAN key and trust details; without them only the catalogue seeds.
    config = Config.from_env() if os.environ.get("PAN_ENCRYPTION_KEY") else None
    counts = run_seed(url, password, config)
    print(f"seeded: {counts}")  # noqa: T201  # CLI output


if __name__ == "__main__":
    main()

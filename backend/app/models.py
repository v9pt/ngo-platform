"""Database schema. Invariants live here (constraints, uniques, checks), not only in app code.

Money is stored as integer paise. Receipts are immutable (enforced by a DB trigger in the
initial migration) so an issued receipt number can never be edited or removed.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('donor','editor','admin')", name="ck_users_role"),
        CheckConstraint("preferred_language IN ('hi','en')", name="ck_users_language"),
        # Emails are unique case-insensitively.
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="donor")
    preferred_language: Mapped[str] = mapped_column(String(2), nullable=False, server_default="hi")
    # Encrypted at rest (Fernet). Optional until the donor first needs an 80G certificate.
    pan_ciphertext: Mapped[str | None] = mapped_column(Text)
    pan_masked: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[datetime] = _created_at()


class Scheme(Base):
    __tablename__ = "schemes"
    __table_args__ = (
        CheckConstraint("status IN ('draft','in_review','published')", name="ck_schemes_status"),
        Index("ix_schemes_status_need", "status", "need"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    title_hi: Mapped[str] = mapped_column(String(300), nullable=False)
    need: Mapped[str] = mapped_column(String(40), nullable=False)
    # Empty array means the scheme applies across all districts.
    districts: Mapped[list[str]] = mapped_column(
        ARRAY(String(60)), nullable=False, server_default=text("'{}'")
    )
    benefit_en: Mapped[str] = mapped_column(Text, nullable=False)
    benefit_hi: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    who_can_apply_en: Mapped[str] = mapped_column(Text, nullable=False)
    documents: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    how_to_apply_en: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    help_centre: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    last_checked: Mapped[date] = mapped_column(Date, nullable=False)
    # Eligibility rules as validated data: [{"field","op","value"}, ...]
    rules: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    # Plain text of the official notice used as input for AI summary drafts.
    notice_text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="draft")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SchemeSummary(Base):
    """A Hindi summary of a scheme. AI drafts are created as 'draft' and never self-publish."""

    __tablename__ = "scheme_summaries"
    __table_args__ = (
        CheckConstraint("source IN ('ai','human')", name="ck_summaries_source"),
        CheckConstraint("status IN ('draft','approved','rejected')", name="ck_summaries_status"),
        # Approved summaries must record who approved them and when.
        CheckConstraint(
            "status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_summaries_approval_recorded",
        ),
        Index("ix_summaries_scheme_status", "scheme_id", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    scheme_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schemes.id", ondelete="CASCADE"), nullable=False
    )
    hindi_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="draft")
    # Results of the deterministic checks run on AI drafts (script, length, numbers match source).
    checks: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("status IN ('draft','live','closed')", name="ck_campaigns_status"),
        CheckConstraint("goal_paise IS NULL OR goal_paise > 0", name="ck_campaigns_goal"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    title_en: Mapped[str] = mapped_column(String(200), nullable=False)
    title_hi: Mapped[str] = mapped_column(String(300), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    description_hi: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    goal_paise: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="draft")
    created_at: Mapped[datetime] = _created_at()


class Donation(Base):
    __tablename__ = "donations"
    __table_args__ = (
        CheckConstraint("amount_paise >= 10000", name="ck_donations_min_amount"),  # Rs 100 floor
        CheckConstraint("kind IN ('one_time','monthly')", name="ck_donations_kind"),
        CheckConstraint("status IN ('pending','paid','failed')", name="ck_donations_status"),
        # A retried POST with the same key must not create a second donation.
        UniqueConstraint("donor_id", "idempotency_key", name="uq_donations_donor_idem"),
        Index("ix_donations_donor_created", "donor_id", "created_at"),
        Index("ix_donations_campaign_status", "campaign_id", "status"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    donor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
    gateway_ref: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = _created_at()
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReceiptCounter(Base):
    """One row per financial year. Locked with UPDATE ... RETURNING inside the issue transaction."""

    __tablename__ = "receipt_counters"
    __table_args__ = (CheckConstraint("last_seq >= 0", name="ck_receipt_counters_seq"),)

    fy: Mapped[str] = mapped_column(String(7), primary_key=True)  # e.g. '2026-27'
    last_seq: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")


class Receipt(Base):
    """Immutable once inserted. Snapshot columns keep re-rendered PDFs identical forever."""

    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("fy", "seq", name="uq_receipts_fy_seq"),
        CheckConstraint("seq > 0", name="ck_receipts_seq"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    donation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("donations.id"), unique=True, nullable=False
    )
    fy: Mapped[str] = mapped_column(String(7), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    donor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    donor_email: Mapped[str] = mapped_column(String(254), nullable=False)
    donor_pan_ciphertext: Mapped[str | None] = mapped_column(Text)
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    campaign_title: Mapped[str] = mapped_column(String(300), nullable=False)
    trust_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity", "entity_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    entity: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(60), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    created_at: Mapped[datetime] = _created_at()

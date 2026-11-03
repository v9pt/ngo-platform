"""Request and response models. Every string is bounded; unknown fields are rejected."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    preferred_language: Literal["hi", "en"] = "hi"


class LoginRequest(StrictModel):
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Literal["donor", "editor", "admin"]
    preferred_language: Literal["hi", "en"]
    pan_masked: str | None = None


class DonationCreate(StrictModel):
    campaign_slug: str = Field(min_length=1, max_length=80)
    # Integer paise; the database enforces the same Rs 100 floor.
    amount_paise: int = Field(ge=10_000, le=10_000_000_00)
    kind: Literal["one_time", "monthly"] = "one_time"


class DonationOut(BaseModel):
    id: uuid.UUID
    campaign_slug: str
    campaign_title_en: str = ""
    campaign_title_hi: str = ""
    amount_paise: int
    kind: str
    status: str
    gateway_ref: str
    receipt_number: str | None = None
    # True when the receipt carries the donor's PAN, which makes it an 80G certificate.
    has_80g: bool = False
    failure_reason: str | None = None
    created_at: datetime | None = None


class PanUpdate(StrictModel):
    pan: str = Field(min_length=10, max_length=14)


class TestCharge(StrictModel):
    card_number: str = Field(min_length=12, max_length=24)
    issuing_country: str = Field(min_length=2, max_length=2)


class MandateOut(BaseModel):
    id: uuid.UUID
    campaign_title_en: str
    campaign_title_hi: str
    amount_paise: int
    status: str
    next_charge_on: date


class MandateRunOut(BaseModel):
    charged: int
    skipped: int


class WebhookEvent(StrictModel):
    gateway_ref: str = Field(min_length=1, max_length=80)
    event: Literal["payment.succeeded", "payment.failed"]


class SchemeSummaryOut(BaseModel):
    code: str
    title_en: str
    title_hi: str
    need: str
    districts: list[str]
    benefit_en: str
    benefit_hi: str


class SchemeDetailOut(SchemeSummaryOut):
    summary_hi: str | None = None
    who_can_apply_en: str
    documents: list[str]
    how_to_apply_en: str
    help_centre: str
    who_can_apply_hi: str = ""
    how_to_apply_hi: str = ""
    help_centre_hi: str = ""
    documents_hi: list[str] = []
    notice_text: str = ""
    source_url: str
    last_checked: date


class EligibilityAnswers(StrictModel):
    """Every question is optional: an unanswered question makes a scheme 'possible'."""

    age: int | None = Field(default=None, ge=0, le=120)
    marital_status: Literal["single", "married", "widow", "divorced", "separated"] | None = None
    has_bpl_card: bool | None = None
    pregnant: bool | None = None
    first_child: bool | None = None
    shg_member: bool | None = None
    has_school_age_girl: bool | None = None
    owns_pucca_house: bool | None = None
    district: str | None = Field(default=None, max_length=60)


class InterpretRequest(StrictModel):
    text: str = Field(min_length=3, max_length=500)


class InterpretOut(BaseModel):
    """Suggested answers. Nothing is decided here; the person reviews them first."""

    answers: dict[str, Any]
    unsure: list[str]
    source: Literal["ai", "rules"]


class CallbackCreate(StrictModel):
    # A 10-digit Indian mobile number; the country code is stripped by the client.
    phone: str = Field(pattern=r"^[6-9]\d{9}$")
    name: str = Field(default="", max_length=120)
    scheme_code: str | None = Field(default=None, max_length=20)
    language: Literal["hi", "en"] = "hi"
    consent: Literal[True]


class CallbackOut(BaseModel):
    id: uuid.UUID
    phone: str
    name: str
    scheme_code: str | None
    language: str
    status: str
    created_at: datetime


class RuleResultOut(BaseModel):
    field: str
    op: str
    value: Any
    outcome: Literal["met", "not_met", "unknown"]


class SchemeCheckOut(BaseModel):
    code: str
    title_en: str
    title_hi: str
    need: str = ""
    benefit_en: str = ""
    benefit_hi: str = ""
    status: Literal["match", "possible", "excluded"]
    rules: list[RuleResultOut]


class CampaignOut(BaseModel):
    slug: str
    title_en: str
    title_hi: str
    description_en: str
    description_hi: str
    goal_paise: int | None
    raised_paise: int


class AdminSchemeRow(BaseModel):
    code: str
    title_en: str
    title_hi: str
    status: str
    notice_text: str
    benefit_hi: str


class Rule(StrictModel):
    field: str = Field(max_length=40)
    op: Literal["eq", "in", "between", "gte"]
    value: bool | int | str | list[int] | list[str]


Need = Literal["pension", "livelihood", "health", "education", "housing", "safety"]


class SchemeEdit(StrictModel):
    title_en: str | None = Field(default=None, min_length=1, max_length=200)
    title_hi: str | None = Field(default=None, min_length=1, max_length=300)
    need: Need | None = None
    districts: list[str] | None = Field(default=None, max_length=60)
    benefit_en: str | None = Field(default=None, max_length=4000)
    benefit_hi: str | None = Field(default=None, max_length=4000)
    who_can_apply_en: str | None = Field(default=None, max_length=4000)
    who_can_apply_hi: str | None = Field(default=None, max_length=4000)
    documents: list[str] | None = Field(default=None, max_length=30)
    documents_hi: list[str] | None = Field(default=None, max_length=30)
    how_to_apply_en: str | None = Field(default=None, max_length=4000)
    how_to_apply_hi: str | None = Field(default=None, max_length=4000)
    help_centre: str | None = Field(default=None, max_length=1000)
    help_centre_hi: str | None = Field(default=None, max_length=1000)
    source_url: str | None = Field(default=None, pattern=r"^https?://", max_length=500)
    last_checked: date | None = None
    rules: list[Rule] | None = Field(default=None, max_length=20)
    notice_text: str | None = Field(default=None, max_length=20000)


class SchemeCreate(StrictModel):
    title_en: str = Field(min_length=1, max_length=200)
    title_hi: str = Field(min_length=1, max_length=300)
    need: Need


class AdminSchemeDetail(AdminSchemeRow):
    need: str
    districts: list[str]
    benefit_en: str
    who_can_apply_en: str
    who_can_apply_hi: str
    documents: list[str]
    documents_hi: list[str]
    how_to_apply_en: str
    how_to_apply_hi: str
    help_centre: str
    help_centre_hi: str
    source_url: str
    last_checked: date
    rules: list[dict[str, Any]]


class AuditEntry(BaseModel):
    action: str
    actor_name: str | None
    detail: dict[str, Any]
    created_at: datetime


class SummaryCreate(StrictModel):
    hindi_text: str = Field(min_length=1, max_length=2000)


class Transition(StrictModel):
    to: Literal["draft", "in_review", "published"]


class SummaryOut(BaseModel):
    id: uuid.UUID
    scheme_code: str
    hindi_text: str
    source: str
    status: str
    checks: dict[str, Any]
    approved_by: uuid.UUID | None = None


class SummaryEdit(StrictModel):
    hindi_text: str = Field(min_length=1, max_length=2000)


class CampaignReport(BaseModel):
    slug: str
    title_en: str = ""
    status: str = ""
    goal_paise: int | None = None
    paid_count: int
    paid_paise: int
    pending_count: int
    failed_count: int

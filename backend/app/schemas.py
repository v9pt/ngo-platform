"""Request and response models. Every string is bounded; unknown fields are rejected."""

from __future__ import annotations

import uuid
from datetime import date
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
    amount_paise: int
    kind: str
    status: str
    gateway_ref: str
    receipt_number: str | None = None


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
    who_can_apply_en: str
    documents: list[str]
    how_to_apply_en: str
    help_centre: str
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


class RuleResultOut(BaseModel):
    field: str
    op: str
    value: Any
    outcome: Literal["met", "not_met", "unknown"]


class SchemeCheckOut(BaseModel):
    code: str
    title_en: str
    title_hi: str
    status: Literal["match", "possible", "excluded"]
    rules: list[RuleResultOut]

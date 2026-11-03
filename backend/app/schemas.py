"""Request and response models. Every string is bounded; unknown fields are rejected."""

from __future__ import annotations

import uuid
from typing import Literal

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

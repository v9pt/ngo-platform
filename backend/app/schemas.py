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

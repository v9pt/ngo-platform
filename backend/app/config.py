"""Application configuration: every value comes from the environment and is
validated once at startup, so a misconfigured process refuses to boot instead
of failing on the first request."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from cryptography.fernet import Fernet

AppEnv = Literal["dev", "test", "prod"]


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    app_env: AppEnv
    database_url: str
    jwt_secret: str
    pan_encryption_key: str
    gateway_webhook_secret: str
    cors_origins: tuple[str, ...]
    anthropic_api_key: str | None
    summary_model: str
    cookie_secure: bool
    # Trust details printed on receipts and 80G certificates. In this build they
    # are clearly fake placeholders (assumption A3 in the TDD).
    trust_name: str
    trust_pan: str
    trust_80g_reg: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        e = os.environ if env is None else env

        app_env = e.get("APP_ENV", "dev")
        if app_env not in ("dev", "test", "prod"):
            raise ConfigError("APP_ENV must be one of: dev, test, prod")

        database_url = _required(e, "DATABASE_URL")
        if not database_url.startswith("postgresql+psycopg://"):
            raise ConfigError("DATABASE_URL must start with postgresql+psycopg://")

        jwt_secret = _required(e, "JWT_SECRET")
        if len(jwt_secret) < 32:
            raise ConfigError("JWT_SECRET must be at least 32 characters")

        pan_key = _required(e, "PAN_ENCRYPTION_KEY")
        try:
            Fernet(pan_key.encode())
        except (ValueError, TypeError) as exc:
            raise ConfigError("PAN_ENCRYPTION_KEY must be a valid Fernet key") from exc

        webhook_secret = _required(e, "GATEWAY_WEBHOOK_SECRET")
        if len(webhook_secret) < 32:
            raise ConfigError("GATEWAY_WEBHOOK_SECRET must be at least 32 characters")

        origins = tuple(o.strip() for o in e.get("CORS_ORIGINS", "").split(",") if o.strip())
        if "*" in origins:
            raise ConfigError("CORS_ORIGINS must list explicit origins, never '*'")

        # Cookies must be Secure in production; allow plain HTTP only for local dev/test.
        cookie_secure = app_env == "prod"
        if app_env == "prod" and not origins:
            raise ConfigError("CORS_ORIGINS is required in prod")

        return cls(
            app_env=app_env,  # type: ignore[arg-type]  # narrowed by the check above
            database_url=database_url,
            jwt_secret=jwt_secret,
            pan_encryption_key=pan_key,
            gateway_webhook_secret=webhook_secret,
            cors_origins=origins,
            anthropic_api_key=e.get("ANTHROPIC_API_KEY", "").strip() or None,
            summary_model=e.get("SUMMARY_MODEL", "claude-haiku-5-5"),
            cookie_secure=cookie_secure,
            trust_name=e.get("TRUST_NAME", "Demo Mahila Vikas Trust (placeholder)"),
            trust_pan=e.get("TRUST_PAN", "AAAAA0000A"),
            trust_80g_reg=e.get("TRUST_80G_REG", "DEMO/80G/0000 (placeholder)"),
        )


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required")
    return value

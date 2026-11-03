"""Test fixtures. Tests run against a real Postgres (receipt locking cannot be proven on SQLite).

Set TEST_DATABASE_URL to a throwaway database; the default matches the README's local setup.
The schema is built by running the real Alembic migration, so migrations are tested too.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic.config import Config as AlembicConfig
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from alembic import command
from app.config import Config
from app.main import create_app
from app.routers import auth

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres@localhost:5433/ngo_test"
)
BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_PAN_KEY = Fernet.generate_key().decode()


def make_config(**overrides: str) -> Config:
    env = {
        "APP_ENV": "test",
        "DATABASE_URL": TEST_DB_URL,
        "JWT_SECRET": "test-secret-test-secret-test-secret-1234",
        "PAN_ENCRYPTION_KEY": TEST_PAN_KEY,
        **overrides,
    }
    return Config.from_env(env)


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    """Build the schema once per test session by running the real migrations."""
    os.environ["DATABASE_URL"] = TEST_DB_URL
    cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture
async def app() -> AsyncIterator[object]:
    application = create_app(make_config())
    async with application.state.engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE audit_log, receipts, receipt_counters, donations, scheme_summaries, "
                "campaigns, schemes, users RESTART IDENTITY CASCADE"
            )
        )
    auth.login_limiter.reset()
    auth.register_limiter.reset()
    yield application
    await application.state.engine.dispose()


@pytest.fixture
async def client(app: object) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

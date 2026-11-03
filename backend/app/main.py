"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import Config
from app.db import create_engine, create_sessionmaker
from app.errors import install_error_handlers, problem
from app.routers import auth, campaigns, donations, schemes
from app.security import PanCipher


def create_app(config: Config | None = None) -> FastAPI:
    config = config or Config.from_env()
    engine = create_engine(config)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            # Graceful shutdown: close pooled connections after in-flight requests drain.
            await engine.dispose()

    is_prod = config.app_env == "prod"
    app = FastAPI(
        title="NGO Platform API",
        version="0.1.0",
        lifespan=lifespan,
        # The public schema UI is off in production.
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )
    app.state.config = config
    app.state.engine = engine
    app.state.sessionmaker = create_sessionmaker(engine)
    app.state.pan_cipher = PanCipher(config.pan_encryption_key)

    if config.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(config.cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Content-Type", "Idempotency-Key"],
        )

    install_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(donations.router)
    app.include_router(schemes.router)
    app.include_router(campaigns.router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        """Liveness only. Does not touch the database, so a DB blip cannot cause restarts."""
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"], response_model=None)
    async def ready() -> dict[str, str] | object:
        """Readiness: round-trips the database."""
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            return problem(503, "Database unavailable")
        return {"status": "ready"}

    return app

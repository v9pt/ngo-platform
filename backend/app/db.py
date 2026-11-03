"""Async engine and per-request transactional session."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Config


def create_engine(config: Config) -> AsyncEngine:
    # pool_pre_ping survives managed-database restarts; the pool is sized per instance.
    return create_async_engine(config.database_url, pool_size=5, max_overflow=5, pool_pre_ping=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One transaction per request: commit on success, roll back on any exception."""
    maker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with maker() as session, session.begin():
        yield session


# scope="function" commits before the response is sent. The default scope commits afterwards, so a
# client could hear "done" and read the old row, or be told a payment succeeded and then lose it.
db_session = Depends(get_session, scope="function")

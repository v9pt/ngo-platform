"""Shared FastAPI dependencies: current user and role checks."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.db import db_session
from app.models import User
from app.security import decode_session_token

SESSION_COOKIE = "session"


def get_config(request: Request) -> Config:
    config: Config = request.app.state.config
    return config


async def current_user(
    request: Request,
    session: AsyncSession = db_session,
    config: Config = Depends(get_config),
) -> User:
    """Resolve the signed-in user from the session cookie, or raise a generic 401.

    The real reason a token failed is deliberately not returned to the client.
    """
    token = request.cookies.get(SESSION_COOKIE)
    claims = decode_session_token(config.jwt_secret, token) if token else None
    if claims is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    try:
        user_id = uuid.UUID(claims["sub"])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Please sign in.") from exc
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    """Allow only the listed roles. The role comes from the DB row, not the token."""

    def _check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have access to this.")
        return user

    return _check

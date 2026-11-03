"""Registration, login, logout and the current-user endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.db import get_session
from app.deps import SESSION_COOKIE, current_user, get_config
from app.models import User
from app.ratelimit import RateLimiter
from app.schemas import LoginRequest, PanUpdate, RegisterRequest, UserOut
from app.security import (
    SESSION_TTL,
    create_session_token,
    hash_password,
    is_valid_pan,
    mask_pan,
    normalize_pan,
    verify_password,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])

# 10 attempts per 5 minutes per (client, email). Limits are per process; see ratelimit.py.
login_limiter = RateLimiter(max_events=10, window_seconds=300)
register_limiter = RateLimiter(max_events=10, window_seconds=3600)

# A fixed hash to compare against when the email is unknown, so response time does not
# reveal whether an account exists.
_DUMMY_HASH = hash_password("not-a-real-password")


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, config: Config, user: User) -> None:
    token = create_session_token(config.jwt_secret, user.id, user.role)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_TTL.total_seconds()),
        httponly=True,
        secure=config.cookie_secure,
        samesite="lax",
        path="/",
    )


def _to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        preferred_language=user.preferred_language,
        pan_masked=user.pan_masked,
    )


@router.post("/register", status_code=201, response_model=UserOut)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    config: Config = Depends(get_config),
) -> UserOut:
    register_limiter.check(_client_key(request))
    existing = await session.scalar(
        select(User.id).where(func.lower(User.email) == body.email.lower())
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role="donor",  # never taken from the client
        preferred_language=body.preferred_language,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:  # lost a race with a concurrent registration
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from exc
    _set_session_cookie(response, config, user)
    return _to_out(user)


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    config: Config = Depends(get_config),
) -> UserOut:
    limit_key = f"{_client_key(request)}:{body.email.lower()}"
    login_limiter.check(limit_key)
    user = await session.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    # Always run one hash verification so timing does not reveal whether the email exists.
    ok = verify_password(user.password_hash if user else _DUMMY_HASH, body.password)
    if user is None or not ok:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    login_limiter.forget(limit_key)  # only failures count towards the limit
    _set_session_cookie(response, config, user)
    return _to_out(user)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.put("/me/pan", response_model=UserOut)
async def save_pan(
    body: PanUpdate,
    request: Request,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    """Encrypt and store the donor's PAN. Receipts issued from now on become 80G certificates;
    receipts already issued are immutable and keep what they recorded."""
    pan = normalize_pan(body.pan)
    if not is_valid_pan(pan):
        raise HTTPException(status_code=422, detail="Enter a PAN like ABCDE1234F.")
    user.pan_ciphertext = request.app.state.pan_cipher.encrypt(pan)
    user.pan_masked = mask_pan(pan)
    await session.flush()
    return _to_out(user)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)) -> UserOut:
    return _to_out(user)

"""Password hashing, session tokens and PAN handling (validation, encryption, masking)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

_hasher = PasswordHasher()
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "ngo-platform"
SESSION_TTL = timedelta(hours=12)

# Indian PAN: 5 letters, 4 digits, 1 letter. Format check only; it does not prove the PAN exists.
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True only on a match. Malformed hashes count as a failed login, not a crash."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_session_token(secret: str, user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iss": JWT_ISSUER,
        "iat": now,
        "exp": now + SESSION_TTL,
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def decode_session_token(secret: str, token: str) -> dict[str, str] | None:
    """Verify signature, expiry and issuer with the algorithm pinned. None on any failure."""
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            options={"require": ["exp", "sub", "iss"]},
        )
    except jwt.PyJWTError:
        return None
    return {"sub": str(claims["sub"]), "role": str(claims.get("role", ""))}


def normalize_pan(raw: str) -> str:
    return raw.strip().upper()


def is_valid_pan(pan: str) -> bool:
    return bool(PAN_RE.fullmatch(pan))


def mask_pan(pan: str) -> str:
    """Show only the first two and last characters: ABCDE1234F -> AB*******F."""
    if len(pan) != 10:
        return "**********"
    return f"{pan[:2]}*******{pan[-1]}"


class PanCipher:
    """Encrypts PAN values at rest. The key comes from the environment, never the repo."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, pan: str) -> str:
        return self._fernet.encrypt(pan.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("PAN ciphertext could not be decrypted") from exc

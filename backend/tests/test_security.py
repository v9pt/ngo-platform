import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.fernet import Fernet

from app.security import (
    PanCipher,
    create_session_token,
    decode_session_token,
    hash_password,
    is_valid_pan,
    mask_pan,
    normalize_pan,
    verify_password,
)

SECRET = "s" * 40


def test_password_round_trip_and_wrong_password() -> None:
    h = hash_password("correct horse battery")
    assert verify_password(h, "correct horse battery")
    assert not verify_password(h, "wrong password!!")


def test_malformed_hash_is_a_failed_login_not_a_crash() -> None:
    assert verify_password("not-a-hash", "anything") is False


def test_session_token_round_trip() -> None:
    uid = uuid.uuid4()
    claims = decode_session_token(SECRET, create_session_token(SECRET, uid, "donor"))
    assert claims == {"sub": str(uid), "role": "donor"}


def test_token_signed_with_other_secret_is_rejected() -> None:
    token = create_session_token("other-secret-other-secret-other-1", uuid.uuid4(), "admin")
    assert decode_session_token(SECRET, token) is None


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "iss": "ngo-platform", "exp": past}, SECRET, algorithm="HS256"
    )
    assert decode_session_token(SECRET, token) is None


def test_alg_none_token_is_rejected() -> None:
    token = jwt.encode({"sub": "x", "iss": "ngo-platform"}, key="", algorithm="none")
    assert decode_session_token(SECRET, token) is None


def test_token_with_wrong_issuer_is_rejected() -> None:
    exp = datetime.now(UTC) + timedelta(hours=1)
    token = jwt.encode({"sub": "x", "iss": "someone-else", "exp": exp}, SECRET, algorithm="HS256")
    assert decode_session_token(SECRET, token) is None


@pytest.mark.parametrize(
    ("pan", "valid"),
    [
        ("ABCDE1234F", True),
        ("abcde1234f", False),  # callers must normalize first
        ("ABCDE12345", False),
        ("ABCD1234FF", False),
        ("ABCDE1234", False),
        ("ABCDE1234FG", False),
        ("", False),
    ],
)
def test_pan_format_validation(pan: str, valid: bool) -> None:
    assert is_valid_pan(pan) is valid


def test_normalize_pan_trims_and_uppercases() -> None:
    assert normalize_pan("  abcde1234f ") == "ABCDE1234F"


def test_mask_pan_hides_the_middle() -> None:
    assert mask_pan("ABCDE1234F") == "AB*******F"
    assert mask_pan("bad") == "**********"


def test_pan_cipher_round_trip_and_ciphertext_hides_value() -> None:
    cipher = PanCipher(Fernet.generate_key().decode())
    ct = cipher.encrypt("ABCDE1234F")
    assert "ABCDE1234F" not in ct
    assert cipher.decrypt(ct) == "ABCDE1234F"


def test_pan_cipher_rejects_ciphertext_from_another_key() -> None:
    ct = PanCipher(Fernet.generate_key().decode()).encrypt("ABCDE1234F")
    with pytest.raises(ValueError, match="could not be decrypted"):
        PanCipher(Fernet.generate_key().decode()).decrypt(ct)

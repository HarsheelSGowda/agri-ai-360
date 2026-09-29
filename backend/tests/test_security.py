"""
Unit tests for app/core/security.py — password hashing/verification and JWT
issuing/decoding. No network, no DB, fully deterministic.
"""

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_hash_password_produces_a_bcrypt_hash_different_from_the_plaintext():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # bcrypt hash format


def test_hash_password_is_salted_so_the_same_password_hashes_differently_each_time():
    a = hash_password("samepassword")
    b = hash_password("samepassword")
    assert a != b


def test_verify_password_accepts_the_correct_password():
    hashed = hash_password("mypassword123")
    assert verify_password("mypassword123", hashed) is True


def test_verify_password_rejects_an_incorrect_password():
    hashed = hash_password("mypassword123")
    assert verify_password("wrongpassword", hashed) is False


def test_verify_password_is_case_sensitive():
    hashed = hash_password("MyPassword123")
    assert verify_password("mypassword123", hashed) is False


def test_hash_password_rejects_passwords_over_72_bytes_KNOWN_LIMITATION():
    """
    Documents real, currently-existing behavior (not modified by this test pass):
    the `bcrypt` library used here hard-rejects any password over 72 bytes with
    a ValueError. RegisterRequest.password (schemas/auth.py) allows up to 255
    characters, so a legitimate long passphrase between 73-255 characters
    currently crashes hash_password() instead of being handled gracefully.
    See test_auth.py::test_register_with_password_over_72_bytes_currently_raises_KNOWN_BUG
    for the resulting API-level impact.
    """
    long_password = "a" * 100  # valid per the schema's max_length=255, invalid per bcrypt's 72-byte limit
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(long_password)


def test_hash_password_accepts_exactly_72_bytes():
    password_72_bytes = "a" * 72
    hashed = hash_password(password_72_bytes)
    assert verify_password(password_72_bytes, hashed) is True


def test_create_and_decode_access_token_roundtrip():
    token = create_access_token(subject="farmer@example.com")
    assert decode_access_token(token) == "farmer@example.com"


def test_decode_access_token_rejects_garbage_string():
    assert decode_access_token("not.a.jwt") is None


def test_decode_access_token_rejects_empty_string():
    assert decode_access_token("") is None


def test_decode_access_token_rejects_token_signed_with_a_different_secret():
    bad_token = jwt.encode(
        {"sub": "farmer@example.com", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "a-completely-different-secret",
        algorithm=settings.algorithm,
    )
    assert decode_access_token(bad_token) is None


def test_decode_access_token_rejects_an_expired_token():
    expired_token = jwt.encode(
        {"sub": "farmer@example.com", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    assert decode_access_token(expired_token) is None


def test_decode_access_token_accepts_a_token_with_no_exp_claim():
    """
    Documents actual behavior: jose's jwt.decode does not require an `exp`
    claim to be present. Since create_access_token() always sets one, this
    can't happen through normal app usage, but it means a hand-crafted token
    with no expiry would never expire if it reached decode_access_token().
    """
    token_without_exp = jwt.encode({"sub": "farmer@example.com"}, settings.secret_key, algorithm=settings.algorithm)
    assert decode_access_token(token_without_exp) == "farmer@example.com"

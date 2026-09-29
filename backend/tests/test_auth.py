"""
Tests for the authentication API (app/api/auth.py) and the shared
authorization dependency chain (app/api/deps.py: get_current_user ->
get_current_farmer), exercised through a real protected endpoint (GET
/api/farms) since deps.py has no router of its own.
"""

import uuid

from app.core.security import create_access_token
from app.models.user import Farmer, User


def _unique_email(prefix: str = "auth") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------


def test_register_success_returns_token_and_user(client):
    email = _unique_email()
    resp = client.post(
        "/api/auth/register",
        json={"name": "Ramesh Patil", "email": email, "password": "secret123", "location": "Nagpur, Maharashtra"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == email
    assert body["user"]["name"] == "Ramesh Patil"
    assert body["user"]["location"] == "Nagpur, Maharashtra"
    assert body["user"]["preferred_language"] == "English"  # schema default


def test_register_without_location_is_allowed(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "No Location Farmer", "email": _unique_email(), "password": "secret123"},
    )
    assert resp.status_code == 201
    assert resp.json()["user"]["location"] is None


def test_register_duplicate_email_returns_409(client):
    email = _unique_email()
    payload = {"name": "First", "email": email, "password": "secret123"}
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/auth/register", json={**payload, "name": "Second"})
    assert second.status_code == 409
    assert "already exists" in second.json()["detail"].lower()


def test_register_duplicate_email_check_is_case_sensitive_KNOWN_LIMITATION(client):
    """
    Documents actual behavior (not modified by this test pass): the duplicate-
    email check is a plain SQL equality filter (User.email == payload.email)
    with no case normalization, and SQLite string comparison is case-sensitive
    by default. So "Farmer@Example.com" and "farmer@example.com" are treated
    as two different accounts today, even though most real-world email
    systems treat the local part/domain as effectively case-insensitive for
    login purposes. This is a validation gap worth fixing separately, not a
    5xx crash - so it's documented as a limitation, not a hard bug.
    """
    base = uuid.uuid4().hex[:10]
    lower_email = f"casetest_{base}@example.com"
    upper_email = f"CaseTest_{base}@EXAMPLE.com"

    first = client.post("/api/auth/register", json={"name": "Lower", "email": lower_email, "password": "secret123"})
    assert first.status_code == 201

    second = client.post("/api/auth/register", json={"name": "Upper", "email": upper_email, "password": "secret123"})
    assert second.status_code == 201  # not rejected as a duplicate - documents current behavior


def test_register_rejects_invalid_email_format(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Bad Email", "email": "not-an-email", "password": "secret123"},
    )
    assert resp.status_code == 422


def test_register_rejects_password_shorter_than_6_chars(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Short Password", "email": _unique_email(), "password": "12345"},
    )
    assert resp.status_code == 422


def test_register_rejects_missing_name(client):
    resp = client.post("/api/auth/register", json={"email": _unique_email(), "password": "secret123"})
    assert resp.status_code == 422


def test_register_rejects_empty_name(client):
    resp = client.post("/api/auth/register", json={"name": "", "email": _unique_email(), "password": "secret123"})
    assert resp.status_code == 422


def test_register_with_password_over_72_bytes_currently_raises_KNOWN_BUG(client):
    """
    Documents a genuine, currently-unfixed bug (found while adding this test
    coverage, not fixed here per this pass's "don't change production
    behavior" rule): RegisterRequest.password (schemas/auth.py) permits up to
    255 characters, but hash_password() uses the `bcrypt` library directly,
    which raises ValueError for any password over 72 bytes. auth.py's
    register() has no try/except around hash_password(), so this currently
    surfaces as an unhandled exception (not a clean 4xx) for any legitimate
    long passphrase between 73 and 255 characters - i.e. within the range the
    API's own schema advertises as valid. TestClient re-raises unhandled
    server exceptions by default, which is what this test asserts.
    """
    import pytest

    long_password = "a" * 100  # <= schema's max_length=255, > bcrypt's real 72-byte limit
    with pytest.raises(ValueError, match="72 bytes"):
        client.post(
            "/api/auth/register",
            json={"name": "Long Password Farmer", "email": _unique_email(), "password": long_password},
        )


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


def test_login_success_returns_token(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"name": "Login Test", "email": email, "password": "secret123"})

    resp = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["email"] == email


def test_login_wrong_password_returns_401(client):
    email = _unique_email()
    client.post("/api/auth/register", json={"name": "Login Test", "email": email, "password": "secret123"})

    resp = client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    assert resp.status_code == 401
    assert "incorrect email or password" in resp.json()["detail"].lower()


def test_login_nonexistent_email_returns_401(client):
    resp = client.post("/api/auth/login", json={"email": _unique_email("ghost"), "password": "whatever123"})
    assert resp.status_code == 401


def test_login_does_not_reveal_whether_the_email_exists(client):
    """Both 'wrong password' and 'no such account' must return the identical
    generic message, so a login form can't be used to enumerate real accounts."""
    email = _unique_email()
    client.post("/api/auth/register", json={"name": "Enumeration Test", "email": email, "password": "secret123"})

    wrong_password_resp = client.post("/api/auth/login", json={"email": email, "password": "wrongpassword"})
    no_account_resp = client.post("/api/auth/login", json={"email": _unique_email("ghost"), "password": "whatever123"})

    assert wrong_password_resp.status_code == no_account_resp.status_code == 401
    assert wrong_password_resp.json()["detail"] == no_account_resp.json()["detail"]


def test_login_for_user_with_no_farmer_profile_returns_404(client, db_session):
    """A User row can in principle exist without a Farmer row (e.g. partial data
    migration) - login must fail cleanly (404), not crash or fabricate a profile."""
    email = _unique_email("orphan")
    from app.core.security import hash_password

    user = User(email=email, password_hash=hash_password("secret123"))
    db_session.add(user)
    db_session.commit()

    resp = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    assert resp.status_code == 404
    assert "farmer profile" in resp.json()["detail"].lower()


def test_login_rejects_invalid_email_format(client):
    resp = client.post("/api/auth/login", json={"email": "not-an-email", "password": "secret123"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Authorization dependency chain (deps.py), exercised via GET /api/farms
# ---------------------------------------------------------------------------


def test_protected_endpoint_without_any_auth_header_returns_401(client):
    resp = client.get("/api/farms")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"


def test_protected_endpoint_with_garbage_token_returns_401(client):
    resp = client.get("/api/farms", headers={"Authorization": "Bearer this.is.not.a.valid.jwt"})
    assert resp.status_code == 401
    assert "invalid or expired" in resp.json()["detail"].lower()


def test_protected_endpoint_with_expired_token_returns_401(client):
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from app.core.config import settings

    expired = jwt.encode(
        {"sub": "someone@example.com", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.algorithm,
    )
    resp = client.get("/api/farms", headers={"Authorization": f"Bearer {expired}"})
    assert resp.status_code == 401


def test_protected_endpoint_with_token_for_nonexistent_user_returns_401(client):
    token = create_access_token(subject=_unique_email("never-registered"))
    resp = client.get("/api/farms", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "user not found" in resp.json()["detail"].lower()


def test_protected_endpoint_with_valid_token_but_no_farmer_profile_returns_404(client, db_session):
    from app.core.security import hash_password

    email = _unique_email("orphan2")
    user = User(email=email, password_hash=hash_password("secret123"))
    db_session.add(user)
    db_session.commit()

    token = create_access_token(subject=email)
    resp = client.get("/api/farms", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert "farmer profile" in resp.json()["detail"].lower()


def test_protected_endpoint_with_valid_token_succeeds(client, auth_headers):
    resp = client.get("/api/farms", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []  # freshly registered farmer has no farms yet


def test_protected_endpoint_with_malformed_authorization_header_returns_401(client):
    # No "Bearer " scheme prefix at all.
    resp = client.get("/api/farms", headers={"Authorization": "just-a-raw-token-value"})
    assert resp.status_code == 401


def test_protected_endpoint_with_wrong_auth_scheme_returns_401(client, auth_headers):
    token = auth_headers["Authorization"].split(" ", 1)[1]
    resp = client.get("/api/farms", headers={"Authorization": f"Basic {token}"})
    assert resp.status_code == 401


def test_full_register_login_access_roundtrip_uses_two_independent_valid_tokens(client):
    """Register, then log in separately, and confirm both tokens independently
    authorize the same account (no session/single-token coupling bug)."""
    email = _unique_email()
    register_resp = client.post("/api/auth/register", json={"name": "Roundtrip", "email": email, "password": "secret123"})
    register_token = register_resp.json()["access_token"]

    login_resp = client.post("/api/auth/login", json={"email": email, "password": "secret123"})
    login_token = login_resp.json()["access_token"]

    for token in (register_token, login_token):
        resp = client.get("/api/farms", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

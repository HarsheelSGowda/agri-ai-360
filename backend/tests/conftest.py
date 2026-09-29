"""
Shared pytest fixtures for backend API tests.

Uses a dedicated SQLite file (separate from the dev/demo `agriai.db`) so tests
never touch real data, wired in via FastAPI's dependency_overrides for get_db
(the standard pattern - no changes needed to application code to test it).
"""

import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models import *  # noqa: F401,F403  (registers all ORM models with Base metadata)

TEST_DB_PATH = Path(__file__).parent / "test_agriai.db"
engine = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_session():
    """Direct access to the test database session, for tests that need to set up
    state the API itself can't produce (e.g. a User row with no Farmer profile)."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def auth_headers(client):
    """A fresh registered farmer for each test (unique email avoids cross-test collisions)."""
    email = f"test_{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Test Farmer",
            "email": email,
            "password": "testpass123",
            "location": "Nashik, Maharashtra",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def farm(client, auth_headers):
    resp = client.post(
        "/api/farms",
        json={
            "name": "Test Farm",
            "location": "Nashik, Maharashtra",
            "area_acres": 5,
            "soil_type": "Loamy",
            "irrigation_available": True,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()

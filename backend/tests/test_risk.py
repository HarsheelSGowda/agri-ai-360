"""
Tests for app/api/risk.py (GET /risk?farm_id=) - the original rule-based
weather/soil/water/disease risk endpoint (distinct from the ML-based
risk_ml_router.py). risk_service.compute_risk() and soil_health.py are
already fully covered elsewhere; these tests focus on this router's own
wiring: farm ownership, the required farm_id query param, "most recent soil
record wins", and that weather/soil/irrigation values genuinely flow through
to the returned risk. Weather is stubbed (via monkeypatching
get_weather_provider, the same pattern used in test_dashboard.py and
test_notification_service.py) only where a specific risk tier needs to be
pinned deterministically.
"""

import uuid
from datetime import datetime, timedelta, timezone

import app.api.risk as risk_module
from app.models.soil import SoilRecord

GOOD_SOIL = {"nitrogen": 80, "phosphorus": 40, "potassium": 55, "ph": 6.75}  # score 100
BAD_SOIL = {"nitrogen": 5, "phosphorus": 2, "potassium": 5, "ph": 4.0}  # score 24

CALM_WEATHER = {  # 0 weather-risk flags -> LOW
    "temperature_c": 25, "rainfall_mm": 5, "humidity_pct": 50, "wind_kmh": 10,
    "condition": "Clear Sky", "forecast": [], "source": "mock",
}
SEVERE_WEATHER = {  # 3 flags -> HIGH
    "temperature_c": 42, "rainfall_mm": 0, "humidity_pct": 95, "wind_kmh": 30,
    "condition": "Clear Sky", "forecast": [], "source": "mock",
}
LOW_RAINFALL_WEATHER = {  # calm otherwise, but rainfall < 2mm so irrigation availability matters for water_risk
    "temperature_c": 25, "rainfall_mm": 1, "humidity_pct": 50, "wind_kmh": 10,
    "condition": "Clear Sky", "forecast": [], "source": "mock",
}


class _StubWeatherProvider:
    def __init__(self, data: dict):
        self._data = data

    def get_current(self, _location: str) -> dict:
        return self._data


def _register_and_get_headers(client, name="Risk Test Farmer"):
    email = f"risk_{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _add_soil(db_session, farm_id, values: dict, created_at: datetime | None = None):
    record = SoilRecord(farm_id=farm_id, soil_type="Loamy", **values)
    db_session.add(record)
    db_session.commit()
    if created_at is not None:
        record.created_at = created_at
        db_session.commit()
    return record


# ---------------------------------------------------------------------------
# Auth / ownership / validation
# ---------------------------------------------------------------------------


def test_risk_requires_authentication(client, farm):
    resp = client.get("/api/risk", params={"farm_id": farm["id"]})
    assert resp.status_code == 401


def test_risk_requires_the_farm_id_query_param(client, auth_headers):
    resp = client.get("/api/risk", headers=auth_headers)
    assert resp.status_code == 422


def test_risk_rejects_a_non_integer_farm_id(client, auth_headers):
    resp = client.get("/api/risk", params={"farm_id": "not-a-number"}, headers=auth_headers)
    assert resp.status_code == 422


def test_risk_returns_404_for_a_nonexistent_farm(client, auth_headers):
    resp = client.get("/api/risk", params={"farm_id": 999999999}, headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Farm not found"


def test_risk_returns_404_for_a_farm_owned_by_a_different_farmer(client, auth_headers, farm):
    other_headers = _register_and_get_headers(client)
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=other_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


def test_risk_response_has_exactly_the_expected_keys(client, auth_headers, farm, monkeypatch):
    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {"overall", "weather_risk", "soil_risk", "water_risk", "disease_risk", "notes", "is_prototype"}
    assert resp.json()["is_prototype"] is True


# ---------------------------------------------------------------------------
# Soil wiring
# ---------------------------------------------------------------------------


def test_risk_without_any_soil_record_treats_soil_risk_as_medium(client, auth_headers, farm, monkeypatch):
    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.json()["soil_risk"] == "MEDIUM"


def test_risk_with_good_soil_record_gives_low_soil_risk(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)  # score 100
    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.json()["soil_risk"] == "LOW"


def test_risk_with_bad_soil_record_gives_high_soil_risk(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], BAD_SOIL)  # score 24
    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.json()["soil_risk"] == "HIGH"


def test_risk_uses_the_most_recently_created_soil_record(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], BAD_SOIL, created_at=datetime.now(timezone.utc) - timedelta(days=1))
    _add_soil(db_session, farm["id"], GOOD_SOIL, created_at=datetime.now(timezone.utc))
    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.json()["soil_risk"] == "LOW"  # reflects GOOD_SOIL (most recent), not BAD_SOIL


# ---------------------------------------------------------------------------
# Weather wiring
# ---------------------------------------------------------------------------


def test_risk_with_calm_weather_gives_low_weather_risk(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)
    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=auth_headers)
    body = resp.json()
    assert body["weather_risk"] == "LOW"
    assert body["overall"] == "LOW"


def test_risk_with_severe_weather_gives_high_weather_risk_and_overall(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)
    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(SEVERE_WEATHER))
    resp = client.get("/api/risk", params={"farm_id": farm["id"]}, headers=auth_headers)
    body = resp.json()
    assert body["weather_risk"] == "HIGH"
    assert body["overall"] == "HIGH"
    assert body["disease_risk"] == "HIGH"  # SEVERE_WEATHER's 95% humidity also drives disease_risk up


# ---------------------------------------------------------------------------
# Irrigation wiring
# ---------------------------------------------------------------------------


def test_risk_irrigation_available_lowers_water_risk_under_low_rainfall(client, db_session, monkeypatch):
    """Confirms risk.py actually reads Farm.irrigation_available (not a
    hardcoded value) - same style of check already used in test_dashboard.py."""
    from app.core.security import create_access_token, hash_password
    from app.models.farm import Farm
    from app.models.user import Farmer, User

    def make_farm(irrigation_available):
        email = f"risk_irrig_{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=email, password_hash=hash_password("x"))
        db_session.add(user)
        db_session.flush()
        farmer = Farmer(user_id=user.id, name="Irrigation Test")
        db_session.add(farmer)
        db_session.flush()
        farm = Farm(farmer_id=farmer.id, name="F", location="Pune", area_acres=1, soil_type="Loamy", irrigation_available=irrigation_available)
        db_session.add(farm)
        db_session.commit()
        return farm, create_access_token(subject=email)

    monkeypatch.setattr(risk_module, "get_weather_provider", lambda: _StubWeatherProvider(LOW_RAINFALL_WEATHER))

    farm_with, token_with = make_farm(True)
    farm_without, token_without = make_farm(False)

    resp_with = client.get("/api/risk", params={"farm_id": farm_with.id}, headers={"Authorization": f"Bearer {token_with}"})
    resp_without = client.get("/api/risk", params={"farm_id": farm_without.id}, headers={"Authorization": f"Bearer {token_without}"})

    assert resp_with.json()["water_risk"] == "LOW"
    assert resp_without.json()["water_risk"] == "HIGH"

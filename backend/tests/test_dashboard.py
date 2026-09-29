"""
Tests for app/api/dashboard.py (GET /api/dashboard/{farm_id}) - the farmer
dashboard aggregation endpoint (farm info + soil health + weather + risk +
farm health), combining several already-tested services. Weather is stubbed
(via monkeypatching get_weather_provider, the same pattern already used in
test_notification_service.py) only where a specific risk/farm-health outcome
needs to be pinned deterministically; soil health and risk are always
computed for real. No dedicated response schema exists for this endpoint
(it returns a plain dict, not a Pydantic model) - these tests pin its actual
shape directly.
"""

import uuid
from datetime import datetime, timedelta, timezone

import app.api.dashboard as dashboard_module
from app.models.soil import SoilRecord
from app.services.soil_health import compute_soil_health

GOOD_SOIL = {"nitrogen": 80, "phosphorus": 40, "potassium": 55, "ph": 6.75}  # score 100
BAD_SOIL = {"nitrogen": 5, "phosphorus": 2, "potassium": 5, "ph": 4.0}  # score 24
MEDIUM_SOIL = {"nitrogen": 25, "phosphorus": 10, "potassium": 20, "ph": 4.5}  # score 53

CALM_WEATHER = {  # 0 weather-risk flags -> LOW
    "temperature_c": 25, "rainfall_mm": 5, "humidity_pct": 50, "wind_kmh": 10,
    "condition": "Clear Sky", "forecast": [], "source": "mock",
}
ONE_FLAG_WEATHER = {  # temp > 38 only -> MEDIUM
    "temperature_c": 40, "rainfall_mm": 5, "humidity_pct": 50, "wind_kmh": 10,
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


def _register_and_get_headers(client, name="Dashboard Test Farmer"):
    email = f"dash_{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_farm(client, headers, *, irrigation_available=True, location="Pune, Maharashtra"):
    resp = client.post(
        "/api/farms",
        json={"name": "Dashboard Farm", "location": location, "area_acres": 2, "soil_type": "Loamy", "irrigation_available": irrigation_available},
        headers=headers,
    )
    return resp.json()


def _add_soil(db_session, farm_id, values: dict, created_at: datetime | None = None):
    record = SoilRecord(farm_id=farm_id, soil_type="Loamy", **values)
    db_session.add(record)
    db_session.commit()
    if created_at is not None:
        record.created_at = created_at
        db_session.commit()
    return record


# ---------------------------------------------------------------------------
# Auth / ownership
# ---------------------------------------------------------------------------


def test_dashboard_requires_authentication(client, farm):
    resp = client.get(f"/api/dashboard/{farm['id']}")
    assert resp.status_code == 401


def test_dashboard_returns_404_for_a_nonexistent_farm(client, auth_headers):
    resp = client.get("/api/dashboard/999999999", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Farm not found"


def test_dashboard_returns_404_for_a_farm_owned_by_a_different_farmer(client, auth_headers, farm):
    other_headers = _register_and_get_headers(client, "Other Dashboard Farmer")
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=other_headers)
    assert resp.status_code == 404


def test_dashboard_rejects_a_non_integer_farm_id(client, auth_headers):
    resp = client.get("/api/dashboard/not-a-number", headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------


def test_dashboard_response_has_exactly_the_expected_top_level_keys(client, auth_headers, farm):
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert set(resp.json().keys()) == {"farm", "soil_health", "weather", "farm_health", "risk"}


def test_dashboard_farm_info_matches_the_real_farm_row(client, auth_headers, farm):
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    body = resp.json()["farm"]
    assert body == {"id": farm["id"], "name": farm["name"], "location": farm["location"]}


def test_dashboard_weather_has_the_expected_shape(client, auth_headers, farm):
    """Default mock provider (no override) - just checks the real shape,
    since exact values are seeded from the farm's location hash."""
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    weather = resp.json()["weather"]
    assert weather["source"] == "mock"
    assert set(weather.keys()) == {"temperature_c", "humidity_pct", "rainfall_mm", "wind_kmh", "condition", "forecast", "source"}


# ---------------------------------------------------------------------------
# Soil health / farm health - no soil record on file
# ---------------------------------------------------------------------------


def test_dashboard_without_any_soil_record_returns_null_soil_health_and_farm_health(client, auth_headers, farm, monkeypatch):
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    body = resp.json()
    assert body["soil_health"] is None
    assert body["farm_health"] is None


def test_dashboard_without_soil_record_still_computes_a_risk_with_medium_soil_risk(client, auth_headers, farm, monkeypatch):
    """risk_service.py treats a missing soil_score as MEDIUM soil_risk (not
    LOW or an error) - the dashboard must still return a full risk object."""
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    risk = resp.json()["risk"]
    assert risk["soil_risk"] == "MEDIUM"
    assert risk["overall"] in ("LOW", "MEDIUM", "HIGH")


# ---------------------------------------------------------------------------
# Soil health - with a soil record
# ---------------------------------------------------------------------------


def test_dashboard_soil_health_matches_direct_compute_soil_health_call(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    expected = compute_soil_health(**GOOD_SOIL)
    assert resp.json()["soil_health"] == expected


def test_dashboard_uses_the_most_recently_created_soil_record(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], BAD_SOIL, created_at=datetime.now(timezone.utc) - timedelta(days=1))
    _add_soil(db_session, farm["id"], GOOD_SOIL, created_at=datetime.now(timezone.utc))
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))

    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    assert resp.json()["soil_health"]["score"] == 100  # GOOD_SOIL's score, not BAD_SOIL's 24


# ---------------------------------------------------------------------------
# farm_health - pinned arithmetic across LOW / MEDIUM / HIGH weather risk
# ---------------------------------------------------------------------------


def test_farm_health_with_good_soil_and_low_weather_risk(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)  # soil_score = 100
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    body = resp.json()
    assert body["risk"]["weather_risk"] == "LOW"
    assert body["farm_health"] == 95  # round((100 + 90) / 2)


def test_farm_health_with_good_soil_and_medium_weather_risk(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(ONE_FLAG_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    body = resp.json()
    assert body["risk"]["weather_risk"] == "MEDIUM"
    assert body["farm_health"] == 80  # round((100 + 60) / 2)


def test_farm_health_with_good_soil_and_high_weather_risk(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(SEVERE_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    body = resp.json()
    assert body["risk"]["weather_risk"] == "HIGH"
    assert body["farm_health"] == 65  # round((100 + 30) / 2)


def test_farm_health_with_bad_soil_and_low_weather_risk(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], BAD_SOIL)  # soil_score = 24
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    assert resp.json()["farm_health"] == 57  # round((24 + 90) / 2)


def test_farm_health_rounds_a_half_value_to_even_python_default_behavior(client, auth_headers, farm, db_session, monkeypatch):
    """MEDIUM_SOIL scores 53; with LOW weather_risk (component 90),
    (53 + 90) / 2 = 71.5 exactly - documents that this uses Python's
    round-half-to-even (banker's rounding), giving 72, not 71."""
    _add_soil(db_session, farm["id"], MEDIUM_SOIL)
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    assert resp.json()["farm_health"] == 72


# ---------------------------------------------------------------------------
# Risk wiring - irrigation_available and soil_score flow through correctly
# ---------------------------------------------------------------------------


def test_dashboard_irrigation_available_lowers_water_risk_under_low_rainfall(client, db_session, monkeypatch):
    """With <2mm rainfall, water_risk is LOW only if irrigation_available is
    True - confirms dashboard.py actually reads Farm.irrigation_available
    (not a hardcoded value) when building the risk computation."""
    from app.core.security import create_access_token, hash_password
    from app.models.farm import Farm
    from app.models.user import Farmer, User

    def make_farm(irrigation_available):
        email = f"irrig_{uuid.uuid4().hex[:8]}@example.com"
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

    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(LOW_RAINFALL_WEATHER))

    farm_with, token_with = make_farm(True)
    farm_without, token_without = make_farm(False)

    resp_with = client.get(f"/api/dashboard/{farm_with.id}", headers={"Authorization": f"Bearer {token_with}"})
    resp_without = client.get(f"/api/dashboard/{farm_without.id}", headers={"Authorization": f"Bearer {token_without}"})

    assert resp_with.json()["risk"]["water_risk"] == "LOW"
    assert resp_without.json()["risk"]["water_risk"] == "HIGH"


def test_dashboard_risk_includes_all_expected_fields(client, auth_headers, farm, db_session, monkeypatch):
    _add_soil(db_session, farm["id"], GOOD_SOIL)
    monkeypatch.setattr(dashboard_module, "get_weather_provider", lambda: _StubWeatherProvider(CALM_WEATHER))
    resp = client.get(f"/api/dashboard/{farm['id']}", headers=auth_headers)
    risk = resp.json()["risk"]
    assert set(risk.keys()) == {"overall", "weather_risk", "soil_risk", "water_risk", "disease_risk", "notes", "is_prototype"}
    assert risk["is_prototype"] is True

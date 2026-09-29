"""
Tests for app/api/farms.py - farm CRUD (create/list/get) and soil record
submission/retrieval. This is the foundational router every other feature
depends on; despite that, GET /farms/{id} and GET /farms/{id}/soil had never
been directly tested before this pass (only exercised incidentally via other
test files' fixtures), and the farm-ownership 404 path had never been hit at
all. Uses the real soil_health.compute_soil_health() for cross-checking, not
a mock.
"""

import uuid

from app.services.soil_health import compute_soil_health

SOIL_PAYLOAD = {
    "nitrogen": 80, "phosphorus": 40, "potassium": 55, "ph": 6.75, "soil_type": "Loamy",
    "organic_carbon": 0.6, "moisture": 20, "electrical_conductivity": 1.2,
}


def _register_and_get_headers(client, name="Farms Test Farmer"):
    email = f"farms_{uuid.uuid4().hex[:10]}@example.com"
    resp = client.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# POST /farms
# ---------------------------------------------------------------------------


def test_create_farm_success(client, auth_headers):
    resp = client.post(
        "/api/farms",
        json={"name": "Green Acres", "location": "Pune, Maharashtra", "area_acres": 5, "soil_type": "Loamy", "irrigation_available": True},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Green Acres"
    assert body["location"] == "Pune, Maharashtra"
    assert body["area_acres"] == 5
    assert body["irrigation_available"] is True
    assert "id" in body and "created_at" in body


def test_create_farm_defaults_irrigation_available_to_false(client, auth_headers):
    resp = client.post(
        "/api/farms",
        json={"name": "Dry Farm", "location": "Rajasthan", "area_acres": 2, "soil_type": "Sandy"},
        headers=auth_headers,
    )
    assert resp.json()["irrigation_available"] is False


def test_create_farm_requires_authentication(client):
    resp = client.post("/api/farms", json={"name": "X", "location": "Y", "area_acres": 1, "soil_type": "Loamy"})
    assert resp.status_code == 401


def test_create_farm_rejects_zero_area_acres(client, auth_headers):
    resp = client.post("/api/farms", json={"name": "X", "location": "Y", "area_acres": 0, "soil_type": "Loamy"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_farm_rejects_area_acres_above_100000(client, auth_headers):
    resp = client.post("/api/farms", json={"name": "X", "location": "Y", "area_acres": 100001, "soil_type": "Loamy"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_farm_rejects_empty_name(client, auth_headers):
    resp = client.post("/api/farms", json={"name": "", "location": "Y", "area_acres": 1, "soil_type": "Loamy"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_farm_rejects_missing_required_field(client, auth_headers):
    resp = client.post("/api/farms", json={"name": "X", "area_acres": 1, "soil_type": "Loamy"}, headers=auth_headers)
    assert resp.status_code == 422


def test_create_farm_is_owned_by_the_creating_farmer(client, auth_headers):
    """Two farmers each create a farm - each must only see their own via GET /farms."""
    farm_resp = client.post("/api/farms", json={"name": "Mine", "location": "L", "area_acres": 1, "soil_type": "Loamy"}, headers=auth_headers)
    other_headers = _register_and_get_headers(client)
    other_farm_resp = client.post("/api/farms", json={"name": "Theirs", "location": "L", "area_acres": 1, "soil_type": "Loamy"}, headers=other_headers)

    my_farms = client.get("/api/farms", headers=auth_headers).json()
    their_farms = client.get("/api/farms", headers=other_headers).json()
    assert farm_resp.json()["id"] in [f["id"] for f in my_farms]
    assert other_farm_resp.json()["id"] not in [f["id"] for f in my_farms]
    assert other_farm_resp.json()["id"] in [f["id"] for f in their_farms]


# ---------------------------------------------------------------------------
# GET /farms
# ---------------------------------------------------------------------------


def test_list_farms_empty_for_a_fresh_farmer(client, auth_headers):
    resp = client.get("/api/farms", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_farms_requires_authentication(client):
    resp = client.get("/api/farms")
    assert resp.status_code == 401


def test_list_farms_ordered_newest_first(client, auth_headers):
    client.post("/api/farms", json={"name": "First", "location": "L", "area_acres": 1, "soil_type": "Loamy"}, headers=auth_headers)
    client.post("/api/farms", json={"name": "Second", "location": "L", "area_acres": 1, "soil_type": "Loamy"}, headers=auth_headers)
    resp = client.get("/api/farms", headers=auth_headers)
    names = [f["name"] for f in resp.json()]
    assert names == ["Second", "First"]


# ---------------------------------------------------------------------------
# GET /farms/{farm_id}
# ---------------------------------------------------------------------------


def test_get_farm_success(client, auth_headers, farm):
    resp = client.get(f"/api/farms/{farm['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == farm


def test_get_farm_returns_404_for_a_nonexistent_farm(client, auth_headers):
    resp = client.get("/api/farms/999999999", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Farm not found"


def test_get_farm_returns_404_for_a_farm_owned_by_a_different_farmer(client, auth_headers, farm):
    other_headers = _register_and_get_headers(client)
    resp = client.get(f"/api/farms/{farm['id']}", headers=other_headers)
    assert resp.status_code == 404


def test_get_farm_requires_authentication(client, farm):
    resp = client.get(f"/api/farms/{farm['id']}")
    assert resp.status_code == 401


def test_get_farm_rejects_a_non_integer_farm_id(client, auth_headers):
    resp = client.get("/api/farms/not-a-number", headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /farms/{farm_id}/soil
# ---------------------------------------------------------------------------


def test_submit_soil_success_and_health_matches_direct_computation(client, auth_headers, farm):
    resp = client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["farm_id"] == farm["id"]
    assert body["nitrogen"] == 80
    assert body["organic_carbon"] == 0.6
    expected_health = compute_soil_health(80, 40, 55, 6.75)
    assert body["health"] == expected_health


def test_submit_soil_persists_multiple_records_without_overwriting(client, auth_headers, farm, db_session):
    from app.models.soil import SoilRecord

    client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    client.post(f"/api/farms/{farm['id']}/soil", json={**SOIL_PAYLOAD, "nitrogen": 10}, headers=auth_headers)
    count = db_session.query(SoilRecord).filter(SoilRecord.farm_id == farm["id"]).count()
    assert count == 2


def test_submit_soil_optional_fields_can_be_omitted(client, auth_headers, farm):
    minimal = {"nitrogen": 80, "phosphorus": 40, "potassium": 55, "ph": 6.75, "soil_type": "Loamy"}
    resp = client.post(f"/api/farms/{farm['id']}/soil", json=minimal, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["organic_carbon"] is None
    assert body["moisture"] is None
    assert body["electrical_conductivity"] is None


def test_submit_soil_returns_404_for_a_nonexistent_farm(client, auth_headers):
    resp = client.post("/api/farms/999999999/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 404


def test_submit_soil_returns_404_for_a_farm_owned_by_a_different_farmer(client, auth_headers, farm):
    other_headers = _register_and_get_headers(client)
    resp = client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=other_headers)
    assert resp.status_code == 404


def test_submit_soil_requires_authentication(client, farm):
    resp = client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD)
    assert resp.status_code == 401


def test_submit_soil_rejects_negative_nitrogen(client, auth_headers, farm):
    resp = client.post(f"/api/farms/{farm['id']}/soil", json={**SOIL_PAYLOAD, "nitrogen": -1}, headers=auth_headers)
    assert resp.status_code == 422


def test_submit_soil_rejects_ph_above_14(client, auth_headers, farm):
    resp = client.post(f"/api/farms/{farm['id']}/soil", json={**SOIL_PAYLOAD, "ph": 14.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_submit_soil_rejects_electrical_conductivity_above_50(client, auth_headers, farm):
    resp = client.post(f"/api/farms/{farm['id']}/soil", json={**SOIL_PAYLOAD, "electrical_conductivity": 51}, headers=auth_headers)
    assert resp.status_code == 422


def test_submit_soil_rejects_missing_required_field(client, auth_headers, farm):
    incomplete = {k: v for k, v in SOIL_PAYLOAD.items() if k != "ph"}
    resp = client.post(f"/api/farms/{farm['id']}/soil", json=incomplete, headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /farms/{farm_id}/soil
# ---------------------------------------------------------------------------


def test_get_latest_soil_returns_null_when_none_submitted_yet(client, auth_headers, farm):
    resp = client.get(f"/api/farms/{farm['id']}/soil", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() is None


def test_get_latest_soil_returns_the_submitted_record_with_health(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json=SOIL_PAYLOAD, headers=auth_headers)
    resp = client.get(f"/api/farms/{farm['id']}/soil", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["nitrogen"] == 80
    assert body["health"] == compute_soil_health(80, 40, 55, 6.75)


def test_get_latest_soil_returns_the_most_recently_submitted_record(client, auth_headers, farm):
    client.post(f"/api/farms/{farm['id']}/soil", json={**SOIL_PAYLOAD, "nitrogen": 10}, headers=auth_headers)
    client.post(f"/api/farms/{farm['id']}/soil", json={**SOIL_PAYLOAD, "nitrogen": 90}, headers=auth_headers)
    resp = client.get(f"/api/farms/{farm['id']}/soil", headers=auth_headers)
    assert resp.json()["nitrogen"] == 90  # the second (most recent) submission, not the first


def test_get_latest_soil_returns_404_for_a_nonexistent_farm(client, auth_headers):
    resp = client.get("/api/farms/999999999/soil", headers=auth_headers)
    assert resp.status_code == 404


def test_get_latest_soil_returns_404_for_a_farm_owned_by_a_different_farmer(client, auth_headers, farm):
    other_headers = _register_and_get_headers(client)
    resp = client.get(f"/api/farms/{farm['id']}/soil", headers=other_headers)
    assert resp.status_code == 404


def test_get_latest_soil_requires_authentication(client, farm):
    resp = client.get(f"/api/farms/{farm['id']}/soil")
    assert resp.status_code == 401

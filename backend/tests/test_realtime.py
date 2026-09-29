"""
Tests for Real-Time Agri Intelligence: Satellite (planned/integration-ready
architecture, Feature 10B) and IoT (demo-simulation + real ingestion
architecture, Feature 10C). Neither module may claim to be live data unless
it actually is.
"""


def test_satellite_status_is_honestly_labeled_planned(client, auth_headers, farm):
    resp = client.get("/api/satellite/status", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "PLANNED"
    assert body["configured"] is False
    assert len(body["planned_metrics"]) > 0
    assert "not yet connected" in body["message"].lower()


def test_satellite_status_requires_owned_farm(client, auth_headers):
    resp = client.get("/api/satellite/status", params={"farm_id": 999999}, headers=auth_headers)
    assert resp.status_code == 404


def test_iot_readings_empty_before_any_seed(client, auth_headers, farm):
    resp = client.get("/api/iot/readings", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["readings"] == []
    assert body["has_real_device_data"] is False


def test_iot_demo_seed_creates_labeled_demo_readings(client, auth_headers, farm):
    resp = client.post("/api/iot/demo/seed", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["readings"]) == 4  # soil_moisture, temperature, humidity, ec
    assert body["has_real_device_data"] is False
    assert all(r["source"] == "demo_simulation" for r in body["readings"])


def test_iot_real_ingestion_is_distinguished_from_demo_data(client, auth_headers, farm):
    resp = client.post(
        "/api/iot/readings",
        json={"farm_id": farm["id"], "sensor_type": "soil_moisture", "value": 32.5},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["source"] == "device"

    resp = client.get("/api/iot/readings", params={"farm_id": farm["id"]}, headers=auth_headers)
    assert resp.json()["has_real_device_data"] is True


def test_iot_ingestion_rejects_unknown_sensor_type(client, auth_headers, farm):
    resp = client.post(
        "/api/iot/readings",
        json={"farm_id": farm["id"], "sensor_type": "not_a_real_sensor", "value": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_iot_readings_require_owned_farm(client, auth_headers):
    resp = client.get("/api/iot/readings", params={"farm_id": 999999}, headers=auth_headers)
    assert resp.status_code == 404

"""
API-level tests for app/api/fertilizer_router.py (GET /fertilizer/options,
POST /fertilizer/recommend) - request validation, auth enforcement, and
response shape. Calculation correctness itself is covered in
test_fertilizer_service.py.
"""

BASE_PAYLOAD = {
    "crop": "rice",
    "nitrogen": 80,
    "phosphorus": 40,
    "potassium": 55,
    "ph": 6.5,
    "growth_stage": "vegetative",
}


def test_fertilizer_options_returns_all_growth_stages(client, auth_headers):
    resp = client.get("/api/fertilizer/options", headers=auth_headers)
    assert resp.status_code == 200
    stages = resp.json()["growth_stages"]
    assert set(stages) == {"seedling", "vegetative", "flowering", "fruiting", "maturity"}


def test_fertilizer_options_requires_authentication(client):
    resp = client.get("/api/fertilizer/options")
    assert resp.status_code == 401


def test_recommend_success_shape(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["crop"] == "rice"
    assert body["growth_stage"] == "vegetative"
    assert len(body["deficiencies"]) == 3
    assert body["warnings"] == []
    assert "not a calibrated dosage" in body["disclaimer"].lower()


def test_recommend_deficient_and_excess_nutrients_reflected_in_response(client, auth_headers):
    resp = client.post(
        "/api/fertilizer/recommend",
        json={**BASE_PAYLOAD, "nitrogen": 10, "potassium": 150},
        headers=auth_headers,
    )
    body = resp.json()
    statuses = {d["nutrient"]: d["status"] for d in body["deficiencies"]}
    assert statuses["Nitrogen (N)"] == "DEFICIENT"
    assert statuses["Potassium (K)"] == "EXCESS"
    assert any("already above" in w.lower() for w in body["warnings"])


def test_recommend_farm_id_is_accepted_but_has_no_effect_on_the_response_KNOWN_BEHAVIOR(client, auth_headers, farm):
    """Same no-op pattern already found in water_router.py, profit_router.py,
    risk_ml_router.py and yield_router.py: FertilizerRecommendationInput.farm_id
    exists in the schema but recommend() never reads it - nothing is
    persisted, and the response is identical with or without it."""
    without_farm_id = client.post("/api/fertilizer/recommend", json=BASE_PAYLOAD, headers=auth_headers).json()
    with_farm_id = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "farm_id": farm["id"]}, headers=auth_headers).json()
    assert without_farm_id == with_farm_id


def test_recommend_requires_authentication(client):
    resp = client.post("/api/fertilizer/recommend", json=BASE_PAYLOAD)
    assert resp.status_code == 401


def test_recommend_rejects_negative_nitrogen(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "nitrogen": -1}, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_rejects_nitrogen_above_300(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "nitrogen": 301}, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_rejects_ph_above_14(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "ph": 14.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_rejects_organic_carbon_above_100(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "organic_carbon": 101}, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_rejects_zero_farm_area_acres(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "farm_area_acres": 0}, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_rejects_empty_crop_string(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "crop": ""}, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_rejects_empty_growth_stage_string(client, auth_headers):
    resp = client.post("/api/fertilizer/recommend", json={**BASE_PAYLOAD, "growth_stage": ""}, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_rejects_missing_required_field(client, auth_headers):
    incomplete = {k: v for k, v in BASE_PAYLOAD.items() if k != "ph"}
    resp = client.post("/api/fertilizer/recommend", json=incomplete, headers=auth_headers)
    assert resp.status_code == 422


def test_recommend_accepts_omitted_optional_fields(client, auth_headers):
    """organic_carbon, moisture, farm_area_acres and farm_id are all optional."""
    resp = client.post("/api/fertilizer/recommend", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["organic_matter_guidance"] is None
    assert body["farm_area_acres"] is None

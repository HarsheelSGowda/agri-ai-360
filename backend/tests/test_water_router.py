"""
API-level tests for app/api/water_router.py (GET /predict/water/options,
POST /predict/water) - request validation, auth enforcement, the
date->month_index conversion, and the 503 error path. All calculation
correctness itself is covered in test_water_service.py; these tests focus
on the HTTP layer's own behavior.
"""

import pytest

import app.api.water_router as water_router_module
from app.services.water_service import WaterDataUnavailableError

BASE_PAYLOAD = {
    "crop": "rice",
    "state": "Maharashtra",
    "temperature_c": 28.0,
    "rainfall_mm": 50.0,
    "date": "2026-07-15",  # pinned so month_index is deterministic regardless of when the suite runs
}


def test_water_options_returns_crops_and_states(client, auth_headers):
    resp = client.get("/api/predict/water/options", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "rice" in body["supported_crops"]
    assert "Maharashtra" in body["states"]


def test_water_options_requires_authentication(client):
    resp = client.get("/api/predict/water/options")
    assert resp.status_code == 401


def test_predict_water_success_with_pinned_date(client, auth_headers):
    resp = client.post("/api/predict/water", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is True
    assert body["month"] == "Jul"
    assert body["crop_water_use_mm_per_day"] == 7.47
    assert body["net_irrigation_mm_per_day"] == 0.0


def test_predict_water_without_a_date_defaults_to_the_current_month(client, auth_headers):
    """Documents real behavior: omitting `date` uses date.today(), so this
    test only checks the response is well-formed and month is a valid
    3-letter name - asserting an exact month here would make the suite
    flaky depending on what day it's run."""
    payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "date"}
    resp = client.post("/api/predict/water", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is True
    assert body["month"] in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def test_predict_water_unsupported_crop_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "crop": "wheat"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is False
    assert "wheat" in body["reason"]


def test_predict_water_unrecognized_state_returns_200_with_supported_false(client, auth_headers):
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "state": "Atlantis"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["supported"] is False


def test_predict_water_with_area_acres_includes_total_liters(client, auth_headers):
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "rainfall_mm": 0.0, "area_acres": 3.0}, headers=auth_headers)
    body = resp.json()
    assert body["net_irrigation_liters_total_per_day"] is not None
    assert body["net_irrigation_liters_total_per_day"] == pytest.approx(body["net_irrigation_liters_per_acre_per_day"] * 3.0)


def test_predict_water_farm_id_is_accepted_but_has_no_effect_on_the_response_KNOWN_BEHAVIOR(client, auth_headers, farm):
    """
    Documents actual current behavior: WaterRequirementInput.farm_id exists
    in the schema, but water_router.py's predict_water_endpoint() never reads
    payload.farm_id at all - unlike predict.py's crop endpoint, nothing is
    persisted to any table (there is no water-estimate table in the schema),
    and the response is byte-for-byte identical whether farm_id is supplied
    or not. Not a crash, just a schema field with no current implementation
    behind it - worth knowing before assuming water estimates are saved to
    history anywhere.
    """
    without_farm_id = client.post("/api/predict/water", json=BASE_PAYLOAD, headers=auth_headers).json()
    with_farm_id = client.post("/api/predict/water", json={**BASE_PAYLOAD, "farm_id": farm["id"]}, headers=auth_headers).json()
    assert without_farm_id == with_farm_id


def test_predict_water_farm_id_for_a_farm_the_caller_does_not_own_still_succeeds(client, auth_headers):
    """Further confirms farm_id is never validated/used - an id belonging to
    nobody doesn't raise a 404 the way predict.py's ownership-checked
    persistence path would; it's simply ignored."""
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "farm_id": 999999999}, headers=auth_headers)
    assert resp.status_code == 200


def test_predict_water_rejects_temperature_below_min(client, auth_headers):
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "temperature_c": -10.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_water_rejects_negative_rainfall(client, auth_headers):
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "rainfall_mm": -1}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_water_rejects_rainfall_above_1000(client, auth_headers):
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "rainfall_mm": 1000.1}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_water_rejects_zero_area_acres_at_the_schema_level(client, auth_headers):
    resp = client.post("/api/predict/water", json={**BASE_PAYLOAD, "area_acres": 0}, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_water_rejects_missing_required_field(client, auth_headers):
    incomplete = {k: v for k, v in BASE_PAYLOAD.items() if k != "state"}
    resp = client.post("/api/predict/water", json=incomplete, headers=auth_headers)
    assert resp.status_code == 422


def test_predict_water_requires_authentication(client):
    resp = client.post("/api/predict/water", json=BASE_PAYLOAD)
    assert resp.status_code == 401


def test_predict_water_returns_503_when_reference_data_unavailable(client, auth_headers, monkeypatch):
    def boom(*_args, **_kwargs):
        raise WaterDataUnavailableError("Water Kc reference has not been built yet.")

    monkeypatch.setattr(water_router_module, "predict_water_requirement", boom)
    resp = client.post("/api/predict/water", json=BASE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 503
    assert "kc reference" in resp.json()["detail"].lower()

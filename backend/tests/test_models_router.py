"""
Tests for app/api/models_router.py (GET /models, GET /models/performance) -
the crop-recommendation Model Lab / Research Center endpoints. Runs against
the real committed models/metrics.json wherever possible; only the
"metrics missing" and "unusual metrics shape" scenarios monkeypatch the
router's own `load_metrics` reference (the same pattern already used for
disease_router.py/risk_ml_router.py/water_router.py/profit_router.py),
using copies of the *real* metrics dict as their base rather than fabricated
data.
"""

import copy

import app.api.models_router as models_router_module
from app.services.ml_service import load_metrics

REAL_METRICS = load_metrics()
assert REAL_METRICS is not None, "models/metrics.json must exist for these tests to be meaningful"


# ---------------------------------------------------------------------------
# GET /models
# ---------------------------------------------------------------------------


def test_list_models_requires_authentication(client):
    resp = client.get("/api/models")
    assert resp.status_code == 401


def test_list_models_returns_real_data(client, auth_headers):
    resp = client.get("/api/models", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["models"] == ["random_forest", "gradient_boosting", "xgboost", "svm"]
    assert body["active_model"] == "random_forest"
    assert body["trained_at"] == REAL_METRICS["trained_at"]


def test_list_models_works_for_a_user_with_no_farmer_profile(client, db_session):
    """/models uses get_current_user, not get_current_farmer - unlike
    farmer-scoped endpoints (e.g. predict_disease), a User with no Farmer
    profile must still be able to call this successfully."""
    from app.core.security import create_access_token, hash_password
    from app.models.user import User

    email = "models_router_orphan_user@example.com"
    user = User(email=email, password_hash=hash_password("secret123"))
    db_session.add(user)
    db_session.commit()
    token = create_access_token(subject=email)

    resp = client.get("/api/models", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_list_models_when_metrics_missing_omits_trained_at_entirely_KNOWN_BEHAVIOR(client, auth_headers, monkeypatch):
    """
    Documents a real minor API-contract inconsistency (not fixed, per
    instructions): when metrics ARE available, the response always includes
    a `trained_at` key. When metrics are missing, the early-return branch
    `{"models": [], "active_model": None}` omits `trained_at` entirely rather
    than including it as null - so the response shape differs depending on
    whether the metrics file exists, which a strict client type wouldn't
    expect from the same endpoint.
    """
    monkeypatch.setattr(models_router_module, "load_metrics", lambda: None)
    resp = client.get("/api/models", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"models": [], "active_model": None}
    assert "trained_at" not in body


# ---------------------------------------------------------------------------
# GET /models/performance - success path, real data
# ---------------------------------------------------------------------------


def test_model_performance_requires_authentication(client):
    resp = client.get("/api/models/performance")
    assert resp.status_code == 401


def test_model_performance_returns_all_four_algorithms_in_order(client, auth_headers):
    resp = client.get("/api/models/performance", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    algos = [m["algorithm"] for m in body["models"]]
    assert algos == ["Random Forest", "Gradient Boosting", "XGBoost", "SVM"]
    assert all(m["status"] == "trained" for m in body["models"])


def test_model_performance_metrics_match_the_real_metrics_file(client, auth_headers):
    resp = client.get("/api/models/performance", headers=auth_headers)
    body = resp.json()
    rf_row = next(m for m in body["models"] if m["algorithm"] == "Random Forest")
    real_rf = REAL_METRICS["models"]["random_forest"]
    assert rf_row["accuracy"] == real_rf["accuracy"]
    assert rf_row["precision"] == real_rf["precision"]
    assert rf_row["recall"] == real_rf["recall"]
    assert rf_row["f1_score"] == real_rf["f1_score"]
    assert rf_row["trained_at"] == REAL_METRICS["trained_at"]


def test_model_performance_dataset_info_matches_real_metrics_file(client, auth_headers):
    resp = client.get("/api/models/performance", headers=auth_headers)
    body = resp.json()
    assert body["active_model"] == "Random Forest"
    assert body["dataset_records"] == REAL_METRICS["dataset_records"]
    assert body["dataset_source"] == REAL_METRICS["dataset_source"]


def test_model_performance_feature_importance_matches_real_data_sorted_descending(client, auth_headers):
    resp = client.get("/api/models/performance", headers=auth_headers)
    feature_importance = resp.json()["feature_importance"]
    assert feature_importance is not None

    real_fi = REAL_METRICS["models"]["random_forest"]["feature_importance"]
    expected_order = sorted(real_fi.items(), key=lambda kv: -kv[1])
    assert [(f["feature"], f["importance"]) for f in feature_importance] == expected_order

    importances = [f["importance"] for f in feature_importance]
    assert importances == sorted(importances, reverse=True)


def test_model_performance_confusion_matrix_matches_real_data(client, auth_headers):
    resp = client.get("/api/models/performance", headers=auth_headers)
    confusion_matrix = resp.json()["confusion_matrix"]
    assert confusion_matrix is not None

    real_rf = REAL_METRICS["models"]["random_forest"]
    assert confusion_matrix["labels"] == real_rf["labels"]
    assert confusion_matrix["matrix"] == real_rf["confusion_matrix"]
    assert len(confusion_matrix["labels"]) == 22
    assert len(confusion_matrix["matrix"]) == 22
    assert all(len(row) == 22 for row in confusion_matrix["matrix"])


# ---------------------------------------------------------------------------
# GET /models/performance - metrics missing entirely
# ---------------------------------------------------------------------------


def test_model_performance_when_metrics_missing_marks_every_algorithm_not_evaluated(client, auth_headers, monkeypatch):
    monkeypatch.setattr(models_router_module, "load_metrics", lambda: None)
    resp = client.get("/api/models/performance", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert all(m["status"] == "not_evaluated" for m in body["models"])
    assert all(m["accuracy"] is None and m["precision"] is None and m["recall"] is None and m["f1_score"] is None for m in body["models"])
    assert body["active_model"] == "Not trained"
    assert body["dataset_records"] == 0
    assert body["dataset_source"] == "Not documented"
    assert body["feature_importance"] is None
    assert body["confusion_matrix"] is None


# ---------------------------------------------------------------------------
# GET /models/performance - partial / unusual metrics shapes (real data, modified)
# ---------------------------------------------------------------------------


def test_model_performance_with_only_some_algorithms_trained(client, auth_headers, monkeypatch):
    """Simulates a metrics file where only random_forest has been trained so
    far - a real, plausible intermediate state (e.g. mid-training-pipeline),
    built from a copy of the real metrics rather than fabricated data."""
    partial = copy.deepcopy(REAL_METRICS)
    del partial["models"]["gradient_boosting"]
    del partial["models"]["xgboost"]
    del partial["models"]["svm"]
    monkeypatch.setattr(models_router_module, "load_metrics", lambda: partial)

    resp = client.get("/api/models/performance", headers=auth_headers)
    body = resp.json()
    by_algo = {m["algorithm"]: m for m in body["models"]}
    assert by_algo["Random Forest"]["status"] == "trained"
    assert by_algo["Gradient Boosting"]["status"] == "not_evaluated"
    assert by_algo["XGBoost"]["status"] == "not_evaluated"
    assert by_algo["SVM"]["status"] == "not_evaluated"


def test_model_performance_active_model_without_feature_importance_omits_it(client, auth_headers, monkeypatch):
    """svm has no feature_importance in the real metrics file (SVM doesn't
    natively expose it the way tree models do) - if svm were ever set active,
    feature_importance must correctly come back null, not error or a stale
    value from a different model."""
    svm_active = copy.deepcopy(REAL_METRICS)
    svm_active["active_model"] = "svm"
    monkeypatch.setattr(models_router_module, "load_metrics", lambda: svm_active)

    resp = client.get("/api/models/performance", headers=auth_headers)
    body = resp.json()
    assert body["active_model"] == "SVM"
    assert body["feature_importance"] is None
    assert body["confusion_matrix"] is not None  # svm DOES have a confusion matrix in the real data
    assert body["confusion_matrix"]["labels"] == REAL_METRICS["models"]["svm"]["labels"]


def test_model_performance_active_model_not_a_known_algorithm_falls_back_to_the_raw_name(client, auth_headers, monkeypatch):
    """Documents actual fallback behavior: DISPLAY_NAMES.get(active, active or
    'Not trained') returns the raw, unmapped string when `active_model`
    doesn't match any of the 4 known algorithm keys - not an error."""
    weird = copy.deepcopy(REAL_METRICS)
    weird["active_model"] = "some_future_algorithm"
    monkeypatch.setattr(models_router_module, "load_metrics", lambda: weird)

    resp = client.get("/api/models/performance", headers=auth_headers)
    body = resp.json()
    assert body["active_model"] == "some_future_algorithm"
    assert body["feature_importance"] is None
    assert body["confusion_matrix"] is None

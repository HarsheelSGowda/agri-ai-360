"""
Tests for app/services/risk_ml_service.py - the ML-based yield-risk
classifier (LOW/MEDIUM/HIGH tier per crop/state/season). Runs against the
real trained model artifacts already committed under models/
(risk_random_forest.joblib, risk_feature_encoder.joblib,
risk_label_encoder.joblib, risk_metrics.json) - same approach already used
for ml_service.py and yield_service.py: no mocking of the ML layer itself,
only the "artifact missing" paths use a temp dir + lru_cache.cache_clear().
"""

import pytest

from app.services import risk_ml_service as rs
from app.services.risk_ml_service import (
    RiskModelUnavailableError,
    active_risk_model_name,
    load_feature_encoder,
    load_label_encoder,
    load_risk_metrics,
    load_risk_model,
    predict_yield_risk,
    supported_risk_crops,
)


# ---------------------------------------------------------------------------
# Reference data / artifact loading
# ---------------------------------------------------------------------------


def test_active_risk_model_name_matches_real_metrics_file():
    assert active_risk_model_name() == "risk_random_forest"


def test_supported_risk_crops_matches_real_reference_file():
    crops = supported_risk_crops()
    assert crops == sorted(crops)
    assert set(crops) == {
        "banana", "blackgram", "chickpea", "cotton", "jute", "lentil", "maize", "mothbeans", "mungbean", "pigeonpeas", "rice",
    }


def test_supported_risk_crops_matches_supported_yield_crops():
    """
    Both risk_metrics.json and yield_metrics.json were built from the same
    underlying India crop-production dataset, and both include "Moth"
    (mothbeans) in their respective crops_covered/supported_crops lists - so
    the two models' recommendation-engine crop coverage is identical today.
    Verified directly against both real reference files rather than assumed.
    """
    from app.services.yield_service import supported_recommendation_crops

    assert supported_risk_crops() == supported_recommendation_crops()


def test_supported_risk_crops_returns_empty_list_when_metrics_missing(tmp_path, monkeypatch):
    load_risk_metrics.cache_clear()
    monkeypatch.setattr(rs, "_models_dir", lambda: tmp_path)
    try:
        assert supported_risk_crops() == []
    finally:
        load_risk_metrics.cache_clear()


def test_load_risk_metrics_returns_real_data():
    metrics = load_risk_metrics()
    assert metrics is not None
    assert metrics["active_model"] == "risk_random_forest"
    assert "Rice" in metrics["crops_covered"]


def test_load_risk_metrics_returns_none_when_file_missing(tmp_path, monkeypatch):
    load_risk_metrics.cache_clear()
    monkeypatch.setattr(rs, "_models_dir", lambda: tmp_path)
    try:
        assert load_risk_metrics() is None
    finally:
        load_risk_metrics.cache_clear()


def test_load_feature_encoder_loads_a_real_encoder():
    encoder = load_feature_encoder()
    assert hasattr(encoder, "transform")


def test_load_feature_encoder_raises_when_artifact_missing(tmp_path, monkeypatch):
    load_feature_encoder.cache_clear()
    monkeypatch.setattr(rs, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(RiskModelUnavailableError, match="risk_feature_encoder"):
            load_feature_encoder()
    finally:
        load_feature_encoder.cache_clear()


def test_load_label_encoder_loads_a_real_encoder():
    encoder = load_label_encoder()
    assert hasattr(encoder, "inverse_transform")


def test_load_label_encoder_raises_when_artifact_missing(tmp_path, monkeypatch):
    load_label_encoder.cache_clear()
    monkeypatch.setattr(rs, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(RiskModelUnavailableError, match="risk_label_encoder"):
            load_label_encoder()
    finally:
        load_label_encoder.cache_clear()


def test_load_risk_model_loads_the_real_active_model():
    model = load_risk_model("risk_random_forest")
    assert hasattr(model, "predict_proba")


def test_load_risk_model_raises_for_a_name_that_does_not_exist():
    with pytest.raises(RiskModelUnavailableError, match="not found"):
        load_risk_model("totally_fake_risk_model_xyz")


def test_active_risk_model_name_falls_back_to_default_when_metrics_missing(tmp_path, monkeypatch):
    load_risk_metrics.cache_clear()
    monkeypatch.setattr(rs, "_models_dir", lambda: tmp_path)
    try:
        assert active_risk_model_name() == "risk_random_forest"
    finally:
        load_risk_metrics.cache_clear()


# ---------------------------------------------------------------------------
# predict_yield_risk - real inference against the real trained model
# ---------------------------------------------------------------------------


def test_predict_yield_risk_full_pinned_result_for_rice_maharashtra_kharif():
    result = predict_yield_risk("rice", "Maharashtra", "Kharif")
    assert result == {
        "supported": True,
        "crop": "rice",
        "mapped_crop": "Rice",
        "state": "Maharashtra",
        "season": "Kharif",
        "risk_level": "HIGH",
        "probabilities": {"LOW": 0.124, "MEDIUM": 0.142, "HIGH": 0.734},
        "model_used": "risk_random_forest",
        "model_accuracy": pytest.approx(0.5527965963502676),
    }


def test_predict_yield_risk_probabilities_sum_to_one():
    result = predict_yield_risk("rice", "Maharashtra", "Kharif")
    assert sum(result["probabilities"].values()) == pytest.approx(1.0, abs=0.005)


def test_predict_yield_risk_level_matches_the_highest_probability():
    result = predict_yield_risk("rice", "Maharashtra", "Kharif")
    top_label = max(result["probabilities"], key=result["probabilities"].get)
    assert result["risk_level"] == top_label


def test_predict_yield_risk_all_three_probability_keys_always_present():
    result = predict_yield_risk("maize", "Punjab", "Kharif")
    assert set(result["probabilities"].keys()) == {"LOW", "MEDIUM", "HIGH"}
    assert all(0.0 <= p <= 1.0 for p in result["probabilities"].values())


def test_predict_yield_risk_is_case_insensitive_on_crop_name():
    result = predict_yield_risk("RICE", "Maharashtra", "Kharif")
    assert result["supported"] is True
    assert result["mapped_crop"] == "Rice"
    assert result["crop"] == "RICE"  # echoes back the original casing


def test_predict_yield_risk_unsupported_crop_returns_supported_false():
    result = predict_yield_risk("wheat", "Maharashtra", "Kharif")
    assert result["supported"] is False
    assert result["mapped_crop"] is None
    assert "wheat" in result["reason"]


def test_predict_yield_risk_raises_when_metrics_missing(tmp_path, monkeypatch):
    load_risk_metrics.cache_clear()
    monkeypatch.setattr(rs, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(RiskModelUnavailableError, match="Risk model"):
            predict_yield_risk("rice", "Maharashtra", "Kharif")
    finally:
        load_risk_metrics.cache_clear()


# ---------------------------------------------------------------------------
# KNOWN BUG: state and season are never validated
# ---------------------------------------------------------------------------


def test_predict_yield_risk_does_not_validate_state_KNOWN_BUG():
    """
    Documents a genuine, currently-unfixed, high-severity bug (found while
    adding this test coverage, not fixed here per this pass's rules):
    predict_yield_risk() validates `crop` against crops_covered, but never
    validates `state` against any known list of states the way
    yield_service.predict_yield() does. A completely fictional state (never
    seen during training) is silently fed to feature_encoder.transform() and
    the classifier, which produces a full, confident-looking prediction
    (a specific risk_level and specific probabilities) instead of returning
    supported: False or raising an error. This means the API can return a
    fabricated-looking risk assessment for a state that doesn't exist -
    exactly the kind of silent fabrication this project's own rules say to
    avoid elsewhere (see yield_service.py and water_service.py, which both
    correctly reject an unrecognized state).
    """
    result = predict_yield_risk("rice", "Atlantis", "Kharif")
    assert result["supported"] is True  # should arguably be False, like yield_service's equivalent check
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert sum(result["probabilities"].values()) == pytest.approx(1.0, abs=0.005)


def test_predict_yield_risk_does_not_validate_season_KNOWN_BUG():
    """Same class of bug as the state case above, for `season`."""
    result = predict_yield_risk("rice", "Maharashtra", "Monsoon")  # "Monsoon" is not one of the 6 real seasons
    assert result["supported"] is True  # should arguably be False
    assert result["risk_level"] in ("LOW", "MEDIUM", "HIGH")


def test_predict_yield_risk_unvalidated_state_and_season_are_deterministic():
    """Even though the bug above lets garbage through, at least the specific
    (wrong) result it produces is stable/reproducible, not random, for a
    given input - pins current behavior precisely."""
    result_a = predict_yield_risk("rice", "Atlantis", "Kharif")
    result_b = predict_yield_risk("rice", "Atlantis", "Kharif")
    assert result_a == result_b

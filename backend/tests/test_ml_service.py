"""
Tests for app/services/ml_service.py — the crop-recommendation ML pipeline
(prediction + SHAP explanation). Runs against the real trained model
artifacts already committed under models/ (random_forest.joblib,
label_encoder.joblib, metrics.json) - no mocking of the ML layer itself,
since these are local files with no network/credential dependency. Only the
"artifact missing" error paths use a temp directory + monkeypatch, since
that's real file-not-found behavior that can't otherwise be triggered
without deleting the real model files.
"""

import pytest

from app.services import ml_service
from app.services.ml_service import (
    ModelUnavailableError,
    _build_narrative,
    _to_frame,
    active_model_name,
    confidence_label,
    explain_prediction,
    load_label_encoder,
    load_metrics,
    load_model,
    predict_top_k,
)

RICE_PAYLOAD = {"nitrogen": 90, "phosphorus": 42, "potassium": 43, "temperature": 20.8, "humidity": 82, "ph": 6.5, "rainfall": 202.9}


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def test_confidence_label_boundaries():
    assert confidence_label(1.0) == "HIGH"
    assert confidence_label(0.6) == "HIGH"
    assert confidence_label(0.5999) == "MEDIUM"
    assert confidence_label(0.3) == "MEDIUM"
    assert confidence_label(0.2999) == "LOW"
    assert confidence_label(0.0) == "LOW"


def test_to_frame_preserves_feature_order_and_values():
    frame = _to_frame(RICE_PAYLOAD)
    assert list(frame.columns) == ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    row = frame.iloc[0]
    assert row["N"] == 90
    assert row["P"] == 42
    assert row["K"] == 43
    assert row["rainfall"] == 202.9


def test_build_narrative_mentions_the_crop_and_top_positive_features():
    contributions = [
        {"feature": "rainfall", "value": 200, "contribution": 0.3},
        {"feature": "N", "value": 90, "contribution": 0.2},
        {"feature": "ph", "value": 4.0, "contribution": -0.05},
    ]
    narrative = _build_narrative("rice", contributions)
    assert "Rice" in narrative
    assert "rainfall" in narrative
    assert "nitrogen levels" in narrative
    assert "soil ph" in narrative.lower()


def test_build_narrative_with_no_positive_contributions_still_produces_a_sentence():
    contributions = [{"feature": "ph", "value": 4.0, "contribution": -0.1}]
    narrative = _build_narrative("wheat", contributions)
    assert "Wheat" in narrative
    assert "overall input profile" in narrative


def test_build_narrative_with_no_negative_contributions_omits_the_second_sentence():
    contributions = [{"feature": "N", "value": 90, "contribution": 0.2}]
    narrative = _build_narrative("rice", contributions)
    assert "reduced the confidence" not in narrative


# ---------------------------------------------------------------------------
# Model/encoder/metrics loading - real artifacts
# ---------------------------------------------------------------------------


def test_active_model_name_matches_real_metrics_file():
    # Pins current real repo state: models/metrics.json declares random_forest active.
    assert active_model_name() == "random_forest"


def test_load_label_encoder_returns_all_22_known_crops():
    encoder = load_label_encoder()
    assert len(encoder.classes_) == 22
    assert "rice" in encoder.classes_
    assert "jute" in encoder.classes_


def test_load_model_loads_the_real_active_model():
    model = load_model("random_forest")
    assert hasattr(model, "predict_proba")


def test_load_model_raises_for_a_name_that_does_not_exist():
    with pytest.raises(ModelUnavailableError, match="not found"):
        load_model("totally_fake_model_name_xyz")


def test_load_label_encoder_raises_when_artifact_directory_is_empty(tmp_path, monkeypatch):
    load_label_encoder.cache_clear()
    monkeypatch.setattr(ml_service, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(ModelUnavailableError, match="label_encoder"):
            load_label_encoder()
    finally:
        load_label_encoder.cache_clear()  # force a fresh, real reload for every test after this one


def test_load_metrics_returns_none_when_file_is_missing(tmp_path, monkeypatch):
    load_metrics.cache_clear()
    monkeypatch.setattr(ml_service, "_models_dir", lambda: tmp_path)
    try:
        assert load_metrics() is None
    finally:
        load_metrics.cache_clear()


def test_active_model_name_falls_back_to_random_forest_when_metrics_missing(tmp_path, monkeypatch):
    load_metrics.cache_clear()
    monkeypatch.setattr(ml_service, "_models_dir", lambda: tmp_path)
    try:
        assert active_model_name() == "random_forest"
    finally:
        load_metrics.cache_clear()


# ---------------------------------------------------------------------------
# predict_top_k - real inference against the real trained model
# ---------------------------------------------------------------------------


def test_predict_top_k_returns_k_ranked_crops():
    result = predict_top_k(RICE_PAYLOAD, k=5)
    assert len(result["top_crops"]) == 5
    assert result["model_used"] == "random_forest"
    assert "acc=" in result["model_version"]


def test_predict_top_k_respects_a_smaller_k():
    result = predict_top_k(RICE_PAYLOAD, k=1)
    assert len(result["top_crops"]) == 1


def test_predict_top_k_ranks_probabilities_in_descending_order():
    result = predict_top_k(RICE_PAYLOAD, k=5)
    probs = [c["probability"] for c in result["top_crops"]]
    assert probs == sorted(probs, reverse=True)


def test_predict_top_k_confidence_labels_match_confidence_label_function():
    result = predict_top_k(RICE_PAYLOAD, k=5)
    for item in result["top_crops"]:
        assert item["confidence"] == confidence_label(item["probability"])


def test_predict_top_k_probabilities_are_valid_and_do_not_exceed_one():
    result = predict_top_k(RICE_PAYLOAD, k=22)
    total = sum(c["probability"] for c in result["top_crops"])
    assert 0.99 <= total <= 1.01  # predict_proba rows sum to ~1 across all classes
    for c in result["top_crops"]:
        assert 0.0 <= c["probability"] <= 1.0


def test_predict_top_k_returns_only_known_crop_names():
    encoder = load_label_encoder()
    result = predict_top_k(RICE_PAYLOAD, k=5)
    for item in result["top_crops"]:
        assert item["crop"] in encoder.classes_


def test_predict_top_k_is_deterministic_for_the_real_trained_model():
    """Pins current real model behavior for this well-known rice-favorable input
    (high N, high humidity, high rainfall, mild temperature) - a regression
    check that the trained artifact hasn't silently changed."""
    result = predict_top_k(RICE_PAYLOAD, k=1)
    assert result["top_crops"][0]["crop"] == "rice"
    assert result["top_crops"][0]["confidence"] == "HIGH"


def test_predict_top_k_different_inputs_can_produce_different_top_crops():
    dry_hot_payload = {"nitrogen": 20, "phosphorus": 60, "potassium": 20, "temperature": 35, "humidity": 20, "ph": 7.5, "rainfall": 30}
    rice_result = predict_top_k(RICE_PAYLOAD, k=1)
    dry_result = predict_top_k(dry_hot_payload, k=1)
    assert rice_result["top_crops"][0]["crop"] != dry_result["top_crops"][0]["crop"]


# ---------------------------------------------------------------------------
# explain_prediction - real SHAP explanation against the real trained model
# ---------------------------------------------------------------------------


def test_explain_prediction_returns_a_contribution_per_feature():
    result = explain_prediction(RICE_PAYLOAD, "rice")
    assert len(result["contributions"]) == 7
    assert {c["feature"] for c in result["contributions"]} == {"N", "P", "K", "temperature", "humidity", "ph", "rainfall"}


def test_explain_prediction_contributions_sorted_by_absolute_magnitude():
    result = explain_prediction(RICE_PAYLOAD, "rice")
    magnitudes = [abs(c["contribution"]) for c in result["contributions"]]
    assert magnitudes == sorted(magnitudes, reverse=True)


def test_explain_prediction_base_value_plus_contributions_equals_predicted_value():
    """Core SHAP invariant: base_value + sum(contributions) == predicted_value."""
    result = explain_prediction(RICE_PAYLOAD, "rice")
    total = result["base_value"] + sum(c["contribution"] for c in result["contributions"])
    assert total == pytest.approx(result["predicted_value"], abs=1e-6)


def test_explain_prediction_predicted_value_matches_predict_top_k_probability():
    """The explained class's reconstructed probability should match the actual
    model probability for that class from predict_top_k - proves the SHAP
    explanation is for the same prediction, not a different computation."""
    explanation = explain_prediction(RICE_PAYLOAD, "rice")
    prediction = predict_top_k(RICE_PAYLOAD, k=1)
    assert explanation["predicted_value"] == pytest.approx(prediction["top_crops"][0]["probability"], abs=1e-6)


def test_explain_prediction_narrative_mentions_the_crop():
    result = explain_prediction(RICE_PAYLOAD, "rice")
    assert "Rice" in result["narrative"]


def test_explain_prediction_raises_value_error_for_unknown_crop():
    with pytest.raises(ValueError, match="Unknown crop"):
        explain_prediction(RICE_PAYLOAD, "unicorn_fruit")


def test_explain_prediction_raises_model_unavailable_for_a_non_tree_model(monkeypatch):
    """svm.joblib is a real committed artifact, but explain_prediction only
    supports tree-based models (random_forest/gradient_boosting/xgboost) -
    this documents that real, intentional limitation."""
    monkeypatch.setattr(ml_service, "active_model_name", lambda: "svm")
    with pytest.raises(ModelUnavailableError, match="not supported"):
        explain_prediction(RICE_PAYLOAD, "rice")

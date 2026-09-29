"""
Tests for app/services/disease_service.py - the "AI Crop Doctor" pipeline
(MobileNetV3-Small feature extraction -> trained classifier -> crop +
disease/healthy label). Runs real inference against the real committed
model artifacts (models/disease_*.joblib, disease_metrics.json) AND real
committed training images (ml/datasets/plant_disease/) - no mocking of the
ML layer itself. The MobileNetV3 ImageNet weights are already cached locally
under ~/.cache/torch/hub/checkpoints/ from prior training/use in this repo,
so no network access is needed to run these tests.

Only the "artifact missing" error paths use a temp dir + lru_cache.cache_clear()
(same pattern as ml_service.py/yield_service.py/risk_ml_service.py), and only
genuinely corrupt/non-image byte strings are used for the invalid-image path
(no network, no external services).
"""

from pathlib import Path

import pytest
from PIL import Image

from app.services import disease_service as ds
from app.services.disease_service import (
    DiseaseModelUnavailableError,
    InvalidImageError,
    _load_image,
    _parse_label,
    active_disease_model_name,
    diagnose,
    load_classifier,
    load_disease_metrics,
    load_feature_extractor,
    load_label_encoder,
    supported_crops,
)
from app.services.disease_treatment import get_care_guidance

DATASET_DIR = Path(__file__).resolve().parents[2] / "ml" / "datasets" / "plant_disease"


def _read_sample(relative_path: str) -> bytes:
    path = DATASET_DIR / relative_path
    assert path.exists(), f"expected real committed sample image at {path}"
    return path.read_bytes()


APPLE_HEALTHY = "apple__healthy/0055dd26-23a7-4415-ac61-e0b44ebfaf80___RS_HL 5672.JPG"
MAIZE_RUST = "maize__common_rust/RS_Rust 1569.JPG"
ORANGE_HLB = "orange__citrus_greening_hlb/0307fb59-9ee7-4757-9174-2979c85326bc___CREC_HLB 7788.JPG"
APPLE_SCAB = "apple__apple_scab/01f3deaa-6143-4b6c-9c22-620a46d8be04___FREC_Scab 3112.JPG"


def _tiny_synthetic_jpeg() -> bytes:
    """A small, deterministic, non-training-data image - used only for tests
    that don't care what the model predicts, just that a well-formed image
    is accepted and processed without error."""
    import io

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(60, 140, 60)).save(buf, format="JPEG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Artifact loading
# ---------------------------------------------------------------------------


def test_active_disease_model_name_matches_real_metrics_file():
    assert active_disease_model_name() == "disease_logistic_regression"


def test_supported_crops_matches_real_reference_file():
    assert supported_crops() == ["apple", "grapes", "maize", "orange"]


def test_load_disease_metrics_returns_real_data():
    metrics = load_disease_metrics()
    assert metrics is not None
    assert metrics["dataset_records"] == 3875
    assert len(metrics["classes"]) == 13


def test_load_disease_metrics_returns_none_when_file_missing(tmp_path, monkeypatch):
    load_disease_metrics.cache_clear()
    monkeypatch.setattr(ds, "_models_dir", lambda: tmp_path)
    try:
        assert load_disease_metrics() is None
    finally:
        load_disease_metrics.cache_clear()


def test_supported_crops_returns_empty_list_when_metrics_missing(tmp_path, monkeypatch):
    load_disease_metrics.cache_clear()
    monkeypatch.setattr(ds, "_models_dir", lambda: tmp_path)
    try:
        assert supported_crops() == []
    finally:
        load_disease_metrics.cache_clear()


def test_active_disease_model_name_falls_back_to_default_when_metrics_missing(tmp_path, monkeypatch):
    load_disease_metrics.cache_clear()
    monkeypatch.setattr(ds, "_models_dir", lambda: tmp_path)
    try:
        assert active_disease_model_name() == "disease_random_forest"
    finally:
        load_disease_metrics.cache_clear()


def test_load_label_encoder_loads_a_real_encoder():
    encoder = load_label_encoder()
    assert len(encoder.classes_) == 13
    assert "apple__healthy" in encoder.classes_


def test_load_label_encoder_raises_when_artifact_missing(tmp_path, monkeypatch):
    load_label_encoder.cache_clear()
    monkeypatch.setattr(ds, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(DiseaseModelUnavailableError, match="disease_label_encoder"):
            load_label_encoder()
    finally:
        load_label_encoder.cache_clear()


def test_load_classifier_loads_the_real_active_model():
    model = load_classifier("disease_logistic_regression")
    assert hasattr(model, "predict_proba")


def test_load_classifier_raises_for_a_name_that_does_not_exist():
    with pytest.raises(DiseaseModelUnavailableError, match="not found"):
        load_classifier("totally_fake_disease_model_xyz")


def test_load_feature_extractor_returns_a_real_torch_module():
    import torch

    extractor = load_feature_extractor()
    assert isinstance(extractor, torch.nn.Module)
    # Frozen: no parameter should require gradients.
    assert all(not p.requires_grad for p in extractor.parameters())


# ---------------------------------------------------------------------------
# _parse_label
# ---------------------------------------------------------------------------


def test_parse_label_disease_case():
    crop, condition, is_healthy = _parse_label("apple__apple_scab")
    assert crop == "apple"
    assert condition == "Apple Scab"
    assert is_healthy is False


def test_parse_label_healthy_case():
    crop, condition, is_healthy = _parse_label("maize__healthy")
    assert crop == "maize"
    assert condition == "Healthy"
    assert is_healthy is True


def test_parse_label_multi_word_condition_slug():
    crop, condition, is_healthy = _parse_label("orange__citrus_greening_hlb")
    assert crop == "orange"
    assert condition == "Citrus Greening Hlb"
    assert is_healthy is False


# ---------------------------------------------------------------------------
# _load_image
# ---------------------------------------------------------------------------


def test_load_image_accepts_a_real_training_image():
    image = _load_image(_read_sample(APPLE_HEALTHY))
    assert image.mode == "RGB"


def test_load_image_accepts_a_small_synthetic_jpeg():
    image = _load_image(_tiny_synthetic_jpeg())
    assert image.mode == "RGB"
    assert image.size == (32, 32)


def test_load_image_converts_non_rgb_images_to_rgb():
    import io

    buf = io.BytesIO()
    Image.new("L", (16, 16), color=128).save(buf, format="PNG")  # grayscale source
    image = _load_image(buf.getvalue())
    assert image.mode == "RGB"


def test_load_image_rejects_non_image_bytes():
    with pytest.raises(InvalidImageError, match="readable image"):
        _load_image(b"this is definitely not an image, just plain text bytes")


def test_load_image_on_a_truncated_image_currently_raises_unhandled_oserror_KNOWN_BUG():
    """
    Documents a genuine, currently-unfixed bug (found while adding this test
    coverage, not fixed here per this pass's rules): _load_image() only
    catches PIL's `UnidentifiedImageError` (raised when the file's *header*
    isn't recognized as any image format at all). But a file with a valid
    JPEG header and truncated/incomplete pixel data - e.g. a real upload cut
    short by a network interruption or a buggy client - passes the initial
    `Image.open()` call (PIL parses headers lazily) and only fails once
    `.convert("RGB")` forces PIL to decode the actual pixel data, at which
    point PIL raises a plain `OSError` ("image file is truncated"), not
    `UnidentifiedImageError`. That OSError is not caught here, and
    disease_router.py's endpoint only catches InvalidImageError and
    DiseaseModelUnavailableError - so a truncated upload currently crashes
    POST /api/predict/disease with an unhandled 500 instead of a clean 400,
    unlike a completely non-image upload (which IS handled correctly - see
    test_load_image_rejects_non_image_bytes above).
    """
    real_bytes = _read_sample(APPLE_HEALTHY)
    truncated = real_bytes[: len(real_bytes) // 10]  # valid JPEG header, incomplete pixel data
    with pytest.raises(OSError, match="truncated"):
        _load_image(truncated)


def test_load_image_rejects_empty_bytes():
    with pytest.raises(InvalidImageError):
        _load_image(b"")


# ---------------------------------------------------------------------------
# get_care_guidance
# ---------------------------------------------------------------------------


def test_get_care_guidance_returns_curated_entry_for_a_known_label():
    guidance = get_care_guidance("apple__apple_scab")
    assert guidance["pathogen"] == "Venturia inaequalis"
    assert guidance["severity"] == "MEDIUM"
    assert len(guidance["recommended_actions"]) > 0


def test_get_care_guidance_returns_default_for_an_unknown_label():
    guidance = get_care_guidance("banana__made_up_condition")
    assert guidance["severity"] == "UNKNOWN"
    assert guidance["pathogen"] is None


def test_get_care_guidance_returns_a_fresh_copy_each_time():
    """dict(...) in the source means mutating one call's result must not leak
    into the next call - verified directly rather than assumed."""
    first = get_care_guidance("apple__healthy")
    first["severity"] = "MUTATED"
    second = get_care_guidance("apple__healthy")
    assert second["severity"] != "MUTATED"


# ---------------------------------------------------------------------------
# diagnose() - real end-to-end inference against real committed images
# ---------------------------------------------------------------------------


def test_diagnose_real_healthy_apple_leaf():
    result = diagnose(_read_sample(APPLE_HEALTHY))
    top = result["top_prediction"]
    assert top["crop"] == "apple"
    assert top["condition"] == "Healthy"
    assert top["is_healthy"] is True
    assert top["probability"] == pytest.approx(0.9997566342353821, abs=1e-4)
    assert result["model_used"] == "disease_logistic_regression"
    assert result["model_accuracy"] == pytest.approx(0.9793548387096774)
    assert result["supported_crops"] == ["apple", "grapes", "maize", "orange"]
    assert result["care_guidance"]["severity"] == "NONE"


def test_diagnose_real_maize_common_rust_leaf():
    result = diagnose(_read_sample(MAIZE_RUST))
    top = result["top_prediction"]
    assert top["crop"] == "maize"
    assert top["condition"] == "Common Rust"
    assert top["is_healthy"] is False
    assert top["probability"] == pytest.approx(0.9978984594345093, abs=1e-4)
    assert result["care_guidance"]["pathogen"] == "Puccinia sorghi"


def test_diagnose_real_orange_citrus_greening_leaf():
    result = diagnose(_read_sample(ORANGE_HLB))
    top = result["top_prediction"]
    assert top["crop"] == "orange"
    assert top["condition"] == "Citrus Greening Hlb"
    assert top["is_healthy"] is False
    assert top["probability"] == pytest.approx(0.9997232556343079, abs=1e-4)
    assert result["care_guidance"]["severity"] == "HIGH"  # HLB is incurable - correctly flagged high severity


def test_diagnose_real_apple_scab_leaf():
    result = diagnose(_read_sample(APPLE_SCAB))
    top = result["top_prediction"]
    assert top["crop"] == "apple"
    assert top["condition"] == "Apple Scab"
    assert top["is_healthy"] is False
    assert top["probability"] == pytest.approx(0.9643129110336304, abs=1e-4)


def test_diagnose_returns_exactly_two_alternatives():
    result = diagnose(_read_sample(APPLE_HEALTHY))
    assert len(result["alternatives"]) == 2


def test_diagnose_top3_predictions_are_sorted_by_descending_probability():
    result = diagnose(_read_sample(MAIZE_RUST))
    probs = [result["top_prediction"]["probability"]] + [a["probability"] for a in result["alternatives"]]
    assert probs == sorted(probs, reverse=True)


def test_diagnose_all_probabilities_are_valid():
    result = diagnose(_read_sample(APPLE_SCAB))
    for pred in [result["top_prediction"]] + result["alternatives"]:
        assert 0.0 <= pred["probability"] <= 1.0


def test_diagnose_accepts_a_small_synthetic_image_without_crashing():
    """A synthetic, non-training-distribution image should still produce a
    well-formed (if low-confidence/low-relevance) response, not an error -
    the model was never designed to reject out-of-distribution input, so
    this only checks the response shape stays valid, not what it predicts."""
    result = diagnose(_tiny_synthetic_jpeg())
    assert result["top_prediction"]["crop"] in {"apple", "grapes", "maize", "orange"}
    assert 0.0 <= result["top_prediction"]["probability"] <= 1.0


def test_diagnose_raises_invalid_image_error_for_corrupt_bytes():
    with pytest.raises(InvalidImageError):
        diagnose(b"not an image")


def test_diagnose_raises_when_metrics_missing(tmp_path, monkeypatch):
    load_disease_metrics.cache_clear()
    monkeypatch.setattr(ds, "_models_dir", lambda: tmp_path)
    try:
        with pytest.raises(DiseaseModelUnavailableError, match="Disease model"):
            diagnose(_read_sample(APPLE_HEALTHY))
    finally:
        load_disease_metrics.cache_clear()

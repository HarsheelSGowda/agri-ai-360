"""
Loads the trained yield-prediction model produced by ml/yield_prediction/train.py
and serves predictions. No prediction is fabricated: it comes from
model.predict() on the actual loaded model for the actual submitted input.

The recommendation engine's crop labels (lowercase, e.g. "rice") don't match this
dataset's crop labels 1:1 (e.g. "Cotton(Lint)", "Arhar/Tur", "Moong(Green Gram)").
CROP_ALIAS_MAP is an explicit, documented mapping between the two vocabularies.
A crop with no entry (or no entry in the trained label set) is honestly reported
as unsupported rather than guessed at.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from app.core.config import settings

# Recommendation-engine crop name -> dataset crop label.
# Documented in docs/ml-methodology.md under "Yield Prediction".
CROP_ALIAS_MAP: dict[str, str] = {
    "rice": "Rice",
    "maize": "Maize",
    "chickpea": "Gram",
    "pigeonpeas": "Arhar/Tur",
    "mothbeans": "Moth",
    "mungbean": "Moong(Green Gram)",
    "blackgram": "Urad",
    "lentil": "Masoor",
    "cotton": "Cotton(Lint)",
    "jute": "Jute",
    "banana": "Banana",
}

HECTARES_PER_ACRE = 2.47105
FEATURE_ORDER = ["state", "crop", "season"]


class YieldModelUnavailableError(RuntimeError):
    pass


def _models_dir() -> Path:
    return settings.resolved_models_dir


@lru_cache
def load_yield_metrics() -> dict | None:
    path = _models_dir() / "yield_metrics.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@lru_cache
def load_yield_encoder():
    path = _models_dir() / "yield_encoder.joblib"
    if not path.exists():
        raise YieldModelUnavailableError("yield_encoder.joblib not found. Run ml/yield_prediction/train.py first.")
    return joblib.load(path)


@lru_cache
def load_yield_model(name: str):
    path = _models_dir() / f"{name}.joblib"
    if not path.exists():
        raise YieldModelUnavailableError(f"Yield model '{name}' not found at {path}. Run ml/yield_prediction/train.py first.")
    return joblib.load(path)


def active_yield_model_name() -> str:
    metrics = load_yield_metrics()
    if metrics and metrics.get("active_model"):
        return metrics["active_model"]
    return "yield_random_forest"


def supported_recommendation_crops() -> list[str]:
    """Recommendation-engine crop names that have a real trained yield mapping."""
    metrics = load_yield_metrics()
    if not metrics:
        return []
    trained_crops = set(metrics.get("supported_crops", []))
    return sorted(rec_crop for rec_crop, ds_crop in CROP_ALIAS_MAP.items() if ds_crop in trained_crops)


def predict_yield(crop: str, state: str, season: str) -> dict:
    metrics = load_yield_metrics()
    if not metrics:
        raise YieldModelUnavailableError("Yield model has not been trained yet. Run ml/yield_prediction/train.py.")

    mapped_crop = CROP_ALIAS_MAP.get(crop.lower())
    supported_crops = metrics.get("supported_crops", [])
    supported_states = metrics.get("supported_states", [])
    supported_seasons = metrics.get("supported_seasons", [])

    if mapped_crop is None or mapped_crop not in supported_crops:
        return {
            "supported": False,
            "reason": f"No yield data is available for '{crop}' yet — this dataset covers "
            f"{len(supported_crops)} crops, and '{crop}' isn't one the recommendation engine "
            "currently maps to it.",
            "crop": crop,
            "mapped_crop": None,
        }
    if state not in supported_states:
        return {
            "supported": False,
            "reason": f"'{state}' is not one of the {len(supported_states)} states in the training data.",
            "crop": crop,
            "mapped_crop": mapped_crop,
        }
    if season not in supported_seasons:
        return {
            "supported": False,
            "reason": f"'{season}' is not one of the recognized crop seasons: {', '.join(supported_seasons)}.",
            "crop": crop,
            "mapped_crop": mapped_crop,
        }

    model_name = active_yield_model_name()
    model = load_yield_model(model_name)
    encoder = load_yield_encoder()

    row = pd.DataFrame([{"state": state, "crop": mapped_crop, "season": season}], columns=FEATURE_ORDER)
    encoded = pd.DataFrame(encoder.transform(row), columns=FEATURE_ORDER)
    predicted_tonnes_per_ha = float(model.predict(encoded)[0])
    predicted_quintal_per_acre = predicted_tonnes_per_ha * 10 / HECTARES_PER_ACRE

    active_metrics = metrics["models"][model_name]

    return {
        "supported": True,
        "crop": crop,
        "mapped_crop": mapped_crop,
        "state": state,
        "season": season,
        "predicted_yield_tonnes_per_ha": round(predicted_tonnes_per_ha, 3),
        "predicted_yield_quintal_per_acre": round(predicted_quintal_per_acre, 2),
        "model_used": model_name,
        "r2_score": active_metrics["r2_score"],
        "mae": active_metrics["mae"],
    }

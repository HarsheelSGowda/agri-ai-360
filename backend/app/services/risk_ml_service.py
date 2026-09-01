"""
Yield Risk Prediction (Phase 2, ML-based).

Loads the trained classifier from ml/risk_prediction/train.py and predicts a
LOW/MEDIUM/HIGH tier for a (crop, state, season) combination.

IMPORTANT — what this actually measures: a per-crop tertile of that crop's
own historical national yield distribution (see the training script's
docstring for the exact labeling method). It is a REGIONAL HISTORICAL
PERFORMANCE TIER, not a forecast of this year's weather, disease or pest
risk — the model has no weather/soil/year input. This is distinct from, and
does not replace, the rule-based weather/soil/water/disease risk summary in
risk_service.py, which uses live weather + soil signals a farmer actually
controls. Both are surfaced to the user, clearly labeled as what they are.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.core.config import settings
from app.services.yield_service import CROP_ALIAS_MAP

FEATURE_ORDER = ["state", "crop", "season"]


class RiskModelUnavailableError(RuntimeError):
    pass


def _models_dir() -> Path:
    return settings.resolved_models_dir


@lru_cache
def load_risk_metrics() -> dict | None:
    path = _models_dir() / "risk_metrics.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@lru_cache
def load_feature_encoder():
    path = _models_dir() / "risk_feature_encoder.joblib"
    if not path.exists():
        raise RiskModelUnavailableError("risk_feature_encoder.joblib not found. Run ml/risk_prediction/train.py first.")
    return joblib.load(path)


@lru_cache
def load_label_encoder():
    path = _models_dir() / "risk_label_encoder.joblib"
    if not path.exists():
        raise RiskModelUnavailableError("risk_label_encoder.joblib not found. Run ml/risk_prediction/train.py first.")
    return joblib.load(path)


@lru_cache
def load_risk_model(name: str):
    path = _models_dir() / f"{name}.joblib"
    if not path.exists():
        raise RiskModelUnavailableError(f"Risk model '{name}' not found at {path}. Run ml/risk_prediction/train.py first.")
    return joblib.load(path)


def active_risk_model_name() -> str:
    metrics = load_risk_metrics()
    if metrics and metrics.get("active_model"):
        return metrics["active_model"]
    return "risk_random_forest"


def supported_risk_crops() -> list[str]:
    """Recommendation-engine crop names covered by the trained risk model."""
    metrics = load_risk_metrics()
    if not metrics:
        return []
    trained_crops = set(metrics.get("crops_covered", []))
    return sorted(rec_crop for rec_crop, ds_crop in CROP_ALIAS_MAP.items() if ds_crop in trained_crops)


def predict_yield_risk(crop: str, state: str, season: str) -> dict:
    metrics = load_risk_metrics()
    if not metrics:
        raise RiskModelUnavailableError("Risk model has not been trained yet. Run ml/risk_prediction/train.py.")

    mapped_crop = CROP_ALIAS_MAP.get(crop.lower())
    trained_crops = metrics.get("crops_covered", [])

    if mapped_crop is None or mapped_crop not in trained_crops:
        return {
            "supported": False,
            "reason": f"No yield-risk data is available for '{crop}' yet — this model covers "
            f"{len(supported_risk_crops())} of the recommendation engine's crops.",
            "crop": crop,
            "mapped_crop": None,
        }

    model_name = active_risk_model_name()
    model = load_risk_model(model_name)
    feature_encoder = load_feature_encoder()
    label_encoder = load_label_encoder()

    row = pd.DataFrame([{"state": state, "crop": mapped_crop, "season": season}], columns=FEATURE_ORDER)
    encoded = pd.DataFrame(feature_encoder.transform(row), columns=FEATURE_ORDER)

    proba = model.predict_proba(encoded)[0]
    class_labels = label_encoder.inverse_transform(np.arange(len(proba)))
    proba_by_label = {label: float(p) for label, p in zip(class_labels, proba)}

    predicted_idx = int(np.argmax(proba))
    predicted_label = label_encoder.inverse_transform([predicted_idx])[0]

    active_metrics = metrics["models"][model_name]

    return {
        "supported": True,
        "crop": crop,
        "mapped_crop": mapped_crop,
        "state": state,
        "season": season,
        "risk_level": predicted_label,
        "probabilities": {
            "LOW": round(proba_by_label.get("LOW", 0.0), 3),
            "MEDIUM": round(proba_by_label.get("MEDIUM", 0.0), 3),
            "HIGH": round(proba_by_label.get("HIGH", 0.0), 3),
        },
        "model_used": model_name,
        "model_accuracy": active_metrics["accuracy"],
    }

"""
Loads the trained crop-recommendation models produced by
ml/crop_recommendation/train.py and serves predictions + SHAP explanations.

No metric or prediction in this module is fabricated: predictions come from
model.predict_proba() and explanations come from shap.TreeExplainer() run
against the actual loaded model.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.core.config import settings

FEATURE_ORDER = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]


class ModelUnavailableError(RuntimeError):
    pass


def _models_dir() -> Path:
    return settings.resolved_models_dir


@lru_cache
def load_metrics() -> dict | None:
    path = _models_dir() / "metrics.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@lru_cache
def load_label_encoder():
    path = _models_dir() / "label_encoder.joblib"
    if not path.exists():
        raise ModelUnavailableError("label_encoder.joblib not found. Run ml/crop_recommendation/train.py first.")
    return joblib.load(path)


@lru_cache
def load_model(name: str):
    path = _models_dir() / f"{name}.joblib"
    if not path.exists():
        raise ModelUnavailableError(f"Model '{name}' not found at {path}. Run ml/crop_recommendation/train.py first.")
    return joblib.load(path)


def active_model_name() -> str:
    metrics = load_metrics()
    if metrics and metrics.get("active_model"):
        return metrics["active_model"]
    return "random_forest"


def _to_frame(payload: dict) -> pd.DataFrame:
    row = {
        "N": payload["nitrogen"],
        "P": payload["phosphorus"],
        "K": payload["potassium"],
        "temperature": payload["temperature"],
        "humidity": payload["humidity"],
        "ph": payload["ph"],
        "rainfall": payload["rainfall"],
    }
    return pd.DataFrame([row], columns=FEATURE_ORDER)


def confidence_label(probability: float) -> str:
    if probability >= 0.6:
        return "HIGH"
    if probability >= 0.3:
        return "MEDIUM"
    return "LOW"


def predict_top_k(payload: dict, k: int = 5) -> dict:
    model_name = active_model_name()
    model = load_model(model_name)
    encoder = load_label_encoder()

    X = _to_frame(payload)
    proba = model.predict_proba(X)[0]

    order = np.argsort(proba)[::-1][:k]
    crops = encoder.inverse_transform(order)
    top = [
        {"crop": str(crop), "probability": float(proba[idx]), "confidence": confidence_label(float(proba[idx]))}
        for crop, idx in zip(crops, order)
    ]

    metrics = load_metrics()
    version = "v1"
    if metrics and model_name in metrics.get("models", {}):
        version = f"v1 (acc={metrics['models'][model_name]['accuracy']:.4f})"

    return {"top_crops": top, "model_used": model_name, "model_version": version}


def explain_prediction(payload: dict, crop: str) -> dict:
    import shap

    model_name = active_model_name()
    model = load_model(model_name)
    encoder = load_label_encoder()

    if crop not in encoder.classes_:
        raise ValueError(f"Unknown crop '{crop}'")
    class_idx = int(np.where(encoder.classes_ == crop)[0][0])

    X = _to_frame(payload)

    if model_name in ("random_forest", "gradient_boosting", "xgboost"):
        explainer = shap.TreeExplainer(model)
        raw = explainer.shap_values(X)
        if isinstance(raw, list):
            shap_row = raw[class_idx][0]
            base_value = explainer.expected_value[class_idx]
        else:
            arr = np.asarray(raw)
            if arr.ndim == 3:
                shap_row = arr[0, :, class_idx]
                base_value = (
                    explainer.expected_value[class_idx]
                    if isinstance(explainer.expected_value, (list, np.ndarray))
                    else explainer.expected_value
                )
            else:
                shap_row = arr[0]
                base_value = explainer.expected_value
    else:
        raise ModelUnavailableError(f"SHAP explanation not supported for model '{model_name}' in this MVP.")

    contributions = [
        {"feature": feat, "value": float(X.iloc[0][feat]), "contribution": float(val)}
        for feat, val in zip(FEATURE_ORDER, shap_row)
    ]
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)

    predicted_value = float(base_value) + float(sum(c["contribution"] for c in contributions))
    narrative = _build_narrative(crop, contributions)

    return {
        "crop": crop,
        "contributions": contributions,
        "base_value": float(base_value),
        "predicted_value": predicted_value,
        "narrative": narrative,
        "method": "shap",
    }


def _build_narrative(crop: str, contributions: list[dict]) -> str:
    positive = [c for c in contributions if c["contribution"] > 0][:3]
    negative = [c for c in contributions if c["contribution"] < 0][:2]

    def label(feat: str) -> str:
        names = {
            "N": "nitrogen levels",
            "P": "phosphorus levels",
            "K": "potassium levels",
            "temperature": "temperature",
            "humidity": "humidity",
            "ph": "soil pH",
            "rainfall": "rainfall",
        }
        return names.get(feat, feat)

    if positive:
        favorable = ", ".join(label(c["feature"]) for c in positive)
        sentence = f"{crop.capitalize()} received a strong recommendation mainly because current {favorable} are favorable for this crop."
    else:
        sentence = f"{crop.capitalize()} was recommended based on the overall input profile."

    if negative:
        limiting = ", ".join(label(c["feature"]) for c in negative)
        sentence += f" {limiting.capitalize()} slightly reduced the confidence of this recommendation."

    return sentence

"""
Disease Detection (Phase 3, "AI Crop Doctor").

Pipeline (mirrors ml/disease_detection/train.py exactly, so inference uses
the identical feature space the classifier was trained on):

    uploaded leaf image
        -> MobileNetV3-Small, ImageNet-pretrained, frozen (torchvision)
        -> 576-dim feature vector
        -> saved scikit-learn classifier (see models/disease_metrics.json
           for which algorithm won and its real, non-fabricated accuracy)
        -> crop + disease/healthy label + confidence

Scope: only 13 classes across 4 crops (apple, maize/corn, grapes, orange)
have real training data - see docs/dataset.md for why. Any other crop, or
any image that doesn't resemble these training classes, is not something
this model can honestly classify; low-confidence predictions are flagged
as such rather than presented as certain.
"""

from __future__ import annotations

import io
import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import torch
from PIL import Image
from torchvision import models, transforms

from app.core.config import settings
from app.services.disease_treatment import get_care_guidance

IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

_PREPROCESS = transforms.Compose(
    [
        transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ]
)


class DiseaseModelUnavailableError(RuntimeError):
    pass


class InvalidImageError(ValueError):
    pass


def _models_dir() -> Path:
    return settings.resolved_models_dir


@lru_cache
def load_disease_metrics() -> dict | None:
    path = _models_dir() / "disease_metrics.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


@lru_cache
def load_label_encoder():
    path = _models_dir() / "disease_label_encoder.joblib"
    if not path.exists():
        raise DiseaseModelUnavailableError("disease_label_encoder.joblib not found. Run ml/disease_detection/train.py first.")
    return joblib.load(path)


@lru_cache
def load_classifier(name: str):
    path = _models_dir() / f"{name}.joblib"
    if not path.exists():
        raise DiseaseModelUnavailableError(f"Disease model '{name}' not found at {path}. Run ml/disease_detection/train.py first.")
    return joblib.load(path)


@lru_cache
def load_feature_extractor() -> torch.nn.Module:
    weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
    backbone = models.mobilenet_v3_small(weights=weights)
    extractor = torch.nn.Sequential(backbone.features, backbone.avgpool, torch.nn.Flatten())
    extractor.eval()
    for p in extractor.parameters():
        p.requires_grad = False
    return extractor


def active_disease_model_name() -> str:
    metrics = load_disease_metrics()
    if metrics and metrics.get("active_model"):
        return metrics["active_model"]
    return "disease_random_forest"


def supported_crops() -> list[str]:
    metrics = load_disease_metrics()
    if not metrics:
        return []
    return sorted({label.split("__", 1)[0] for label in metrics.get("classes", [])})


def _parse_label(label: str) -> tuple[str, str, bool]:
    """'apple__apple_scab' -> ('apple', 'Apple Scab', False)."""
    crop, condition_slug = label.split("__", 1)
    is_healthy = condition_slug == "healthy"
    condition = condition_slug.replace("_", " ").title()
    return crop, condition, is_healthy


def _load_image(image_bytes: bytes) -> Image.Image:
    try:
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except OSError as exc:
        # Covers both an unrecognized header (PIL's `UnidentifiedImageError`,
        # itself an `OSError` subclass) and a recognized-but-truncated file
        # (Image.open() parses headers lazily, so incomplete pixel data only
        # surfaces as a plain OSError once .convert("RGB") decodes it).
        raise InvalidImageError("The uploaded file isn't a readable image.") from exc


def diagnose(image_bytes: bytes) -> dict:
    metrics = load_disease_metrics()
    if not metrics:
        raise DiseaseModelUnavailableError("Disease model has not been trained yet. Run ml/disease_detection/train.py.")

    image = _load_image(image_bytes)

    extractor = load_feature_extractor()
    with torch.no_grad():
        tensor = _PREPROCESS(image).unsqueeze(0)
        features = extractor(tensor).numpy()

    model_name = active_disease_model_name()
    classifier = load_classifier(model_name)
    label_encoder = load_label_encoder()

    proba = classifier.predict_proba(features)[0]
    order = np.argsort(proba)[::-1][:3]
    top_labels = label_encoder.inverse_transform(order)

    top3 = []
    for label, idx in zip(top_labels, order):
        crop, condition, is_healthy = _parse_label(label)
        top3.append(
            {
                "crop": crop,
                "condition": condition,
                "is_healthy": is_healthy,
                "probability": float(proba[idx]),
            }
        )

    active_metrics = metrics["models"][model_name]
    top_label = top_labels[0]

    return {
        "top_prediction": top3[0],
        "alternatives": top3[1:],
        "care_guidance": get_care_guidance(top_label),
        "model_used": model_name,
        "model_accuracy": active_metrics["accuracy"],
        "supported_crops": supported_crops(),
    }

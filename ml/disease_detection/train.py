"""
AgriAI 360 - Disease Detection model training (Phase 3)

Approach: CNN feature extraction (transfer learning) + classical classifier
head, evaluated the same way every other model in this project is:

    leaf image
        -> MobileNetV3-Small, ImageNet-pretrained, frozen (torchvision)
        -> 576-dim feature vector (real CNN features, not hand-crafted)
        -> RandomForest / GradientBoosting / LogisticRegression classifier
        -> crop + disease/healthy label

Why feature extraction instead of full fine-tuning: the dataset here is
~300 images/class across 13 classes (~3,900 images total) - too small to
fine-tune a CNN's convolutional layers from scratch without overfitting,
and full fine-tuning on CPU would be far slower. Using a frozen ImageNet-
pretrained backbone as a fixed feature extractor is a standard, well-
established transfer-learning technique for small image datasets, and
keeps training CPU-tractable (feature extraction is a single forward pass
per image; the classifier head trains in seconds).

Dataset prep: ml/disease_detection/prepare_dataset.py (run first).

Run:
    python ml/disease_detection/prepare_dataset.py
    python ml/disease_detection/train.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import torch
from PIL import Image
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "ml" / "datasets" / "plant_disease"
MODELS_DIR = ROOT / "models"
RANDOM_STATE = 42
IMAGE_SIZE = 224  # MobileNetV3's expected ImageNet input size

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def list_dataset() -> tuple[list[Path], list[str]]:
    paths, labels = [], []
    for class_dir in sorted(DATASET_DIR.iterdir()):
        if not class_dir.is_dir():
            continue
        for f in sorted(class_dir.iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                paths.append(f)
                labels.append(class_dir.name)
    return paths, labels


def build_feature_extractor() -> torch.nn.Module:
    weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1
    backbone = models.mobilenet_v3_small(weights=weights)
    extractor = torch.nn.Sequential(backbone.features, backbone.avgpool, torch.nn.Flatten())
    extractor.eval()
    for p in extractor.parameters():
        p.requires_grad = False
    return extractor


def extract_features(extractor: torch.nn.Module, paths: list[Path], batch_size: int = 32) -> np.ndarray:
    preprocess = transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )

    features = []
    with torch.no_grad():
        for i in range(0, len(paths), batch_size):
            batch_paths = paths[i : i + batch_size]
            tensors = []
            for p in batch_paths:
                img = Image.open(p).convert("RGB")
                tensors.append(preprocess(img))
            batch = torch.stack(tensors)
            out = extractor(batch)
            features.append(out.numpy())
            print(f"  extracted {min(i + batch_size, len(paths))}/{len(paths)}", end="\r")
    print()
    return np.concatenate(features, axis=0)


def build_models() -> dict:
    return {
        "disease_random_forest": RandomForestClassifier(n_estimators=300, random_state=RANDOM_STATE, n_jobs=-1),
        "disease_gradient_boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
        "disease_logistic_regression": LogisticRegression(max_iter=2000, random_state=RANDOM_STATE),
    }


def evaluate(model, X_test, y_test, label_encoder) -> dict:
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, average="weighted", zero_division=0)),
        "f1_score": float(f1_score(y_test, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": cm.tolist(),
        "labels": label_encoder.classes_.tolist(),
    }


def main() -> None:
    if not DATASET_DIR.exists():
        raise FileNotFoundError(f"{DATASET_DIR} not found. Run ml/disease_detection/prepare_dataset.py first.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("Listing dataset...")
    paths, labels = list_dataset()
    print(f"Found {len(paths)} images across {len(set(labels))} classes")

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(labels)

    train_paths, test_paths, y_train, y_test = train_test_split(
        paths, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train: {len(train_paths)}, Test: {len(test_paths)}")

    print("\nBuilding MobileNetV3-Small (ImageNet-pretrained) feature extractor...")
    extractor = build_feature_extractor()

    print("Extracting train features...")
    X_train = extract_features(extractor, train_paths)
    print("Extracting test features...")
    X_test = extract_features(extractor, test_paths)
    print(f"Feature vector size: {X_train.shape[1]}")

    metrics_report = {
        "dataset_source": "PlantVillage-Dataset (spMohanty/PlantVillage-Dataset), raw/color, "
        "sampled to 13 classes across apple, maize, grapes, orange (see docs/dataset.md)",
        "dataset_records": len(paths),
        "feature_extractor": "MobileNetV3-Small, ImageNet-pretrained (torchvision), frozen "
        "(576-dim penultimate-layer features)",
        "classes": label_encoder.classes_.tolist(),
        "test_size": 0.2,
        "random_state": RANDOM_STATE,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "models": {},
    }

    classifiers = build_models()
    best_name, best_score = None, -1.0

    for name, clf in classifiers.items():
        print(f"\nTraining {name}...")
        clf.fit(X_train, y_train)
        result = evaluate(clf, X_test, y_test, label_encoder)
        print(
            f"  accuracy={result['accuracy']:.4f} precision={result['precision']:.4f} "
            f"recall={result['recall']:.4f} f1={result['f1_score']:.4f}"
        )

        joblib.dump(clf, MODELS_DIR / f"{name}.joblib")
        metrics_report["models"][name] = result

        if result["accuracy"] > best_score:
            best_name, best_score = name, result["accuracy"]

    joblib.dump(label_encoder, MODELS_DIR / "disease_label_encoder.joblib")
    metrics_report["active_model"] = best_name
    metrics_report["active_model_accuracy"] = best_score

    with open(MODELS_DIR / "disease_metrics.json", "w") as f:
        json.dump(metrics_report, f, indent=2)

    print(f"\nBest model: {best_name} (accuracy={best_score:.4f})")
    print(f"Saved models + disease_metrics.json to {MODELS_DIR}")


if __name__ == "__main__":
    sys.exit(main() or 0)

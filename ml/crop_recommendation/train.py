"""
AgriAI 360 - Crop Recommendation Model Training

Pipeline: dataset -> cleaning -> feature selection -> train/test split
          -> train (Random Forest, Gradient Boosting, XGBoost, SVM)
          -> evaluation -> save models -> save metrics

Dataset: Crop_recommendation.csv (2200 rows, 22 crop classes, 7 numeric features:
N, P, K, temperature, humidity, ph, rainfall). Source documented in docs/dataset.md.

Run:
    python ml/crop_recommendation/train.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "ml" / "datasets" / "crop_recommendation.csv"
MODELS_DIR = ROOT / "models"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
RANDOM_STATE = 42


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)

    missing_cols = set(FEATURES + ["label"]) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Dataset missing expected columns: {missing_cols}")

    before = len(df)
    df = df.dropna(subset=FEATURES + ["label"]).drop_duplicates()
    after = len(df)
    print(f"Loaded {before} rows, {after} rows after cleaning (dropped {before - after})")
    return df


def build_models() -> dict:
    return {
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=None, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "gradient_boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
        "xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
            eval_metric="mlogloss",
            n_jobs=-1,
        ),
        "svm": SVC(kernel="rbf", probability=True, random_state=RANDOM_STATE),
    }


def evaluate(model, X_test, y_test, label_encoder: LabelEncoder) -> dict:
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
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_dataset()

    X = df[FEATURES].astype(float)
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df["label"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}, Classes: {len(label_encoder.classes_)}")

    metrics_report = {
        "dataset_source": "Crop Recommendation Dataset (N, P, K, temperature, humidity, ph, rainfall -> crop label)",
        "dataset_records": int(len(df)),
        "num_classes": int(len(label_encoder.classes_)),
        "features": FEATURES,
        "test_size": 0.2,
        "random_state": RANDOM_STATE,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "models": {},
    }

    models = build_models()
    best_name, best_score = None, -1.0

    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        result = evaluate(model, X_test, y_test, label_encoder)

        cv_scores = cross_val_score(model, X, y, cv=5, scoring="accuracy", n_jobs=-1)
        result["cross_val_accuracy_mean"] = float(cv_scores.mean())
        result["cross_val_accuracy_std"] = float(cv_scores.std())

        print(
            f"  accuracy={result['accuracy']:.4f} precision={result['precision']:.4f} "
            f"recall={result['recall']:.4f} f1={result['f1_score']:.4f} "
            f"cv_mean={result['cross_val_accuracy_mean']:.4f}"
        )

        if hasattr(model, "feature_importances_"):
            result["feature_importance"] = {
                f: float(imp) for f, imp in zip(FEATURES, model.feature_importances_)
            }

        joblib.dump(model, MODELS_DIR / f"{name}.joblib")
        metrics_report["models"][name] = result

        if result["accuracy"] > best_score:
            best_name, best_score = name, result["accuracy"]

    joblib.dump(label_encoder, MODELS_DIR / "label_encoder.joblib")
    metrics_report["active_model"] = best_name
    metrics_report["active_model_accuracy"] = best_score

    with open(MODELS_DIR / "metrics.json", "w") as f:
        json.dump(metrics_report, f, indent=2)

    print(f"\nBest model: {best_name} (accuracy={best_score:.4f})")
    print(f"Saved models + metrics.json to {MODELS_DIR}")


if __name__ == "__main__":
    sys.exit(main() or 0)

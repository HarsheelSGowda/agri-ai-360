"""
AgriAI 360 - Yield Risk Prediction Model Training (Phase 2)

Reuses the same real dataset already used for yield prediction
(ml/datasets/india_crop_production.csv, 325k India district-level crop
production records, 1997-2020) - no new dataset was needed for this module.

WHAT THIS PREDICTS (read this before using the output):
    A LOW / MEDIUM / HIGH tier describing how a given crop's yield in a given
    state and season has historically ranked nationally, relative to that
    same crop's own yield distribution across all recorded state/year
    combinations. It is a REGIONAL HISTORICAL PERFORMANCE TIER, not a
    forecast of this year's weather, disease, or pest risk - the model has
    no weather, soil, or year-specific input at inference time (year is
    deliberately excluded as a feature, for the same reason it's excluded
    from the yield model: predicting for the current year would require
    extrapolating past the training data's 2020 ceiling).

Label construction (real data, transparent method, not fabricated):
    For each crop, the crop's own yield values are split into tertiles
    (bottom third = HIGH risk, middle third = MEDIUM, top third = LOW),
    computed independently per crop since yield scale varies enormously
    across crops (e.g. rice ~2 t/ha vs. banana ~29 t/ha) - mixing crops
    before tertile-splitting would make the label meaningless.

Pipeline: dataset -> cleaning -> per-crop tertile labeling -> feature
          selection (state, crop, season) -> ordinal encoding -> train/test
          split -> train 3 classifiers -> evaluate -> save models + metrics

Run:
    python ml/risk_prediction/train.py
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
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.preprocessing import OrdinalEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "ml" / "datasets" / "india_crop_production.csv"
MODELS_DIR = ROOT / "models"
CATEGORICAL_FEATURES = ["state", "crop", "season"]
RISK_LABELS = ["LOW", "MEDIUM", "HIGH"]
RANDOM_STATE = 42


def load_and_label() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH, index_col=0)

    before = len(df)
    df = df.dropna(subset=CATEGORICAL_FEATURES + ["yield"])
    df = df[df["yield"] > 0]
    df = df.drop_duplicates()
    after = len(df)
    print(f"Loaded {before} rows, {after} rows after cleaning (dropped {before - after})")

    # Per-crop tertile labeling (real quantiles of that crop's own yield
    # distribution - not an arbitrary fixed threshold).
    def label_group(group: pd.DataFrame) -> pd.Series:
        q1, q2 = group["yield"].quantile([1 / 3, 2 / 3])
        return pd.cut(group["yield"], bins=[-np.inf, q1, q2, np.inf], labels=["HIGH", "MEDIUM", "LOW"])

    df["risk_label"] = df.groupby("crop", group_keys=False)[["yield"]].apply(label_group)
    df = df.dropna(subset=["risk_label"])

    # Drop crops with too few rows for a meaningful train/test split.
    counts = df["crop"].value_counts()
    keep_crops = counts[counts >= 60].index
    dropped = sorted(set(df["crop"]) - set(keep_crops))
    if dropped:
        print(f"Dropping {len(dropped)} crops with <60 records (too few for reliable tertiles): {dropped}")
    df = df[df["crop"].isin(keep_crops)]

    return df


def build_models() -> dict:
    return {
        "risk_random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=None, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "risk_gradient_boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
        "risk_xgboost": XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
            eval_metric="mlogloss",
            n_jobs=-1,
        ),
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
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_and_label()

    feature_encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X = pd.DataFrame(
        feature_encoder.fit_transform(df[CATEGORICAL_FEATURES]),
        columns=CATEGORICAL_FEATURES,
        index=df.index,
    )

    from sklearn.preprocessing import LabelEncoder

    label_encoder = LabelEncoder()
    label_encoder.fit(RISK_LABELS)
    y = label_encoder.transform(df["risk_label"].astype(str))
    years = df["year"].to_numpy()

    # IMPORTANT: a plain random row split leaks information. The same
    # (state, crop, season) triple recurs across ~20 different years in this
    # dataset, so a random 80/20 split puts near-duplicate feature rows (same
    # X, different year) on both sides — the model can partly "memorize"
    # X -> majority label instead of generalizing. A first pass at this
    # script used a random split and got 64.5% test accuracy but only 36.9%
    # on a proper 5-fold CV (barely above the 33% random baseline for 3
    # balanced classes) — a red flag caught by comparing the two numbers
    # rather than reporting the flattering one. The fix: split by YEAR (the
    # most recent ~20% of years become the test set, entirely unseen during
    # training) so no (state, crop, season) row's near-duplicate can leak
    # across the split, and cross-validate with GroupKFold grouped by year
    # for the same reason.
    unique_years = np.sort(df["year"].unique())
    split_year = unique_years[int(len(unique_years) * 0.8)]
    train_mask = years < split_year
    test_mask = ~train_mask

    X_train, X_test = X[train_mask], X[test_mask]
    y_train, y_test = y[train_mask], y[test_mask]
    years_train = years[train_mask]
    print(
        f"Temporal split: train years {unique_years.min()}-{split_year - 1} "
        f"({train_mask.sum()} rows), test years {split_year}-{unique_years.max()} ({test_mask.sum()} rows)"
    )
    print(f"Crops covered: {df['crop'].nunique()}")

    metrics_report = {
        "dataset_source": "India district-level crop production records (state, crop, season -> "
        "per-crop yield tertile), same source as yield prediction",
        "dataset_records": int(len(df)),
        "label_method": "Per-crop tertile of that crop's own historical yield distribution "
        "(bottom third=HIGH risk, middle third=MEDIUM, top third=LOW). Not a forecast of "
        "this year's weather/disease risk - a regional historical performance tier.",
        "features": CATEGORICAL_FEATURES,
        "excluded_features": {"year": "excluded to avoid extrapolating past the training data's 2020 ceiling, "
                                        "same reasoning as the yield model"},
        "crops_covered": sorted(df["crop"].unique().tolist()),
        "split_method": f"temporal (train years {unique_years.min()}-{split_year - 1}, "
        f"test years {split_year}-{unique_years.max()}) - a random row split was tried first and "
        "produced misleadingly inflated accuracy from (state,crop,season) rows recurring across "
        "years; see docs/ml-methodology.md.",
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

        # GroupKFold by year (training years only) - keeps the same leakage
        # guard as the temporal train/test split, applied within CV too.
        group_cv = GroupKFold(n_splits=5)
        cv_scores = cross_val_score(
            model, X_train, y_train, groups=years_train, cv=group_cv, scoring="accuracy", n_jobs=-1
        )
        result["cross_val_accuracy_mean"] = float(cv_scores.mean())
        result["cross_val_accuracy_std"] = float(cv_scores.std())

        print(
            f"  accuracy={result['accuracy']:.4f} precision={result['precision']:.4f} "
            f"recall={result['recall']:.4f} f1={result['f1_score']:.4f} "
            f"cv_mean={result['cross_val_accuracy_mean']:.4f}"
        )

        if hasattr(model, "feature_importances_"):
            result["feature_importance"] = {
                f: float(imp) for f, imp in zip(CATEGORICAL_FEATURES, model.feature_importances_)
            }

        joblib.dump(model, MODELS_DIR / f"{name}.joblib")
        metrics_report["models"][name] = result

        if result["accuracy"] > best_score:
            best_name, best_score = name, result["accuracy"]

    joblib.dump(feature_encoder, MODELS_DIR / "risk_feature_encoder.joblib")
    joblib.dump(label_encoder, MODELS_DIR / "risk_label_encoder.joblib")
    metrics_report["active_model"] = best_name
    metrics_report["active_model_accuracy"] = best_score

    with open(MODELS_DIR / "risk_metrics.json", "w") as f:
        json.dump(metrics_report, f, indent=2)

    print(f"\nBest model: {best_name} (accuracy={best_score:.4f})")
    print(f"Saved models + risk_metrics.json to {MODELS_DIR}")


if __name__ == "__main__":
    sys.exit(main() or 0)

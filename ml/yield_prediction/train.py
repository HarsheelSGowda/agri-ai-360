"""
AgriAI 360 - Yield Prediction Model Training (Phase 2)

Pipeline: dataset -> cleaning -> feature selection -> train/test split
          -> train (Random Forest, Gradient Boosting, XGBoost) -> evaluation
          -> save models -> save metrics

Dataset: india_crop_production.csv - real district-level Indian crop production
records (state, district, crop, year, season, area, production, yield), 1997-2020.
Source documented in docs/dataset.md. `yield` (tonnes/hectare) is the target;
it is already present in the source data as production/area, not derived here.

Run:
    python ml/yield_prediction/train.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OrdinalEncoder
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "ml" / "datasets" / "india_crop_production.csv"
MODELS_DIR = ROOT / "models"
CATEGORICAL_FEATURES = ["state", "crop", "season"]
TARGET = "yield"
RANDOM_STATE = 42


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH, index_col=0)

    missing_cols = set(CATEGORICAL_FEATURES + [TARGET]) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Dataset missing expected columns: {missing_cols}")

    before = len(df)
    df = df.dropna(subset=CATEGORICAL_FEATURES + [TARGET])
    # yield <= 0 is a data-entry artifact (failed/unrecorded crop), not a real
    # zero-yield harvest worth training on.
    df = df[df[TARGET] > 0]
    df = df.drop_duplicates()
    after = len(df)
    print(f"Loaded {before} rows, {after} rows after cleaning (dropped {before - after})")
    return df


def build_models() -> dict:
    return {
        "yield_random_forest": RandomForestRegressor(
            n_estimators=200, max_depth=18, random_state=RANDOM_STATE, n_jobs=-1
        ),
        "yield_gradient_boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
        "yield_xgboost": XGBRegressor(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.1,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        # SVR intentionally excluded: O(n^2)-O(n^3) training cost makes it
        # impractical on ~300k rows. Documented in docs/ml-methodology.md.
    }


def evaluate(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    return {
        "r2_score": float(r2_score(y_test, y_pred)),
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
    }


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    df = load_dataset()

    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X = pd.DataFrame(
        encoder.fit_transform(df[CATEGORICAL_FEATURES]),
        columns=CATEGORICAL_FEATURES,
        index=df.index,
    )
    y = df[TARGET].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE
    )
    print(f"Train size: {len(X_train)}, Test size: {len(X_test)}")

    metrics_report = {
        "dataset_source": "India district-level crop production records (state, district, "
        "crop, year, season, area, production, yield), 1997-2020",
        "dataset_records": int(len(df)),
        "features": CATEGORICAL_FEATURES,
        "target": TARGET,
        "target_unit": "tonnes per hectare",
        "test_size": 0.2,
        "random_state": RANDOM_STATE,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "supported_states": sorted(df["state"].unique().tolist()),
        "supported_seasons": sorted(df["season"].unique().tolist()),
        "supported_crops": sorted(df["crop"].unique().tolist()),
        "models": {},
    }

    models = build_models()
    best_name, best_score = None, -np.inf

    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        result = evaluate(model, X_test, y_test)
        print(f"  r2={result['r2_score']:.4f} mae={result['mae']:.4f} rmse={result['rmse']:.4f}")

        if hasattr(model, "feature_importances_"):
            result["feature_importance"] = {
                f: float(imp) for f, imp in zip(CATEGORICAL_FEATURES, model.feature_importances_)
            }

        joblib.dump(model, MODELS_DIR / f"{name}.joblib")
        metrics_report["models"][name] = result

        if result["r2_score"] > best_score:
            best_name, best_score = name, result["r2_score"]

    joblib.dump(encoder, MODELS_DIR / "yield_encoder.joblib")
    metrics_report["active_model"] = best_name
    metrics_report["active_model_r2"] = best_score

    with open(MODELS_DIR / "yield_metrics.json", "w") as f:
        json.dump(metrics_report, f, indent=2)

    print(f"\nBest model: {best_name} (r2={best_score:.4f})")
    print(f"Saved models + yield_metrics.json to {MODELS_DIR}")


if __name__ == "__main__":
    sys.exit(main() or 0)

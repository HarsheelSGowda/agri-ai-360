# ML Methodology

## Pipeline

```
crop_recommendation.csv
    → cleaning (drop null/duplicate rows)
    → feature selection (N, P, K, temperature, humidity, ph, rainfall)
    → label encoding (22 crop classes)
    → stratified 80/20 train/test split (random_state=42)
    → train 4 classifiers
    → evaluate (accuracy, precision, recall, F1, confusion matrix, 5-fold CV)
    → save models + metrics.json
    → FastAPI loads the active model for inference + SHAP for explanation
```

Implementation: [`ml/crop_recommendation/train.py`](../ml/crop_recommendation/train.py).

## Models trained

| Algorithm | Library | Key hyperparameters |
|---|---|---|
| Random Forest | `sklearn.ensemble.RandomForestClassifier` | 300 trees, unlimited depth |
| Gradient Boosting | `sklearn.ensemble.GradientBoostingClassifier` | scikit-learn defaults |
| XGBoost | `xgboost.XGBClassifier` | 300 trees, depth 6, lr 0.1 |
| SVM | `sklearn.svm.SVC` | RBF kernel, `probability=True` |

All four are trained and saved (`models/*.joblib`) so the Model Lab page can show a genuine
comparison. Only one — the **active model** — is used for live `/predict` and `/explain` calls.
The active model is selected automatically as whichever scored highest test accuracy in the most
recent training run (currently Random Forest); this is recorded in `models/metrics.json` under
`active_model`, not hardcoded in the API.

## Evaluation protocol

- **Split**: stratified 80/20, `random_state=42` for reproducibility.
- **Metrics**: accuracy, weighted precision/recall/F1 (`sklearn.metrics`, `zero_division=0`).
- **Cross-validation**: 5-fold `cross_val_score` (accuracy) on the full dataset, reported alongside
  the held-out test metrics as a sanity check against overfitting to one split.
- **Confusion matrix**: computed on the held-out test set for every model, stored per-algorithm in
  `metrics.json`, rendered for the active model on the Model Lab page.
- **Feature importance**: `model.feature_importances_` for the tree-based models, shown on the
  Model Lab page for whichever model is active.

## Why these results are trustworthy (not fabricated)

- `train.py` is a standalone, runnable script with no hardcoded output — anyone can re-run
  `python ml/crop_recommendation/train.py` and get the same (or very similar, given the fixed
  random seed) numbers.
- The FastAPI layer (`app/services/ml_service.py`) never invents a probability: it calls
  `model.predict_proba()` on the actual loaded `.joblib` model for the actual submitted input.
- If `models/metrics.json` or a `.joblib` file is missing, the API returns
  `503 Service Unavailable` / "Not evaluated yet" in the UI rather than fabricating a number.

## Confidence labeling

`HIGH` ≥ 0.60, `MEDIUM` ≥ 0.30, else `LOW` — applied to the raw `predict_proba` output
(`app/services/ml_service.py::confidence_label`). This is a UI presentation threshold, not a
statement about real-world crop success probability (the UI surfaces this caveat as a tooltip).

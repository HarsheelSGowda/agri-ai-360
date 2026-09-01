# Explainable AI (XAI)

## Method

`POST /api/explain/crop` (`app/services/ml_service.py::explain_prediction`) uses
**`shap.TreeExplainer`** against the active tree-based model (Random Forest, Gradient Boosting or
XGBoost — SVM is excluded since `TreeExplainer` doesn't apply to it, and the endpoint returns a
clear `503` if the active model isn't tree-based).

For the requested crop class:

1. Build the single-row feature vector from the submitted input (same 7 features as training).
2. Run `TreeExplainer(model).shap_values(X)` to get a real per-feature SHAP value for that specific
   class prediction.
3. Sort contributions by absolute magnitude (largest influence first).
4. `base_value + sum(contributions) ≈ predicted_value` (the model's probability for that class) —
   this identity is what SHAP guarantees, and is used to double-check the response is coherent
   rather than corrupted.

## UI presentation

- **Research mode** (Model Lab, recommendation detail): a horizontal bar chart
  (`src/charts/SHAPChart.tsx`, built with Recharts) showing signed contribution per feature —
  green for positive (pushed the prediction toward this crop), red for negative.
- **Farmer mode**: a generated sentence (`_build_narrative` in `ml_service.py`) built directly from
  the same contribution list — e.g. *"Rice received a strong recommendation mainly because current
  rainfall, nitrogen levels, humidity are favorable for this crop."* This text is templated around
  the actual top-contributing features for that specific request, not a static string.

Every SHAP chart and narrative in the UI carries a "Powered by Explainable AI" label so it's never
confused with a marketing claim.

## Why this satisfies the "no fabricated explanation" rule

- The contribution numbers are the literal SHAP library output, not hand-tuned.
- The narrative sentence's feature list is derived from `sorted(contributions, key=abs)`, so if
  the model's reasoning changes (different input → different top features), the sentence changes
  with it — it cannot describe a feature the model didn't actually weight highly.

## Known limitation

SHAP's TreeExplainer runs synchronously per request (no caching). For the current 22-class, 7-feature,
few-hundred-tree model this completes in well under a second; it would need batching/caching if the
model or feature count grew substantially.

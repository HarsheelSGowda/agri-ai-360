# Future Scope

Mirrors the in-app **AI Roadmap** page (`/app/roadmap`).

## Phase 1 — Current (this build)
✅ Crop Recommendation · ✅ Soil Intelligence · ✅ Weather Intelligence · ✅ Explainable AI (SHAP) ·
✅ Farmer Dashboard · ✅ Model Comparison · ✅ Risk Summary (rule-based) · ✅ History · ✅ What-If AI

## Phase 2
- ✅ **Yield Prediction** — real XGBoost regressor (R²=0.919) trained on 325k India district-level
  crop production records (1997–2020), predicting expected yield (t/ha) from state, crop and
  season. Live at `POST /predict/yield`, surfaced on the crop recommendation detail page. Covers
  11 of the 22 recommendation-engine crops (see `docs/dataset.md` for the full crop mapping and
  its limitations — it's a regional-historical estimate, not a per-farm forecast).
- ✅ **Profit Prediction** — `Revenue - Cost`, where Revenue = the real yield estimate above ×
  real 2016 Agmarknet mandi price data (median per crop+state), and Cost is farmer-supplied (no
  honest per-farm cost dataset was found — see `docs/dataset.md`). Live at `POST /predict/profit`,
  surfaced right under the yield estimate on the recommendation detail page. Covers 6 crops (the
  intersection of yield-supported crops and price-supported crops).
- **Water Requirement** — crop-water-need estimation, combined with the existing water-risk signal.
- **Risk Prediction (ML-based)** — replace/augment the current rule-based `risk_service.py` with a
  trained model once labeled risk/outcome data is available.

## Phase 3
- **Disease Detection** — CNN-based leaf image classifier. UI shell exists (`AI Crop Doctor` page,
  upload disabled, explicitly labeled "Coming in Phase 2"). Reserved directory:
  `ml/disease_detection/`.
- **AI Agriculture Assistant** — LLM/RAG-backed chat grounded in the farmer's own farm data.
  UI shell exists (`chat_sessions`/`chat_messages` tables already in the schema); currently shows
  static example messages only, explicitly labeled "Development Preview."
- **Voice Assistant** — speech-to-text → AI → text-to-speech, once the AI Assistant's backend
  exists to speak to.
- **Multilingual AI** — the `preferred_language` field is already captured at registration and
  ready to drive UI/response localization.

## Phase 4
- **Satellite Monitoring / NDVI** — remote-sensing vegetation health overlays on the farm map.
- **IoT Sensor Integration** — real-time soil sensor feeds replacing manual soil form entry.

## What "architecture in place" means concretely

- Reserved ML subdirectories (`ml/yield_prediction/`, `ml/disease_detection/`) exist but are
  empty — no placeholder code pretending to be a trained model.
- Reserved DB tables (`alerts`, `model_versions` beyond the current file-based usage,
  `chat_sessions`, `chat_messages`) already exist in the schema.
- `WeatherProvider` is an interface specifically so a real weather API becomes a second
  implementation, not a rewrite (see `docs/architecture.md`).
- Every "coming soon" surface in the UI (`Crop Doctor`, `AI Assistant`) is visually complete but
  functionally inert and explicitly labeled, per the "don't fake it" project rule.

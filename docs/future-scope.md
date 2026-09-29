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
- ✅ **Water Requirement** — FAO Blaney-Criddle reference evapotranspiration (real, published
  formula + tables, fetched and parsed directly from the primary FAO sources) × FAO-56 crop
  coefficients, minus USDA SCS effective rainfall. Live at `POST /predict/water`, surfaced on the
  recommendation detail page alongside yield and profit. Covers 17 of 22 crops (13 crop-specific +
  4 generic-legume FAO-56 category values); see `docs/dataset.md` for exactly which and a
  documented case where a self-derived approximation was caught and replaced with the real source
  table after producing a ~3.7x-too-high result.
- ✅ **Risk Prediction (ML-based)** — a real trained classifier (Random Forest, 55.3% test accuracy
  on years unseen during training, 3-class baseline 33.3%) predicting a LOW/MEDIUM/HIGH tier from
  the same yield dataset, reused with a purpose-built per-crop-tertile label. Live at
  `POST /predict/yield-risk`, surfaced alongside yield/profit on the recommendation detail page.
  Augments — does not replace — the existing rule-based weather/soil/water/disease risk dashboard,
  which uses live signals this model doesn't have access to. See `docs/dataset.md` for a documented
  case where a random train/test split gave a misleadingly high 64.5% accuracy that a proper
  cross-validation (36.9%) caught, fixed with a temporal split, and cross-checked against known
  regional agronomy (Punjab rice correctly predicted low-risk) before shipping.

## Phase 3
- ✅ **Disease Detection** — real, trained image classifier ("AI Crop Doctor"). A leaf photo is run
  through MobileNetV3-Small (ImageNet-pretrained, frozen feature extraction) into a trained
  Logistic Regression classifier (97.9% test accuracy, chosen over Random Forest and Gradient
  Boosting by real comparison — see `docs/ml-methodology.md` Part 6), identifying crop + disease/
  healthy condition with a confidence score. Live at `GET /predict/disease/options` and
  `POST /predict/disease`, surfaced on the `AI Crop Doctor` page. Covers 13 classes across 4 crops
  (apple, maize, grapes, orange) — see `docs/dataset.md` for the full class list and why coverage
  is limited to these crops.
- ✅ **Fertilizer Advisor** — rule-based nutrient-deficiency check reusing the exact soil-health
  reference bands from `soil_health.py` (single source of truth), plus organic-carbon guidance and
  growth-stage application timing. Live at `POST /api/fertilizer/recommend`. Intentionally never
  outputs a kg/acre dosage — that depends on a certified local soil test, crop variety and regional
  package-of-practices this system doesn't have access to; every response carries that disclaimer.
- ✅ **Market Price Intelligence** — current price, trend and market comparison from real 2016
  Agmarknet mandi records (see `docs/dataset.md`), behind a swappable `MarketPriceProvider` (mirrors
  `WeatherProvider`) so a live API can replace it later without touching the service/frontend. Live
  at `GET /api/market-prices*`, surfaced on the Market Prices page.
- ✅ **Personalized Farmer Notifications** — `notification_service.generate_for_farm()` derives
  alerts from each farm's real current soil health, weather, risk, disease diagnosis and
  market-price trend — never invented content, deduplicated per farmer. Live at
  `POST /api/notifications/generate` (and `GET /api/notifications`), surfaced via the notification
  bell + Notifications page.
- ✅ **AI Agriculture Assistant** — a real, working chat grounded in the farmer's own farm data
  (soil health, weather, risk, disease, fertilizer, market price, and the crop recommendation's
  SHAP explanation regenerated live via `explain_prediction()`). No LLM/RAG API is configured for
  this project (no `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` etc. in `.env.example`), so per the
  no-fabrication rule it's built and explicitly labeled as a **rule-based, keyword-classified
  Q&A engine** — not an LLM. It answers only the intents it recognizes (crop recommendation
  reasoning, soil health, risk, irrigation, fertilizer, disease, market price, weather) from data
  that module already computes, and says "I couldn't match that" rather than inventing an answer.
  Live at `POST /api/assistant/ask`, using the `chat_sessions`/`chat_messages` tables. If a real
  LLM/RAG API is added later, `assistant_service.answer_question()` is the single call site to
  swap — the router and DB schema don't need to change.
- **Voice Assistant** — speech-to-text → AI → text-to-speech, layered on top of the assistant above
  once a real LLM backend replaces (or augments) the rule-based one.
- **Multilingual AI** — the `preferred_language` field is already captured at registration and
  ready to drive UI/response localization.

## Phase 4 — Real-Time Agri Intelligence architecture
- ✅ **Satellite Monitoring / NDVI — planned/integration-ready architecture.** No satellite data
  provider is configured (`SATELLITE_API_KEY`/`SATELLITE_PROVIDER` both empty by default). Live at
  `GET /api/satellite/status`, always returns `status: "PLANNED"` and documents the intended
  metrics (NDVI, vegetation health, crop stress, field boundary monitoring) — never a fabricated
  reading. Connecting a real provider (Sentinel Hub/Copernicus, Google Earth Engine, Planet) is a
  new `SatelliteProvider` implementation behind this same endpoint, mirroring `WeatherProvider`.
- ✅ **IoT Sensor Integration — real ingestion path + demo data, no hardware yet.** Architecture:
  Sensor → API/MQTT gateway → Backend → Database (`sensor_readings`) → Dashboard. Two things are
  genuinely real today, not simulated: `POST /api/iot/readings` (any physical gateway/device could
  push a real reading to this endpoint right now) and `GET /api/iot/readings` (reads whatever rows
  actually exist). Because no physical sensor is connected to this deployment, `POST
  /api/iot/demo/seed` generates one demo reading per sensor type (soil moisture, temperature,
  humidity, EC) tagged `source: "demo_simulation"` — never mixed with or presented as real device
  data. Surfaced on the Real-Time Intelligence page alongside Weather and Satellite.

## What "architecture in place" means concretely

- Reserved DB tables (`alerts`, `model_versions` beyond the current file-based usage) still await a
  consumer; `chat_sessions`/`chat_messages` are now actively used by the real AI Assistant above.
- `WeatherProvider` / `MarketPriceProvider` are interfaces specifically so a real weather or
  market-data API becomes a second implementation, not a rewrite (see `docs/architecture.md`).
  `SatelliteProvider` follows the same pattern once a real provider is implemented.
- The AI Assistant, Satellite status and IoT readings are all real, working code paths today — none
  of them are UI-only shells — but each is explicitly labeled for what it actually is (rule-based,
  not LLM; planned, not live; demo, not a real sensor), per the "don't fake it" project rule.

# API Reference

Base URL: `http://localhost:8000/api` (proxied through the frontend dev server at `/api`).
Interactive docs: `http://localhost:8000/docs` (FastAPI auto-generated Swagger UI).

All endpoints except `/auth/register` and `/auth/login` require `Authorization: Bearer <token>`.

## Auth

### `POST /auth/register`
```json
{ "name": "Ramesh Patil", "email": "ramesh@farm.com", "password": "secret123",
  "location": "Nagpur, Maharashtra", "preferred_language": "English" }
```
→ `201` `{ access_token, token_type, user }`. `409` if the email already exists.

### `POST /auth/login`
```json
{ "email": "ramesh@farm.com", "password": "secret123" }
```
→ `200` `{ access_token, token_type, user }`. `401` on bad credentials.

## Farms

- `POST /farms` — `{ name, location, area_acres, soil_type, irrigation_available }` → `201` Farm.
- `GET /farms` — list the current farmer's farms.
- `GET /farms/{id}` — `404` if not owned by the current farmer.
- `POST /farms/{id}/soil` — `{ nitrogen, phosphorus, potassium, ph, soil_type, organic_carbon?,
  moisture?, electrical_conductivity? }` → `201` soil record + computed `health` (score,
  per-nutrient breakdown, generated insights).
- `GET /farms/{id}/soil` — latest soil record + health, or `null` if none submitted yet.

## Weather

- `GET /weather?location=...` → `{ temperature_c, humidity_pct, rainfall_mm, wind_kmh, condition,
  forecast: [...], source: "mock" | "live" }`. `source` is always present so the UI can label mock
  vs. live data honestly.
- Provider is selected by `WEATHER_PROVIDER` in `.env`: `"mock"` (default) — deterministic,
  seeded-by-location demo data, no network call. `"open-meteo"` — real current conditions + 5-day
  forecast from the free open-meteo.com API (geocodes `location` to lat/lon, then fetches
  live data; no API key required). If the live call fails for any reason (network, an
  unrecognized location, a malformed response), the request transparently falls back to the mock
  provider — `source: "mock"` — rather than returning a `5xx` error. See
  `backend/app/services/weather_provider.py`.

## Prediction

- `POST /predict/top-crops` (alias `POST /predict/crop`) —
  `{ nitrogen, phosphorus, potassium, temperature, humidity, ph, rainfall, farm_id? }` →
  `{ top_crops: [{ crop, probability, confidence }] (top 5), model_used, model_version, input }`.
  If `farm_id` is supplied and owned by the caller, the prediction + top-5 breakdown is persisted
  to `crop_predictions` / `crop_scores` for the History page. `503` if no trained model is found.

- `POST /explain/crop` — same body as above plus `{ "crop": "rice" }` →
  `{ crop, contributions: [{ feature, value, contribution }], base_value, predicted_value,
  narrative, method: "shap" }`. `400` for an unknown crop name, `503` if the active model isn't a
  tree-based model SHAP's `TreeExplainer` supports.

## Yield Prediction (Phase 2)

- `GET /predict/yield/options` → `{ states: [...37], seasons: [...6], supported_crops: [...11,
  recommendation-engine names], dataset_records, active_model, active_model_r2 }`. Drives the
  frontend's state/season dropdowns and which crops show a yield estimator at all.

- `POST /predict/yield` — `{ crop, state, season, farm_id? }` →
  `{ supported: bool, crop, mapped_crop, state, season, predicted_yield_tonnes_per_ha,
  predicted_yield_quintal_per_acre, model_used, r2_score, mae, reason }`. When `crop` isn't one of
  the 11 mapped crops, or `state`/`season` isn't in the training data, `supported` is `false` and
  `reason` explains why — the prediction fields are `null` rather than a guess. `503` if the yield
  model hasn't been trained (`ml/yield_prediction/train.py` hasn't been run).

## Profit Prediction (Phase 2)

- `GET /predict/profit/options` → `{ supported_crops: [...6], price_year: "2016" }`.

- `POST /predict/profit` — `{ crop, state, season, cost_per_acre, area_acres?, farm_id? }` →
  `{ supported: bool, crop, mapped_crop, state, season, yield_tonnes_per_ha, price_rs_per_quintal,
  price_source: "state" | "national_fallback", cost_per_acre, revenue_per_acre, profit_per_acre,
  revenue_per_ha, profit_per_ha, margin_pct, total_farm_profit, reason }`. Internally calls the
  yield model, then looks up a real 2016 Agmarknet median price and computes
  `Revenue - farmer-supplied Cost`. `total_farm_profit` is `null` unless `area_acres` is supplied.
  `supported` is `false` (with `reason`) if the crop isn't one of the 6 with price data, or if the
  underlying yield estimate itself isn't supported. `422` for a negative `cost_per_acre`. `503` if
  `ml/profit_prediction/build_price_reference.py` hasn't been run yet.

## Water Requirement (Phase 2)

- `GET /predict/water/options` → `{ supported_crops: [...17], states: [...37] }`.

- `POST /predict/water` — `{ crop, state, temperature_c, rainfall_mm, date?, area_acres?, farm_id? }`
  → `{ supported: bool, crop, kc_mid, kc_category: "specific" | "generic_legume", kc_source_row,
  kc_note, state, latitude_deg, month, p_value, reference_et0_mm_per_day, crop_water_use_mm_per_day,
  effective_rainfall_mm_per_day, net_irrigation_mm_per_day, net_irrigation_liters_per_acre_per_day,
  net_irrigation_liters_total_per_day, reason }`. `date` defaults to today (only the month is used,
  matching the FAO p-table's monthly granularity). Computes reference ET₀ via the FAO
  Blaney-Criddle formula, multiplies by the crop's FAO-56 Kc_mid, and subtracts effective rainfall
  (USDA SCS formula) — see `docs/ml-methodology.md` for the exact formula chain. `supported` is
  `false` (with `reason`) for a crop without Kc data or an unrecognized state. `503` if
  `ml/water_requirement/build_kc_reference.py` / `build_p_reference.py` haven't been run yet.

## Yield Risk (Phase 2, ML-based)

- `GET /predict/yield-risk/options` → `{ supported_crops: [...11], active_model, active_model_accuracy,
  dataset_records }`.

- `POST /predict/yield-risk` — `{ crop, state, season, farm_id? }` →
  `{ supported: bool, crop, mapped_crop, state, season, risk_level: "LOW" | "MEDIUM" | "HIGH",
  probabilities: { LOW, MEDIUM, HIGH }, model_used, model_accuracy, reason }`. A trained classifier
  (Random Forest, 55.3% test accuracy on years unseen during training) predicting which tertile a
  crop's yield in that state/season has historically fallen into nationally — a regional historical
  performance tier, **not** a forecast of this year's weather or disease risk (see
  `docs/ml-methodology.md`). Distinct from `GET /risk` (rule-based, live weather/soil signals) —
  both exist, neither replaces the other. `supported` is `false` (with `reason`) for a crop outside
  the 11 covered. `503` if `ml/risk_prediction/train.py` hasn't been run yet.

## Disease Detection (Phase 3)

- `GET /predict/disease/options` → `{ supported_crops: [...4], classes: [...13], active_model,
  active_model_accuracy, dataset_records }`.

- `POST /predict/disease` — multipart form upload, field name `image` (JPEG/PNG/WebP, max 8 MB) →
  `{ top_prediction: { crop, condition, is_healthy, probability }, alternatives: [...top 2 more],
  model_used, model_accuracy, supported_crops }`. Runs the uploaded leaf photo through a frozen
  MobileNetV3-Small feature extractor + a trained classifier (Logistic Regression, 97.9% test
  accuracy) to identify crop + disease/healthy condition. Covers 13 classes across 4 crops (apple,
  maize, grapes, orange) — see `docs/dataset.md` for why. `400` for a non-image upload, an
  unreadable file, or an unsupported content-type; `503` if `ml/disease_detection/train.py` hasn't
  been run yet.

## Disease History

- `GET /history/disease?farm_id=` (optional filter) → list of past disease diagnoses saved to a
  farm's history (only written when `POST /predict/disease` was called with a `farm_id`), newest
  first (max 100).

## Fertilizer Advisor

- `GET /fertilizer/options` → `{ growth_stages: [...] }`.

- `POST /fertilizer/recommend` — `{ crop, nitrogen, phosphorus, potassium, ph, growth_stage,
  organic_carbon?, moisture?, farm_area_acres? }` → `{ crop, growth_stage, farm_area_acres,
  deficiencies: [{ nutrient, current_value, optimal_range, status: "DEFICIENT"|"ADEQUATE"|"EXCESS",
  recommended_category }], organic_matter_guidance, application_timing, warnings, disclaimer }`.
  Rule-based decision support (reuses the same reference bands as the soil health score) — never
  outputs a kg/acre dosage; always carries an explicit disclaimer to validate against a certified
  local soil test.

## Market Price Intelligence

- `GET /market-prices/crops` → crops covered by the seeded Agmarknet dataset.
- `GET /market-prices/states?crop=` → states with data for that crop.
- `GET /market-prices?crop=&state=&district=&market=&variety=` → `{ found, crop, state, district,
  market, variety, as_of_date, min_price, max_price, modal_price, markets_reporting, source,
  is_live }`. `found: false` (with a human-readable reason) if no matching rows exist.
- `GET /market-prices/trend?crop=&state=&days=` → `{ found, points: [{ date, min_price, max_price,
  modal_price }], trend_direction: "UP"|"DOWN"|"FLAT", change_pct, source, is_live }`.
- `GET /market-prices/comparison?crop=&state=` → per-market breakdown + `best_market`.

All responses carry `source` and `is_live: false` — this is real but **historical** (2016
Agmarknet) reference data, not a live feed. See `docs/dataset.md`.

## Personalized Notifications

- `GET /notifications?unread_only=&farm_id=` → list of notifications, newest first (max 100).
- `POST /notifications/generate?farm_id=` → runs `generate_for_farm()` against that farm's *current*
  soil health, weather, risk, disease and market-price-trend data and inserts any new (deduplicated)
  alerts → `{ created, notifications }`.
- `PATCH /notifications/{id}/read` → marks one notification read.
- `PATCH /notifications/read-all` → marks all of the farmer's notifications read → `{ updated }`.

## AI Agriculture Assistant

Rule-based, **not** an LLM — see `docs/future-scope.md` for why. Grounded entirely in each farm's
real, already-computed data; never invents an answer it doesn't have.

- `POST /assistant/ask` — `{ message, farm_id? }` → `{ session_id, reply: { role, content,
  created_at }, used_data, suggested_questions }`. `used_data` lists which real data sources the
  answer drew on (e.g. `"Latest crop recommendation"`, `"SHAP explanation"`) — empty if the
  question couldn't be grounded (e.g. no farm selected, or the underlying data doesn't exist yet).
  Persists both the farmer's message and the reply to the farmer's chat session.
- `GET /assistant/messages` → `{ session_id, messages }` for the farmer's most recent session (or
  `{ session_id: null, messages: [] }` if none yet).
- `POST /assistant/reset` → starts a fresh, empty session.

## Real-Time Agri Intelligence — Satellite

- `GET /satellite/status?farm_id=` → `{ status: "PLANNED", configured, location, planned_metrics:
  [{ key, label, description }], message }`. No satellite/NDVI provider is configured — this always
  reports `PLANNED` and never returns a fabricated vegetation-health reading. See
  `docs/future-scope.md`.

## Real-Time Agri Intelligence — IoT

- `GET /iot/readings?farm_id=` → `{ farm_id, readings: [{ id, farm_id, sensor_type, value, unit,
  source, recorded_at }], has_real_device_data }`. `source` is `"device"` for a real reading a
  gateway pushed, or `"demo_simulation"` for a generated demo row — `has_real_device_data` is
  `true` only if at least one real device row exists.
- `POST /iot/readings` — `{ farm_id, sensor_type: "soil_moisture"|"temperature"|"humidity"|"ec",
  value, unit? }` → `201` with the created reading (`source: "device"`). A real ingestion endpoint
  any physical sensor gateway (e.g. an MQTT bridge) can call today. `400` for an unknown
  `sensor_type`.
- `POST /iot/demo/seed?farm_id=` → generates one demo reading per sensor type (tagged
  `source: "demo_simulation"`) and returns the updated reading list. Used because no physical
  sensor is connected to this deployment yet — never presented as live sensor data.

## Models

- `GET /models` — trained model names + active model.
- `GET /models/performance` — full comparison table (`accuracy/precision/recall/F1` or
  `"status": "not_evaluated"` per algorithm), dataset provenance, feature importance and confusion
  matrix for the active model.

## History

- `GET /history?farm_id=` (optional filter) → list of past predictions with farm name, crop,
  score, soil/weather summary strings, newest first (max 100).

## Risk

- `GET /risk?farm_id=` → `{ overall, weather_risk, soil_risk, water_risk, disease_risk, notes,
  is_prototype: true }`. Always rule-based and always flagged `is_prototype`.

## Dashboard

- `GET /dashboard/{farm_id}` → combined `{ farm, soil_health, weather, farm_health, risk }` for the
  main dashboard view — one call instead of four.

## Health

- `GET /health` → `{ status: "ok", service: "agri-ai-360-backend" }` (no auth required).

## Error format

Validation errors: `422` with `{ "detail": [...] }` (FastAPI/Pydantic default shape). All other
handled errors: `{ "detail": "human-readable message" }` with the matching HTTP status
(`401`, `403`, `404`, `409`, `503`).

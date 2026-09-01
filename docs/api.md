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
  data honestly.

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

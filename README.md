# 🚜 AgriAI 360

**An Explainable AI-Powered Intelligent Crop Recommendation and Farm Decision Support System**

Final-year Computer Science and Engineering major project.

> **Status: MVP + Phase 2 + Disease Detection (Phase 3, part 1) complete.** Crop recommendation,
> soil intelligence, weather, explainable AI (SHAP), model comparison, risk summary, history, the
> What-If simulator, yield prediction, profit estimation, water requirement, ML-based yield risk,
> and now AI-powered disease detection ("Crop Doctor") are all real and working end to end. The AI
> assistant, voice, multilingual support, and satellite/IoT (rest of Phase 3/4) are intentionally
> **not implemented** — see [Future Scope](docs/future-scope.md) and the in-app AI Roadmap page.
> Nothing in this build fabricates a metric or a prediction: every number shown comes from a
> trained model, real historical data, a published scientific formula, a documented rule-based
> calculation, or is explicitly labeled as a mock/prototype/farmer-supplied input.

---

## Problem Statement

Traditional crop selection depends on farmer experience, guesswork, limited soil knowledge and
unpredictable weather. AgriAI 360 combines soil, weather and machine learning into a single,
explainable decision-support platform, so a farmer sees not just *what* to plant, but *why*.

## Objectives

1. Predict the most suitable crop(s) for a farm from soil (N, P, K, pH) and weather (temperature,
   humidity, rainfall) data using a trained classification model.
2. Make every recommendation explainable (SHAP feature-contribution analysis), not a black box.
3. Provide a transparent, reproducible model comparison (Random Forest, Gradient Boosting,
   XGBoost, SVM) with real accuracy/precision/recall/F1 — never fabricated numbers.
4. Give a rule-based, clearly-labeled soil health score and farm risk summary.
5. Architect the system so further modules (disease detection, an LLM assistant, voice,
   satellite/IoT) can be added without rewriting the core — yield and profit prediction shipped in
   Phase 2 using exactly this extensibility.

## Features (this build)

- Landing page, JWT authentication (register/login/forgot-password UI), protected app shell.
- Farmer dashboard: soil health, weather, farm health, risk — all real, farm-specific data.
- Farm creation, soil analysis form with a threshold-based soil health score + generated insights.
- Weather intelligence via a swappable `WeatherProvider` — mock provider by default (clearly
  labeled), or real **live weather + 5-day forecast** via the free open-meteo.com API
  (`WEATHER_PROVIDER=open-meteo`, no key required), with an automatic, honest fallback to mock data
  if the live API is unreachable.
- Crop recommendation engine: real Random Forest model (99.3% test accuracy), Top-5 ranking with
  actual model probabilities and HIGH/MEDIUM/LOW confidence.
- "Why this crop?" detail page with real SHAP feature-contribution chart + a generated natural
  language explanation (not templated).
- Model Lab / Research Center: real comparison of 4 trained algorithms, feature importance,
  confusion matrix, dataset provenance.
- Rule-based, explicitly-labeled-as-prototype risk dashboard (weather/soil/water/disease risk).
- Recommendation history persisted per farm.
- **What-If AI**: change inputs, re-run the real model, see a before/after ranking change.
- **Yield Prediction** (Phase 2): real XGBoost regressor (R²=0.919) trained on 325k India
  district-level crop production records, estimating expected yield (t/ha) from state, crop and
  season — shown on the recommendation detail page for the 11 crops it has real training data for;
  honestly reports "not available" for the rest rather than guessing.
- **Profit Prediction** (Phase 2): Revenue (real yield estimate × real 2016 Agmarknet mandi price)
  minus a farmer-supplied cost estimate — 6 crops, right under the yield estimate. No invented
  cost-of-cultivation numbers; see Limitations for why.
- **Water Requirement** (Phase 2): real FAO Blaney-Criddle reference evapotranspiration × FAO-56
  crop coefficients − USDA effective rainfall = net irrigation need (mm/day and liters/day/acre) —
  17 crops, right under the profit estimate. Formulas and reference tables fetched and parsed
  directly from the primary FAO documents, not recalled from memory.
- **Yield Risk** (Phase 2, ML-based): a trained classifier (Random Forest, 55.3% test accuracy on
  years unseen during training) predicting a LOW/MEDIUM/HIGH tier for how a crop has historically
  performed nationally in a given state/season — 11 crops, right under the yield estimate. Augments
  (doesn't replace) the existing rule-based risk dashboard; see Limitations for the distinction.
- **Disease Detection / "AI Crop Doctor"** (Phase 3): upload a leaf photo, get a real diagnosis —
  MobileNetV3-Small (ImageNet-pretrained, frozen) feature extraction + a trained Logistic
  Regression classifier (97.9% test accuracy) identifies crop + disease/healthy condition with a
  confidence score and alternatives, plus rule-based care guidance (severity, recommended actions,
  prevention) and diagnosis history per farm. Covers 13 classes across 4 crops (apple, maize,
  grapes, orange); low-confidence results are flagged, and unsupported crops are honestly reported.
- **Fertilizer Advisor**: rule-based nutrient-deficiency check (N/P/K/pH/organic carbon/moisture
  against the same reference bands as the soil health score) with growth-stage application timing
  and an explicit disclaimer that it's decision support, not a calibrated dosage prescription.
- **Market Price Intelligence**: current price, historical trend chart and market comparison from
  real 2016 Agmarknet (Government of India mandi) records — clearly labeled historical/reference
  data, never presented as a live feed. Architected behind a swappable `MarketPriceProvider` so a
  real live API can be connected later without touching the service or frontend.
- **Personalized Notifications**: a notification center generating alerts from each farm's actual
  current soil health, weather, risk, disease and market-price-trend data (no invented content),
  with severity, category, read/unread state and per-farmer deduplication.
- **AI Agriculture Assistant**: a real, working rule-based Q&A chat grounded in the farmer's own
  farm data (soil health, weather, risk, disease, fertilizer, market price, and the crop
  recommendation's SHAP explanation regenerated live). No LLM/RAG API is configured for this
  project, so — per this project's no-fabrication rule — it's built and explicitly labeled as a
  deterministic keyword-classified engine, not a language model; it says so when the underlying
  data doesn't exist yet rather than guessing. Chat history persists per farmer (`chat_sessions`/
  `chat_messages`).
- **Real-Time Agri Intelligence** page: Weather (mock by default, or real live weather via
  open-meteo.com when `WEATHER_PROVIDER=open-meteo` is set) plus two new integration-ready
  architectures — Satellite/NDVI monitoring (explicitly labeled "Planned / Integration-Ready",
  documents the intended metrics, never fakes a reading) and an IoT sensor
  layer (Sensor → API/MQTT gateway → Backend → Database → Dashboard) with a real ingestion endpoint
  (`POST /api/iot/readings`) any physical gateway can call today, plus a clearly-labeled
  "Demo/Simulation" reading generator for when no sensor is connected yet.
- AI Roadmap page showing what's implemented vs. planned.

## Architecture

```
Browser (React + Vite + TS + Tailwind)
        │  JWT bearer token
        ▼
FastAPI backend  ──────────────►  models/*.joblib  (Random Forest, GB, XGBoost, SVM)
        │                                │
        ▼                                ▼
  PostgreSQL / SQLite            SHAP TreeExplainer (real-time explanation)
  (SQLAlchemy ORM)
```

See [docs/architecture.md](docs/architecture.md) for the full breakdown.

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS v4, Lucide icons, Recharts, Zustand, React Router |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2.0 |
| Database | PostgreSQL (production) / SQLite (zero-setup local dev — same SQLAlchemy models) |
| ML | pandas, NumPy, scikit-learn, XGBoost |
| Computer Vision | PyTorch, torchvision (MobileNetV3-Small, ImageNet-pretrained) |
| Explainable AI | SHAP |
| Auth | JWT (python-jose) + bcrypt |

## Dataset

Five independent public data sources (one reused twice) across the six modules — full provenance
and limitations in [docs/dataset.md](docs/dataset.md):

- **Crop Recommendation Dataset** — 2,200 records, 22 crop classes, 7 numeric features
  (N, P, K, temperature, humidity, ph, rainfall → crop label). Originally published on Kaggle by
  Atharva Ingle.
- **India Crop Production records** — 325k district-level rows (state, crop, season, year → yield),
  1997–2020, sourced from a public mirror of India's crop-production statistics. Used for Phase 2
  yield prediction **and** (with a purpose-built tertile label) yield risk prediction.
- **Agmarknet mandi price records** — real 2016 Indian government market-price transactions for 6
  crops, aggregated to a median-price-per-(crop, state) reference table. Used for Phase 2 profit
  prediction (revenue side only — cost is farmer-supplied, see Limitations).
- **FAO Irrigation & Drainage Paper 56 + FAO Crop Water Needs manual** — official published crop
  coefficients (Table 12) and reference-evapotranspiration daylight tables (Table 4), fetched and
  parsed directly from fao.org, not recalled from memory. Used for Phase 2 water requirement.
- **PlantVillage-Dataset** — 3,875 sampled real leaf images (13 classes: apple, maize, grapes,
  orange — healthy + disease conditions), from the canonical public leaf-disease image dataset
  (spMohanty/PlantVillage-Dataset on GitHub, released alongside Mohanty, Hughes & Salathe 2016).
  Used for Phase 3 disease detection.

## ML Methodology

Full methodology for all modules: [docs/ml-methodology.md](docs/ml-methodology.md).

**Crop Recommendation** — four classifiers trained on an 80/20 stratified split
([ml/crop_recommendation/train.py](ml/crop_recommendation/train.py)), evaluated with accuracy,
precision, recall, F1 and 5-fold CV. **Random Forest is the active model** (highest test accuracy).

| Algorithm | Accuracy | Precision | Recall | F1 |
|---|--:|--:|--:|--:|
| Random Forest | 99.32% | 99.35% | 99.32% | 99.32% |
| Gradient Boosting | 98.86% | 98.97% | 98.86% | 98.87% |
| XGBoost | 98.64% | 98.74% | 98.64% | 98.62% |
| SVM | 98.41% | 98.66% | 98.41% | 98.39% |

**Yield Prediction (Phase 2)** — three regressors trained on an 80/20 split
([ml/yield_prediction/train.py](ml/yield_prediction/train.py)), evaluated with R², MAE, RMSE.
**XGBoost is the active model.**

| Algorithm | R² | MAE (t/ha) | RMSE (t/ha) |
|---|--:|--:|--:|
| XGBoost | 0.919 | 1.03 | 3.51 |
| Random Forest | 0.919 | 1.03 | 3.51 |
| Gradient Boosting | 0.793 | 2.09 | 5.63 |

**Profit Prediction (Phase 2)** is not a trained model — it's `Revenue - Cost`, where Revenue =
the real yield estimate above × a real 2016 Agmarknet median mandi price
([ml/profit_prediction/build_price_reference.py](ml/profit_prediction/build_price_reference.py)),
and Cost is farmer-supplied (see Limitations for why no cost dataset was used). Covers the 6-crop
intersection of yield-supported and price-supported crops.

**Water Requirement (Phase 2)** is also not a trained model — it's the real, published FAO
Blaney-Criddle formula (`ETo = p × (0.46 × Tmean + 8)`, p from FAO's own Table 4) × FAO-56's Kc_mid
crop coefficient, minus USDA effective rainfall. An earlier version tried to derive `p` from solar
day-length instead of using FAO's table, and that produced a reference ET₀ ~3.7× too high (22.8 vs.
the real ~6.2 mm/day) for a real test case — caught, documented, and replaced with the actual
source table. See [docs/ml-methodology.md](docs/ml-methodology.md) Part 4 for the full account.
Covers 17 of 22 crops.

**Yield Risk (Phase 2)** is a real trained classifier (Random Forest, 3 algorithms compared) on
the *same* dataset as yield prediction, with a per-crop-tertile label engineered from that crop's
own historical yield distribution. **Test accuracy: 55.3%** on 2016–2020 (years the model never
saw during training; 3-class baseline is 33.3%). A first attempt used a random train/test split and
reported a flattering 64.5% — a proper cross-validation on the same data came back at only 36.9%,
exposing that the split let near-duplicate (state, crop, season) rows from different years leak
across train/test. Fixed with a temporal split; the model's predictions were then spot-checked
against known agronomy (Punjab correctly predicted low-risk for rice — India's best-known
high-yield rice state). Full account: [docs/ml-methodology.md](docs/ml-methodology.md) Part 5.
Covers 11 of 22 crops. Augments, does not replace, the rule-based risk dashboard.

**Disease Detection (Phase 3)** — three classifiers trained on MobileNetV3-Small (ImageNet-
pretrained, frozen) feature vectors extracted from real leaf images, an 80/20 stratified split
([ml/disease_detection/train.py](ml/disease_detection/train.py)). **Logistic Regression is the
active model.**

| Algorithm | Accuracy | Precision | Recall | F1 |
|---|--:|--:|--:|--:|
| Logistic Regression | 97.94% | 97.98% | 97.94% | 97.94% |
| Gradient Boosting | 95.74% | 95.83% | 95.74% | 95.75% |
| Random Forest | 95.48% | 95.60% | 95.48% | 95.48% |

Full pipeline: a leaf photo → MobileNetV3-Small forward pass (576-dim feature vector, convolutional
layers frozen — full fine-tuning wasn't attempted given only ~300 images/class) → the trained
classifier head → crop + disease/healthy label with a confidence score. Covers 13 classes across 4
crops (apple, maize, grapes, orange); any other crop, or an unclear photo, isn't something this
model can honestly classify — low-confidence results are flagged rather than presented as certain.

None of these numbers are hardcoded in the API or UI — they are read live from
`models/metrics.json`, `models/yield_metrics.json`, `models/price_reference.json`,
`models/water_kc_reference.json`, `models/water_p_reference.json`, `models/risk_metrics.json` and
`models/disease_metrics.json`, which each build/training script regenerates on every run.

## Explainable AI

`POST /explain/crop` runs `shap.TreeExplainer` against the actual loaded Random Forest model for
the actual submitted input and returns real per-feature SHAP contributions, which the UI renders
as a horizontal bar chart plus a narrative sentence generated from those values (see
[docs/xai.md](docs/xai.md)).

## Installation & Running

### Prerequisites
- Node.js 20+, Python 3.11+ (tested on 3.14), Git.
- PostgreSQL is optional — the backend defaults to a local SQLite file so you can run everything
  with zero extra setup.

### 1. Clone & environment variables
```bash
cd agri-ai-360/backend
cp .env.example .env
# Edit .env if you have a real PostgreSQL instance / weather API key. SATELLITE_API_KEY has no
# real provider implemented yet even if set (see Future Scope) — leave it blank.
```

### 2. Backend
```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash; use venv\Scripts\activate.bat on cmd.exe
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 3. Train the ML models + build the reference tables (required once, before first use)
```bash
# from the backend venv
python ml/crop_recommendation/train.py
python ml/yield_prediction/train.py
python ml/profit_prediction/build_price_reference.py
python ml/water_requirement/build_kc_reference.py
python ml/water_requirement/build_p_reference.py
python ml/risk_prediction/train.py
python ml/disease_detection/train.py
python ml/market_price/seed_market_prices.py
```
None of these download anything at runtime — they read the CSVs/HTML/images already included under
`ml/datasets/` and write `models/*.joblib` + `models/metrics.json` / `models/yield_metrics.json` /
`models/price_reference.json` / `models/water_kc_reference.json` / `models/water_p_reference.json` /
`models/risk_metrics.json` / `models/disease_metrics.json`. The yield and risk scripts each process
~325k rows and take noticeably longer than the others (a couple of minutes, mostly Random Forest);
the price script depends on the yield model being present (profit prediction calls it internally),
so run it after yield. The disease detection script runs a MobileNetV3 forward pass over ~3,875
images on CPU (several minutes) before training its 3 classifier heads.

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

### 4b. Run backend tests (optional but recommended)
```bash
# from the backend venv
pytest
```

### 5. Switching to real PostgreSQL
Set `DATABASE_URL=postgresql://<user>:<password>@<host>:5432/agriai360` in `backend/.env` and
restart the backend — the same SQLAlchemy models create the schema on startup. No code changes
needed.

## API Endpoints

See [docs/api.md](docs/api.md) for full request/response shapes. Summary:

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/farms
GET    /api/farms
GET    /api/farms/{id}
POST   /api/farms/{id}/soil
GET    /api/farms/{id}/soil
GET    /api/weather
POST   /api/predict/top-crops   (alias: /api/predict/crop)
POST   /api/explain/crop
GET    /api/predict/yield/options
POST   /api/predict/yield
GET    /api/predict/profit/options
POST   /api/predict/profit
GET    /api/predict/water/options
POST   /api/predict/water
GET    /api/predict/yield-risk/options
POST   /api/predict/yield-risk
GET    /api/predict/disease/options
POST   /api/predict/disease
GET    /api/history/disease
GET    /api/fertilizer/options
POST   /api/fertilizer/recommend
GET    /api/market-prices/crops
GET    /api/market-prices/states
GET    /api/market-prices             (current price)
GET    /api/market-prices/trend
GET    /api/market-prices/comparison
GET    /api/notifications
POST   /api/notifications/generate
PATCH  /api/notifications/{id}/read
POST   /api/assistant/ask
GET    /api/assistant/messages
POST   /api/assistant/reset
GET    /api/satellite/status
GET    /api/iot/readings
POST   /api/iot/readings
POST   /api/iot/demo/seed
GET    /api/models
GET    /api/models/performance
GET    /api/history
GET    /api/risk?farm_id=
GET    /api/dashboard/{farm_id}
GET    /health
```

## Database Schema

`users`, `farmers`, `farms`, `soil_records`, `weather_records`, `crop_predictions`, `crop_scores`,
`recommendation_explanations`, `alerts`, `model_versions`, `chat_sessions`, `chat_messages`,
`disease_predictions`, `market_prices`, `notifications`, `sensor_readings`.
Full column definitions: [docs/database.md](docs/database.md).

## Testing

- Automated backend tests (`backend/tests/`, pytest + FastAPI `TestClient` against an isolated
  SQLite test database): `test_assistant.py` (9 tests — the AI Assistant never fabricates an answer
  when the underlying farm data doesn't exist yet, correctly reuses real data once it does, and
  chat history persists/resets correctly), `test_realtime.py` (7 tests — Satellite status is
  always honestly labeled "PLANNED"/not configured, IoT demo readings are always tagged
  `demo_simulation` and never conflated with real device data, farm ownership is enforced), and
  `test_weather_provider.py` (15 tests — the mock provider's shape is unchanged, the real
  `OpenMeteoWeatherProvider`'s parsing/error-handling logic against a mocked HTTP transport, the
  safe fallback-to-mock wrapper never lets a network failure surface as an error, provider
  selection defaults to mock, and one real live-network call against the actual Open-Meteo API
  that proves the integration genuinely works end-to-end — it skips rather than fails if this
  environment ever has no network access). Run with `pytest` from `backend/` (venv active). All
  31 pass.
- Live weather was additionally verified through the running server with `WEATHER_PROVIDER=open-meteo`
  set: two different cities (Nashik, Pune) returned distinct, real current conditions and 5-day
  forecasts with `source: "live"`, confirmed against the actual HTTP response, not just the test
  suite.
- Backend: end-to-end flow (register → login → create farm → submit soil → predict → explain →
  model performance → history → risk → dashboard → yield → profit → water requirement → yield risk
  → disease diagnosis → fertilizer → market price → notifications → AI assistant → satellite status
  → IoT demo seed → live weather) was manually verified against a running `uvicorn` instance with
  real HTTP requests, including negative paths (duplicate email, wrong password, missing/garbage
  token, out-of-range soil values, unknown crop/state/season, non-image upload, wrong content-type,
  unknown sensor type) — see repo history / dev notes.
- Disease detection was verified with real leaf photos from the held-out test set: a maize
  Common Rust image correctly diagnosed at 99.8% confidence, a healthy apple leaf correctly
  diagnosed at 99.98% confidence, both through the actual `POST /api/predict/disease` endpoint
  (not just the offline evaluation metrics).
- Water requirement's formula and results were hand-verified against real-world plausibility (a
  self-derived approximation that produced an unrealistic ~23 mm/day ET₀ was caught this way and
  replaced with FAO's actual published table — see `docs/ml-methodology.md` Part 4).
- Yield risk's evaluation methodology was corrected mid-development after comparing two different
  accuracy numbers (64.5% random-split vs. 36.9% proper CV) exposed train/test leakage; the fix and
  a follow-up domain sanity check (Punjab rice correctly predicted low-risk) are documented in
  `docs/ml-methodology.md` Part 5.
- Database persistence was verified directly against the SQLite file (row counts, foreign-key
  joins across `crop_predictions`/`crop_scores`), not just through the API layer.
- Frontend: `npm run build` (TypeScript project build + Vite production build) passes with zero
  errors. The full user journey (landing → register → dashboard → create farm → soil → crop
  recommendation → What-If simulation → explanation → yield estimate → profit estimate → water
  requirement → yield risk → model lab → risk → history → roadmap) was driven with a headless
  Chrome browser against the real backend, with zero console/JS errors, across multiple runs as
  each Phase 2 module was added.

## Future Scope

Still planned: a real **LLM/RAG-backed** version of the AI Assistant (today it's a real, working
rule-based fallback grounded in actual farm data — not an LLM, and explicitly labeled as such), a
**voice interface** on top of it, **multilingual** responses (the `preferred_language` field is
already captured at registration), a **live** satellite/NDVI data provider (today: an
integration-ready, honestly-labeled "Planned" architecture with no fake readings), and **real
physical IoT sensors** (today: a genuine ingestion endpoint + database table, populated with
clearly-labeled demo data since no hardware is connected). Yield, profit, water requirement, yield
risk, disease detection, fertilizer recommendation, market price intelligence, personalized
notifications, the rule-based AI Assistant, and now **live weather** (open-meteo.com, opt-in, no
key required) all ship real, working functionality.
Details: [docs/future-scope.md](docs/future-scope.md).

## Limitations

- Weather defaults to a deterministic **mock provider** (clearly labeled in the UI). A real, live
  provider (`OpenMeteoWeatherProvider`, using the free open-meteo.com API — no key required) is
  implemented and opt-in via `WEATHER_PROVIDER=open-meteo` in `backend/.env`; it geocodes the
  farm's location and fetches real current conditions + a 5-day forecast, and safely falls back to
  the mock provider (never a 500) if the live API is unreachable. See
  `backend/app/services/weather_provider.py` and `backend/tests/test_weather_provider.py`.
- The soil-health scoring and the farm-risk dashboard are **transparent rule-based systems**, not
  trained models — labeled "prototype assessment" everywhere they appear in the UI.
- Yield prediction is a **regional-historical estimate** (state + crop + season, 1997–2020), not a
  per-farm forecast — it has no access to an individual farm's soil, irrigation, or this season's
  actual weather. It also only covers 11 of the 22 recommendation-engine crops; the rest honestly
  report "not available" rather than guessing. See `docs/dataset.md` and `docs/ml-methodology.md`.
- Profit prediction's revenue side uses **real but 2016, non-inflation-adjusted** mandi prices, and
  only covers 6 crops (the intersection of yield- and price-supported crops). Its cost side is
  **farmer-supplied, not modeled** — no honest public per-farm cost-of-cultivation dataset was
  found; inventing one would violate this project's own "never fabricate" rule. See
  `docs/dataset.md` and `docs/ml-methodology.md` for what was searched and why this design was
  chosen instead.
- Water requirement uses **FAO's own "rough estimate only" Blaney-Criddle method** (not its more
  accurate but data-hungry Penman-Monteith method), state-capital latitude rather than the farm's
  actual GPS position, and only the mid-season (peak-demand) crop coefficient — not a full
  growth-stage water-balance model. Covers 17 of 22 crops. See `docs/dataset.md` and
  `docs/ml-methodology.md`.
- Yield risk is a **modest, real signal** (55.3% test accuracy on a 3-class problem, 33.3%
  baseline), evaluated on years the model never trained on. It answers a narrower question than it
  might sound like — "how has this crop historically ranked nationally in this state/season?" — not
  a forecast of this year's weather, disease or pest risk, and it has no weather/soil/year input.
  Covers 11 of 22 crops. It augments, and does not replace, the rule-based weather/soil/water/
  disease risk dashboard. See `docs/dataset.md` and `docs/ml-methodology.md` Part 5 for the full
  methodology, including a documented train/test-leakage bug that was caught and fixed before this
  shipped.
- Disease detection covers **only 13 classes across 4 crops** (apple, maize, grapes, orange) — the
  intersection of PlantVillage's available classes and this project's 22-crop recommendation list.
  It's a **frozen-feature-extractor** approach (MobileNetV3 backbone not fine-tuned), chosen because
  the dataset (~300 images/class) is too small to fine-tune convolutional layers without
  overfitting; a larger, India-field-condition dataset (rather than PlantVillage's controlled lab
  backgrounds) would be needed for a more field-robust model. Any other crop, or a low-confidence
  result, is reported honestly rather than guessed. See `docs/dataset.md` and
  `docs/ml-methodology.md`.
- Market price data is **real but historical** — 2016 Agmarknet records for a limited set of
  crops/states, not a live feed. Fertilizer recommendations use the same general agronomic
  reference bands as the soil health score, and are explicitly disclaimed as decision support, not
  a calibrated dosage prescription — always validate against a certified local soil test.
- The **AI Agriculture Assistant is rule-based, not an LLM** — no language-model API key is
  configured for this project. It answers only the intents its keyword classifier currently
  recognizes (crop recommendation reasoning, soil health, risk, irrigation, fertilizer, disease,
  market price, weather) using each farm's real, already-computed data; anything else gets an
  honest "I couldn't match that" fallback rather than an invented answer.
- **Satellite monitoring is architecture only** — no NDVI/remote-sensing provider is connected;
  the module always reports `status: "PLANNED"` and never returns a fabricated vegetation reading.
- **IoT sensor readings are demo/simulation only** — no physical sensor is connected to this
  deployment. The real ingestion endpoint (`POST /api/iot/readings`) and database table exist and
  work today for when hardware is connected; every demo-generated row is tagged
  `source: "demo_simulation"` and is never presented as live sensor data.
- Automated backend test coverage is currently limited to the AI Assistant and Real-Time
  Intelligence modules (`backend/tests/`, 16 pytest tests); the rest of the API is covered by the
  manual/scripted E2E verification described above, not automated tests yet.
- Single active model at inference time per module (Random Forest for crop recommendation and yield
  risk, XGBoost for yield, Logistic Regression for disease detection); the other trained models are
  kept only for their comparison pages, not served live.
- No production deployment / CI pipeline configured yet.

## Research Contribution

Demonstrates a full pipeline from a public benchmark dataset through model comparison,
explainable AI (SHAP) and a farmer-facing decision-support UI, with an explicit separation between
implemented/real functionality and roadmap placeholders — intended to be reproducible end to end
from this repository.

---

🤖 Built with [Claude Code](https://claude.com/claude-code)

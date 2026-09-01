# 🚜 AgriAI 360

**An Explainable AI-Powered Intelligent Crop Recommendation and Farm Decision Support System**

Final-year Computer Science and Engineering major project.

> **Status: MVP + Phase 2 (Yield, Profit & Water Prediction).** Crop recommendation, soil
> intelligence, weather, explainable AI (SHAP), model comparison, risk summary, history, the
> What-If simulator, yield prediction, profit estimation, and water requirement are real and
> working end to end. Disease detection, the AI assistant, voice, and satellite/IoT are
> intentionally **not implemented** — see [Future Scope](docs/future-scope.md) and the in-app AI
> Roadmap page. Nothing in this build fabricates a metric or a prediction: every number shown
> comes from a trained model, real historical data, a published scientific formula, a documented
> rule-based calculation, or is explicitly labeled as a mock/prototype/farmer-supplied input.

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
- Weather intelligence via a swappable `WeatherProvider` (mock provider by default, clearly labeled).
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
- AI Roadmap page showing what's implemented vs. planned.
- UI shells (clearly marked "coming in Phase 2/3") for Crop Doctor (disease detection) and the AI
  Agriculture Assistant — no fake model or LLM behind them.

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
| Explainable AI | SHAP |
| Auth | JWT (python-jose) + bcrypt |

## Dataset

Four independent public data sources, one per module (full provenance and limitations in
[docs/dataset.md](docs/dataset.md)):

- **Crop Recommendation Dataset** — 2,200 records, 22 crop classes, 7 numeric features
  (N, P, K, temperature, humidity, ph, rainfall → crop label). Originally published on Kaggle by
  Atharva Ingle.
- **India Crop Production records** — 325k district-level rows (state, crop, season, year → yield),
  1997–2020, sourced from a public mirror of India's crop-production statistics. Used for Phase 2
  yield prediction.
- **Agmarknet mandi price records** — real 2016 Indian government market-price transactions for 6
  crops, aggregated to a median-price-per-(crop, state) reference table. Used for Phase 2 profit
  prediction (revenue side only — cost is farmer-supplied, see Limitations).
- **FAO Irrigation & Drainage Paper 56 + FAO Crop Water Needs manual** — official published crop
  coefficients (Table 12) and reference-evapotranspiration daylight tables (Table 4), fetched and
  parsed directly from fao.org, not recalled from memory. Used for Phase 2 water requirement.

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

None of these numbers are hardcoded in the API or UI — they are read live from
`models/metrics.json`, `models/yield_metrics.json`, `models/price_reference.json`,
`models/water_kc_reference.json` and `models/water_p_reference.json`, which each build/training
script regenerates on every run.

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
# Edit .env if you have a real PostgreSQL instance / weather API key.
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
```
None of these download anything at runtime — they read the CSVs/HTML already included under
`ml/datasets/` and write `models/*.joblib` + `models/metrics.json` / `models/yield_metrics.json` /
`models/price_reference.json` / `models/water_kc_reference.json` / `models/water_p_reference.json`.
The yield script processes ~325k rows and takes noticeably longer than the others (a couple of
minutes, mostly Random Forest); the price script depends on the yield model being present (profit
prediction calls it internally), so run it after yield.

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

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
GET    /api/models
GET    /api/models/performance
GET    /api/history
GET    /api/risk?farm_id=
GET    /api/dashboard/{farm_id}
GET    /health
```

## Database Schema

`users`, `farmers`, `farms`, `soil_records`, `weather_records`, `crop_predictions`, `crop_scores`,
`recommendation_explanations`, `alerts`, `model_versions`, `chat_sessions`, `chat_messages`.
Full column definitions: [docs/database.md](docs/database.md).

## Testing

- Backend: end-to-end flow (register → login → create farm → submit soil → predict → explain →
  model performance → history → risk → dashboard → yield → profit → water requirement) was manually
  verified against a running `uvicorn` instance with real HTTP requests, including negative paths
  (duplicate email, wrong password, missing/garbage token, out-of-range soil values, unknown
  crop/state/season) — see repo history / dev notes.
- Water requirement's formula and results were hand-verified against real-world plausibility (a
  self-derived approximation that produced an unrealistic ~23 mm/day ET₀ was caught this way and
  replaced with FAO's actual published table — see `docs/ml-methodology.md` Part 4).
- Database persistence was verified directly against the SQLite file (row counts, foreign-key
  joins across `crop_predictions`/`crop_scores`), not just through the API layer.
- Frontend: `npm run build` (TypeScript project build + Vite production build) passes with zero
  errors. The full user journey (landing → register → dashboard → create farm → soil → crop
  recommendation → What-If simulation → explanation → yield estimate → profit estimate → water
  requirement → model lab → risk → history → roadmap) was driven with a headless Chrome browser
  against the real backend, with zero console/JS errors, across multiple runs as each Phase 2
  module was added.

## Future Scope

A trained (not rule-based) risk model, disease detection (computer vision), a real LLM/RAG-backed
AI assistant, voice interface, multilingual support, satellite/NDVI monitoring and IoT sensor
ingestion. All have UI shells or clearly-marked "roadmap" placeholders already in place. Yield,
profit and water requirement (previously listed here) shipped in Phase 2. Details:
[docs/future-scope.md](docs/future-scope.md).

## Limitations

- Weather is a deterministic **mock provider** (clearly labeled in the UI) — no live weather API
  key is configured. Swapping in a real provider only requires implementing `WeatherProvider` and
  is architected for that (see `backend/app/services/weather_provider.py`).
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
- No automated backend/frontend test suite yet (manual + scripted E2E verification only).
- Single active model at inference time per module (Random Forest for crop recommendation, XGBoost
  for yield); the other trained models are kept only for their comparison pages, not served live.
- No production deployment / CI pipeline configured yet.

## Research Contribution

Demonstrates a full pipeline from a public benchmark dataset through model comparison,
explainable AI (SHAP) and a farmer-facing decision-support UI, with an explicit separation between
implemented/real functionality and roadmap placeholders — intended to be reproducible end to end
from this repository.

---

🤖 Built with [Claude Code](https://claude.com/claude-code)

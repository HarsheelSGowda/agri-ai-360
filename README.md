# 🚜 AgriAI 360

**An Explainable AI-Powered Intelligent Crop Recommendation and Farm Decision Support System**

Final-year Computer Science and Engineering major project.

> **Status: ~50% MVP.** Crop recommendation, soil intelligence, weather, explainable AI (SHAP),
> model comparison, risk summary, history and the What-If simulator are real and working end to
> end. Yield/profit prediction, disease detection, the AI assistant, voice, and satellite/IoT are
> intentionally **not implemented** — see [Future Scope](docs/future-scope.md) and the in-app
> AI Roadmap page. Nothing in this build fabricates a metric or a prediction: every number shown
> comes from a trained model, a documented rule-based calculation, or is explicitly labeled as a
> mock/prototype.

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
5. Architect the system so future modules (yield/profit prediction, disease detection, an LLM
   assistant, voice, satellite/IoT) can be added without rewriting the core.

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

**Crop Recommendation Dataset** — 2,200 records, 22 crop classes, 7 numeric features
(N, P, K, temperature, humidity, ph, rainfall → crop label). Publicly available and widely used
for this exact task (originally published on Kaggle by Atharva Ingle). Full provenance,
column definitions and known limitations are documented in [docs/dataset.md](docs/dataset.md).

## ML Methodology

Four classifiers are trained on an 80/20 stratified split (see
[ml/crop_recommendation/train.py](ml/crop_recommendation/train.py)) and evaluated with accuracy,
precision, recall, F1 and 5-fold cross-validation. **Random Forest is the active model**
(highest test accuracy). Full methodology: [docs/ml-methodology.md](docs/ml-methodology.md).

**Actual results from the last training run** (see `models/metrics.json` for the source of truth):

| Algorithm | Accuracy | Precision | Recall | F1 |
|---|--:|--:|--:|--:|
| Random Forest | 99.32% | 99.35% | 99.32% | 99.32% |
| Gradient Boosting | 98.86% | 98.97% | 98.86% | 98.87% |
| XGBoost | 98.64% | 98.74% | 98.64% | 98.62% |
| SVM | 98.41% | 98.66% | 98.41% | 98.39% |

These numbers are not hardcoded in the API or UI — they are read live from `models/metrics.json`,
which `train.py` regenerates every time it runs.

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

### 3. Train the ML models (required once, before first use)
```bash
# from the backend venv
python ml/crop_recommendation/train.py
```
This downloads nothing at runtime — it reads `ml/datasets/crop_recommendation.csv` (already
included) and writes `models/*.joblib` + `models/metrics.json`.

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
  model performance → history → risk → dashboard) was manually verified against a running
  `uvicorn` instance with real HTTP requests (see repo history / dev notes).
- Frontend: `npm run build` (TypeScript project build + Vite production build) passes with zero
  errors. The full user journey (landing → register → dashboard → create farm → soil → crop
  recommendation → What-If simulation → explanation → model lab → risk → history → roadmap) was
  driven with a headless Chrome browser against the real backend, with zero console/JS errors.
- No automated test suite (`tests/`) has been written yet for this MVP — see Limitations.

## Future Scope

Yield prediction, profit intelligence, water requirement modeling, a trained (not rule-based)
risk model, disease detection (computer vision), a real LLM/RAG-backed AI assistant, voice
interface, multilingual support, satellite/NDVI monitoring and IoT sensor ingestion. All have UI
shells or clearly-marked "roadmap" placeholders already in place. Details:
[docs/future-scope.md](docs/future-scope.md).

## Limitations

- Weather is a deterministic **mock provider** (clearly labeled in the UI) — no live weather API
  key is configured. Swapping in a real provider only requires implementing `WeatherProvider` and
  is architected for that (see `backend/app/services/weather_provider.py`).
- The soil-health scoring and the farm-risk dashboard are **transparent rule-based systems**, not
  trained models — labeled "prototype assessment" everywhere they appear in the UI.
- No automated backend/frontend test suite yet (manual + scripted E2E verification only).
- Single active model at inference time (Random Forest); the other three trained models are kept
  only for the comparison page, not served for live predictions.
- No production deployment / CI pipeline configured yet.

## Research Contribution

Demonstrates a full pipeline from a public benchmark dataset through model comparison,
explainable AI (SHAP) and a farmer-facing decision-support UI, with an explicit separation between
implemented/real functionality and roadmap placeholders — intended to be reproducible end to end
from this repository.

---

🤖 Built with [Claude Code](https://claude.com/claude-code)

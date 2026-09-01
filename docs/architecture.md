# Architecture

## High-level

```
┌─────────────────────────────┐        JWT Bearer         ┌───────────────────────────────┐
│  React + Vite + TypeScript   │ ─────────────────────────►│         FastAPI backend        │
│  (frontend/)                 │◄───────────────────────── │         (backend/app/)         │
└─────────────────────────────┘        JSON over /api      └──────────────┬─────────────────┘
                                                                            │
                              ┌────────────────────────────────────────────┼───────────────────┐
                              ▼                                            ▼                    ▼
                    SQLAlchemy ORM (app/models)              app/services/ml_service.py   app/services/
                              │                                            │              weather_provider.py,
                              ▼                                            ▼              soil_health.py,
                    PostgreSQL / SQLite                     models/*.joblib + SHAP        risk_service.py
                    (DATABASE_URL-driven)                   (trained by ml/crop_recommendation/train.py)
```

## Directory layout

```
agri-ai-360/
  frontend/           React app (components/, pages/, layouts/, services/, hooks/, charts/, types/)
  backend/app/
    api/              FastAPI routers (one file per resource)
    core/             config.py (env settings), security.py (JWT + bcrypt)
    database/         SQLAlchemy engine/session (base.py, session.py)
    models/           SQLAlchemy ORM models (one file per domain area)
    schemas/          Pydantic request/response schemas
    services/         Business logic: ml_service, weather_provider, soil_health, risk_service
    main.py           FastAPI app wiring, CORS, router registration
  ml/
    crop_recommendation/train.py   Training pipeline (dataset → saved models + metrics.json)
    datasets/         crop_recommendation.csv
    preprocessing/, explainability/, evaluation/, yield_prediction/, disease_detection/
                       Reserved for Phase 2/3 modules — architecture in place, not yet implemented
  models/             Trained model artifacts (*.joblib) + metrics.json — generated, not hand-written
  docs/               This documentation set
```

## Why this structure

- **Frontend/backend/ml are fully separable.** The ML pipeline writes plain `.joblib` + JSON files
  to `models/`; the backend only knows how to *load and query* those files
  (`app/services/ml_service.py`). Retraining never requires touching backend code, and the backend
  never requires touching the ML pipeline.
- **One router per resource** (`api/auth.py`, `api/farms.py`, `api/predict.py`, …) keeps `main.py`
  a thin composition root instead of a growing monolith.
- **Services own business logic**, routers stay thin (parse request → call service → return
  response). This is what lets `soil_health.py` and `risk_service.py` be unit-testable in
  isolation and reused by both the dedicated endpoints (`/risk`) and the combined `/dashboard/{id}`
  endpoint without duplicating logic.
- **`WeatherProvider` is an abstract interface** (`app/services/weather_provider.py`) so a real
  weather API can be added later by implementing one class, with zero changes to any route or
  frontend code — this is the same pattern the master spec asked for so Phase 2/3 modules
  (yield/profit prediction, disease detection) can be added without rewriting the app.
- **DATABASE_URL drives Postgres vs. SQLite** transparently through the same SQLAlchemy models —
  there is no SQLite-only or Postgres-only code path.

## Adding a future module (example: Yield Prediction)

1. Add a training script under `ml/yield_prediction/` that saves `yield_model.joblib` to `models/`.
2. Add `predict_yield()` to a new `app/services/yield_service.py` following the same pattern as
   `ml_service.py`.
3. Add `POST /predict/yield` in a new `app/api/yield_router.py`, included in `main.py`.
4. Add a `YieldCard` component + wire it into the dashboard/recommendation detail page.

No existing file needs to change beyond `main.py`'s router registration — this is the extensibility
the master spec required.

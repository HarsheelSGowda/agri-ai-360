# Database Schema

SQLAlchemy 2.0 declarative models (`backend/app/models/`), created via
`Base.metadata.create_all()` on startup. Works identically against SQLite (local dev default) and
PostgreSQL (set `DATABASE_URL` in `.env`) — no per-database code paths.

## Tables

### `users`
Auth identity only. `id`, `email` (unique), `password_hash` (bcrypt), `created_at`.

### `farmers`
Profile data, 1:1 with `users`. `id`, `user_id` (FK → users, unique), `name`, `location`,
`preferred_language`, `created_at`.

### `farms`
`id`, `farmer_id` (FK → farmers), `name`, `location`, `area_acres`, `soil_type`,
`irrigation_available`, `created_at`.

### `soil_records`
One row per soil submission (history preserved, latest used for current health score).
`id`, `farm_id` (FK → farms), `nitrogen`, `phosphorus`, `potassium`, `ph`, `soil_type`,
`organic_carbon` (nullable), `moisture` (nullable), `electrical_conductivity` (nullable),
`created_at`.

### `weather_records`
Reserved for persisting fetched weather snapshots (schema in place; the mock provider currently
returns data live without writing to this table — wiring it up is a small follow-up once a real
weather API is connected). `id`, `location`, `temperature_c`, `humidity_pct`, `rainfall_mm`,
`wind_kmh`, `condition`, `source`, `created_at`.

### `crop_predictions`
One row per `/predict/top-crops` call made with a `farm_id`. `id`, `farm_id` (FK → farms),
`model_version_id` (FK → model_versions, nullable), `input_json` (the exact request payload),
`top_crop`, `top_score`, `created_at`.

### `crop_scores`
Top-5 breakdown per prediction. `id`, `prediction_id` (FK → crop_predictions), `crop`,
`probability`, `rank`.

### `recommendation_explanations`
1:1 with a prediction, reserved for persisting a SHAP explanation alongside its prediction (the
`/explain/crop` endpoint currently computes explanations on demand and does not yet persist them
here — see Limitations). `id`, `prediction_id` (FK, unique), `method`, `contributions_json`,
`narrative`.

### `alerts`
Reserved for future proactive notifications (e.g. disease risk, extreme weather). `id`, `farm_id`
(FK → farms), `severity`, `message`, `created_at`.

### `model_versions`
Reserved for a full model registry (currently `models/metrics.json` on disk is the source of
truth for active model + metrics; this table is schema-ready for when model metadata needs to live
in the DB instead of a file, e.g. for multi-tenant model rollout). `id`, `algorithm`, `version`,
`accuracy`, `is_active`, `trained_at`.

### `chat_sessions` / `chat_messages`
Reserved for the Phase 3 AI Agriculture Assistant. `chat_sessions`: `id`, `farmer_id` (FK),
`created_at`. `chat_messages`: `id`, `session_id` (FK), `role`, `content`, `created_at`.

## Migrations

The MVP uses `Base.metadata.create_all()` at startup for fast iteration (safe for SQLite/dev and
for an empty Postgres database). Alembic is a natural next step once the schema needs to evolve
against a database with existing production data — not required for a fresh install of this MVP.

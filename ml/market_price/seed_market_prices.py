"""
AgriAI 360 - Market Price Intelligence: DB seeder (Phase 2, new priority feature)

Loads real historical Agmarknet (Indian government mandi) per-transaction price
records from ml/datasets/agmarknet_prices/*.csv into the `market_prices` table,
so the market-price API can query by crop/state/district/market/variety/date
with real SQL filtering instead of holding ~289k rows in memory per request.

Source: raw per-transaction mandi records (state, district, market, variety,
group, arrivals, min/max/modal price in Rs./Quintal, date) for calendar year
2016 - the most recent full year available in the source mirror (same source
already used by ml/profit_prediction/build_price_reference.py). This is
historical reference data, NOT a live feed - see docs/dataset.md /
DATASETS.md. MarketPriceProvider (backend/app/services/market_price_provider.py)
is the swap point for a future live Agmarknet API integration.

Run from backend/ (so the default sqlite:///./agriai.db path matches the one
the running app uses - this script does not override DATABASE_URL, it reuses
app.database.session exactly as the API does) - idempotent, clears prior
agmarknet_2016_historical rows first:

    cd backend
    venv/Scripts/python.exe ../ml/market_price/seed_market_prices.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRICES_DIR = ROOT / "ml" / "datasets" / "agmarknet_prices"
MODELS_DIR = ROOT / "models"

sys.path.insert(0, str(ROOT / "backend"))

from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.models.market_price import MarketPrice  # noqa: E402

# file key -> crop label (same vocabulary as app/services/ml_service.py's crop labels)
CROP_FILE_MAP = {
    "rice_2016.csv": "rice",
    "maize_2016.csv": "maize",
    "arhar_tur_2016.csv": "pigeonpeas",
    "black_gram_2016.csv": "blackgram",
    "green_gram_2016.csv": "mungbean",
    "lentil_2016.csv": "lentil",
}

SOURCE_LABEL = "agmarknet_2016_historical"
COLUMNS = ["state", "district", "market", "variety", "group", "arrivals_tonnes", "min_price", "max_price", "modal_price", "date"]
CHUNK_SIZE = 5000


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=None, names=COLUMNS)
    before = len(df)

    for col in ("arrivals_tonnes", "min_price", "max_price", "modal_price"):
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", "", regex=False), errors="coerce")
    for col in ("state", "district", "market", "variety", "group"):
        df[col] = df[col].astype(str).str.strip()

    df = df[(df["modal_price"] > 0) & (df["min_price"] > 0) & (df["max_price"] > 0)]
    df = df[df["min_price"] <= df["max_price"]]

    # IQR-based outlier removal (wide 3x multiplier - real market data has
    # legitimate regional variation; this only drops obvious data-entry errors).
    q1, q3 = df["modal_price"].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
    df = df[(df["modal_price"] >= lower) & (df["modal_price"] <= upper)]

    df["date"] = pd.to_datetime(df["date"], format="%d %b %Y", errors="coerce")
    df = df.dropna(subset=["date"])

    after = len(df)
    print(f"  {path.name}: {before} rows -> {after} after cleaning (dropped {before - after})")
    return df


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    deleted = db.query(MarketPrice).filter(MarketPrice.source == SOURCE_LABEL).delete()
    db.commit()
    if deleted:
        print(f"Cleared {deleted} existing {SOURCE_LABEL} rows before reseeding.\n")

    report = {
        "source": "Agmarknet (Indian government mandi price records), calendar year 2016",
        "price_unit": "Rs. per quintal",
        "not_inflation_adjusted": True,
        "not_live_data": True,
        "seeded_at": datetime.now(timezone.utc).isoformat(),
        "crops": {},
    }

    total_inserted = 0
    for filename, crop in CROP_FILE_MAP.items():
        path = PRICES_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing price file: {path}")

        print(f"Processing {crop}...")
        df = load_and_clean(path)

        records = [
            {
                "crop": crop,
                "state": row.state,
                "district": row.district,
                "market": row.market,
                "variety": row.variety,
                "group_name": row.group,
                "arrivals_tonnes": float(row.arrivals_tonnes) if pd.notna(row.arrivals_tonnes) else None,
                "min_price": float(row.min_price),
                "max_price": float(row.max_price),
                "modal_price": float(row.modal_price),
                "price_date": row.date.date(),
                "source": SOURCE_LABEL,
            }
            for row in df.itertuples(index=False)
        ]

        for i in range(0, len(records), CHUNK_SIZE):
            db.bulk_insert_mappings(MarketPrice, records[i : i + CHUNK_SIZE])
        db.commit()

        total_inserted += len(records)
        report["crops"][crop] = {
            "records_inserted": len(records),
            "states_covered": df["state"].nunique(),
            "markets_covered": df["market"].nunique(),
            "date_min": df["date"].min().date().isoformat(),
            "date_max": df["date"].max().date().isoformat(),
        }

    db.close()

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODELS_DIR / "market_price_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nInserted {total_inserted} market price records into the database.")
    print(f"Report saved to {MODELS_DIR / 'market_price_report.json'}")


if __name__ == "__main__":
    main()

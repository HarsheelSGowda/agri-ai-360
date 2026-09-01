"""
AgriAI 360 - Profit Prediction: market price reference builder (Phase 2)

This is NOT a trained ML model. It aggregates real historical Agmarknet
(government mandi) price records into a per-(crop, state) median price
lookup table, used as the revenue side of the profit calculation. Cost is
deliberately NOT estimated from a dataset (see docs/dataset.md /
docs/ml-methodology.md for why) — the farmer supplies their own cost
estimate, and the backend just does Revenue - Cost.

Source: raw per-transaction mandi records (state, district, market, variety,
group, arrivals, min/max/modal price in Rs./Quintal, date) for calendar year
2016 - the most recent full year available in the source mirror. Prices are
NOT adjusted for inflation; treat them as a historical relative benchmark,
not today's price.

Run:
    python ml/profit_prediction/build_price_reference.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRICES_DIR = ROOT / "ml" / "datasets" / "agmarknet_prices"
MODELS_DIR = ROOT / "models"

# file key -> recommendation-engine crop label (same vocabulary as
# app/services/ml_service.py's crop labels)
CROP_FILE_MAP = {
    "rice_2016.csv": "rice",
    "maize_2016.csv": "maize",
    "arhar_tur_2016.csv": "pigeonpeas",
    "black_gram_2016.csv": "blackgram",
    "green_gram_2016.csv": "mungbean",
    "lentil_2016.csv": "lentil",
}

COLUMNS = ["state", "district", "market", "variety", "group", "arrivals_tonnes", "min_price", "max_price", "modal_price", "date"]


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, header=None, names=COLUMNS)
    before = len(df)

    df = df[df["modal_price"] > 0]

    # IQR-based outlier removal (wide 3x multiplier — this is real market
    # data with legitimate regional variation; only drop obvious data-entry
    # errors like a single 210000 Rs/quintal row among a ~2000-3000 median).
    q1, q3 = df["modal_price"].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 3 * iqr, q3 + 3 * iqr
    df = df[(df["modal_price"] >= lower) & (df["modal_price"] <= upper)]

    after = len(df)
    print(f"  {path.name}: {before} rows -> {after} after cleaning (dropped {before - after})")
    return df


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    reference: dict[str, dict] = {}
    report = {
        "source": "Agmarknet (Indian government mandi price records), calendar year 2016",
        "price_unit": "Rs. per quintal (modal price)",
        "aggregation": "median modal price per (crop, state), after IQR outlier removal",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "not_inflation_adjusted": True,
        "crops": {},
    }

    for filename, crop in CROP_FILE_MAP.items():
        path = PRICES_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing price file: {path}")

        print(f"Processing {crop}...")
        df = load_and_clean(path)

        by_state = df.groupby("state")["modal_price"].median().round(2).to_dict()
        national_median = round(float(df["modal_price"].median()), 2)

        reference[crop] = {"national_median": national_median, "by_state": by_state}
        report["crops"][crop] = {
            "national_median_rs_per_quintal": national_median,
            "states_covered": len(by_state),
            "records_used": len(df),
        }

    with open(MODELS_DIR / "price_reference.json", "w") as f:
        json.dump(reference, f, indent=2)

    with open(MODELS_DIR / "price_reference_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nSaved price_reference.json + price_reference_report.json to {MODELS_DIR}")
    print(f"Crops covered: {sorted(reference.keys())}")


if __name__ == "__main__":
    main()

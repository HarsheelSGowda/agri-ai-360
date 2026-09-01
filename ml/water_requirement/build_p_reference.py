"""
AgriAI 360 - Water Requirement: Blaney-Criddle "p" reference builder (Phase 2)

Parses FAO "Crop Water Needs" (Irrigation Water Management Training Manual
No. 3), Chapter 3, Table 4 - "Mean daily percentage (p) of annual daytime
hours for different latitudes" - directly from the official FAO document
(saved locally at ml/datasets/fao56/fao_blaney_criddle_table4.html, fetched
from https://www.fao.org/4/s2022e/s2022e07.htm), the same source that gives
the exact Blaney-Criddle formula used in water_service.py:

    ETo = p x (0.46 x Tmean + 8)   [mm/day, monthly-average basis]

An earlier version of this module tried to derive p from pure solar
astronomy (day length / 12). That produced ETo ~23 mm/day for a real July
Nagpur input - roughly 3-4x too high versus the ~5-6 mm/day this real table
gives for the same input. Rather than trust a self-derived approximation
that was empirically wrong, this script extracts FAO's own published p
table so the formula matches its documented, verified form.

Run:
    python ml/water_requirement/build_p_reference.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
SOURCE_HTML = ROOT / "ml" / "datasets" / "fao56" / "fao_blaney_criddle_table4.html"
MODELS_DIR = ROOT / "models"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main() -> None:
    if not SOURCE_HTML.exists():
        raise FileNotFoundError(f"FAO source page not found at {SOURCE_HTML}")

    with open(SOURCE_HTML, encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")
    marker = soup.find(string=re.compile(r"MEAN DAILY PERCENTAGE \(p\) OF ANNUAL DAYTIME HOURS"))
    table = marker.find_next("table")
    rows = table.find_all("tr")

    # rows[0] = header (Latitude/North + month names), rows[1] = South-hemisphere
    # alt month header, rows[2:] = one row per latitude band, Northern-hemisphere
    # column order (Jan..Dec), latitude descending from 60 to 0.
    p_table: dict[str, dict[str, float]] = {}
    for tr in rows[2:]:
        tds = tr.find_all("td")
        cells = [td.get_text(strip=True) for td in tds]
        lat_label = cells[0].replace("°", "").strip()
        values = cells[2:14]  # skip latitude cell + blank 'North' cell
        if len(values) != 12:
            raise ValueError(f"Expected 12 monthly p values for latitude {lat_label}, got {len(values)}: {values}")
        p_table[lat_label] = {month: float(v) for month, v in zip(MONTHS, values)}

    expected_lats = {"60", "55", "50", "45", "40", "35", "30", "25", "20", "15", "10", "5", "0"}
    if set(p_table.keys()) != expected_lats:
        raise ValueError(f"Unexpected latitude set parsed: {sorted(p_table.keys())}")

    report = {
        "source": "FAO Irrigation Water Management Training Manual No. 3, 'Crop Water Needs', Table 4",
        "source_url": "https://www.fao.org/4/s2022e/s2022e07.htm",
        "local_copy": str(SOURCE_HTML.relative_to(ROOT)),
        "formula": "ETo = p x (0.46 x Tmean + 8)  [mm/day]",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "latitude_bands_deg_north": sorted((int(k) for k in p_table.keys()), reverse=True),
    }

    with open(MODELS_DIR / "water_p_reference.json", "w") as f:
        json.dump(p_table, f, indent=2)
    with open(MODELS_DIR / "water_p_reference_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Extracted p-table: {len(p_table)} latitude bands x 12 months")
    print("Sample (20N):", p_table["20"])
    print(f"Saved water_p_reference.json + water_p_reference_report.json to {MODELS_DIR}")


if __name__ == "__main__":
    main()

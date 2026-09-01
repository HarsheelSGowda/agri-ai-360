"""
AgriAI 360 - Water Requirement: crop coefficient (Kc) reference builder (Phase 2)

Parses FAO Irrigation and Drainage Paper No. 56 (Allen, Pereira, Raes & Smith,
1998), Chapter 6, Table 12 - "Single (time-averaged) crop coefficients, Kc,
... for non stressed, well-managed crops" - directly from the official FAO
document (saved locally at ml/datasets/fao56/fao56_chapter6_table12.html,
fetched from https://www.fao.org/4/x0490e/x0490e0b.htm) rather than from
memory, so every Kc value in this app traces back to a verifiable primary
source, not a recalled approximation.

Not every recommendation-engine crop has a row in Table 12. Where a crop-
specific row exists, it's used directly. Where it doesn't but the crop is a
pulse/legume, FAO-56's own generic "Beans, dry and Pulses" group value is
used (Table 12 is explicitly organized so "coefficients... within the same
group" can stand in for a specific member - see the FAO-56 text). Crops with
neither a specific row nor a defensible generic category are left out
entirely rather than guessed at.

Run:
    python ml/water_requirement/build_kc_reference.py
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
SOURCE_HTML = ROOT / "ml" / "datasets" / "fao56" / "fao56_chapter6_table12.html"
MODELS_DIR = ROOT / "models"

# recommendation-engine crop -> (FAO-56 Table 12 row name, category, note)
# category "specific": this exact crop has its own Table 12 row.
# category "generic_legume": no crop-specific row exists; FAO-56's generic
# "Beans, dry and Pulses" group value is used instead (documented above).
CROP_SOURCE_MAP = {
    "rice": ("Rice", "specific", None),
    "maize": ("Maize, Field (grain)(field corn)", "specific", None),
    "chickpea": ("Chick pea", "specific", None),
    "mungbean": ("Green Gram and Cowpeas", "specific", None),
    "lentil": ("Lentil", "specific", None),
    "cotton": ("Cotton", "specific", "Table 12 gives a range (1.15-1.20); midpoint used."),
    "banana": ("Banana", "specific", "Year-2 (mature plant) row used."),
    "grapes": ("Grapes", "specific", 'Table/raisin variety row used (not wine grapes).'),
    "watermelon": ("Watermelon", "specific", None),
    "muskmelon": ("Cantaloupe", "specific", "Botanically the same species (Cucumis melo) as muskmelon."),
    "apple": ("Apples, Cherries, Pears19", "specific", "'No ground cover' row used; Kc_mid is stable across the frost/no-frost variants."),
    "orange": ("Citrus, no ground cover21", "specific", "70% canopy (mature orchard) row used."),
    "coffee": ("Coffee", "specific", "'Bare ground cover' row used (not the 'with weeds' variant)."),
    "kidneybeans": ("Beans, dry and Pulses", "generic_legume", None),
    "blackgram": ("Beans, dry and Pulses", "generic_legume", None),
    "pigeonpeas": ("Beans, dry and Pulses", "generic_legume", None),
    "mothbeans": ("Beans, dry and Pulses", "generic_legume", None),
}

# Crops with no Table 12 row and no defensible generic category - intentionally excluded.
UNSUPPORTED_CROPS = ["pomegranate", "mango", "papaya", "coconut", "jute"]

# Special multi-row lookups (crop group headers / sub-rows aren't single (group, name) pairs)
SPECIAL_ROW_INDEX = {
    "Grapes": "- Table or Raisin",
    "Apples, Cherries, Pears19": "- no ground cover, no frosts",
    "Citrus, no ground cover21": "- 70% canopy",
    "Coffee": "- bare ground cover",
    "Banana": "- 2ndyear",
}


def _clean_kc(raw: str) -> tuple[float, str]:
    """Strip trailing footnote-marker digits from a Table 12 cell value.

    Table 12 cells are e.g. "1.152" (=1.15, footnote 2) or "0.60-0.35" plain,
    or "0.60-0.3511" (=0.60-0.35, footnote 11). Returns (numeric_value, raw_text).
    For a range "a-b", the midpoint is returned as the numeric value.
    """
    raw = raw.strip()
    # range like "1.15-1.20" possibly with trailing footnote digits after the second number
    m = re.match(r"^(\d\.\d{2})-(\d\.\d{2})(\d{0,2})$", raw)
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        return round((lo + hi) / 2, 3), raw
    # plain value possibly with trailing footnote digits, e.g. "1.152" -> 1.15
    m = re.match(r"^(\d\.\d{2})(\d{0,2})$", raw)
    if m:
        return float(m.group(1)), raw
    raise ValueError(f"Could not parse Kc cell: {raw!r}")


def parse_table12() -> dict[str, dict]:
    if not SOURCE_HTML.exists():
        raise FileNotFoundError(f"FAO-56 source page not found at {SOURCE_HTML}")

    with open(SOURCE_HTML, encoding="utf-8", errors="replace") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")
    marker = soup.find(string=re.compile(r"TABLE 12\. Single"))
    table = marker.find_next("table")
    rows = table.find_all("tr")

    # Build a lookup of crop_name -> list of (subrow_label_or_None, kc_mid_raw)
    raw_rows: dict[str, list[tuple[str | None, str]]] = {}
    current_name = None
    for tr in rows[1:]:
        tds = tr.find_all("td")
        if len(tds) == 1:
            continue  # group section header
        if len(tds) < 5:
            continue
        first_cell = tds[0].get_text(strip=True)
        vals = [td.get_text(strip=True) for td in tds[1:]]

        if first_cell:
            current_name = first_cell
            subrow_label = None
            kc_mid_raw = vals[1] if len(vals) > 1 else vals[0]
        else:
            subrow_label = vals[0]
            kc_mid_raw = vals[2] if len(vals) > 2 else None

        if current_name and kc_mid_raw:
            raw_rows.setdefault(current_name, []).append((subrow_label, kc_mid_raw))

    return raw_rows


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    raw_rows = parse_table12()

    reference: dict[str, dict] = {}
    for crop, (source_name, category, note) in CROP_SOURCE_MAP.items():
        if source_name not in raw_rows:
            raise ValueError(f"Expected FAO-56 row '{source_name}' for crop '{crop}' not found in parsed table")

        entries = raw_rows[source_name]
        wanted_subrow = SPECIAL_ROW_INDEX.get(source_name)
        if wanted_subrow:
            match = next((e for e in entries if e[0] == wanted_subrow), None)
            if match is None:
                raise ValueError(f"Sub-row '{wanted_subrow}' not found for '{source_name}' (got {entries})")
            kc_mid_raw = match[1]
        else:
            kc_mid_raw = entries[0][1]

        kc_mid, raw_text = _clean_kc(kc_mid_raw)
        reference[crop] = {
            "kc_mid": kc_mid,
            "kc_mid_raw_table_value": raw_text,
            "fao56_row": source_name,
            "category": category,
            "note": note,
        }

    report = {
        "source": "FAO Irrigation and Drainage Paper No. 56 (Allen et al., 1998), Chapter 6, Table 12",
        "source_url": "https://www.fao.org/4/x0490e/x0490e0b.htm",
        "local_copy": str(SOURCE_HTML.relative_to(ROOT)),
        "built_at": datetime.now(timezone.utc).isoformat(),
        "supported_crops": sorted(reference.keys()),
        "unsupported_crops": sorted(UNSUPPORTED_CROPS),
    }

    with open(MODELS_DIR / "water_kc_reference.json", "w") as f:
        json.dump(reference, f, indent=2)
    with open(MODELS_DIR / "water_kc_reference_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Extracted Kc_mid for {len(reference)} crops:")
    for crop, data in sorted(reference.items()):
        print(f"  {crop:14s} Kc_mid={data['kc_mid']:.3f}  ({data['category']}, source row: {data['fao56_row']})")
    print(f"\nSaved water_kc_reference.json + water_kc_reference_report.json to {MODELS_DIR}")


if __name__ == "__main__":
    main()

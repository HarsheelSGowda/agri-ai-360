# Dataset

This project uses three independent public data sources — one per module. They are not merged;
each has its own build/training script, model artifacts and metrics file.

## 1. Crop Recommendation

### Source

**Crop Recommendation Dataset** — a public dataset widely used for crop-recommendation
classification tasks, originally published on Kaggle by Atharva Ingle
(`atharvaingle/crop-recommendation-dataset`). This project fetched a mirror of the identical CSV
from a public GitHub repository and stored it locally at
[`ml/datasets/crop_recommendation.csv`](../ml/datasets/crop_recommendation.csv) so training is
fully reproducible offline.

### Shape

- **2,200 rows**, no missing values, no duplicate rows (verified in `train.py`'s cleaning step).
- **22 crop classes** (labels), each with exactly 100 samples: rice, maize, chickpea, kidneybeans,
  pigeonpeas, mothbeans, mungbean, blackgram, lentil, pomegranate, banana, mango, grapes,
  watermelon, muskmelon, apple, orange, papaya, coconut, cotton, jute, coffee.
- **7 numeric features**:

| Column | Meaning | Typical range in dataset |
|---|---|---|
| `N` | Nitrogen content in soil (kg/ha) | ~0–140 |
| `P` | Phosphorus content in soil (kg/ha) | ~5–145 |
| `K` | Potassium content in soil (kg/ha) | ~5–205 |
| `temperature` | Ambient temperature (°C) | ~9–44 |
| `humidity` | Relative humidity (%) | ~14–100 |
| `ph` | Soil pH | ~3.5–10 |
| `rainfall` | Rainfall (mm) | ~20–300 |

### Preprocessing

1. Drop rows with any missing value in the 7 features or the label (none were found on this copy).
2. Drop exact duplicate rows (none were found on this copy).
3. Label-encode the 22 crop names with `sklearn.preprocessing.LabelEncoder` (encoder saved to
   `models/label_encoder.joblib` so the API can decode predictions back to crop names).
4. No feature scaling is applied — Random Forest, Gradient Boosting and XGBoost are scale-invariant;
   SVM is trained on raw features in this MVP (a documented limitation — see below).

### Known limitations of this dataset

- It is a clean, synthetic-feeling benchmark (each class has exactly 100 samples, classes are
  fully separable) — this is why all four models score 98–99% accuracy. Real agronomic field data
  is noisier; production use would need a much larger, messier, India/region-specific dataset with
  proper train/production distribution monitoring.
- It does not include soil type, location, season or irrigation availability, even though the
  UI's Soil Analysis and Farm Creation forms collect them — those fields are currently used for the
  rule-based soil-health score and risk dashboard, not yet as ML model inputs. Extending the model
  to consume them is listed in [future-scope.md](future-scope.md).
- SVM was trained without feature scaling (a `StandardScaler` step is the documented next
  improvement for that specific model — see `ml/crop_recommendation/train.py`).

## 2. Yield Prediction (Phase 2)

### Source

**India crop production records** — real district-level Indian agricultural statistics (state,
district, crop, year, season, area, production, yield), 1997–2020, sourced from a public GitHub
mirror (`Aditya12084/Crop-Statistics-India`, `data/main_crops.csv`) of what is commonly distributed
as India's official crop-production statistics (originally from data.gov.in / Ministry of
Agriculture releases, as popularized in several public "Crop Production in India" datasets). Stored
locally at [`ml/datasets/india_crop_production.csv`](../ml/datasets/india_crop_production.csv).

### Shape

- **326,846 rows** before cleaning → **325,280 after** (1,566 rows with `yield <= 0` dropped as
  data-entry artifacts; zero duplicate rows).
- **54 distinct crops**, **37 states/union territories**, **6 seasons** (Kharif, Rabi, Autumn,
  Summer, Winter, Whole Year), years 1997–2020.
- `yield` (tonnes/hectare) is already present in the source data as `production / area` — this
  project does not compute or estimate it.

### Features used

`state`, `crop`, `season` — all categorical, ordinal-encoded (`sklearn.preprocessing.OrdinalEncoder`,
unknown categories mapped to a sentinel value so an unrecognized state/season is rejected rather
than silently mispredicted — see `app/services/yield_service.py`). `year` and `district` are present
in the raw data but intentionally **not** used as features — see limitations below.

### Known limitations of this dataset

- **Crop vocabulary mismatch with the recommendation engine.** This dataset's 54 crop names
  (Indian agricultural terminology, e.g. "Arhar/Tur", "Moong(Green Gram)", "Cotton(Lint)") don't
  match the recommendation engine's 22 crop labels 1:1. Only **11 of 22** have a defensible mapping
  (`CROP_ALIAS_MAP` in `app/services/yield_service.py`): rice, maize, chickpea→Gram,
  pigeonpeas→Arhar/Tur, mothbeans→Moth, mungbean→Moong(Green Gram), blackgram→Urad, lentil→Masoor,
  cotton→Cotton(Lint), jute, banana. The other 11 (kidneybeans, pomegranate, mango, grapes,
  watermelon, muskmelon, apple, orange, papaya, coconut, coffee) have **no yield estimate available**
  — the UI says so explicitly rather than guessing.
- **`year` was dropped as a feature on purpose.** Including it would let the model pick up a
  historical trend, but predicting for the current year would then require extrapolating past the
  training data's 2020 ceiling — a form of quiet fabrication. Dropping it means every prediction is
  a "typical yield for this state/crop/season across 1997–2020," not a forecast for a specific year.
  This is stated in the UI next to every yield estimate.
- **State/season/crop only — no soil, weather, or farm-specific signal.** This is a national/state-
  level historical-statistics model, not a per-farm yield forecaster. It cannot account for an
  individual farm's actual soil health, irrigation, or this season's specific weather. This is a
  real methodological limitation, stated in `docs/ml-methodology.md` and in the UI tooltip.
- District-level granularity exists in the raw data but isn't used as a feature (the app only
  collects farm *location* as free text, not a validated district), so predictions are at
  state-level resolution.

## 3. Profit Prediction (Phase 2)

### Source

**Agmarknet mandi price records** — real Indian government market-price transactions (state,
district, market, variety, group, arrivals, min/max/modal price in Rs./quintal, date), calendar
year **2016** (the most recent full year available in the public mirror used:
`iancovert/Agmarknet` on GitHub). Downloaded per-crop and stored locally under
[`ml/datasets/agmarknet_prices/`](../ml/datasets/agmarknet_prices/). Not merged with the yield
dataset — profit prediction calls the yield model internally and combines its output with this
price data at request time (see `app/services/profit_service.py`).

This is **not a trained model** — it's a real-data-derived reference lookup table
(median price per crop per state), built once by
[`ml/profit_prediction/build_price_reference.py`](../ml/profit_prediction/build_price_reference.py)
into `models/price_reference.json`. Median (not mean) is used specifically because the raw data
contains data-entry outliers (e.g. a single ₹210,000/quintal rice row among a ~₹2,350 median) —
an IQR-based filter removes the most extreme rows before aggregating, documented in the script.

### Crops covered

Only **6 crops** have price data in the source mirror that maps cleanly to the recommendation
engine's vocabulary: rice, maize, pigeonpeas (Arhar/Tur), blackgram (Urd), mungbean (Moong),
lentil (Masur). This is a *subset* of the 11 crops the yield model supports — profit prediction is
only offered where **both** a yield estimate and a price exist.

**Chickpea was deliberately excluded**, even though the source repo has a "Kabuli Chana" (white
chickpea) price series: Kabuli chana is a distinct, higher-value commercial variety from the
desi/Bengal gram most farmers mean by "chickpea" in this context, and its price would be a
materially misleading stand-in. Rather than silently substitute a different crop's price, the app
reports chickpea profit as unsupported.

### Known limitations

- **Prices are from 2016 and are not inflation-adjusted.** No inflation-rate assumption is applied
  anywhere in this codebase — doing so would mean presenting an invented adjustment factor as if it
  were real data, which is exactly the kind of fabrication this project's rules prohibit. The UI
  states the price year and source next to every profit estimate so this is never hidden.
- **Cost of cultivation is not from any dataset.** No public, cleanly-structured cost-of-cultivation
  data (e.g. from India's Commission for Agricultural Costs and Prices) was found in a usable form
  during this project. Rather than invent per-crop cost figures and present them as data-driven,
  the farmer supplies their own cost-per-acre estimate, and the backend only computes
  `Revenue - Cost`. This is a deliberate design choice, not an oversight — see
  `docs/ml-methodology.md`.
- **State-level price, not local mandi price.** A farmer's actual nearest market may trade well
  above or below their state's median. When a crop has no recorded trades at all in the selected
  state, the app falls back to the national median and labels that explicitly
  (`price_source: "national_fallback"`).

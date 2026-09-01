# Dataset

This project uses two independent public datasets — one per ML module. They are not merged; each
has its own training script, model artifacts and metrics file.

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

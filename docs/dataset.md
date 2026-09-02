# Dataset

This project uses five independent public data sources — one per module (one reused twice). They
are not merged; each has its own build/training script, model artifacts and metrics file.

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

## 4. Water Requirement (Phase 2)

### Source

Two official FAO documents, fetched directly and parsed programmatically (not transcribed from
memory) — both saved locally under [`ml/datasets/fao56/`](../ml/datasets/fao56/):

- **FAO Irrigation and Drainage Paper No. 56** (Allen, Pereira, Raes & Smith, 1998), Chapter 6,
  **Table 12** — "Single (time-averaged) crop coefficients, Kc" — fetched from
  `https://www.fao.org/4/x0490e/x0490e0b.htm`, saved as `fao56_chapter6_table12.html`, extracted by
  [`ml/water_requirement/build_kc_reference.py`](../ml/water_requirement/build_kc_reference.py) into
  `models/water_kc_reference.json`.
- **FAO "Crop Water Needs"** (Irrigation Water Management Training Manual No. 3), Chapter 3,
  **Table 4** — "Mean daily percentage (p) of annual daytime hours for different latitudes" —
  fetched from `https://www.fao.org/4/s2022e/s2022e07.htm`, saved as
  `fao_blaney_criddle_table4.html`, extracted by
  [`ml/water_requirement/build_p_reference.py`](../ml/water_requirement/build_p_reference.py) into
  `models/water_p_reference.json`.

### Crop coefficients (Kc) — 17 crops covered

13 crops have a **crop-specific** Table 12 row (rice, maize, chickpea, mungbean, lentil, cotton,
banana, grapes, watermelon, muskmelon [mapped to the botanically identical "Cantaloupe" row],
apple, orange, coffee). 4 more (kidneybeans, blackgram, pigeonpeas, mothbeans) have no
crop-specific row, so FAO-56's own generic **"Beans, dry and Pulses"** group value is used instead
— this is FAO-56's documented intent for its group structure, not an invented substitution, and the
API/UI label these explicitly as `"category": "generic_legume"`. 5 crops (pomegranate, mango,
papaya, coconut, jute) have neither a specific row nor a defensible generic category and are
reported as unsupported.

### An honesty note on how this module's formula was chosen

An earlier implementation tried to derive the Blaney-Criddle "p" factor from pure solar-geometry
day length (day length ÷ 12) instead of using FAO's own table. That produced a reference ET₀ of
**~23 mm/day** for a real July/Nagpur test case — physically implausible (real-world ET₀ rarely
exceeds ~8–10 mm/day even in extreme desert heat) and roughly 3–4× higher than the ~6 mm/day the
real FAO Table 4 gives for the same input. Rather than ship a self-derived formula that looked
plausible but was empirically wrong, the module was rebuilt to fetch and parse FAO's actual
published Table 4. This is recorded here deliberately: a formula "written correctly" from a
half-remembered principle is still a fabrication risk if it isn't checked against a real,
citable source — checking is what caught it.

### Known limitations

- **State-level, not GPS-level, latitude.** Each state's representative latitude is its capital
  city's coordinates (real, verifiable geography), not the farm's actual location — the app only
  collects free-text location, not GPS.
- **Interpolated, not tabulated, latitude bands.** FAO Table 4 is tabulated in 5° latitude steps;
  values between steps are linearly interpolated (`app/services/water_service.py::_lookup_p`).
- **Blaney-Criddle is explicitly a rough method.** FAO's own documentation for this formula states
  it "is not very accurate; it provides a rough estimate... only," and can be off by up to ~40-60%
  in extreme wind/humidity conditions the formula doesn't account for. This is a planning-level
  estimate, not a substitute for local agronomic advice — stated in the UI on every result.
  Penman-Monteith (FAO-56's primary recommended method) would be more accurate but requires wind
  speed, solar radiation and humidity data this app's weather layer doesn't provide.
- **Only mid-season (peak) crop coefficient is used.** Kc changes through a crop's growth stages
  (initial/development/mid-season/late-season); this module only uses Kc_mid (peak water demand),
  not a full-season water-balance curve, since the app doesn't collect planting dates.

## 5. Yield Risk (Phase 2, ML-based)

### Source

The **same** India crop production dataset used for yield prediction
([`ml/datasets/india_crop_production.csv`](../ml/datasets/india_crop_production.csv)) — no new
dataset was needed. This module trains a classifier on it with a different, purpose-built label.

### Label construction

For each of the 54 crops in the dataset, that crop's own yield values (across every state, season
and year recorded) are split into **tertiles**: the bottom third of that crop's yield distribution
is labeled `HIGH` risk, the middle third `MEDIUM`, the top third `LOW`. Tertiles are computed
**per crop**, never across crops — yield scale varies by roughly an order of magnitude between
crops (e.g. rice ~2 t/ha vs. banana ~29 t/ha), so a single global threshold would be meaningless.
Crops with fewer than 60 records are dropped before training (too few for a reliable tertile split).

**What the resulting LOW/MEDIUM/HIGH label actually means:** how a (state, crop, season)
combination's yield has historically ranked *nationally, relative to that same crop's own
distribution* — a regional historical performance tier. It is explicitly **not** a forecast of
this year's weather, disease, or pest risk: the model has no weather, soil, or year-specific input
at inference time.

### A methodology correction, kept in the repo on purpose

The first version of this model used a random 80/20 row split and reported a flattering-looking
**64.5% test accuracy** — but a proper 5-fold cross-validation on the same data came back at only
**36.9%**, barely above the 33.3% baseline for guessing among 3 balanced classes. The cause: the
same (state, crop, season) triple recurs across ~20 different years in this dataset, so a random
row split puts near-duplicate feature rows (identical inputs, different year) on both sides of the
split — the model could partly memorize `X -> majority label` from training rather than generalize.
The fix was a **temporal split**: train on 1997–2015, test on entirely unseen years (2016–2020),
with 5-fold cross-validation grouped by year within the training set so no fold shares a year with
another. The corrected, honest result — **Random Forest, 55.3% test accuracy, evaluated on years
the model never saw during training** — is what's actually shipped. This is recorded here (and in
`docs/ml-methodology.md`) as a deliberate reminder that comparing a headline metric against a
second, differently-computed metric is what catches this kind of leakage — a single flattering
number in isolation would not have.

### Sanity check against real-world knowledge

Punjab is widely known as India's highest-yielding rice-growing state (intensively irrigated,
Green Revolution heartland). The trained model predicts **LOW risk (100% confidence)** for
rice/Punjab/Kharif and **HIGH risk (73%)** for rice/Maharashtra/Kharif for the same season —
matching real agronomic expectation, which is a good sign the model learned a genuine regional
signal rather than noise, despite the modest 55% accuracy on a 3-class problem.

### Known limitations

- 55.3% accuracy on a 3-class problem (33.3% baseline) is a **real but modest** signal — useful as
  a rough regional indicator, not a precise risk score. The UI shows the full LOW/MEDIUM/HIGH
  probability breakdown, not just the top class, so the farmer can see how confident the model
  actually is.
- Covers 11 of 22 recommendation-engine crops — the same crops (and the same `CROP_ALIAS_MAP`) as
  yield prediction, since it's trained on the same dataset.
- This is a *different kind of risk* from the rule-based weather/soil/water/disease risk dashboard
  (`risk_service.py`, `/app/risk`) — that one uses live weather + soil signals a farmer actually
  controls; this one is a historical regional-performance signal. Both are shown, both are labeled
  for what they are, and neither replaces the other.

## 6. Disease Detection (Phase 3)

### Source

**PlantVillage-Dataset** (`spMohanty/PlantVillage-Dataset` on GitHub) — the canonical public
leaf-disease image dataset, 54,306 images across 38 crop-disease classes, released alongside
Mohanty, Hughes & Salathé (2016), *"Using Deep Learning for Image-Based Plant Disease Detection."*
Only the `raw/color` classes matching this project's existing 22-crop recommendation list were
fetched (a git sparse-checkout of the upstream repo, scratch input, not committed to this repo —
see `ml/disease_detection/prepare_dataset.py`): Apple, Corn (maize), Grape and Orange, 13 classes
total.

### Sampling

`ml/disease_detection/prepare_dataset.py` samples a fixed cap of **300 images per class**
(a CPU-trainable dataset size and a git-repo-friendly footprint — full source classes range from
275 to 5,507 images) into [`ml/datasets/plant_disease/`](../ml/datasets/plant_disease/), which IS
committed (manifest at `ml/datasets/plant_disease/manifest.csv` records exactly how many of each
source class's images were available vs. sampled). **Result: 3,875 images across 13 classes**
(one class, `apple__cedar_apple_rust`, has only 275 source images — sampled `min(300, available)`).

| Crop | Classes | Conditions |
|---|---|---|
| Apple | 4 | Apple Scab, Black Rot, Cedar Apple Rust, Healthy |
| Maize (corn) | 4 | Gray Leaf Spot, Common Rust, Northern Leaf Blight, Healthy |
| Grapes | 4 | Black Rot, Esca (Black Measles), Leaf Blight, Healthy |
| Orange | 1 | Citrus Greening (HLB) — only disease class available for this crop in the source |

### Approach: frozen CNN feature extraction, not full fine-tuning

`ml/disease_detection/train.py` runs each image through **MobileNetV3-Small**
(`torchvision.models.mobilenet_v3_small`, ImageNet-pretrained weights, all convolutional layers
frozen) to get a 576-dimensional feature vector, then trains classical classifiers (Random Forest,
Gradient Boosting, Logistic Regression) on those vectors — the same "train several algorithms,
compare real metrics, pick the winner" pattern used everywhere else in this project. Full
fine-tuning of the CNN backbone was not attempted: ~300 images/class across 13 classes is too small
to fine-tune convolutional layers from scratch without overfitting, and it would be far slower on
CPU. A frozen ImageNet-pretrained backbone as a fixed feature extractor is a standard,
well-established transfer-learning technique for small image datasets.

### Known limitations of this dataset

- **PlantVillage images are lab-condition photos** — controlled backgrounds, consistent lighting,
  single leaf per image. Real farmer-submitted phone photos (cluttered backgrounds, variable
  lighting, multiple leaves, motion blur) are a materially different distribution; real-world
  accuracy on field photos will likely be lower than the 97.9% test accuracy measured on this
  dataset's own held-out split. This is a widely documented limitation of PlantVillage-based
  disease classifiers in the literature, not specific to this implementation.
- **Only 13 of 38 upstream PlantVillage classes are covered** — the subset matching this project's
  22-crop recommendation list (apple, maize, grapes, orange). The other 18 recommendation-engine
  crops have no disease model at all; the UI reports this honestly (`supported_crops` in the API
  response) rather than guessing on an unsupported crop.
- **Orange has only 1 class** (Citrus Greening / HLB) — no healthy-orange or other-disease class
  exists in the source dataset for this crop, so the model cannot distinguish a healthy orange leaf
  from a diseased one; any orange-crop image will be classified as HLB.
- **300-image-per-class cap** (vs. thousands available for some classes, e.g. orange HLB had 5,507)
  trades a larger, more diverse training set for a CPU-trainable, git-repo-friendly dataset size —
  a documented trade-off, not an oversight.

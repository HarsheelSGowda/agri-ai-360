# Dataset

## Source

**Crop Recommendation Dataset** — a public dataset widely used for crop-recommendation
classification tasks, originally published on Kaggle by Atharva Ingle
(`atharvaingle/crop-recommendation-dataset`). This project fetched a mirror of the identical CSV
from a public GitHub repository and stored it locally at
[`ml/datasets/crop_recommendation.csv`](../ml/datasets/crop_recommendation.csv) so training is
fully reproducible offline.

## Shape

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

## Preprocessing

1. Drop rows with any missing value in the 7 features or the label (none were found on this copy).
2. Drop exact duplicate rows (none were found on this copy).
3. Label-encode the 22 crop names with `sklearn.preprocessing.LabelEncoder` (encoder saved to
   `models/label_encoder.joblib` so the API can decode predictions back to crop names).
4. No feature scaling is applied — Random Forest, Gradient Boosting and XGBoost are scale-invariant;
   SVM is trained on raw features in this MVP (a documented limitation — see below).

## Known limitations of this dataset

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

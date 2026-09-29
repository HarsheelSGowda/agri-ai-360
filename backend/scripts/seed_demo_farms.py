"""
AgriAI 360 - Demo data seeder for the 3 existing presentation farms.

Populates realistic soil, crop-recommendation, leaf-disease, notification and
IoT demo data for farm_id 1/2/3 (farmer_id 1/2/3) so the dashboard and every
implemented feature has meaningful data to show during a live demo.

This does NOT fabricate results: every OUTPUT value (soil health score, top
crop, risk level, disease diagnosis) is computed live by the same real
trained models / real service functions the API routes call
(app.services.ml_service.predict_top_k, app.services.disease_service.diagnose,
app.services.notification_service.generate_for_farm,
app.services.iot_service.generate_demo_batch). Only the raw INPUT values
(soil test numbers, climate numbers, which sample leaf photo) are hand-picked
to be agronomically realistic for each farm's real location - the same way a
farmer would type numbers into the form.

Disease diagnosis uses real sample photos already checked into
ml/datasets/plant_disease/ (the same PlantVillage-derived training data used
by ml/disease_detection/train.py), run through the real trained classifier -
not a fabricated result.

NOT idempotent: farms 1/2/3 already carry real historical data from prior
manual testing (soil records, crop predictions, notifications) which this
script never touches or deletes - it only INSERTs new rows alongside them.
Re-running this script will add a second set of demo rows for the same three
farms rather than replacing the first. Intended to run once during demo prep.

Run from backend/ (so the default sqlite:///./agriai.db path matches the one
the running app uses - this script reuses app.database.session exactly as
the API does):

    cd backend
    venv/Scripts/python.exe scripts/seed_demo_farms.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = ROOT / "ml" / "datasets" / "plant_disease"

sys.path.insert(0, str(ROOT / "backend"))

from app.database.session import SessionLocal  # noqa: E402
from app.models.disease import DiseaseDetection  # noqa: E402
from app.models.farm import Farm  # noqa: E402
from app.models.prediction import CropPrediction, CropScore  # noqa: E402
from app.models.soil import SoilRecord  # noqa: E402
from app.models.user import Farmer  # noqa: E402
from app.services import iot_service  # noqa: E402
from app.services.disease_service import diagnose  # noqa: E402
from app.services.ml_service import predict_top_k  # noqa: E402
from app.services.notification_service import generate_for_farm  # noqa: E402

# Per-farm realistic demo inputs. Values are agronomically plausible for each
# farm's REAL location (already on file, untouched by this script):
# Bangalore (inland Karnataka, moderate rainfall), Udupi x2 (coastal
# Karnataka, high-rainfall paddy belt - alluvial soil is fertile there,
# laterite is common and less fertile/more acidic - both real characteristics
# of that region, not invented).
PLAN = {
    1: {  # Test Farm, Bangalore, Karnataka, Loamy, no irrigation
        "soil": dict(nitrogen=85, phosphorus=48, potassium=45, ph=6.4,
                     soil_type="Loamy", organic_carbon=0.7, moisture=22, electrical_conductivity=0.9),
        "crop_input": dict(nitrogen=85, phosphorus=48, potassium=45,
                            temperature=24.5, humidity=62.0, ph=6.4, rainfall=105.0),
        "disease_class": "maize__healthy",
    },
    2: {  # Disha Farm, Udupi, Alluvial, irrigation available
        "soil": dict(nitrogen=95, phosphorus=55, potassium=50, ph=6.0,
                     soil_type="Alluvial", organic_carbon=0.9, moisture=35, electrical_conductivity=1.0),
        "crop_input": dict(nitrogen=95, phosphorus=55, potassium=50,
                            temperature=27.0, humidity=85.0, ph=6.0, rainfall=225.0),
        "disease_class": "apple__cedar_apple_rust",
    },
    3: {  # Demo Farm, Udupi, Karnataka, Laterite, irrigation available
        "soil": dict(nitrogen=55, phosphorus=28, potassium=30, ph=5.3,
                     soil_type="Laterite", organic_carbon=0.4, moisture=18, electrical_conductivity=0.6),
        "crop_input": dict(nitrogen=55, phosphorus=28, potassium=30,
                            temperature=26.0, humidity=78.0, ph=5.3, rainfall=180.0),
        "disease_class": "maize__gray_leaf_spot",
    },
}

TARGET_FARM_IDS = (1, 2, 3)


def sample_image_bytes(disease_class: str) -> bytes:
    class_dir = DATASET_ROOT / disease_class
    files = sorted(class_dir.iterdir())
    if not files:
        raise RuntimeError(f"No sample images found for {disease_class}")
    return files[0].read_bytes()


def main() -> None:
    db = SessionLocal()
    report: dict[int, dict] = {}
    try:
        farms = db.query(Farm).filter(Farm.id.in_(TARGET_FARM_IDS)).all()
        found_ids = {f.id for f in farms}
        assert found_ids == set(TARGET_FARM_IDS), f"Expected farms {TARGET_FARM_IDS}, found {found_ids}"

        for farm in farms:
            plan = PLAN[farm.id]
            farmer = db.query(Farmer).filter(Farmer.id == farm.farmer_id).one()
            entry = {"farm_name": farm.name, "farm_id": farm.id}

            # 1) Soil record - mirrors POST /farms/{id}/soil
            soil = SoilRecord(farm_id=farm.id, **plan["soil"])
            db.add(soil)
            db.flush()
            entry["soil_record_id"] = soil.id

            # 2) Crop recommendation - mirrors POST /predict/top-crops (farm_id given)
            result = predict_top_k(plan["crop_input"])
            top = result["top_crops"][0]
            prediction = CropPrediction(
                farm_id=farm.id,
                input_json=plan["crop_input"],
                top_crop=top["crop"],
                top_score=top["probability"],
            )
            db.add(prediction)
            db.flush()
            for rank, item in enumerate(result["top_crops"], start=1):
                db.add(CropScore(prediction_id=prediction.id, crop=item["crop"], probability=item["probability"], rank=rank))
            entry["crop_prediction_id"] = prediction.id
            entry["top_crop"] = top["crop"]
            entry["top_crop_probability"] = round(top["probability"], 4)
            entry["model_used"] = result["model_used"]

            # 3) Disease diagnosis - mirrors POST /predict/disease (farm_id given),
            #    run on a REAL sample leaf photo through the real trained model.
            image_bytes = sample_image_bytes(plan["disease_class"])
            diag = diagnose(image_bytes)
            top_diag = diag["top_prediction"]
            detection = DiseaseDetection(
                farm_id=farm.id,
                crop=top_diag["crop"],
                condition=top_diag["condition"],
                is_healthy=top_diag["is_healthy"],
                probability=top_diag["probability"],
                model_used=diag["model_used"],
            )
            db.add(detection)
            db.flush()
            entry["disease_detection_id"] = detection.id
            entry["disease_result"] = (
                f"{top_diag['crop']} / {top_diag['condition']} "
                f"({top_diag['probability']:.1%}, {'healthy' if top_diag['is_healthy'] else 'NOT healthy'})"
            )

            db.flush()  # so notification_service can see the rows just added

            # 4) Personalized notifications - mirrors POST /notifications/generate
            created_notes = generate_for_farm(db, farm, farmer)
            entry["notifications_created"] = [n.title for n in created_notes]

            # 5) IoT demo sensor readings - mirrors POST /iot/demo/seed
            iot_rows = iot_service.generate_demo_batch(db, farm.id)
            entry["iot_readings"] = [(r.sensor_type, r.value, r.unit) for r in iot_rows]

            report[farm.id] = entry

        db.commit()
        print("COMMIT OK")
        for fid, e in report.items():
            print(f"\n--- Farm {fid}: {e['farm_name']} ---")
            for k, v in e.items():
                print(f"  {k}: {v}")

    except Exception:
        db.rollback()
        print("ROLLED BACK - an error occurred, no changes were saved")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

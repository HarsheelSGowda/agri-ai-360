"""
AgriAI 360 - Disease Detection: dataset preparation (Phase 3)

Source: PlantVillage-Dataset (spMohanty/PlantVillage-Dataset on GitHub), the
canonical public leaf-disease image dataset (54,306 images, 38 crop-disease
classes, originally released alongside Mohanty, Hughes & Salathe 2016,
"Using Deep Learning for Image-Based Plant Disease Detection"). Only the
raw/color images for classes matching AgriAI 360's existing 22-crop
recommendation list were fetched (git sparse-checkout of the upstream repo,
not committed to this repo - see docs/dataset.md): Apple, Corn (maize),
Grape and Orange, 13 classes total.

This script samples a fixed cap of images per class (for a CPU-trainable
dataset size and a git-repo-friendly footprint) into
ml/datasets/plant_disease/<label>/, which IS committed. The full upstream
checkout is scratch input, deleted after this runs.

Run:
    python ml/disease_detection/prepare_dataset.py
"""

from __future__ import annotations

import random
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "ml" / "datasets" / "plantvillage_raw" / "raw" / "color"
DEST_DIR = ROOT / "ml" / "datasets" / "plant_disease"
MAX_PER_CLASS = 300
RANDOM_STATE = 42

# source folder name -> (crop, human-readable condition, is_healthy)
CLASS_MAP: dict[str, tuple[str, str, bool]] = {
    "Apple___Apple_scab": ("apple", "Apple Scab", False),
    "Apple___Black_rot": ("apple", "Black Rot", False),
    "Apple___Cedar_apple_rust": ("apple", "Cedar Apple Rust", False),
    "Apple___healthy": ("apple", "Healthy", True),
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": ("maize", "Gray Leaf Spot", False),
    "Corn_(maize)___Common_rust_": ("maize", "Common Rust", False),
    "Corn_(maize)___Northern_Leaf_Blight": ("maize", "Northern Leaf Blight", False),
    "Corn_(maize)___healthy": ("maize", "Healthy", True),
    "Grape___Black_rot": ("grapes", "Black Rot", False),
    "Grape___Esca_(Black_Measles)": ("grapes", "Esca (Black Measles)", False),
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": ("grapes", "Leaf Blight", False),
    "Grape___healthy": ("grapes", "Healthy", True),
    "Orange___Haunglongbing_(Citrus_greening)": ("orange", "Citrus Greening (HLB)", False),
}


def slugify(crop: str, condition: str) -> str:
    return f"{crop}__{condition.lower().replace(' ', '_').replace('(', '').replace(')', '')}"


def main() -> None:
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(
            f"{SOURCE_DIR} not found. Fetch the upstream PlantVillage-Dataset raw/color folders "
            "for the classes in CLASS_MAP first (see docs/dataset.md)."
        )

    rng = random.Random(RANDOM_STATE)
    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)
    DEST_DIR.mkdir(parents=True)

    manifest_lines = ["label,crop,condition,is_healthy,source_class,sampled,available"]
    for source_name, (crop, condition, is_healthy) in CLASS_MAP.items():
        src = SOURCE_DIR / source_name
        files = sorted(p for p in src.iterdir() if p.is_file())
        rng.shuffle(files)
        sampled = files[:MAX_PER_CLASS]

        label = slugify(crop, condition)
        dest = DEST_DIR / label
        dest.mkdir(parents=True, exist_ok=True)
        for f in sampled:
            shutil.copy2(f, dest / f.name)

        print(f"{label}: {len(sampled)}/{len(files)} images")
        manifest_lines.append(f"{label},{crop},{condition},{is_healthy},{source_name},{len(sampled)},{len(files)}")

    (DEST_DIR / "manifest.csv").write_text("\n".join(manifest_lines) + "\n")
    print(f"\nPrepared dataset at {DEST_DIR}")


if __name__ == "__main__":
    main()

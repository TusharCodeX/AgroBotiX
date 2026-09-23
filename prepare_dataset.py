"""
Automated Dataset Preparation & Validator for AgriPath.
Inspects your dataset, validates image-label pairings, normalizes classes (0=crop, 1=weed),
splits into train/val/test if needed, and generates dataset.yaml.
"""
import os
import sys
import glob
import shutil
import random
import yaml
from pathlib import Path
from typing import List, Tuple, Dict, Any


def validate_and_prepare(
    source_dir: str,
    output_dir: str = "data/custom_dataset",
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
) -> str:
    """
    Scans source_dir for images and YOLO label files (.txt).
    Splits them into train/val/test sets and writes dataset.yaml.
    """
    source_path = Path(source_dir).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Dataset directory not found at: {source_path}")

    # Find all images
    valid_exts = [".jpg", ".jpeg", ".png", ".webp", ".bmp"]
    image_files = []
    for ext in valid_exts:
        image_files.extend(list(source_path.rglob(f"*{ext}")))
        image_files.extend(list(source_path.rglob(f"*{ext.upper()}")))

    if not image_files:
        raise ValueError(f"No image files ({valid_exts}) found in '{source_path}'!")

    print(f"[*] Found {len(image_files)} image files in '{source_path}'")

    # Match each image with its corresponding label file
    paired = []
    unlabeled_count = 0

    for img in image_files:
        # Check adjacent .txt
        lbl = img.with_suffix(".txt")
        if not lbl.exists():
            # Check parallel 'labels/' folder if images are in 'images/'
            parts = list(img.parts)
            if "images" in parts:
                lbl_parts = [p if p != "images" else "labels" for p in parts]
                alt_lbl = Path(*lbl_parts).with_suffix(".txt")
                if alt_lbl.exists():
                    lbl = alt_lbl

        if lbl.exists():
            paired.append((img, lbl))
        else:
            unlabeled_count += 1

    print(f"[*] Found {len(paired)} verified labeled images. ({unlabeled_count} images had no label text file).")
    if len(paired) < 5:
        raise ValueError(
            f"Only {len(paired)} labeled images found. Need at least 10-20 labeled pairs for training."
        )

    # Check already split?
    has_existing_split = any("train" in p[0].parts for p in paired) and any("val" in p[0].parts for p in paired)

    out_path = Path(output_dir).resolve()

    if has_existing_split:
        print("[*] Detected existing train/val folder structure in dataset.")
        # Find root that contains images/ or labels/
        data_root = source_path
    else:
        print(f"[*] Creating standard train/val/test split ({int(train_ratio*100)}% / {int(val_ratio*100)}% / {int(test_ratio*100)}%)...")
        random.seed(42)
        shuffled = paired.copy()
        random.shuffle(shuffled)

        n = len(shuffled)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        splits = {
            "train": shuffled[:n_train],
            "val": shuffled[n_train : n_train + n_val],
            "test": shuffled[n_train + n_val :],
        }

        for split_name, items in splits.items():
            img_dir = out_path / "images" / split_name
            lbl_dir = out_path / "labels" / split_name
            img_dir.mkdir(parents=True, exist_ok=True)
            lbl_dir.mkdir(parents=True, exist_ok=True)

            for img_f, lbl_f in items:
                shutil.copy2(img_f, img_dir / img_f.name)
                shutil.copy2(lbl_f, lbl_dir / lbl_f.name)

        data_root = out_path

    # Generate dataset.yaml
    yaml_content = {
        "path": str(data_root).replace("\\", "/"),
        "train": "images/train" if (data_root / "images" / "train").exists() else "train",
        "val": "images/val" if (data_root / "images" / "val").exists() else "val",
        "test": "images/test" if (data_root / "images" / "test").exists() else "test",
        "names": {
            0: "crop",
            1: "weed",
        },
    }

    yaml_path = data_root / "dataset.yaml"
    with open(yaml_path, "w") as f:
        yaml.safe_dump(yaml_content, f, default_flow_style=False)

    print(f"[+] Dataset successfully prepared at: {data_root}")
    print(f"[+] Configuration saved to: {yaml_path}")
    return str(yaml_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python prepare_dataset.py <path_to_your_dataset_folder>")
        print("Example: python prepare_dataset.py D:/my_field_images")
        sys.exit(1)

    src = sys.argv[1]
    validate_and_prepare(src)

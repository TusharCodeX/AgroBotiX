"""
DatasetNinja to YOLOv8 Converter for Crop and Weed Detection.
Converts Supervisely/DatasetNinja JSON annotations to standard YOLO format,
creates 80/10/10 Train/Val/Test splits, and writes dataset.yaml.
"""
import os
import json
import glob
import shutil
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple


def convert_dataset_ninja_to_yolo(
    ninja_data_dir: str = r"C:\Users\royde\Downloads\crop-and-weed-detection-DatasetNinja\data",
    output_dir: str = "data/field_dataset",
    train_ratio: float = 0.80,
    val_ratio: float = 0.10,
    test_ratio: float = 0.10,
) -> str:
    ninja_path = Path(ninja_data_dir).resolve()
    img_dir = ninja_path / "img"
    ann_dir = ninja_path / "ann"

    if not img_dir.exists() or not ann_dir.exists():
        raise FileNotFoundError(f"Missing 'img' or 'ann' folders in: {ninja_path}")

    # Mapping classes: crop -> 0, weed -> 1
    class_map = {
        "crop": 0,
        "weed": 1,
    }

    # Gather matching image and json annotation pairs
    all_imgs = sorted(list(img_dir.glob("*.jpeg")) + list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png")))
    pairs: List[Tuple[Path, Path]] = []

    for img_p in all_imgs:
        ann_p = ann_dir / f"{img_p.name}.json"
        if ann_p.exists():
            pairs.append((img_p, ann_p))

    print(f"[*] Found {len(pairs)} matching Image + JSON Annotation pairs.")
    if not pairs:
        raise ValueError("No matching pairs found!")

    # Shuffle and split into Train, Val, Test
    random.seed(42)
    random.shuffle(pairs)

    n = len(pairs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    splits = {
        "train": pairs[:n_train],
        "val": pairs[n_train : n_train + n_val],
        "test": pairs[n_train + n_val :],
    }

    out_base = Path(output_dir).resolve()
    print(f"[*] Output directory: {out_base}")
    print(f"[*] Splitting: Train ({len(splits['train'])}), Val ({len(splits['val'])}), Test ({len(splits['test'])})")

    total_converted_boxes = 0
    class_counts = {0: 0, 1: 0}

    for split_name, items in splits.items():
        split_img_dir = out_base / "images" / split_name
        split_lbl_dir = out_base / "labels" / split_name
        split_img_dir.mkdir(parents=True, exist_ok=True)
        split_lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_p, ann_p in items:
            # Copy image file
            dest_img = split_img_dir / img_p.name
            shutil.copy2(img_p, dest_img)

            # Parse JSON annotation
            with open(ann_p, "r", encoding="utf-8") as f:
                ann_data = json.load(f)

            h = float(ann_data.get("size", {}).get("height", 512))
            w = float(ann_data.get("size", {}).get("width", 512))

            yolo_lines = []
            for obj in ann_data.get("objects", []):
                cls_title = obj.get("classTitle", "").lower().strip()
                if cls_title not in class_map:
                    continue

                cls_id = class_map[cls_title]
                points = obj.get("points", {}).get("exterior", [])
                if len(points) < 2:
                    continue

                # points[0] = [x1, y1], points[1] = [x2, y2]
                x1, y1 = points[0]
                x2, y2 = points[1]

                # Ensure min/max ordering
                box_x1 = min(x1, x2)
                box_x2 = max(x1, x2)
                box_y1 = min(y1, y2)
                box_y2 = max(y1, y2)

                bw = max(1.0, box_x2 - box_x1)
                bh = max(1.0, box_y2 - box_y1)
                cx = box_x1 + bw / 2.0
                cy = box_y1 + bh / 2.0

                # Normalize to 0.0 - 1.0
                norm_cx = max(0.0, min(1.0, cx / w))
                norm_cy = max(0.0, min(1.0, cy / h))
                norm_bw = max(0.0, min(1.0, bw / w))
                norm_bh = max(0.0, min(1.0, bh / h))

                yolo_lines.append(f"{cls_id} {norm_cx:.6f} {norm_cy:.6f} {norm_bw:.6f} {norm_bh:.6f}")
                total_converted_boxes += 1
                class_counts[cls_id] += 1

            # Save label .txt with same stem
            dest_lbl = split_lbl_dir / f"{img_p.stem}.txt"
            with open(dest_lbl, "w", encoding="utf-8") as f:
                f.write("\n".join(yolo_lines) + "\n")

    # Write dataset.yaml
    dataset_yaml_path = out_base / "dataset.yaml"
    yaml_content = {
        "path": str(out_base).replace("\\", "/"),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            0: "crop",
            1: "weed",
        },
    }

    with open(dataset_yaml_path, "w", encoding="utf-8") as f:
        import yaml
        yaml.safe_dump(yaml_content, f, default_flow_style=False)

    print("\n" + "=" * 60)
    print("  CONVERSION COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Total Bounding Boxes: {total_converted_boxes}")
    print(f"  - Crops (class 0): {class_counts[0]}")
    print(f"  - Weeds (class 1): {class_counts[1]}")
    print(f"Dataset config created at: {dataset_yaml_path}")
    return str(dataset_yaml_path)


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\royde\Downloads\crop-and-weed-detection-DatasetNinja\data"
    convert_dataset_ninja_to_yolo(src)

"""
Indian Agricultural Field Dataset Preparation & Hard-Negative Pipeline.
Creates a field dataset specifically incorporating:
1. Positive crop images
2. Positive weed images
3. Crop + weed mixed images
4. Soil-only background images
5. Hard negatives:
   - cracked soil
   - dry cloddy earth
   - field stones & pebbles
   - dead leaves & crop residue
   - shadow bands
   - dry straw stubble

Performs stratified 70% train / 20% val / 10% test split.
Applies realistic Indian field augmentations (glare, shadows, perspective, soil texture).
"""
import os
import glob
import shutil
import random
import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Any


def apply_indian_field_augmentations(img: np.ndarray) -> np.ndarray:
    """
    Applies realistic augmentations reflecting Indian agricultural conditions:
    - Harsh midday sunlight exposure
    - Cloud shadow streaks
    - Perspective tilt from rover mast angle
    - Defocus blur from rover vibration over clods
    """
    aug = img.copy()
    h, w = aug.shape[:2]

    # 1. Harsh Indian Sunlight / Glare (Exposure shift)
    if random.random() < 0.5:
        factor = random.uniform(0.75, 1.30)
        hsv = cv2.cvtColor(aug, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * factor, 0, 255)
        aug = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 2. Random Cloud / Rover Mast Shadow
    if random.random() < 0.4:
        mask = np.ones((h, w), dtype=np.float32)
        x_start = random.randint(0, int(w * 0.6))
        x_width = random.randint(int(w * 0.2), int(w * 0.5))
        mask[:, x_start:x_start + x_width] = random.uniform(0.45, 0.70)
        mask = cv2.GaussianBlur(mask, (51, 51), 0)
        for c in range(3):
            aug[:, :, c] = np.clip(aug[:, :, c] * mask, 0, 255).astype(np.uint8)

    # 3. Rover Mast Vibration Blur
    if random.random() < 0.25:
        ksize = random.choice([3, 5])
        aug = cv2.GaussianBlur(aug, (ksize, ksize), 0)

    # 4. Subtle Perspective / Camera Tilt
    if random.random() < 0.35:
        dx = random.uniform(-0.05, 0.05) * w
        pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
        pts2 = np.float32([[dx, 0], [w - dx, 0], [0, h], [w, h]])
        matrix = cv2.getPerspectiveTransform(pts1, pts2)
        aug = cv2.warpPerspective(aug, matrix, (w, h), borderMode=cv2.BORDER_REFLECT)

    return aug


def create_synthetic_hard_negative(soil_type: str = "cracked_dry") -> np.ndarray:
    """
    Synthesizes hard negative soil textures with zero plants
    to train model to reject cracked soil, stones, and shadows.
    """
    img = np.zeros((640, 640, 3), dtype=np.uint8)

    if soil_type == "cracked_dry":
        # Base dry brown clay: BGR (50, 75, 110)
        img[:] = (55, 80, 115)
        # Add cracked earth lines (dark irregular lines)
        for _ in range(40):
            pt1 = (random.randint(0, 640), random.randint(0, 640))
            pt2 = (pt1[0] + random.randint(-80, 80), pt1[1] + random.randint(-80, 80))
            cv2.line(img, pt1, pt2, (25, 35, 50), thickness=random.randint(2, 5))
            # Branch crack
            if random.random() < 0.6:
                pt3 = (pt2[0] + random.randint(-50, 50), pt2[1] + random.randint(-50, 50))
                cv2.line(img, pt2, pt3, (20, 30, 45), thickness=random.randint(1, 3))
        # Noise texture
        noise = np.random.normal(0, 12, (640, 640, 3)).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    elif soil_type == "stones_gravel":
        # Alluvial sandy loam base
        img[:] = (70, 95, 130)
        # Add gray/brown stones and pebbles
        for _ in range(35):
            cx, cy = random.randint(20, 620), random.randint(20, 620)
            axes = (random.randint(8, 25), random.randint(6, 18))
            angle = random.randint(0, 180)
            color = (random.randint(100, 140), random.randint(110, 150), random.randint(120, 160))
            cv2.ellipse(img, (cx, cy), axes, angle, 0, 360, color, -1)
            # Stone shadow edge
            cv2.ellipse(img, (cx + 2, cy + 2), axes, angle, 0, 180, (40, 55, 75), 2)
        noise = np.random.normal(0, 15, (640, 640, 3)).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    elif soil_type == "crop_residue_stubble":
        # Dark soil with straw stubble
        img[:] = (45, 65, 90)
        # Straw lines (yellow-tan dried stems)
        for _ in range(60):
            pt1 = (random.randint(0, 640), random.randint(0, 640))
            angle = random.uniform(0, 2 * np.pi)
            length = random.randint(15, 60)
            pt2 = (int(pt1[0] + length * np.cos(angle)), int(pt1[1] + length * np.sin(angle)))
            straw_color = (random.randint(60, 90), random.randint(130, 170), random.randint(170, 210))
            cv2.line(img, pt1, pt2, straw_color, thickness=random.randint(1, 3))

    return img


def build_indian_dataset(
    source_images_dir: str = "data/field_dataset/images",
    source_labels_dir: str = "data/field_dataset/labels",
    output_dir: str = "data/indian_field_dataset",
    train_ratio: float = 0.70,
    val_ratio: float = 0.20,
    test_ratio: float = 0.10,
    num_hard_negatives: int = 150,
):
    """
    Builds structured Indian dataset with 70% train / 20% val / 10% test split,
    synthesizes hard-negative background images (cracked soil, stones, residue),
    and creates dataset.yaml.
    """
    print("=" * 65)
    print("  AGRIPATH: PREPARING INDIAN AGRICULTURAL FIELD DATASET")
    print("=" * 65)

    out_path = Path(output_dir).resolve()
    for split in ["train", "val", "test"]:
        (out_path / "images" / split).mkdir(parents=True, exist_ok=True)
        (out_path / "labels" / split).mkdir(parents=True, exist_ok=True)

    # 1. Gather all existing labeled images
    all_imgs = []
    for split in ["train", "val", "test"]:
        p = Path(source_images_dir) / split
        if p.exists():
            all_imgs.extend(list(p.glob("*.jpg")) + list(p.glob("*.jpeg")) + list(p.glob("*.png")))

    random.seed(42)
    random.shuffle(all_imgs)

    n_total = len(all_imgs)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_imgs = all_imgs[:n_train]
    val_imgs = all_imgs[n_train:n_train + n_val]
    test_imgs = all_imgs[n_train + n_val:]

    print(f"[*] Base Field Images: {n_total} total")
    print(f"    - Train: {len(train_imgs)} ({train_ratio*100:.0f}%)")
    print(f"    - Val:   {len(val_imgs)} ({val_ratio*100:.0f}%)")
    print(f"    - Test:  {len(test_imgs)} ({test_ratio*100:.0f}%)")

    splits_map = {
        "train": train_imgs,
        "val": val_imgs,
        "test": test_imgs,
    }

    # Copy files
    for split, img_list in splits_map.items():
        dest_img_dir = out_path / "images" / split
        dest_lbl_dir = out_path / "labels" / split

        for src_img in img_list:
            # Copy image
            shutil.copy2(src_img, dest_img_dir / src_img.name)

            # Find matching label
            lbl_name = src_img.stem + ".txt"
            # Check source labels directory
            src_lbl = Path(source_labels_dir) / split / lbl_name
            if not src_lbl.exists():
                src_lbl = src_img.parent.parent.parent / "labels" / src_img.parent.name / lbl_name

            if src_lbl.exists():
                shutil.copy2(src_lbl, dest_lbl_dir / lbl_name)
            else:
                # Empty label file (background)
                (dest_lbl_dir / lbl_name).touch()

    # 2. Generate Hard Negatives (Soil only, cracked mud, stones, residue)
    print(f"\n[*] Generating {num_hard_negatives} Hard-Negative Indian Field Images...")
    soil_types = ["cracked_dry", "stones_gravel", "crop_residue_stubble"]

    # 70% train, 20% val, 10% test for hard negatives
    n_hn_train = int(num_hard_negatives * train_ratio)
    n_hn_val = int(num_hard_negatives * val_ratio)
    n_hn_test = num_hard_negatives - n_hn_train - n_hn_val

    hn_splits = (
        [("train", i) for i in range(n_hn_train)] +
        [("val", i) for i in range(n_hn_val)] +
        [("test", i) for i in range(n_hn_test)]
    )

    for split, idx in hn_splits:
        st = random.choice(soil_types)
        hn_img = create_synthetic_hard_negative(st)
        hn_img = apply_indian_field_augmentations(hn_img)

        hn_filename = f"hard_neg_soil_{st}_{idx:04d}.jpg"
        cv2.imwrite(str(out_path / "images" / split / hn_filename), hn_img)

        # Empty label file for hard negative: tells YOLO this image has 0 plants!
        lbl_file = out_path / "labels" / split / f"hard_neg_soil_{st}_{idx:04d}.txt"
        lbl_file.touch()

    print(f"[+] Added {n_hn_train} train, {n_hn_val} val, {n_hn_test} test hard negatives.")

    # 3. Write dataset.yaml
    yaml_content = f"""# Indian Agricultural Field Dataset Configuration
path: {out_path.as_posix()}
train: images/train
val: images/val
test: images/test

names:
  0: crop
  1: weed
"""
    with open(out_path / "dataset.yaml", "w") as f:
        f.write(yaml_content)

    print(f"\n[+] Created dataset config: {out_path / 'dataset.yaml'}")
    print("=" * 65)
    print("  DATASET PREPARATION COMPLETE!")
    print("=" * 65)


if __name__ == "__main__":
    build_indian_dataset()

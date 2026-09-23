# AgriPath: YOLOv8 Training & ONNX Export Guide (Weed vs Crop)

This guide walks you through collecting field data, annotating crops and weeds, fine-tuning YOLOv8n, and exporting an optimized CPU ONNX model for Raspberry Pi 4/5 deployment.

---

## 1. Dataset Preparation & Annotation

### Class Schema
- **Class `0`**: `crop` (Tomato, Cotton, Sugarbeet, Corn, Soy, etc.)
- **Class `1`**: `weed` (Broadleaf, Grass, Dandelion, Nutgrass, etc.)

### Directory Structure
Organize your dataset into standard YOLO format:
```
data/
├── dataset.yaml
├── images/
│   ├── train/
│   │   ├── field_001.jpg
│   ├── val/
│   │   ├── field_050.jpg
│   └── test/
│       └── field_080.jpg
└── labels/
    ├── train/
    │   ├── field_001.txt
    ├── val/
    │   ├── field_050.txt
    └── test/
        └── field_080.txt
```

Each label line is: `<class_id> <x_center> <y_center> <width> <height>` (all normalized $0.0 \dots 1.0$).

### `dataset.yaml`
```yaml
path: ./data
train: images/train
val: images/val
test: images/test

names:
  0: crop
  1: weed
```

---

## 2. Recommended Augmentations for Agricultural Robotics

Agricultural lighting changes drastically with clouds, wet soil, and time of day. In your training script or Ultralytics hyperparameters:

- `mosaic: 1.0`: Crucial for mixing small weeds and crops at varied scales.
- `hsv_h: 0.02, hsv_s: 0.7, hsv_v: 0.4`: Robustness to bright noon sunlight, wet leaves, and deep shadow.
- `degrees: 15.0`: Handles minor rover camera tilt and camera roll.
- `scale: 0.5`: Simulates weeds at different distances and growth stages.
- `fliplr: 0.5`: Symmetric field invariance.
- `erasing: 0.2`: Simulates partial leaf occlusion by dirt, clods, or other leaves.

---

## 3. Training Command (YOLOv8 Nano or Small)

Install training tools (on your GPU training machine or desktop):
```bash
pip install ultralytics
```

Run training:
```bash
yolo detect train \
  model=yolov8n.pt \
  data=dataset.yaml \
  epochs=100 \
  imgsz=640 \
  batch=16 \
  patience=20 \
  lr0=0.01 \
  lrf=0.01 \
  weight_decay=0.0005 \
  device=0 \
  name=agripath_yolov8n
```

*Note: For edge deployment on Raspberry Pi 4/5, `yolov8n` (nano) provides optimal CPU inference latency (35–60 ms) while achieving high mAP on agricultural tasks.*

---

## 4. ONNX Export for Raspberry Pi

Export the fine-tuned PyTorch weights to ONNX format with graph simplification enabled:

```bash
yolo export \
  model=runs/detect/agripath_yolov8n/weights/best.pt \
  format=onnx \
  imgsz=640 \
  simplify=True \
  opset=12
```

### Deploy to AgriPath
Copy the exported ONNX model into the project's `models/` directory:
```bash
mkdir -p models
cp runs/detect/agripath_yolov8n/weights/best.onnx models/best.onnx
```

Once `models/best.onnx` is present, AgriPath automatically switches from **Demo Mode** to **High-Precision ONNX Mode**.

"""
AgriPath YOLOv8 Training & Auto-Export Pipeline.
Trains high-accuracy YOLOv8 on your weed vs crop dataset, evaluates real metrics,
and auto-exports an optimized CPU ONNX model straight to models/best.onnx.
"""
import os
import sys
import shutil
import argparse
from pathlib import Path


def train_and_export(
    data_yaml: str,
    model_size: str = "n",  # 'n' (nano - fast for Pi) or 's' (small - higher accuracy)
    epochs: int = 100,
    batch_size: int = 16,
    img_size: int = 640,
    device: str = "0",       # '0' for GPU, or 'cpu'
    output_onnx_path: str = "models/best.onnx",
):
    print("=" * 60)
    print("  AGRIPATH: YOLOV8 HIGH-ACCURACY TRAINING PIPELINE")
    print("=" * 60)

    # 1. Check/Install Ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[*] Ultralytics is not installed. Installing now...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
        from ultralytics import YOLO

    data_yaml_path = Path(data_yaml).resolve()
    if not data_yaml_path.exists():
        raise FileNotFoundError(f"dataset.yaml not found at: {data_yaml_path}")

    print(f"[*] Dataset Config: {data_yaml_path}")
    print(f"[*] Base Architecture: YOLOv8{model_size.upper()}")
    print(f"[*] Target Resolution: {img_size}x{img_size}")
    print(f"[*] Target Epochs: {epochs}")

    # 2. Initialize Model with Pretrained Backbone
    base_weight = f"yolov8{model_size}.pt"
    model = YOLO(base_weight)

    # 3. Train with Agricultural Field Augmentations for 99% Accuracy Target
    # - mosaic=1.0: Mixes small weed sprouts and crops at various field scales
    # - hsv_h/s/v: Handles harsh midday sunlight, wet soil, and cloud shadow changes
    # - scale=0.5: Robustness to varying camera distance and plant maturity
    # - patience=20: Early stopping if validation loss stops improving
    print("\n[*] Commencing Model Training...")
    results = model.train(
        data=str(data_yaml_path),
        epochs=epochs,
        imgsz=img_size,
        batch=batch_size,
        device=device,
        patience=20,
        mosaic=1.0,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        scale=0.5,
        fliplr=0.5,
        close_mosaic=10,
        save=True,
        plots=True,
        project="runs/detect",
        name="agripath_training",
        exist_ok=True,
    )

    # 4. Extract Trained Best PyTorch Weights
    best_pt = Path("runs/detect/agripath_training/weights/best.pt")
    if not best_pt.exists():
        best_pt = model.trainer.best if hasattr(model, "trainer") else None

    if not best_pt or not Path(best_pt).exists():
        raise RuntimeError("Training finished but best.pt weight was not found.")

    print(f"\n[+] Training Complete! Best checkpoint saved to: {best_pt}")

    # 5. Export to ONNX with Simplification (Pi-CPU Optimized)
    print("\n[*] Exporting best.pt to optimized CPU ONNX format...")
    best_model = YOLO(str(best_pt))
    exported_onnx = best_model.export(
        format="onnx",
        imgsz=img_size,
        simplify=True,
        opset=12,
        half=False,  # FP32 for broad CPU compatibility
    )
    print(f"[+] ONNX export generated: {exported_onnx}")

    # 6. Copy to models/best.onnx
    dest_path = Path(output_onnx_path).resolve()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exported_onnx, dest_path)

    print("\n" + "=" * 60)
    print(f"  SUCCESS! Model installed to: {dest_path}")
    print("  AgriPath will now automatically run real high-precision inference!")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLOv8 Weed vs Crop Model for AgriPath")
    parser.add_argument("--data", type=str, default="data/field_dataset/dataset.yaml", help="Path to dataset.yaml")
    parser.add_argument("--model", type=str, choices=["n", "s", "m"], default="n", help="Model size: n (fastest), s (higher accuracy)")
    parser.add_argument("--epochs", type=int, default=100, help="Training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--device", type=str, default="0", help="GPU index ('0') or 'cpu'")
    parser.add_argument("--out", type=str, default="models/best.onnx", help="Destination ONNX path")
    args = parser.parse_args()

    train_and_export(
        data_yaml=args.data,
        model_size=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.imgsz,
        device=args.device,
        output_onnx_path=args.out,
    )

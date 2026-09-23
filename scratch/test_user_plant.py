import sys
import os
sys.path.insert(0, os.path.abspath("."))
import cv2
import numpy as np
from backend.detector.onnx_detector import OnnxDetector

# Load screenshot
screenshot_path = "C:/Users/royde/.gemini/antigravity/brain/e334b8ae-425a-4bf9-92c7-488456234f20/.user_uploaded/media_1790165582474.png"
img = cv2.imread(screenshot_path)

if img is None:
    print("Could not load screenshot")
    exit(1)

# In the screenshot (1920x1080 or similar), let's find the field photo boundaries
# The canvas is roughly from x=195 to x=630, y=308 to y=920
h, w = img.shape[:2]
print(f"Screenshot size: {w}x{h}")

# The field area roughly:
# Let's crop the square image area
# Based on typical 1366x768 or 1920x1080:
# Let's crop x ~ [195, 630], y ~ [308, 925] for 1366x768
field_crop = img[int(h*0.30):int(h*0.92), int(w*0.19):int(w*0.53)]
cv2.imwrite("scratch/cropped_field.jpg", field_crop)
print(f"Cropped field image size: {field_crop.shape[1]}x{field_crop.shape[0]}")

# Run real trained YOLOv8 ONNX model
detector = OnnxDetector(model_path="models/best.onnx", conf_threshold=0.30)
res = detector.detect(field_crop)

print(f"\nReal Trained Model Detections on this plant:")
print(f"Total plants detected: {len(res.detections)}")
for d in res.detections:
    print(f" - Class: {d.raw_class_name.upper()} | Confidence: {d.confidence:.2f} | Status: {d.status.value} | Bbox: {d.bbox_px}")

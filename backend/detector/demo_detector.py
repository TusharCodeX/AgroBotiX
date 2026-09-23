"""
DemoDetector: High-quality mock plant detector based on OpenCV color segmentation.
Active when models/best.onnx is missing, allowing full UI, calibration, and path planning
testing prior to model training.
"""
import time
import cv2
import numpy as np
from typing import List, Tuple
from .base import PlantDetection, DetectionResult, PlantStatus, PlantClass


class DemoDetector:
    """Mock detector using HSV color segmentation and morphological contour analysis."""

    def __init__(self, conf_threshold: float = 0.60, uncertain_min: float = 0.30):
        self.model_name = "DEMO (Green Color Segmentation)"
        self.conf_threshold = conf_threshold
        self.uncertain_min = uncertain_min

    def detect(self, image: np.ndarray) -> DetectionResult:
        start_time = time.perf_counter()
        h, w = image.shape[:2]

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Green plant mask
        lower_green = np.array([25, 35, 35])
        upper_green = np.array([90, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        # Morphological opening to remove salt-and-pepper noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detections: List[PlantDetection] = []
        plant_idx = 1

        # If image does not have enough green contours (e.g. synthetic plain test),
        # create mock plants distributed in field for testing
        valid_contours = [c for c in contours if cv2.contourArea(c) > 300]

        if len(valid_contours) < 2:
            # Generate deterministic synthetic plant patterns across field
            mock_specs = [
                (int(w * 0.3), int(h * 0.4), 60, 60, 0, 0.88),   # Crop (confirmed)
                (int(w * 0.7), int(h * 0.4), 65, 65, 0, 0.92),   # Crop (confirmed)
                (int(w * 0.5), int(h * 0.6), 45, 45, 1, 0.85),   # Weed (confirmed)
                (int(w * 0.35), int(h * 0.75), 40, 40, 1, 0.78), # Weed (confirmed)
                (int(w * 0.75), int(h * 0.75), 35, 35, 1, 0.45), # Weed (uncertain -> yellow obstacle)
            ]
            for cx, cy, bw, bh, cls_id, conf in mock_specs:
                x1 = max(0, cx - bw // 2)
                y1 = max(0, cy - bh // 2)
                x2 = min(w, cx + bw // 2)
                y2 = min(h, cy + bh // 2)
                det = self._classify_detection(plant_idx, cls_id, conf, (x1, y1, x2, y2), (cx, cy))
                if det:
                    detections.append(det)
                    plant_idx += 1
        else:
            for cnt in valid_contours:
                area = cv2.contourArea(cnt)
                if area > (h * w * 0.8):  # Ignore background bounding
                    continue
                x, y, bw, bh = cv2.boundingRect(cnt)
                cx = x + bw / 2.0
                cy = y + bh / 2.0

                # Larger patches more likely crop, smaller ones weed
                if area > 2500:
                    cls_id = 0
                    conf = min(0.96, 0.65 + (area / 10000.0) * 0.3)
                else:
                    cls_id = 1
                    # Alternate between confirmed weed and uncertain weed for demonstration
                    conf = 0.82 if (plant_idx % 3 != 0) else 0.48

                det = self._classify_detection(
                    plant_idx, cls_id, float(conf),
                    (float(x), float(y), float(x + bw), float(y + bh)),
                    (float(cx), float(cy))
                )
                if det:
                    detections.append(det)
                    plant_idx += 1

        elapsed = (time.perf_counter() - start_time) * 1000.0
        fps = 1000.0 / elapsed if elapsed > 0 else 0.0

        return DetectionResult(
            detections=detections,
            inference_time_ms=elapsed,
            demo_mode=True,
            model_name="DEMO (Green Color Segmentation)",
            image_shape=(h, w),
            fps=fps
        )

    def _classify_detection(
        self,
        plant_id: int,
        cls_id: int,
        conf: float,
        bbox_px: Tuple[float, float, float, float],
        center_px: Tuple[float, float]
    ) -> PlantDetection:
        """Applies AgriPath safety confidence policy."""
        # conf >= 0.60: accept prediction
        # 0.30 <= conf < 0.60: UNCERTAIN -> treated as CROP / obstacle, never targeted
        # conf < 0.30: discard
        if conf < self.uncertain_min:
            return None

        if conf >= self.conf_threshold:
            if cls_id == PlantClass.CROP:
                status = PlantStatus.CROP
                is_obstacle = True
                is_target = False
            else:
                status = PlantStatus.WEED
                is_obstacle = False
                is_target = True
        else:
            # Uncertain (0.30 - 0.60): treat as CROP for safety!
            status = PlantStatus.UNCERTAIN
            is_obstacle = True  # SAFETY: never target, treat as obstacle
            is_target = False

        return PlantDetection(
            id=plant_id,
            class_id=cls_id,
            raw_class_name="crop" if cls_id == 0 else "weed",
            status=status,
            confidence=conf,
            bbox_px=bbox_px,
            center_px=center_px,
            is_obstacle=is_obstacle,
            is_target=is_target,
        )

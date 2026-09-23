"""
Tiled (SAHI-style) inference manager for high-resolution images.
Ensures small weed sprouts are not lost during single-pass downscaling.
"""
import time
import cv2
import numpy as np
from typing import List, Tuple, Any
from .base import PlantDetection, DetectionResult, PlantStatus


class TiledInferenceManager:
    """Manages overlapping image slicing, tile inference, and global NMS fusion."""

    def __init__(
        self,
        tile_size: int = 640,
        overlap_ratio: float = 0.20,
        min_image_dimension: int = 960,
        iou_threshold: float = 0.45
    ):
        self.tile_size = tile_size
        self.overlap_ratio = overlap_ratio
        self.min_image_dimension = min_image_dimension
        self.iou_threshold = iou_threshold

    def should_tile(self, image_shape: Tuple[int, int]) -> bool:
        """Determines if image dimensions warrant sliced inference."""
        h, w = image_shape[:2]
        return max(h, w) >= self.min_image_dimension

    def detect_tiled(self, detector: Any, image: np.ndarray) -> DetectionResult:
        """
        Runs sliced inference across tiles, shifts coordinates, and applies global NMS.
        """
        start_time = time.perf_counter()
        h, w = image.shape[:2]

        if not self.should_tile((h, w)):
            return detector.detect(image)

        stride = int(self.tile_size * (1.0 - self.overlap_ratio))
        all_detections: List[PlantDetection] = []

        y_starts = list(range(0, h - self.tile_size + 1, stride))
        if len(y_starts) == 0 or y_starts[-1] + self.tile_size < h:
            y_starts.append(max(0, h - self.tile_size))

        x_starts = list(range(0, w - self.tile_size + 1, stride))
        if len(x_starts) == 0 or x_starts[-1] + self.tile_size < w:
            x_starts.append(max(0, w - self.tile_size))

        # Remove duplicates
        y_starts = sorted(list(set(y_starts)))
        x_starts = sorted(list(set(x_starts)))

        for y0 in y_starts:
            for x0 in x_starts:
                tile = image[y0 : y0 + self.tile_size, x0 : x0 + self.tile_size]
                res = detector.detect(tile)
                for det in res.detections:
                    # Shift bbox back to global image coordinates
                    gx1 = det.bbox_px[0] + x0
                    gy1 = det.bbox_px[1] + y0
                    gx2 = det.bbox_px[2] + x0
                    gy2 = det.bbox_px[3] + y0
                    gcx = det.center_px[0] + x0
                    gcy = det.center_px[1] + y0

                    all_detections.append(
                        PlantDetection(
                            id=0,
                            class_id=det.class_id,
                            raw_class_name=det.raw_class_name,
                            status=det.status,
                            confidence=det.confidence,
                            bbox_px=(gx1, gy1, gx2, gy2),
                            center_px=(gcx, gcy),
                            is_obstacle=det.is_obstacle,
                            is_target=det.is_target,
                        )
                    )

        # Global NMS to remove duplicate detections in overlap areas
        fused_detections = self._global_nms(all_detections)

        elapsed = (time.perf_counter() - start_time) * 1000.0
        fps = 1000.0 / elapsed if elapsed > 0 else 0.0

        return DetectionResult(
            detections=fused_detections,
            inference_time_ms=elapsed,
            demo_mode=getattr(detector, "demo_mode", False),
            model_name=f"Tiled {getattr(detector, 'model_name', 'Detector')}",
            image_shape=(h, w),
            fps=fps
        )

    def _global_nms(self, detections: List[PlantDetection]) -> List[PlantDetection]:
        if not detections:
            return []

        boxes = []
        scores = []
        for det in detections:
            x1, y1, x2, y2 = det.bbox_px
            boxes.append([int(x1), int(y1), int(x2 - x1), int(y2 - y1)])
            scores.append(float(det.confidence))

        indices = cv2.dnn.NMSBoxes(
            boxes, scores, score_threshold=0.25, nms_threshold=self.iou_threshold
        )

        fused: List[PlantDetection] = []
        new_id = 1
        if len(indices) > 0:
            for idx in indices.flatten():
                d = detections[idx]
                d.id = new_id
                fused.append(d)
                new_id += 1

        return fused

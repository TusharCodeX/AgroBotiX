"""
TemporalFilter: Multi-frame temporal voting to stabilize detections and eliminate flicker in live video.
"""
from collections import deque
from typing import List
import numpy as np

from .base import PlantDetection, DetectionResult


class TemporalFilter:
    """Sliding-window voting across consecutive frames."""

    def __init__(self, window_size: int = 4, min_hits: int = 2, iou_match_threshold: float = 0.35):
        self.window_size = window_size
        self.min_hits = min_hits
        self.iou_match_threshold = iou_match_threshold
        self.history = deque(maxlen=window_size)

    def filter_frame(self, result: DetectionResult) -> DetectionResult:
        """Appends current detections and returns temporally smoothed detections."""
        current_dets = result.detections
        self.history.append(current_dets)

        if len(self.history) < 2:
            return result

        # For each detection in current frame, count matching appearances in previous frames
        stabilized_dets: List[PlantDetection] = []

        for curr_det in current_dets:
            hits = 1
            matched_confs = [curr_det.confidence]

            for past_frame in list(self.history)[:-1]:
                match_found = False
                for past_det in past_frame:
                    iou = self._calculate_iou(curr_det.bbox_px, past_det.bbox_px)
                    if iou >= self.iou_match_threshold and curr_det.status == past_det.status:
                        match_found = True
                        matched_confs.append(past_det.confidence)
                        break
                if match_found:
                    hits += 1

            if hits >= self.min_hits:
                # Average confidence over temporal window
                curr_det.confidence = float(np.mean(matched_confs))
                stabilized_dets.append(curr_det)

        result.detections = stabilized_dets
        return result

    @staticmethod
    def _calculate_iou(boxA, boxB) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        unionArea = boxAArea + boxBArea - interArea
        if unionArea <= 0:
            return 0.0
        return interArea / unionArea

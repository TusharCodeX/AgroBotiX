"""
YOLOv8 ONNX Runtime plant detector.
Executes CPU-only inference optimized for Raspberry Pi and host testing.
"""
import os
import time
import cv2
import numpy as np
from typing import List, Tuple, Optional
import onnxruntime as ort

from .base import PlantDetection, DetectionResult, PlantStatus, PlantClass
from ..camera.web_source import WebUploadSource


class OnnxDetector:
    """CPU-friendly YOLOv8 detector using ONNX Runtime."""

    def __init__(
        self,
        model_path: str = "models/best.onnx",
        input_size: int = 640,
        conf_threshold: float = 0.60,
        uncertain_min: float = 0.30,
        iou_threshold: float = 0.45,
    ):
        self.model_path = model_path
        self.model_name = "YOLOv8 ONNX (CPU)"
        self.input_size = input_size
        self.conf_threshold = conf_threshold
        self.uncertain_min = uncertain_min
        self.iou_threshold = iou_threshold
        self.session: Optional[ort.InferenceSession] = None
        self._init_session()

    def _init_session(self) -> None:
        if os.path.exists(self.model_path):
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=opts,
                providers=["CPUExecutionProvider"]
            )

    def is_model_loaded(self) -> bool:
        return self.session is not None

    def detect(self, image: np.ndarray) -> DetectionResult:
        """
        Runs YOLOv8 ONNX inference on image and applies confidence safety policy.
        """
        if self.session is None:
            raise RuntimeError(f"ONNX model file not found at '{self.model_path}'.")

        start_time = time.perf_counter()
        orig_h, orig_w = image.shape[:2]

        # Letterbox image to model input size
        padded_img, ratio, (pad_w, pad_h) = WebUploadSource.letterbox(
            image, target_size=self.input_size
        )

        # Preprocess: BGR -> RGB, HWC -> CHW, 0..255 -> 0.0..1.0
        rgb = cv2.cvtColor(padded_img, cv2.COLOR_BGR2RGB)
        input_tensor = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
        input_tensor = np.expand_dims(input_tensor, axis=0)

        # Run ONNX inference
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: input_tensor})
        raw_output = outputs[0]  # Shape: (1, 4 + num_classes, 8400)

        # Transpose to (8400, 4 + num_classes)
        predictions = np.squeeze(raw_output, axis=0).T

        boxes = []
        confidences = []
        class_ids = []

        num_classes = predictions.shape[1] - 4

        for row in predictions:
            cx, cy, bw, bh = row[0:4]
            class_scores = row[4:4 + num_classes]
            best_class_id = int(np.argmax(class_scores))
            max_conf = float(class_scores[best_class_id])

            # Discard below uncertain_min
            if max_conf < self.uncertain_min:
                continue

            # Convert letterboxed cx, cy, bw, bh to x1, y1, x2, y2
            x1 = cx - bw / 2.0
            y1 = cy - bh / 2.0

            boxes.append([int(x1), int(y1), int(bw), int(bh)])
            confidences.append(max_conf)
            class_ids.append(best_class_id)

        # Apply Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(
            boxes, confidences, score_threshold=self.uncertain_min, nms_threshold=self.iou_threshold
        )

        detections: List[PlantDetection] = []
        plant_id = 1

        if len(indices) > 0:
            for idx in indices.flatten():
                bx, by, bw, bh = boxes[idx]
                conf = confidences[idx]
                cls_id = class_ids[idx]

                # Map coordinates back from letterbox to original image
                orig_x1 = max(0.0, (bx - pad_w) / ratio)
                orig_y1 = max(0.0, (by - pad_h) / ratio)
                orig_x2 = min(float(orig_w), (bx + bw - pad_w) / ratio)
                orig_y2 = min(float(orig_h), (by + bh - pad_h) / ratio)

                cx = (orig_x1 + orig_x2) / 2.0
                cy = (orig_y1 + orig_y2) / 2.0

                # Confidence policy
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
                    # Uncertain: safety critical -> treat as CROP obstacle!
                    status = PlantStatus.UNCERTAIN
                    is_obstacle = True
                    is_target = False

                detections.append(
                    PlantDetection(
                        id=plant_id,
                        class_id=cls_id,
                        raw_class_name="crop" if cls_id == 0 else "weed",
                        status=status,
                        confidence=conf,
                        bbox_px=(orig_x1, orig_y1, orig_x2, orig_y2),
                        center_px=(cx, cy),
                        is_obstacle=is_obstacle,
                        is_target=is_target,
                    )
                )
                plant_id += 1

        elapsed = (time.perf_counter() - start_time) * 1000.0
        fps = 1000.0 / elapsed if elapsed > 0 else 0.0

        return DetectionResult(
            detections=detections,
            inference_time_ms=elapsed,
            demo_mode=False,
            model_name=os.path.basename(self.model_path),
            image_shape=(orig_h, orig_w),
            fps=fps
        )

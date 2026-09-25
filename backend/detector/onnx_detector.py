"""
Hierarchical YOLOv8 ONNX Plant Detector for Indian Agricultural Conditions.
Executes 3-Stage Inference:
1. Field Perception (CPU ONNX Runtime, Letterbox, NMS)
2. Indian Crop-Specific Agronomic Profiling (Species Metadata Attachment)
3. Multi-Tiered Safety & Soil Rejection (ExG/VARI Soil Filter, Confidence Gating, Crop Safety Buffer)
"""
import os
import time
import math
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
import onnxruntime as ort

from .base import PlantDetection, DetectionResult, PlantStatus, PlantClass
from .indian_crops import get_crop_profile, match_weed_species, IndianCropProfile
from .soil_filter import IndianSoilVegetationValidator
from ..camera.web_source import WebUploadSource


class OnnxDetector:
    """CPU-friendly YOLOv8 detector tailored for Indian field conditions."""

    def __init__(
        self,
        model_path: str = "models/best.onnx",
        input_size: int = 640,
        candidate_threshold: float = 0.70,
        uncertain_min: float = 0.50,
        iou_threshold: float = 0.45,
        default_crop_context: str = "wheat",
    ):
        self.model_path = model_path
        self.model_name = "YOLOv8 ONNX (CPU)"
        self.model_version = "YOLOv8s-IndianField-v1.0"
        self.input_size = input_size
        self.candidate_threshold = candidate_threshold
        self.uncertain_min = uncertain_min
        self.iou_threshold = iou_threshold
        self.default_crop_context = default_crop_context
        self.session: Optional[ort.InferenceSession] = None
        self.soil_validator = IndianSoilVegetationValidator()
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

    def detect(
        self,
        image: np.ndarray,
        crop_context: Optional[str] = None,
        candidate_threshold: Optional[float] = None,
        uncertain_min: Optional[float] = None,
        safety_buffer_cm: Optional[float] = None,
        cm_per_pixel: float = 0.15,
    ) -> DetectionResult:
        """
        Executes hierarchical 3-stage perception and safety pipeline.
        Strictly no fake demo detections.
        """
        if self.session is None:
            return DetectionResult(
                detections=[],
                inference_time_ms=0.0,
                demo_mode=False,
                model_name=os.path.basename(self.model_path),
                model_available=False,
                status_message="MODEL UNAVAILABLE: models/best.onnx not loaded.",
            )

        start_time = time.perf_counter()
        orig_h, orig_w = image.shape[:2]

        ctx = (crop_context or self.default_crop_context).lower().strip()
        crop_profile: IndianCropProfile = get_crop_profile(ctx)

        cand_thresh = candidate_threshold if candidate_threshold is not None else self.candidate_threshold
        unc_min = uncertain_min if uncertain_min is not None else self.uncertain_min
        buffer_cm = safety_buffer_cm if safety_buffer_cm is not None else crop_profile.default_safety_buffer_cm

        # =====================================================================
        # STAGE 1: FIELD PERCEPTION (ONNX Inference)
        # =====================================================================
        padded_img, ratio, (pad_w, pad_h) = WebUploadSource.letterbox(
            image, target_size=self.input_size
        )
        rgb = cv2.cvtColor(padded_img, cv2.COLOR_BGR2RGB)
        input_tensor = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
        input_tensor = np.expand_dims(input_tensor, axis=0)

        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: input_tensor})
        raw_output = outputs[0]  # Shape: (1, 4 + num_classes, 8400)
        predictions = np.squeeze(raw_output, axis=0).T

        boxes = []
        confidences = []
        class_ids = []
        num_classes = predictions.shape[1] - 4

        # Filter initial raw predictions at low threshold (0.25) to catch potential candidates for evaluation
        for row in predictions:
            cx, cy, bw, bh = row[0:4]
            class_scores = row[4:4 + num_classes]
            best_class_id = int(np.argmax(class_scores))
            max_conf = float(class_scores[best_class_id])

            if max_conf < 0.25:
                continue

            x1 = cx - bw / 2.0
            y1 = cy - bh / 2.0
            boxes.append([int(x1), int(y1), int(bw), int(bh)])
            confidences.append(max_conf)
            class_ids.append(best_class_id)

        # Apply Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(
            boxes, confidences, score_threshold=0.25, nms_threshold=self.iou_threshold
        )

        raw_detections: List[Dict[str, Any]] = []
        if len(indices) > 0:
            for idx in indices.flatten():
                bx, by, bw, bh = boxes[idx]
                conf = confidences[idx]
                cls_id = class_ids[idx]

                orig_x1 = max(0.0, (bx - pad_w) / ratio)
                orig_y1 = max(0.0, (by - pad_h) / ratio)
                orig_x2 = min(float(orig_w), (bx + bw - pad_w) / ratio)
                orig_y2 = min(float(orig_h), (by + bh - pad_h) / ratio)

                box_w = max(1.0, orig_x2 - orig_x1)
                box_h = max(1.0, orig_y2 - orig_y1)
                area_px = box_w * box_h
                aspect_ratio = box_h / box_w

                raw_detections.append({
                    "class_id": cls_id,
                    "confidence": conf,
                    "bbox_px": (orig_x1, orig_y1, orig_x2, orig_y2),
                    "center_px": ((orig_x1 + orig_x2) / 2.0, (orig_y1 + orig_y2) / 2.0),
                    "area_px": area_px,
                    "aspect_ratio": aspect_ratio,
                })

        # =====================================================================
        # STAGE 2 & 3: INDIAN AGRONOMIC PROFILING & MULTI-TIERED SAFETY
        # =====================================================================
        processed_detections: List[PlantDetection] = []
        plant_id = 1

        # Separate crops first to construct the spatial safety buffers
        crops_list: List[Dict[str, Any]] = []
        weeds_and_others: List[Dict[str, Any]] = []

        for d in raw_detections:
            if d["class_id"] == PlantClass.CROP and d["confidence"] >= unc_min:
                crops_list.append(d)
            else:
                weeds_and_others.append(d)

        # Process Crops
        for c in crops_list:
            bbox = c["bbox_px"]
            # Secondary vegetation validation
            is_veg, veg_score, rej_reason = self.soil_validator.validate_roi(image, bbox)

            if not is_veg:
                # Soil/stone mistaken for crop
                status = PlantStatus.REJECTED
                action = "DO_NOT_CUT"
                is_obs = False
                reason = rej_reason or "Spectral check failed: soil/stone texture"
            else:
                status = PlantStatus.CROP
                action = "PROTECT"
                is_obs = True
                reason = None

            area_cm2 = c["area_px"] * (cm_per_pixel ** 2)

            processed_detections.append(
                PlantDetection(
                    id=plant_id,
                    class_id=PlantClass.CROP,
                    raw_class_name="crop",
                    status=status,
                    confidence=c["confidence"],
                    bbox_px=bbox,
                    center_px=c["center_px"],
                    area_px=c["area_px"],
                    area_cm2=area_cm2,
                    dist_to_nearest_crop_cm=0.0,
                    species_name=None,
                    crop_species=crop_profile.crop_name,
                    action=action,
                    rejection_reason=reason,
                    vegetation_score=veg_score,
                    soil_rejection_passed=is_veg,
                    is_obstacle=is_obs,
                    is_target=False,
                )
            )
            plant_id += 1

        # Process Weeds & Potential Soil False Positives
        for w in weeds_and_others:
            bbox = w["bbox_px"]
            conf = w["confidence"]
            area_cm2 = w["area_px"] * (cm_per_pixel ** 2)

            # Secondary Soil & Vegetation validation
            is_veg, veg_score, rej_reason = self.soil_validator.validate_roi(image, bbox)

            # Weed species metadata
            species_name = None

            # Compute Euclidean distance in cm to nearest confirmed crop
            dist_to_crop_cm = 999.0
            wcx, wcy = w["center_px"]

            for c in crops_list:
                ccx, ccy = c["center_px"]
                # Distance in cm between center points minus half-widths
                px_dist = math.hypot(wcx - ccx, wcy - ccy)
                cm_dist = max(0.0, (px_dist * cm_per_pixel) - 5.0)  # subtract plant radii
                if cm_dist < dist_to_crop_cm:
                    dist_to_crop_cm = cm_dist

            # Decision Logic
            if not is_veg:
                status = PlantStatus.REJECTED
                action = "DO_NOT_CUT"
                is_target = False
                is_obs = False
                reason = rej_reason or "Rejected: Soil, stone, or shadow without living leaf tissue"
            elif conf < unc_min:
                status = PlantStatus.REJECTED
                action = "DO_NOT_CUT"
                is_target = False
                is_obs = False
                reason = f"Confidence ({conf*100:.1f}%) below minimum safety threshold ({unc_min*100:.0f}%)"
            elif conf < cand_thresh:
                # Uncertain confidence (0.50 .. 0.70)
                status = PlantStatus.UNCERTAIN
                action = "DO_NOT_CUT"
                is_target = False
                is_obs = True  # Safety: treat uncertain detection as obstacle!
                reason = f"Confidence ({conf*100:.1f}%) in uncertain range ({unc_min*100:.0f}%-{cand_thresh*100:.0f}%); treated as obstacle"
            elif dist_to_crop_cm < buffer_cm:
                # Weed is confirmed but dangerously close to crop!
                status = PlantStatus.UNCERTAIN
                action = "DO_NOT_CUT"
                is_target = False
                is_obs = True  # Avoid driving over crop zone
                reason = f"Too close to crop safety zone (distance: {dist_to_crop_cm:.1f} cm < buffer: {buffer_cm:.1f} cm)"
            else:
                # Fully Actionable Weed!
                status = PlantStatus.ACTIONABLE_WEED
                action = "CUT"
                is_target = True
                is_obs = False
                reason = None

            processed_detections.append(
                PlantDetection(
                    id=plant_id,
                    class_id=w["class_id"],
                    raw_class_name="weed",
                    status=status,
                    confidence=conf,
                    bbox_px=bbox,
                    center_px=w["center_px"],
                    area_px=w["area_px"],
                    area_cm2=area_cm2,
                    dist_to_nearest_crop_cm=dist_to_crop_cm if crops_list else None,
                    species_name=species_name,
                    crop_species=crop_profile.scientific_name,
                    action=action,
                    rejection_reason=reason,
                    vegetation_score=veg_score,
                    soil_rejection_passed=is_veg,
                    is_obstacle=is_obs,
                    is_target=is_target,
                )
            )
            plant_id += 1

        elapsed = (time.perf_counter() - start_time) * 1000.0
        fps = 1000.0 / elapsed if elapsed > 0 else 0.0

        crops_cnt = sum(1 for d in processed_detections if d.status == PlantStatus.CROP)
        weeds_cnt = sum(1 for d in processed_detections if d.status == PlantStatus.ACTIONABLE_WEED)
        unc_cnt = sum(1 for d in processed_detections if d.status == PlantStatus.UNCERTAIN)
        rej_cnt = sum(1 for d in processed_detections if d.status == PlantStatus.REJECTED)

        # Structured Inference Logging
        print("-" * 65)
        print(f"MODEL:                {self.model_name}")
        print(f"MODEL VERSION:        {self.model_version}")
        print(f"INPUT SIZE:           {self.input_size}x{self.input_size}")
        print(f"CROP CONTEXT:         {crop_profile.crop_name} ({crop_profile.scientific_name})")
        print(f"CONFIDENCE THRESHOLD: Candidate >= {cand_thresh:.2f} | Uncertain: {unc_min:.2f}..{cand_thresh:.2f} | Buffer: {buffer_cm:.1f} cm")
        print(f"NMS/IoU:              {self.iou_threshold:.2f}")
        print(f"INFERENCE TIME:       {elapsed:.1f} ms ({fps:.1f} FPS)")
        print(f"DETECTIONS:           Total: {len(processed_detections)} | Crops: {crops_cnt} | Actionable Weeds: {weeds_cnt} | Uncertain: {unc_cnt} | Rejected: {rej_cnt}")
        print("-" * 65)

        return DetectionResult(
            detections=processed_detections,
            inference_time_ms=elapsed,
            demo_mode=False,
            model_name=os.path.basename(self.model_path),
            crop_context=ctx,
            crop_scientific_name=crop_profile.scientific_name,
            image_shape=(orig_h, orig_w),
            fps=fps,
            model_available=True,
            status_message="OK",
        )

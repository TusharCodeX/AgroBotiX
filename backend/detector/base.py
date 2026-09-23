"""
Data models and interfaces for plant detection under Indian agricultural conditions.
Includes botanical species metadata, soil rejection flags, crop safety margins,
and distance-to-crop metrics for mechanical rover blade safety.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any


class PlantClass(int, Enum):
    CROP = 0
    WEED = 1


class PlantStatus(str, Enum):
    CROP = "CROP"
    ACTIONABLE_WEED = "ACTIONABLE_WEED"
    WEED = "WEED"
    UNCERTAIN = "UNCERTAIN"
    REJECTED = "REJECTED"

    @classmethod
    def from_string(cls, val: str) -> "PlantStatus":
        v = str(val).upper().strip()
        if v in ("ACTIONABLE_WEED", "WEED"):
            return cls.ACTIONABLE_WEED
        if v == "CROP":
            return cls.CROP
        if v == "REJECTED":
            return cls.REJECTED
        return cls.UNCERTAIN


@dataclass
class PlantDetection:
    id: int
    class_id: int
    raw_class_name: str
    status: PlantStatus
    confidence: float
    bbox_px: Tuple[float, float, float, float]  # [x1, y1, x2, y2]
    center_px: Tuple[float, float]               # (cx, cy)
    center_cm: Optional[Tuple[float, float]] = None  # (x_cm, y_cm) in robot frame
    bbox_cm: Optional[Tuple[float, float, float, float]] = None  # [x1, y1, x2, y2] in cm
    area_px: float = 0.0
    area_cm2: Optional[float] = None
    dist_to_nearest_crop_cm: Optional[float] = None  # Distance to closest protected crop boundary
    species_name: Optional[str] = None               # Scientific or common weed species name
    crop_species: Optional[str] = None               # Main target crop species in field
    action: str = "DO_NOT_CUT"                       # "CUT", "DO_NOT_CUT", "PROTECT"
    rejection_reason: Optional[str] = None           # Why rejected or marked uncertain
    vegetation_score: float = 1.0                    # 0..1 from ExG / VARI index
    soil_rejection_passed: bool = True               # True if secondary soil check passed
    mask_polygon_px: Optional[List[Tuple[float, float]]] = None
    mask_polygon_cm: Optional[List[Tuple[float, float]]] = None
    is_obstacle: bool = False                        # True for Crops & Uncertain (safety barrier)
    is_target: bool = False                          # True for Actionable Weeds (target for blades)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "class_id": self.class_id,
            "raw_class_name": self.raw_class_name,
            "status": self.status.value,
            "confidence": round(float(self.confidence), 3),
            "bbox_px": [round(float(v), 1) for v in self.bbox_px],
            "center_px": [round(float(v), 1) for v in self.center_px],
            "center_cm": [round(float(v), 2) for v in self.center_cm] if self.center_cm else None,
            "bbox_cm": [round(float(v), 2) for v in self.bbox_cm] if self.bbox_cm else None,
            "area_px": round(float(self.area_px), 1),
            "area_cm2": round(float(self.area_cm2), 2) if self.area_cm2 is not None else None,
            "dist_to_nearest_crop_cm": round(float(self.dist_to_nearest_crop_cm), 2) if self.dist_to_nearest_crop_cm is not None else None,
            "species_name": self.species_name,
            "crop_species": self.crop_species,
            "action": self.action,
            "rejection_reason": self.rejection_reason,
            "vegetation_score": round(float(self.vegetation_score), 2),
            "soil_rejection_passed": self.soil_rejection_passed,
            "mask_polygon_px": self.mask_polygon_px,
            "mask_polygon_cm": self.mask_polygon_cm,
            "is_obstacle": self.is_obstacle,
            "is_target": self.is_target,
        }


@dataclass
class DetectionResult:
    detections: List[PlantDetection] = field(default_factory=list)
    inference_time_ms: float = 0.0
    demo_mode: bool = False
    model_name: str = "best.onnx"
    crop_context: str = "wheat"
    crop_scientific_name: str = "Triticum aestivum"
    image_shape: Tuple[int, int] = (0, 0)  # (height, width)
    fps: float = 0.0
    model_available: bool = True
    status_message: str = "OK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "inference_time_ms": round(self.inference_time_ms, 1),
            "fps": round(self.fps, 1),
            "demo_mode": self.demo_mode,
            "model_name": self.model_name,
            "model_available": self.model_available,
            "status_message": self.status_message,
            "crop_context": self.crop_context,
            "crop_scientific_name": self.crop_scientific_name,
            "image_shape": list(self.image_shape),
            "total_plants": len(self.detections),
            "actionable_weeds_count": sum(1 for d in self.detections if d.status == PlantStatus.ACTIONABLE_WEED),
            "crops_count": sum(1 for d in self.detections if d.status == PlantStatus.CROP),
            "uncertain_count": sum(1 for d in self.detections if d.status == PlantStatus.UNCERTAIN),
            "rejected_count": sum(1 for d in self.detections if d.status == PlantStatus.REJECTED),
        }

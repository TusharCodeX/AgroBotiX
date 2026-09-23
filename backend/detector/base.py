"""
Data models and interfaces for plant detection.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any


class PlantClass(int, Enum):
    CROP = 0
    WEED = 1


class PlantStatus(str, Enum):
    CROP = "CROP"
    WEED = "WEED"
    UNCERTAIN = "UNCERTAIN"


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
    is_obstacle: bool = False                    # True for Crops & Uncertain (safety barrier)
    is_target: bool = False                      # True for Confirmed Weeds (target for blades)

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
            "is_obstacle": self.is_obstacle,
            "is_target": self.is_target,
        }


@dataclass
class DetectionResult:
    detections: List[PlantDetection] = field(default_factory=list)
    inference_time_ms: float = 0.0
    demo_mode: bool = False
    model_name: str = "best.onnx"
    image_shape: Tuple[int, int] = (0, 0)  # (height, width)
    fps: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detections": [d.to_dict() for d in self.detections],
            "inference_time_ms": round(self.inference_time_ms, 1),
            "fps": round(self.fps, 1),
            "demo_mode": self.demo_mode,
            "model_name": self.model_name,
            "image_shape": list(self.image_shape),
            "total_plants": len(self.detections),
            "weeds_count": sum(1 for d in self.detections if d.status == PlantStatus.WEED),
            "crops_count": sum(1 for d in self.detections if d.status == PlantStatus.CROP),
            "uncertain_count": sum(1 for d in self.detections if d.status == PlantStatus.UNCERTAIN),
        }

"""
AgriPath FastAPI Backend Application
Integrates Vision, Calibration, Path Planning, and Motion Control for Skid-Steer Rover.
"""
import os
import io
import time
import json
import base64
import yaml
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.camera.web_source import WebUploadSource
from backend.camera.pi_source import PiCameraSource
from backend.detector.base import PlantClass, PlantStatus, PlantDetection, DetectionResult
from backend.detector.onnx_detector import OnnxDetector
from backend.detector.demo_detector import DemoDetector
from backend.detector.tiling import TiledInferenceManager
from backend.detector.temporal_filter import TemporalFilter
from backend.calibration.calibrator import RobotCalibrator
from backend.planner.grid import OccupancyGrid
from backend.planner.tsp import MultiTargetPlanner
from backend.planner.commands import PlanResult
from backend.motion.simulated import SimulatedController
from backend.motion.serial_controller import SerialController
from backend.motion.closed_loop import ClosedLoopExecutor


# --- INITIALIZE CONFIGURATION ---
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    return {}

def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False)

config = load_config()

# --- INITIALIZE CORE SERVICES ---
# Detector
model_path = config.get("model", {}).get("path", "models/best.onnx")
if os.path.exists(model_path):
    detector = OnnxDetector(
        model_path=model_path,
        input_size=config.get("model", {}).get("input_size", 640),
        conf_threshold=config.get("model", {}).get("conf_threshold", 0.60),
        uncertain_min=config.get("model", {}).get("uncertain_min", 0.30),
        iou_threshold=config.get("model", {}).get("iou_threshold", 0.45),
    )
    is_demo_mode = False
else:
    detector = DemoDetector(
        conf_threshold=config.get("model", {}).get("conf_threshold", 0.60),
        uncertain_min=config.get("model", {}).get("uncertain_min", 0.30),
    )
    is_demo_mode = True

tiler = TiledInferenceManager(
    tile_size=config.get("model", {}).get("tiling", {}).get("tile_size", 640),
    overlap_ratio=config.get("model", {}).get("tiling", {}).get("overlap_ratio", 0.20),
    min_image_dimension=config.get("model", {}).get("tiling", {}).get("min_image_dimension", 960),
)
temporal_filter = TemporalFilter()

# Calibrator
calib_cfg = config.get("calibration", {})
calibrator = RobotCalibrator(
    cm_per_pixel=calib_cfg.get("cm_per_pixel", 0.15),
    robot_length_cm=config.get("robot", {}).get("length_cm", 30.0),
    ground_y_offset_cm=calib_cfg.get("ground_plane_y_offset_cm", 10.0),
    camera_mount=config.get("camera", {}).get("mount", "robot_front_down"),
    status=calib_cfg.get("status", "uncalibrated"),
    homography_matrix=calib_cfg.get("homography_matrix", None),
)

# Motion Controller
sim_controller = SimulatedController(
    speed_cm_s=config.get("robot", {}).get("speed_cm_s", 15.0),
    turn_time_s_per_90=config.get("robot", {}).get("turn_time_s_per_90", 1.5),
    blade_enabled=config.get("blade", {}).get("enabled", False),
    dry_run=config.get("blade", {}).get("dry_run", True),
)
serial_controller = SerialController(
    port=config.get("motion", {}).get("serial_port", "COM3"),
    baudrate=config.get("motion", {}).get("baudrate", 115200),
    heartbeat_ms=config.get("motion", {}).get("heartbeat_ms", 200),
    failsafe_ms=config.get("motion", {}).get("failsafe_ms", 500),
)

# Create FastAPI App
app = FastAPI(
    title="AgriPath API",
    description="Weed vs Crop Detection and Skid-Steer Path Planning Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REQUEST / RESPONSE MODELS ---
class DetectionRequest(BaseModel):
    image_base64: Optional[str] = None
    is_live: bool = False
    conf_threshold: Optional[float] = None
    uncertain_min: Optional[float] = None

class PlanRequest(BaseModel):
    detections: List[Dict[str, Any]]
    start_pose: Optional[List[float]] = [0.0, 0.0, 0.0]  # [x, y, heading]
    return_to_start: Optional[bool] = False
    safety_margin_cm: Optional[float] = None
    turn_penalty_cm: Optional[float] = None

class CalibrateTwoPointRequest(BaseModel):
    pt1: List[float]  # [x, y]
    pt2: List[float]  # [x, y]
    real_distance_cm: float

class CalibrateManualRequest(BaseModel):
    cm_per_pixel: float

class FeedbackRequest(BaseModel):
    image_base64: Optional[str] = None
    plant_id: int
    corrected_class: str  # "crop" or "weed"
    bbox_px: List[float]


# --- API ROUTES ---
@app.get("/api/health")
def get_health():
    return {
        "status": "online",
        "app_name": "AgriPath",
        "demo_mode": is_demo_mode,
        "detector_model": detector.model_name,
        "calibration": calibrator.to_dict(),
        "robot_config": config.get("robot", {}),
        "blade_config": config.get("blade", {}),
        "serial_connected": serial_controller._is_connected,
    }

@app.get("/api/config")
def get_configuration():
    return config

@app.post("/api/config")
def update_configuration(new_cfg: Dict[str, Any]):
    global config
    config.update(new_cfg)
    save_config(config)
    return {"status": "success", "config": config}

@app.post("/api/detect")
async def detect_plants(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    is_live: bool = Form(False),
):
    """
    Receives image via multipart file or base64, runs detection,
    applies confidence safety policy, and maps coordinates to robot frame cm.
    """
    img_bytes = None
    if file:
        img_bytes = await file.read()
    elif image_base64:
        # Strip data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        img_bytes = base64.b64decode(image_base64)
    else:
        raise HTTPException(status_code=400, detail="No image provided.")

    try:
        image = WebUploadSource.load_from_bytes(img_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)}")

    h, w = image.shape[:2]

    # Run detection (with tiling if image is large)
    if tiler.should_tile((h, w)):
        det_result = tiler.detect_tiled(detector, image)
    else:
        det_result = detector.detect(image)

    # Apply temporal filter in live mode
    if is_live:
        det_result = temporal_filter.filter_frame(det_result)

    # Project pixel coordinates to robot frame (cm)
    for det in det_result.detections:
        cx, cy = det.center_px
        rx_cm, ry_cm = calibrator.pixel_to_robot_cm(cx, cy, (h, w))
        det.center_cm = (rx_cm, ry_cm)

        # Map bounding box corners to cm
        x1, y1, x2, y2 = det.bbox_px
        rx1, ry1 = calibrator.pixel_to_robot_cm(x1, y2, (h, w)) # bottom-left
        rx2, ry2 = calibrator.pixel_to_robot_cm(x2, y1, (h, w)) # top-right
        det.bbox_cm = (min(rx1, rx2), min(ry1, ry2), max(rx1, rx2), max(ry1, ry2))

    res_dict = det_result.to_dict()
    res_dict["calibration"] = calibrator.to_dict()
    return res_dict

@app.post("/api/plan")
def plan_path(req: PlanRequest):
    """
    Builds occupancy grid with inflated crop/uncertain obstacles,
    computes blade tool-offset stopping poses, and plans skid-steer trajectory.
    """
    robot_cfg = config.get("robot", {})
    blade_cfg = config.get("blade", {})
    planner_cfg = config.get("planner", {})

    safety_margin = req.safety_margin_cm or robot_cfg.get("safety_margin_cm", 4.0)
    turn_penalty = req.turn_penalty_cm or planner_cfg.get("turn_penalty_cm", 35.0)

    # Initialize Occupancy Grid
    grid = OccupancyGrid(
        grid_cell_size_cm=robot_cfg.get("grid_cell_size_cm", 2.0),
        robot_length_cm=robot_cfg.get("length_cm", 30.0),
        robot_width_cm=robot_cfg.get("width_cm", 25.0),
        safety_margin_cm=safety_margin,
        blade_offset_forward_cm=blade_cfg.get("offset_forward_cm", 18.0),
        blade_total_width_cm=blade_cfg.get("total_width_cm", 16.0),
        blade_pass_cm=blade_cfg.get("pass_cm", 8.0),
    )

    # Reconstruct PlantDetection list from request dictionaries
    detections: List[PlantDetection] = []
    for d in req.detections:
        det = PlantDetection(
            id=d["id"],
            class_id=d["class_id"],
            raw_class_name=d["raw_class_name"],
            status=PlantStatus(d["status"]),
            confidence=d["confidence"],
            bbox_px=tuple(d["bbox_px"]),
            center_px=tuple(d["center_px"]),
            center_cm=tuple(d["center_cm"]) if d.get("center_cm") else None,
            bbox_cm=tuple(d["bbox_cm"]) if d.get("bbox_cm") else None,
            is_obstacle=d.get("is_obstacle", False),
            is_target=d.get("is_target", False),
        )
        detections.append(det)

    # Populate obstacles in occupancy grid
    grid.populate_obstacles(detections)

    # Run Multi-Target TSP Planner
    planner = MultiTargetPlanner(
        grid=grid,
        turn_penalty_cm=turn_penalty,
        blade_offset_forward_cm=blade_cfg.get("offset_forward_cm", 18.0),
        blade_pass_cm=blade_cfg.get("pass_cm", 8.0),
        linear_speed_cm_s=robot_cfg.get("speed_cm_s", 15.0),
        turn_time_s_per_90=robot_cfg.get("turn_time_s_per_90", 1.5),
        return_to_start=req.return_to_start if req.return_to_start is not None else planner_cfg.get("return_to_start", False),
    )

    start_x = req.start_pose[0] if req.start_pose else 0.0
    start_y = req.start_pose[1] if req.start_pose else 0.0
    start_h = int(req.start_pose[2]) if req.start_pose else 0

    plan_result = planner.plan_mission(
        start_pose=(start_x, start_y, start_h),
        weed_detections=detections
    )

    return plan_result.to_dict()

@app.post("/api/calibrate/two-point")
def calibrate_two_point(req: CalibrateTwoPointRequest):
    scale = calibrator.calibrate_two_points(tuple(req.pt1), tuple(req.pt2), req.real_distance_cm)
    config["calibration"]["cm_per_pixel"] = round(scale, 4)
    config["calibration"]["status"] = "calibrated"
    config["calibration"]["mode"] = "two_point"
    save_config(config)
    return {"status": "success", "cm_per_pixel": scale, "calibration": calibrator.to_dict()}

@app.post("/api/calibrate/manual")
def calibrate_manual(req: CalibrateManualRequest):
    calibrator.calibrate_manual(req.cm_per_pixel)
    config["calibration"]["cm_per_pixel"] = round(req.cm_per_pixel, 4)
    config["calibration"]["status"] = "calibrated"
    config["calibration"]["mode"] = "manual"
    save_config(config)
    return {"status": "success", "cm_per_pixel": req.cm_per_pixel, "calibration": calibrator.to_dict()}

@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest):
    """
    Saves image and corrected bounding box label to data/feedback/ for retraining.
    """
    feedback_dir = os.path.join(os.path.dirname(__file__), "data", "feedback")
    os.makedirs(feedback_dir, exist_ok=True)

    timestamp = int(time.time() * 1000)
    meta = {
        "timestamp": timestamp,
        "plant_id": req.plant_id,
        "corrected_class": req.corrected_class,
        "bbox_px": req.bbox_px,
    }
    json_path = os.path.join(feedback_dir, f"feedback_{timestamp}_{req.plant_id}.json")
    with open(json_path, "w") as f:
        json.dump(meta, f, indent=2)

    if req.image_base64:
        if "," in req.image_base64:
            data = req.image_base64.split(",")[1]
        else:
            data = req.image_base64
        img_bytes = base64.b64decode(data)
        img_path = os.path.join(feedback_dir, f"feedback_{timestamp}_{req.plant_id}.jpg")
        with open(img_path, "wb") as f:
            f.write(img_bytes)

    return {"status": "success", "message": "Feedback saved for model retraining."}

@app.post("/api/motion/execute")
def execute_motion_command(cmd: Dict[str, Any]):
    ctrl = sim_controller if config.get("execution", {}).get("controller") == "simulated" else serial_controller
    c_type = cmd.get("cmd_type", "")
    val = float(cmd.get("value", 0.0))

    if c_type == "FORWARD":
        success = ctrl.forward(val)
    elif c_type == "BACKWARD":
        success = ctrl.backward(val)
    elif c_type == "TURN_LEFT":
        success = ctrl.turn(-val)
    elif c_type == "TURN_RIGHT":
        success = ctrl.turn(val)
    elif c_type == "BLADE_DOWN":
        success = ctrl.blade_down()
    elif c_type == "BLADE_UP":
        success = ctrl.blade_up()
    elif c_type == "BLADE_ON":
        success = ctrl.blade_on()
    elif c_type == "BLADE_OFF":
        success = ctrl.blade_off()
    elif c_type == "STOP":
        success = ctrl.stop()
    elif c_type == "ESTOP":
        success = ctrl.estop()
    else:
        success = False

    return {"success": success, "status": ctrl.get_status()}

@app.get("/api/evaluate")
def evaluate_model():
    from evaluate import evaluate_dataset
    dataset_dir = os.path.join(os.path.dirname(__file__), "data", "test")
    res = evaluate_dataset(dataset_dir, detector)
    return res

# Mount Static Frontend if built
frontend_dist = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

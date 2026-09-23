"""
AgriPath Headless Autonomous Execution Loop.
Designed for Raspberry Pi 4/5 headless deployment (web UI optional).
Usage:
    python run_headless.py --camera pi --loop
    python run_headless.py --synthetic --loop-count 1
"""
import os
import sys
import time
import argparse
import yaml
import cv2
import numpy as np

from backend.camera.pi_source import PiCameraSource
from backend.camera.web_source import WebUploadSource
from backend.detector.onnx_detector import OnnxDetector
from backend.detector.demo_detector import DemoDetector
from backend.calibration.calibrator import RobotCalibrator
from backend.planner.grid import OccupancyGrid
from backend.planner.tsp import MultiTargetPlanner
from backend.motion.simulated import SimulatedController
from backend.motion.serial_controller import SerialController
from backend.motion.closed_loop import ClosedLoopExecutor


def generate_synthetic_image(width: int = 1280, height: int = 720) -> np.ndarray:
    """Generates synthetic soil field image with crops and weeds."""
    # Soil background (brownish)
    img = np.full((height, width, 3), (35, 60, 85), dtype=np.uint8)
    # Add subtle soil texture noise
    noise = np.random.randint(-10, 10, (height, width, 3), dtype=np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Draw Crops (large lush green circles)
    crop_centers = [(int(width * 0.3), int(height * 0.4)), (int(width * 0.7), int(height * 0.4))]
    for cx, cy in crop_centers:
        cv2.circle(img, (cx, cy), 45, (30, 180, 40), -1)
        cv2.circle(img, (cx, cy), 30, (40, 210, 60), -1)

    # Draw Weeds (smaller irregular green patches)
    weed_centers = [(int(width * 0.5), int(height * 0.65)), (int(width * 0.35), int(height * 0.8))]
    for wx, wy in weed_centers:
        cv2.circle(img, (wx, wy), 22, (20, 160, 120), -1)
        cv2.circle(img, (wx, wy), 14, (30, 200, 140), -1)

    return img


def run_cycle(
    cycle_num: int,
    camera_source,
    detector,
    calibrator,
    planner_factory,
    motion_controller,
    args
):
    print(f"\n==========================================")
    print(f"  AGRIPATH MISSION CYCLE #{cycle_num}")
    print(f"==========================================")

    # 1. Capture Image
    t0 = time.time()
    if args.synthetic or camera_source is None:
        frame = generate_synthetic_image()
    else:
        frame = camera_source.capture_frame()

    if args.half_res:
        frame = cv2.resize(frame, (frame.shape[1] // 2, frame.shape[0] // 2))

    h, w = frame.shape[:2]
    print(f"[Vision] Captured image ({w}x{h}) in {(time.time() - t0)*1000:.1f} ms")

    # 2. Plant Detection
    t_det = time.time()
    det_result = detector.detect(frame)
    det_ms = (time.time() - t_det) * 1000.0
    print(f"[Vision] Detected {len(det_result.detections)} plants in {det_ms:.1f} ms (Mode: {detector.model_name})")

    # 3. Project to Robot Frame (cm)
    for det in det_result.detections:
        cx, cy = det.center_px
        rx_cm, ry_cm = calibrator.pixel_to_robot_cm(cx, cy, (h, w))
        det.center_cm = (rx_cm, ry_cm)
        print(f"  - Plant #{det.id}: {det.status.value} (conf: {det.confidence:.2f}) at robot pos ({rx_cm} cm, {ry_cm} cm)")

    # 4. Grid & Path Planning
    t_plan = time.time()
    grid, planner = planner_factory()
    grid.populate_obstacles(det_result.detections)

    plan = planner.plan_mission(
        start_pose=(0.0, 0.0, 0),
        weed_detections=det_result.detections
    )
    plan_ms = (time.time() - t_plan) * 1000.0

    print(f"[Planner] Generated {len(plan.commands)} commands in {plan_ms:.1f} ms")
    print(f"  - Total Distance: {plan.total_distance_cm:.1f} cm | Total Turns: {plan.total_turns} | Est Time: {plan.estimated_time_s:.1f} s")
    print(f"  - Weeds Handled: {plan.handled_weeds} | Skipped: {[s['weed_id'] for s in plan.skipped_weeds]}")

    for cmd in plan.commands:
        print(f"    [{cmd.step:02d}] {cmd.to_serial_code():<8} : {cmd.action_text}")

    # 5. Motion Execution
    print(f"[Motion] Executing mission via {args.controller} controller...")
    executor = ClosedLoopExecutor(motion_controller, mode="open_loop")
    exec_result = executor.execute_plan(plan)
    print(f"[Motion] Execution Status: {exec_result['status']} in {exec_result['elapsed_time_s']:.1f} s. Final Pose: {exec_result['final_pose']}")


def main():
    parser = argparse.ArgumentParser(description="AgriPath Headless Rover Runner")
    parser.add_argument("--camera", type=str, choices=["pi", "web", "synthetic"], default="synthetic")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic field generator")
    parser.add_argument("--loop", action="store_true", help="Run continuous perception-planning loop")
    parser.add_argument("--loop-count", type=int, default=1, help="Number of loops to execute")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between loops in seconds")
    parser.add_argument("--imgsz", type=int, default=640, help="Inference resolution")
    parser.add_argument("--half-res", action="store_true", help="Halve capture resolution for maximum speed on Pi")
    parser.add_argument("--controller", type=str, choices=["simulated", "serial"], default="simulated")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    with open(args.config, "r") as f:
        cfg = yaml.safe_load(f)

    # Initialize Camera
    cam_source = None
    if args.camera == "pi" and not args.synthetic:
        cam_source = PiCameraSource()

    # Initialize Detector
    model_path = cfg.get("model", {}).get("path", "models/best.onnx")
    if os.path.exists(model_path):
        detector = OnnxDetector(model_path=model_path, input_size=args.imgsz)
        print(f"Loaded YOLOv8 ONNX model: {model_path}")
    else:
        detector = DemoDetector()
        print("Model file not found. Running in DEMO MODE.")

    # Initialize Calibrator
    calib_cfg = cfg.get("calibration", {})
    calibrator = RobotCalibrator(
        cm_per_pixel=calib_cfg.get("cm_per_pixel", 0.15),
        robot_length_cm=cfg.get("robot", {}).get("length_cm", 30.0),
        ground_y_offset_cm=calib_cfg.get("ground_plane_y_offset_cm", 10.0),
    )

    # Initialize Motion Controller
    if args.controller == "serial":
        motion_ctrl = SerialController(
            port=cfg.get("motion", {}).get("serial_port", "COM3"),
            baudrate=cfg.get("motion", {}).get("baudrate", 115200),
        )
    else:
        motion_ctrl = SimulatedController(
            speed_cm_s=cfg.get("robot", {}).get("speed_cm_s", 15.0),
            turn_time_s_per_90=cfg.get("robot", {}).get("turn_time_s_per_90", 1.5),
            blade_enabled=cfg.get("blade", {}).get("enabled", False),
            dry_run=cfg.get("blade", {}).get("dry_run", True),
        )

    # Planner Factory
    def make_planner():
        r_cfg = cfg.get("robot", {})
        b_cfg = cfg.get("blade", {})
        p_cfg = cfg.get("planner", {})
        grid = OccupancyGrid(
            grid_cell_size_cm=r_cfg.get("grid_cell_size_cm", 2.0),
            robot_length_cm=r_cfg.get("length_cm", 30.0),
            robot_width_cm=r_cfg.get("width_cm", 25.0),
            safety_margin_cm=r_cfg.get("safety_margin_cm", 4.0),
            blade_offset_forward_cm=b_cfg.get("offset_forward_cm", 18.0),
            blade_total_width_cm=b_cfg.get("total_width_cm", 16.0),
            blade_pass_cm=b_cfg.get("pass_cm", 8.0),
        )
        planner = MultiTargetPlanner(
            grid=grid,
            turn_penalty_cm=p_cfg.get("turn_penalty_cm", 35.0),
            blade_offset_forward_cm=b_cfg.get("offset_forward_cm", 18.0),
            blade_pass_cm=b_cfg.get("pass_cm", 8.0),
            linear_speed_cm_s=r_cfg.get("speed_cm_s", 15.0),
            turn_time_s_per_90=r_cfg.get("turn_time_s_per_90", 1.5),
            return_to_start=p_cfg.get("return_to_start", False),
        )
        return grid, planner

    cycles = 0
    while True:
        cycles += 1
        run_cycle(cycles, cam_source, detector, calibrator, make_planner, motion_ctrl, args)
        if not args.loop and cycles >= args.loop_count:
            break
        time.sleep(args.delay)


if __name__ == "__main__":
    main()

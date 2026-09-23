# AgriPath: 6-Wheel Skid-Steer Rover Weed Targeting & Path Planning System

AgriPath is an autonomous perception and movement-planning robotic system engineered for a **6-wheel skid-steer rover carrying dual front cutting blades**. It detects plants in real-time, classifies them as **CROP** or **WEED** with a strict safety confidence policy, builds an obstacle-inflated real-world occupancy grid, and plans the shortest collision-free trajectory using skid-steer legal motion primitives.

The system is optimized for **offline edge execution on Raspberry Pi 4/5** and communicates with an Arduino or ESP32 microcontroller over USB serial for real-time motor PID and blade control.

---

## Quick Start (2 Commands)

### 1. Launch the Complete System (FastAPI + Built React UI)
```bash
python main.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.
*(The built React + Vite frontend is automatically served directly by FastAPI!)*

### 2. (Optional) Run Headless Autonomous Loop on Raspberry Pi
```bash
python run_headless.py --camera pi --loop
```
*For desktop testing with simulated camera and rover:*
```bash
python run_headless.py --synthetic --loop-count 1
```

---

## System Architecture

```
                                  [ USB Camera / Picamera2 ]
                                              │
                                              ▼
                                 [ Vision Layer (YOLOv8) ]
                                   (ONNX CPU / Demo Fallback)
                                              │
                                              ▼
                               [ Robot Frame Calibration ]
                                (Origin: Rover Center, cm)
                                              │
                                              ▼
                                [ Kinematic Occupancy Grid ]
                           (Crops & Uncertain = Inflated Obstacles)
                                              │
                                              ▼
                              [ 4-Heading Skid-Steer A* + TSP ]
                               (Turn Slip Penalty Optimization)
                                              │
                                              ▼
                               [ Command Generator & Slicer ]
                           (Tool Offset Stops & Consecutive Merging)
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
         [ Web UI / Simulation ]                             [ Serial Line Protocol ]
         - Bounding Boxes & Paths                            - 200 ms Heartbeat Ping
         - Footprint & Blade Zones                           - 500 ms Safety Watchdog
         - Interactive Waypoints                             - Line cmds: F400, TL90, BD, BON
                                                                        │
                                                                        ▼
                                                             [ Arduino / ESP32 Rover ]
```

---

## Robot Kinematics & Tool Geometry

1. **6-Wheel Skid-Steer Drive**:
   - The rover **cannot move sideways**.
   - Strictly legal primitives: `FORWARD <cm>`, `TURN_LEFT 90°`, `TURN_RIGHT 90°`, (optional `BACKWARD <cm>`).
   - Any lateral offset is executed via in-place pivots (`TURN_LEFT 90°` $\rightarrow$ `FORWARD` $\rightarrow$ `TURN_RIGHT 90°`).
   - High turn penalty (`turn_penalty_cm: 35.0`) penalizes excessive skid-turns on soil to prevent wheel slippage.

2. **In-Place Rotation Safety**:
   - Turn collision check uses the rover's circumscribed circle radius:
     $$R_{\text{turn}} = \sqrt{\left(\frac{L}{2} + \text{offset}_{\text{blade}} + \text{pass}\right)^2 + \left(\frac{W}{2}\right)^2}$$
   - Zero crop contact is strictly guaranteed during $90^\circ$ turns.

3. **Front Dual Cutting Blades**:
   - **Tool Point**: Located at $(0, \text{offset\_forward\_cm})$ ahead of the rover center.
   - The rover stops `offset_forward_cm` **before** the weed, facing it.
   - **Blade Cutting Zone**: Width `blade.total_width_cm`, reach $\text{offset} + \text{pass}$. The cutting zone is checked against all crops. If a crop is within the blade path, the weed is safely marked **`SKIPPED - too close to crop / unreachable`**.
   - Standard cutting cycle at weed:
     ```
     STOP -> BLADE_DOWN -> BLADE_ON -> FORWARD pass_cm -> BLADE_OFF -> BLADE_UP
     ```

---

## Safety & Confidence Policy

- **$\text{Confidence} \ge 0.60$**: Confirmed class prediction accepted.
- **$0.30 \le \text{Confidence} < 0.60$**: Marked **`UNCERTAIN`**. Safety critical: **always treated as a CROP obstacle** (never targeted by blades; listed in UI for manual review).
- **$\text{Confidence} < 0.30$**: Discarded as noise.
- **Demo Mode Fallback**: If `models/best.onnx` is missing, the app automatically runs in **Demo Mode** using OpenCV green foliage color segmentation with a prominent banner in the UI.

---

## Microcontroller Firmware & Serial Protocol

The firmware skeleton for Arduino / ESP32 is located in `firmware/skid_steer_rover.ino`.

### Line Protocol (distances in mm, angles in deg):
- `F<dist_mm>`: Forward (e.g., `F400` = 400 mm / 40 cm)
- `B<dist_mm>`: Backward (e.g., `B100`)
- `TL<deg>`: In-place turn left (e.g., `TL90`)
- `TR<deg>`: In-place turn right (e.g., `TR90`)
- `BD`: Lower blades (servo down)
- `BU`: Raise blades (servo up)
- `BON`: Blade cutting motor ON
- `BOFF`: Blade cutting motor OFF
- `STOP`: Controlled deceleration
- `ESTOP`: Emergency hardware stop
- `PING`: Heartbeat message from Raspberry Pi

### Safety Watchdog:
The firmware runs a **500 ms hardware watchdog timer**. If no `PING` is received from the host within 500 ms, the microcontroller immediately cuts drive motor PWM and blade relays.

> [!CAUTION]
> **Bench Testing Rules**:
> 1. Always conduct initial testing with the rover chassis propped up on blocks (**wheels completely off the ground**).
> 2. **Remove cutting blades** from motor shafts until odometry and waypoint navigation are fully calibrated.
> 3. Have a hardware emergency stop kill switch wired in series with the main battery supply.

---

## Raspberry Pi 4 / 5 Setup Guide

### 1. OS & System Packages
Install Raspberry Pi OS 64-bit (Debian Bullseye or Bookworm).
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git libgl1 libglib2.0-0 libgomp1 v4l-utils
```

### 2. Camera Setup (Picamera2)
Enable camera in `raspi-config` (`Interface Options -> Camera`), then test:
```bash
rpicam-hello -t 2000
```

### 3. USB Serial Permissions
Grant user access to Arduino/ESP32 serial ports:
```bash
sudo usermod -a -G dialout $USER
```

### 4. Install AgriPath
```bash
git clone https://github.com/your-repo/AgriPath.git
cd AgriPath
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. High-Speed Flags for Pi
```bash
# Halves camera resolution and uses 320x320 letterbox for ultra-low latency:
python run_headless.py --camera pi --half-res --imgsz 320 --loop
```

### 6. Systemd Autostart Service
Create `/etc/systemd/system/agripath.service`:
```ini
[Unit]
Description=AgriPath Autonomous Weed Rover Service
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/AgriPath
ExecStart=/home/pi/AgriPath/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable agripath.service
sudo systemctl start agripath.service
```

---

## Model Training & Evaluation

- Fine-tuning guide and dataset preparation: see [train.md](file:///d:/SIH/Weed%20Detector/train.md).
- Run automated accuracy benchmark on test datasets:
```bash
python evaluate.py --dataset data/test
```
*(Calculates Precision, Recall, F1, mAP@0.5, per-class breakdown, and confusion matrix without hard-coded numbers).*

---

## Unit & Integration Tests

Run the complete test suite:
```bash
pytest -v tests/
```
Covers:
- Pixel-to-robot cm coordinate conversion
- 2-point and manual scale calibration
- Occupancy grid rasterization and obstacle safety inflation
- Skid-steer non-holonomic footprint and turn radius collision checks
- Heading-aware 4-direction A* pathfinding
- Consecutive step compression and serial code formatting
- Front blade tool-offset stopping positioning
- **Synthetic Field Case 1**: Simple field safe path and cutting cycle
- **Synthetic Field Case 2**: Trapped weed skipped for crop safety
- **Synthetic Field Case 3**: Turn slip penalty collinear route selection

---

## Deliverables & What You Still Must Provide

### Provided in this Build:
- [x] Complete production prototype codebase ready for Raspberry Pi 4/5.
- [x] Full FastAPI backend with ONNX YOLOv8 runtime, SAHI tiled slicing, and Demo Mode green color fallback.
- [x] Responsive React + Vite frontend with live camera streaming, interactive canvas, rover footprint & blade overlays, waypoint animations, and mission exports (JSON / CSV).
- [x] Skid-steer kinematics planner with in-place rotation circles, tool-offset stopping, and Or-opt TSP routing.
- [x] Motion layer with simulated odometry, serial line protocol, 200 ms heartbeat, and closed-loop replanning.
- [x] Arduino / ESP32 firmware skeleton (`firmware/skid_steer_rover.ino`).
- [x] 100% passing test suite across calibration, grid, collision, A*, tool offset, and synthetic fields.
- [x] Standalone headless execution runner (`run_headless.py`).
- [x] Model evaluation suite (`evaluate.py`) and training documentation (`train.md`).

### What You Must Still Provide for Real-World Deployment:
1. **Trained ONNX Model**: Fine-tune YOLOv8 on your specific local weeds and crops following [train.md](file:///d:/SIH/Weed%20Detector/train.md), export with `simplify=True`, and place at `models/best.onnx`.
2. **Camera Calibration**: Mount camera rigidly on the rover chassis and calibrate ground scale (using the 2-point tool or ArUco markers) to determine `cm_per_pixel`.
3. **Physical Chassis Measurements**: Update `config.yaml` with your actual rover chassis length, width, blade reach (`offset_forward_cm`), and cutting width (`total_width_cm`).
4. **Firmware Tuning**: Tune motor encoder ticks per millimeter (`MM_PER_TICK`) and wheel track base (`WHEEL_BASE_MM`) in `firmware/skid_steer_rover.ino` for your specific motors and wheel diameter.

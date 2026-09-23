"""
Unit tests for RobotCalibrator (pixel to robot frame cm conversion).
"""
import pytest
import numpy as np
from backend.calibration.calibrator import RobotCalibrator


def test_manual_calibration():
    calib = RobotCalibrator(cm_per_pixel=0.10)
    assert not calib.is_calibrated()
    calib.calibrate_manual(0.20)
    assert calib.is_calibrated()
    assert calib.cm_per_pixel == 0.20


def test_two_point_calibration():
    calib = RobotCalibrator()
    # 100 pixels between (100, 100) and (200, 100) representing 20.0 cm
    pt1 = (100.0, 100.0)
    pt2 = (200.0, 100.0)
    scale = calib.calibrate_two_points(pt1, pt2, real_distance_cm=20.0)
    assert scale == pytest.approx(0.20, abs=1e-4)
    assert calib.is_calibrated()


def test_pixel_to_robot_cm():
    calib = RobotCalibrator(
        cm_per_pixel=0.10,
        robot_length_cm=30.0,
        ground_y_offset_cm=10.0,
    )
    # Image shape 1000x1000 (h, w)
    # Bottom center is (x=500, y=1000)
    # Front edge Y = 30/2 + 10 = 25 cm
    rx, ry = calib.pixel_to_robot_cm(500.0, 1000.0, (1000, 1000))
    assert rx == pytest.approx(0.0, abs=1e-2)
    assert ry == pytest.approx(25.0, abs=1e-2)

    # 100 px up from bottom (y=900) -> 10 cm further forward -> Y = 35 cm
    rx, ry = calib.pixel_to_robot_cm(500.0, 900.0, (1000, 1000))
    assert rx == pytest.approx(0.0, abs=1e-2)
    assert ry == pytest.approx(35.0, abs=1e-2)

    # 200 px right from center (x=700, y=1000) -> X = +20 cm
    rx, ry = calib.pixel_to_robot_cm(700.0, 1000.0, (1000, 1000))
    assert rx == pytest.approx(20.0, abs=1e-2)
    assert ry == pytest.approx(25.0, abs=1e-2)


def test_roundtrip_transformation():
    calib = RobotCalibrator(
        cm_per_pixel=0.15,
        robot_length_cm=30.0,
        ground_y_offset_cm=10.0,
    )
    shape = (720, 1280)
    orig_px, orig_py = 750.0, 450.0

    rx, ry = calib.pixel_to_robot_cm(orig_px, orig_py, shape)
    rec_px, rec_py = calib.robot_cm_to_pixel(rx, ry, shape)

    assert rec_px == pytest.approx(orig_px, abs=1e-1)
    assert rec_py == pytest.approx(orig_py, abs=1e-1)

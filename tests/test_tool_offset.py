"""
Unit tests for tool point offset calculation and stopping pose alignment.
"""
import math
import pytest
from backend.planner.grid import OccupancyGrid
from backend.planner.commands import CommandGenerator
from backend.detector.base import PlantDetection, PlantStatus


def test_tool_offset_stopping_pose():
    grid = OccupancyGrid(
        grid_cell_size_cm=2.0,
        robot_length_cm=30.0,
        robot_width_cm=25.0,
        blade_offset_forward_cm=18.0,
        blade_pass_cm=8.0,
        blade_total_width_cm=16.0,
    )
    cmd_gen = CommandGenerator(grid, blade_offset_forward_cm=18.0, blade_pass_cm=8.0)

    weed = PlantDetection(
        id=5,
        class_id=1,
        raw_class_name="weed",
        status=PlantStatus.WEED,
        confidence=0.88,
        bbox_px=(0, 0, 10, 10),
        center_px=(5, 5),
        center_cm=(10.0, 50.0),
        is_target=True
    )

    candidates = cmd_gen.compute_candidate_poses_for_weed(weed)
    assert len(candidates) > 0

    # For heading 0 (+Y, facing up):
    # Rover center should be at (wx, wy - 18.0) = (10.0, 32.0)
    # Tool point = robot_center + 18.0 * (0, 1) = (10.0, 50.0) -> EXACTLY weed center!
    pose_h0 = next((p for p in candidates if p[2] == 0), None)
    assert pose_h0 is not None
    rx, ry, heading = pose_h0
    assert rx == pytest.approx(10.0, abs=0.1)
    assert ry == pytest.approx(32.0, abs=0.1)

    # Compute tool point from robot pose
    rad = math.radians(heading)
    tool_x = rx + 18.0 * math.sin(rad)
    tool_y = ry + 18.0 * math.cos(rad)

    assert tool_x == pytest.approx(10.0, abs=0.1)
    assert tool_y == pytest.approx(50.0, abs=0.1)


def test_cutting_sequence_structure():
    grid = OccupancyGrid(grid_cell_size_cm=2.0)
    cmd_gen = CommandGenerator(grid, blade_pass_cm=8.0)

    seq = cmd_gen.generate_cut_sequence(weed_id=3, starting_step=1)
    assert len(seq) == 6

    expected_cmds = ["STOP", "BLADE_DOWN", "BLADE_ON", "FORWARD", "BLADE_OFF", "BLADE_UP"]
    for i, exp in enumerate(expected_cmds):
        assert seq[i].cmd_type == exp
        assert seq[i].target_weed_id == 3

    # Cutting pass forward move must match pass_cm
    assert seq[3].value == 8.0

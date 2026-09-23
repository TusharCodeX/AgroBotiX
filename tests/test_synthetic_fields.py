"""
Integration tests with 3 distinct synthetic field scenarios:
Case 1: Simple open field with 1 weed -> generates safe forward route & cut.
Case 2: Weed trapped right next to a crop -> SKIPPED (never touches crop!).
Case 3: Two weeds where high turn penalty prefers direct straight route over zig-zag.
"""
import pytest
from backend.planner.grid import OccupancyGrid
from backend.planner.tsp import MultiTargetPlanner
from backend.detector.base import PlantDetection, PlantStatus


def test_synthetic_case_1_simple_field():
    """
    Scenario 1: Simple field.
    Rover at (0, 0, 0). One isolated weed ahead at (0, 40).
    Expected: Straight forward move, stopping offset_forward_cm before weed, then cut sequence.
    """
    grid = OccupancyGrid(
        grid_cell_size_cm=2.0,
        x_min_cm=-50.0, x_max_cm=50.0,
        y_min_cm=-10.0, y_max_cm=80.0,
        robot_length_cm=30.0, robot_width_cm=25.0,
        safety_margin_cm=4.0,
        blade_offset_forward_cm=18.0,
        blade_pass_cm=8.0,
    )
    weed = PlantDetection(
        id=1,
        class_id=1,
        raw_class_name="weed",
        status=PlantStatus.WEED,
        confidence=0.92,
        bbox_px=(0, 0, 10, 10),
        center_px=(0, 0),
        center_cm=(0.0, 40.0),
        is_target=True
    )
    grid.populate_obstacles([])

    planner = MultiTargetPlanner(
        grid=grid,
        turn_penalty_cm=35.0,
        blade_offset_forward_cm=18.0,
        blade_pass_cm=8.0,
    )
    plan = planner.plan_mission(start_pose=(0.0, 0.0, 0), weed_detections=[weed])

    assert 1 in plan.handled_weeds
    assert len(plan.skipped_weeds) == 0

    # Rover starts at (0,0) and stops at (0, 40 - 18 = 22)
    first_cmd = plan.commands[0]
    assert first_cmd.cmd_type == "FORWARD"
    assert first_cmd.value == pytest.approx(22.0, abs=2.0)

    # Sequence has cutting steps
    cut_types = [c.cmd_type for c in plan.commands if c.target_weed_id == 1]
    assert "BLADE_DOWN" in cut_types
    assert "BLADE_ON" in cut_types
    assert "BLADE_OFF" in cut_types
    assert "BLADE_UP" in cut_types


def test_synthetic_case_2_weed_trapped_next_to_crop_skipped():
    """
    Scenario 2: Weed trapped right next to a large crop.
    Crop is at (0, 40), Weed is at (1, 40) - inside crop safety margin.
    Expected: Weed marked SKIPPED - too close to crop / unreachable.
    Zero collisions occur.
    """
    grid = OccupancyGrid(
        grid_cell_size_cm=2.0,
        x_min_cm=-50.0, x_max_cm=50.0,
        y_min_cm=-10.0, y_max_cm=80.0,
        robot_length_cm=30.0, robot_width_cm=25.0,
        safety_margin_cm=4.0,
        blade_offset_forward_cm=18.0,
        blade_pass_cm=8.0,
        blade_total_width_cm=16.0,
    )
    crop = PlantDetection(
        id=10,
        class_id=0,
        raw_class_name="crop",
        status=PlantStatus.CROP,
        confidence=0.95,
        bbox_px=(0, 0, 10, 10),
        center_px=(0, 0),
        center_cm=(0.0, 40.0),
        bbox_cm=(-6.0, 34.0, 6.0, 46.0),
        is_obstacle=True
    )
    # Weed right adjacent to crop
    trapped_weed = PlantDetection(
        id=20,
        class_id=1,
        raw_class_name="weed",
        status=PlantStatus.WEED,
        confidence=0.85,
        bbox_px=(0, 0, 5, 5),
        center_px=(0, 0),
        center_cm=(2.0, 40.0),
        is_target=True
    )
    grid.populate_obstacles([crop])

    planner = MultiTargetPlanner(
        grid=grid,
        turn_penalty_cm=35.0,
        blade_offset_forward_cm=18.0,
        blade_pass_cm=8.0,
    )
    plan = planner.plan_mission(start_pose=(0.0, 0.0, 0), weed_detections=[trapped_weed])

    # Must be skipped!
    assert 20 not in plan.handled_weeds
    assert len(plan.skipped_weeds) == 1
    assert plan.skipped_weeds[0]["weed_id"] == 20
    assert "SKIPPED" in plan.skipped_weeds[0]["reason"]


def test_synthetic_case_3_turn_penalty_route_selection():
    """
    Scenario 3: Two weeds in a line vs with a turn.
    High turn penalty forces the planner to prioritize collinear weeds or straight movements
    over zig-zagging routes.
    """
    grid = OccupancyGrid(
        grid_cell_size_cm=2.0,
        x_min_cm=-50.0, x_max_cm=50.0,
        y_min_cm=-10.0, y_max_cm=100.0,
        robot_length_cm=20.0, robot_width_cm=18.0,
        blade_offset_forward_cm=15.0,
        blade_pass_cm=6.0,
    )
    weed1 = PlantDetection(
        id=1, class_id=1, raw_class_name="weed", status=PlantStatus.WEED, confidence=0.9,
        bbox_px=(0,0,1,1), center_px=(0,0), center_cm=(0.0, 35.0), is_target=True
    )
    weed2 = PlantDetection(
        id=2, class_id=1, raw_class_name="weed", status=PlantStatus.WEED, confidence=0.9,
        bbox_px=(0,0,1,1), center_px=(0,0), center_cm=(0.0, 65.0), is_target=True
    )

    grid.populate_obstacles([])
    planner = MultiTargetPlanner(
        grid=grid,
        turn_penalty_cm=50.0, # High turn penalty
        blade_offset_forward_cm=15.0,
        blade_pass_cm=6.0,
    )
    plan = planner.plan_mission(start_pose=(0.0, 0.0, 0), weed_detections=[weed1, weed2])

    assert plan.handled_weeds == [1, 2]
    # Because they are collinear along heading 0, total turns should be 0!
    assert plan.total_turns == 0

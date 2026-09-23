"""
Unit tests for SkidSteerAStar 4-heading state-space pathfinding.
"""
import pytest
from backend.planner.grid import OccupancyGrid
from backend.planner.astar import SkidSteerAStar
from backend.detector.base import PlantDetection, PlantStatus


def test_straight_line_astar():
    grid = OccupancyGrid(grid_cell_size_cm=2.0, x_min_cm=-40.0, x_max_cm=40.0, y_min_cm=-10.0, y_max_cm=60.0)
    astar = SkidSteerAStar(grid)

    start = (0.0, 0.0, 0)
    goal = (0.0, 20.0, 0)

    path = astar.plan(start, goal)
    assert path is not None
    assert len(path) > 1

    # End coordinates match goal
    last_x, last_y, last_h, _ = path[-1]
    assert last_x == pytest.approx(0.0, abs=2.0)
    assert last_y == pytest.approx(20.0, abs=2.0)
    assert last_h == 0

    # Primitives must only be FORWARD
    actions = [p[3] for p in path[1:]]
    assert all(a == "FORWARD" for a in actions)


def test_turn_left_and_right_primitives():
    grid = OccupancyGrid(grid_cell_size_cm=2.0, x_min_cm=-40.0, x_max_cm=40.0, y_min_cm=-10.0, y_max_cm=60.0)
    astar = SkidSteerAStar(grid, turn_penalty_cm=10.0)

    # Move from (0, 0, 0) to (+20, 20, 90)
    start = (0.0, 0.0, 0)
    goal = (20.0, 20.0, 90)

    path = astar.plan(start, goal)
    assert path is not None

    # Check legal primitives only
    actions = set(p[3] for p in path[1:])
    for a in actions:
        assert a in ("FORWARD", "TURN_LEFT", "TURN_RIGHT")


def test_obstacle_avoidance():
    grid = OccupancyGrid(
        grid_cell_size_cm=2.0,
        x_min_cm=-50.0,
        x_max_cm=50.0,
        y_min_cm=-10.0,
        y_max_cm=80.0,
        robot_length_cm=20.0,
        robot_width_cm=15.0,
        safety_margin_cm=2.0
    )
    # Put a crop in the path between (0,0) and (0, 70)
    crop = PlantDetection(
        id=1,
        class_id=0,
        raw_class_name="crop",
        status=PlantStatus.CROP,
        confidence=0.95,
        bbox_px=(0, 0, 1, 1),
        center_px=(0, 0),
        center_cm=(0.0, 35.0),
        bbox_cm=(-4.0, 31.0, 4.0, 39.0),
        is_obstacle=True
    )
    grid.populate_obstacles([crop])

    astar = SkidSteerAStar(grid, turn_penalty_cm=15.0)
    start = (0.0, 0.0, 0)
    goal = (0.0, 70.0, 0)

    path = astar.plan(start, goal)
    assert path is not None

    # Path must detour around obstacle (x != 0 during middle of path)
    xs = [p[0] for p in path]
    assert max(map(abs, xs)) > 5.0  # Successfully maneuvered around crop

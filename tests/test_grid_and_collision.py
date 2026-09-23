"""
Unit tests for OccupancyGrid, obstacle inflation, footprint collision, and turn radius.
"""
import pytest
from backend.planner.grid import OccupancyGrid
from backend.detector.base import PlantDetection, PlantStatus


def test_grid_building_and_mapping():
    grid = OccupancyGrid(grid_cell_size_cm=2.0, x_min_cm=-50.0, x_max_cm=50.0, y_min_cm=0.0, y_max_cm=100.0)
    row, col = grid.world_to_grid(0.0, 50.0)
    wx, wy = grid.grid_to_world(row, col)

    assert wx == pytest.approx(0.0, abs=2.0)
    assert wy == pytest.approx(50.0, abs=2.0)
    assert not grid.is_point_occupied(0.0, 50.0)


def test_obstacle_inflation():
    grid = OccupancyGrid(
        grid_cell_size_cm=2.0,
        x_min_cm=-50.0,
        x_max_cm=50.0,
        y_min_cm=0.0,
        y_max_cm=100.0,
        safety_margin_cm=4.0
    )

    crop = PlantDetection(
        id=1,
        class_id=0,
        raw_class_name="crop",
        status=PlantStatus.CROP,
        confidence=0.95,
        bbox_px=(0, 0, 10, 10),
        center_px=(5, 5),
        center_cm=(0.0, 50.0),
        bbox_cm=(-5.0, 45.0, 5.0, 55.0), # 10x10cm crop
        is_obstacle=True
    )
    grid.populate_obstacles([crop])

    # Center is occupied
    assert grid.is_point_occupied(0.0, 50.0)

    # 3 cm outside the original 5cm box (e.g. at x=8.0) -> inside the 4cm safety margin -> occupied
    assert grid.is_point_occupied(8.0, 50.0)

    # 15 cm outside (e.g. at x=20.0) -> free
    assert not grid.is_point_occupied(20.0, 50.0)


def test_translation_and_turn_collision():
    grid = OccupancyGrid(
        grid_cell_size_cm=2.0,
        robot_length_cm=30.0,
        robot_width_cm=25.0,
        safety_margin_cm=4.0,
        blade_offset_forward_cm=18.0,
    )
    # Place obstacle at (0.0, 60.0)
    crop = PlantDetection(
        id=1,
        class_id=0,
        raw_class_name="crop",
        status=PlantStatus.CROP,
        confidence=0.90,
        bbox_px=(0,0,10,10),
        center_px=(5,5),
        center_cm=(0.0, 60.0),
        bbox_cm=(-5.0, 55.0, 5.0, 65.0),
        is_obstacle=True
    )
    grid.populate_obstacles([crop])

    # Placing robot center at (0.0, 60.0) must collide
    assert not grid.is_translation_safe(0.0, 60.0, heading_deg=0)

    # Placing robot center far away at (0.0, 10.0) is safe
    assert grid.is_translation_safe(0.0, 10.0, heading_deg=0)

    # In-place turn safety: turn radius is ~24cm
    # At (0.0, 60.0 - 20.0 = 40.0), turn circle reaches into obstacle (distance 20cm < turn_radius)
    assert not grid.is_turn_safe(0.0, 40.0)

    # Far away at (0.0, 0.0), turn is safe
    assert grid.is_turn_safe(0.0, 0.0)

"""
Unit tests for command merging and firmware serial code generation.
"""
import pytest
from backend.planner.grid import OccupancyGrid
from backend.planner.commands import CommandGenerator, RoverCommand, PlanResult


def test_consecutive_forward_merging():
    grid = OccupancyGrid(grid_cell_size_cm=2.0)
    cmd_gen = CommandGenerator(grid)

    # 4 consecutive forward steps of 2cm each
    raw_path = [
        (0.0, 0.0, 0, "START"),
        (0.0, 2.0, 0, "FORWARD"),
        (0.0, 4.0, 0, "FORWARD"),
        (0.0, 6.0, 0, "FORWARD"),
        (0.0, 8.0, 0, "FORWARD"),
    ]

    cmds = cmd_gen.compress_path_into_commands(raw_path)
    assert len(cmds) == 1
    assert cmds[0].cmd_type == "FORWARD"
    assert cmds[0].value == pytest.approx(8.0, abs=0.1)
    assert cmds[0].unit == "cm"


def test_turn_and_forward_sequence():
    grid = OccupancyGrid(grid_cell_size_cm=2.0)
    cmd_gen = CommandGenerator(grid)

    raw_path = [
        (0.0, 0.0, 0, "START"),
        (0.0, 4.0, 0, "FORWARD"),
        (0.0, 4.0, 90, "TURN_RIGHT"),
        (4.0, 4.0, 90, "FORWARD"),
    ]

    cmds = cmd_gen.compress_path_into_commands(raw_path)
    assert len(cmds) == 3
    assert cmds[0].cmd_type == "FORWARD"
    assert cmds[0].value == pytest.approx(4.0, abs=0.1)

    assert cmds[1].cmd_type == "TURN_RIGHT"
    assert cmds[1].value == 90.0

    assert cmds[2].cmd_type == "FORWARD"
    assert cmds[2].value == pytest.approx(4.0, abs=0.1)


def test_serial_code_generation():
    fwd = RoverCommand(step=1, cmd_type="FORWARD", value=40.0, unit="cm")
    assert fwd.to_serial_code() == "F400"  # 40cm = 400mm

    turn_l = RoverCommand(step=2, cmd_type="TURN_LEFT", value=90.0, unit="deg")
    assert turn_l.to_serial_code() == "TL90"

    b_down = RoverCommand(step=3, cmd_type="BLADE_DOWN", value=0.0, unit="")
    assert b_down.to_serial_code() == "BD"

    b_on = RoverCommand(step=4, cmd_type="BLADE_ON", value=0.0, unit="")
    assert b_on.to_serial_code() == "BON"

"""
Command Generation, Tool-Offset Stop Calculation, and Consecutive Step Merging.
Translates planned trajectory into skid-steer rover primitives and front blade cutting actions.
"""
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
from .grid import OccupancyGrid
from ..detector.base import PlantDetection, PlantStatus


@dataclass
class RoverCommand:
    step: int
    cmd_type: str  # FORWARD, TURN_LEFT, TURN_RIGHT, BACKWARD, BLADE_DOWN, BLADE_ON, BLADE_OFF, BLADE_UP, STOP
    value: float   # distance in cm or angle in degrees (90)
    unit: str      # "cm" or "deg" or ""
    target_weed_id: Optional[int] = None
    action_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "cmd_type": self.cmd_type,
            "value": round(self.value, 1),
            "unit": self.unit,
            "target_weed_id": self.target_weed_id,
            "action_text": self.action_text,
        }

    def to_serial_code(self) -> str:
        """Converts command to firmware line protocol (distances in mm)."""
        val_mm = int(round(self.value * 10))
        if self.cmd_type == "FORWARD":
            return f"F{val_mm}"
        elif self.cmd_type == "BACKWARD":
            return f"B{val_mm}"
        elif self.cmd_type == "TURN_LEFT":
            return f"TL{int(round(self.value))}"
        elif self.cmd_type == "TURN_RIGHT":
            return f"TR{int(round(self.value))}"
        elif self.cmd_type == "BLADE_DOWN":
            return "BD"
        elif self.cmd_type == "BLADE_UP":
            return "BU"
        elif self.cmd_type == "BLADE_ON":
            return "BON"
        elif self.cmd_type == "BLADE_OFF":
            return "BOFF"
        elif self.cmd_type == "STOP":
            return "STOP"
        return "NOP"


@dataclass
class PlanResult:
    commands: List[RoverCommand] = field(default_factory=list)
    waypoints: List[Dict[str, Any]] = field(default_factory=list)
    total_distance_cm: float = 0.0
    total_turns: int = 0
    estimated_time_s: float = 0.0
    handled_weeds: List[int] = field(default_factory=list)
    skipped_weeds: List[Dict[str, Any]] = field(default_factory=list)
    execution_mode: str = "open_loop"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commands": [c.to_dict() for c in self.commands],
            "waypoints": self.waypoints,
            "total_distance_cm": round(self.total_distance_cm, 1),
            "total_turns": self.total_turns,
            "estimated_time_s": round(self.estimated_time_s, 1),
            "handled_weeds": self.handled_weeds,
            "skipped_weeds": self.skipped_weeds,
            "total_weeds": len(self.handled_weeds) + len(self.skipped_weeds),
            "execution_mode": self.execution_mode,
        }

    def to_csv(self) -> str:
        lines = ["Step,Command,Value,Unit,Weed_ID,Description"]
        for c in self.commands:
            lines.append(
                f'{c.step},{c.cmd_type},{c.value},{c.unit},{c.target_weed_id or ""},"{c.action_text}"'
            )
        return "\n".join(lines)


class CommandGenerator:
    """Computes candidate stop poses for weeds, compresses steps, and builds rover sequences."""

    def __init__(
        self,
        grid: OccupancyGrid,
        blade_offset_forward_cm: float = 18.0,
        blade_pass_cm: float = 8.0,
        linear_speed_cm_s: float = 15.0,
        turn_time_s_per_90: float = 1.5,
    ):
        self.grid = grid
        self.blade_offset = blade_offset_forward_cm
        self.blade_pass = blade_pass_cm
        self.speed = linear_speed_cm_s
        self.turn_time = turn_time_s_per_90

    def compute_candidate_poses_for_weed(
        self, weed: PlantDetection
    ) -> List[Tuple[float, float, int]]:
        """
        Computes valid rover stopping poses (x, y, heading) such that:
        tool_point = robot_centre + blade_offset * heading_vector == weed_center,
        and both body footprint and blade cutting zone are collision-free.
        """
        if weed.center_cm is None:
            return []

        wx, wy = weed.center_cm
        candidates: List[Tuple[float, float, int]] = []

        # Candidate headings:
        # 0 (+Y, facing up): robot is below weed at y = wy - offset
        # 90 (+X, facing right): robot is to left of weed at x = wx - offset
        # 180 (-Y, facing down): robot is above weed at y = wy + offset
        # 270 (-X, left): robot is to right of weed at x = wx + offset
        heading_offsets = [
            (0, 0.0, -self.blade_offset),
            (90, -self.blade_offset, 0.0),
            (180, 0.0, self.blade_offset),
            (270, self.blade_offset, 0.0),
        ]

        for heading, dx, dy in heading_offsets:
            rx = round(wx + dx, 2)
            ry = round(wy + dy, 2)

            # Check 1: robot translation safe at stopping pose
            if not self.grid.is_translation_safe(rx, ry, heading):
                continue

            # Check 2: cutting blade zone does not intersect any crop
            if not self.grid.is_blade_zone_safe(rx, ry, heading):
                continue

            candidates.append((rx, ry, heading))

        return candidates

    def compress_path_into_commands(
        self,
        raw_path: List[Tuple[float, float, int, str]],
        target_weed_id: Optional[int] = None
    ) -> List[RoverCommand]:
        """
        Merges consecutive linear moves (FORWARD 2cm + FORWARD 2cm -> FORWARD 4cm).
        Outputs strictly skid-steer legal primitives.
        """
        if not raw_path or len(raw_path) < 2:
            return []

        merged: List[RoverCommand] = []
        step_counter = 1

        i = 1
        while i < len(raw_path):
            prev_x, prev_y, prev_h, _ = raw_path[i - 1]
            curr_x, curr_y, curr_h, action = raw_path[i]

            if action == "FORWARD":
                # Count consecutive forward steps
                fwd_dist = 0.0
                j = i
                while j < len(raw_path) and raw_path[j][3] == "FORWARD" and raw_path[j][2] == prev_h:
                    px, py, _, _ = raw_path[j - 1]
                    cx, cy, _, _ = raw_path[j]
                    fwd_dist += math.hypot(cx - px, cy - py)
                    j += 1

                merged.append(
                    RoverCommand(
                        step=step_counter,
                        cmd_type="FORWARD",
                        value=round(fwd_dist, 1),
                        unit="cm",
                        target_weed_id=target_weed_id if j >= len(raw_path) else None,
                        action_text=f"Move FORWARD {round(fwd_dist, 1)} cm"
                    )
                )
                step_counter += 1
                i = j

            elif action == "TURN_LEFT":
                merged.append(
                    RoverCommand(
                        step=step_counter,
                        cmd_type="TURN_LEFT",
                        value=90.0,
                        unit="deg",
                        action_text="TURN LEFT 90 deg (skid pivot)"
                    )
                )
                step_counter += 1
                i += 1

            elif action == "TURN_RIGHT":
                merged.append(
                    RoverCommand(
                        step=step_counter,
                        cmd_type="TURN_RIGHT",
                        value=90.0,
                        unit="deg",
                        action_text="TURN RIGHT 90 deg (skid pivot)"
                    )
                )
                step_counter += 1
                i += 1

            elif action == "BACKWARD":
                bwd_dist = math.hypot(curr_x - prev_x, curr_y - prev_y)
                merged.append(
                    RoverCommand(
                        step=step_counter,
                        cmd_type="BACKWARD",
                        value=round(bwd_dist, 1),
                        unit="cm",
                        action_text=f"Move BACKWARD {round(bwd_dist, 1)} cm"
                    )
                )
                step_counter += 1
                i += 1
            else:
                i += 1

        return merged

    def generate_cut_sequence(
        self, weed_id: int, starting_step: int
    ) -> List[RoverCommand]:
        """
        Generates standard cutting cycle:
        STOP -> BLADE_DOWN -> BLADE_ON -> FORWARD pass_cm -> BLADE_OFF -> BLADE_UP.
        """
        step = starting_step
        seq = [
            RoverCommand(
                step=step,
                cmd_type="STOP",
                value=0.0,
                unit="",
                target_weed_id=weed_id,
                action_text=f"STOP at Weed #{weed_id} (tool aligned)"
            ),
            RoverCommand(
                step=step + 1,
                cmd_type="BLADE_DOWN",
                value=0.0,
                unit="",
                target_weed_id=weed_id,
                action_text=f"Lower front dual blades (servo down)"
            ),
            RoverCommand(
                step=step + 2,
                cmd_type="BLADE_ON",
                value=0.0,
                unit="",
                target_weed_id=weed_id,
                action_text=f"Activate blade cutting motor"
            ),
            RoverCommand(
                step=step + 3,
                cmd_type="FORWARD",
                value=self.blade_pass,
                unit="cm",
                target_weed_id=weed_id,
                action_text=f"Advance FORWARD {self.blade_pass} cm cutting pass"
            ),
            RoverCommand(
                step=step + 4,
                cmd_type="BLADE_OFF",
                value=0.0,
                unit="",
                target_weed_id=weed_id,
                action_text=f"Deactivate blade cutting motor"
            ),
            RoverCommand(
                step=step + 5,
                cmd_type="BLADE_UP",
                value=0.0,
                unit="",
                target_weed_id=weed_id,
                action_text=f"Raise front dual blades (safe travel position)"
            ),
        ]
        return seq

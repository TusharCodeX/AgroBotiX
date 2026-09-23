"""
Simulated Motion Controller for testing, desktop demonstrations, and open-loop visualization.
"""
import math
import time
from typing import Tuple, Dict, Any, List
from .base import MotionController


class SimulatedController(MotionController):
    """Virtual rover motion controller tracking odometry, blade state, and command execution."""

    def __init__(
        self,
        speed_cm_s: float = 15.0,
        turn_time_s_per_90: float = 1.5,
        blade_enabled: bool = False,
        dry_run: bool = True,
    ):
        self.speed = speed_cm_s
        self.turn_time = turn_time_s_per_90
        self.blade_enabled = blade_enabled
        self.dry_run = dry_run

        self.x: float = 0.0
        self.y: float = 0.0
        self.heading: float = 0.0  # 0 deg = +Y

        self.blade_is_down: bool = False
        self.blade_is_on: bool = False
        self.is_stopped: bool = True
        self.is_estopped: bool = False

        self.execution_log: List[Dict[str, Any]] = []

    def forward(self, distance_cm: float) -> bool:
        if self.is_estopped:
            return False
        rad = math.radians(self.heading)
        self.x += distance_cm * math.sin(rad)
        self.y += distance_cm * math.cos(rad)
        self.is_stopped = False
        self._log(f"FORWARD {distance_cm:.1f} cm", {"x": self.x, "y": self.y, "h": self.heading})
        return True

    def backward(self, distance_cm: float) -> bool:
        if self.is_estopped:
            return False
        rad = math.radians(self.heading)
        self.x -= distance_cm * math.sin(rad)
        self.y -= distance_cm * math.cos(rad)
        self.is_stopped = False
        self._log(f"BACKWARD {distance_cm:.1f} cm", {"x": self.x, "y": self.y, "h": self.heading})
        return True

    def turn(self, deg: float) -> bool:
        if self.is_estopped:
            return False
        self.heading = (self.heading + deg) % 360.0
        self.is_stopped = False
        action = f"TURN_RIGHT {deg:.1f}°" if deg > 0 else f"TURN_LEFT {abs(deg):.1f}°"
        self._log(action, {"x": self.x, "y": self.y, "h": self.heading})
        return True

    def blade_down(self) -> bool:
        self.blade_is_down = True
        self._log("BLADE_DOWN", {"blade_down": True})
        return True

    def blade_up(self) -> bool:
        # Safety: turn off blade when lifting
        if self.blade_is_on:
            self.blade_off()
        self.blade_is_down = False
        self._log("BLADE_UP", {"blade_down": False})
        return True

    def blade_on(self) -> bool:
        if not self.blade_enabled and not self.dry_run:
            self._log("BLADE_ON_REJECTED", {"reason": "blade disabled in config"})
            return False
        self.blade_is_on = True
        self._log("BLADE_ON", {"blade_on": True, "dry_run": self.dry_run})
        return True

    def blade_off(self) -> bool:
        self.blade_is_on = False
        self._log("BLADE_OFF", {"blade_on": False})
        return True

    def stop(self) -> bool:
        self.is_stopped = True
        self._log("STOP", {})
        return True

    def estop(self) -> bool:
        self.is_estopped = True
        self.is_stopped = True
        self.blade_is_on = False
        self.blade_is_down = False
        self._log("ESTOP_TRIGGERED", {})
        return True

    def reset_estop(self) -> None:
        self.is_estopped = False
        self._log("ESTOP_RESET", {})

    def get_pose(self) -> Tuple[float, float, float]:
        return round(self.x, 2), round(self.y, 2), round(self.heading, 1)

    def get_status(self) -> Dict[str, Any]:
        return {
            "type": "simulated",
            "pose": {"x": round(self.x, 2), "y": round(self.y, 2), "heading": round(self.heading, 1)},
            "blade": {
                "is_down": self.blade_is_down,
                "is_on": self.blade_is_on,
                "enabled": self.blade_enabled,
                "dry_run": self.dry_run,
            },
            "is_stopped": self.is_stopped,
            "is_estopped": self.is_estopped,
            "log_count": len(self.execution_log),
        }

    def _log(self, action: str, details: Dict[str, Any]) -> None:
        self.execution_log.append({
            "timestamp": time.time(),
            "action": action,
            "details": details
        })

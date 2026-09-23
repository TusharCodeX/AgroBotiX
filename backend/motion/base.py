"""
Base interface for Rover Motion Controllers.
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any


class MotionController(ABC):
    """Abstract motion controller for skid-steer rover and dual cutting blades."""

    @abstractmethod
    def forward(self, distance_cm: float) -> bool:
        """Drives rover forward distance_cm."""
        pass

    @abstractmethod
    def backward(self, distance_cm: float) -> bool:
        """Drives rover backward distance_cm."""
        pass

    @abstractmethod
    def turn(self, deg: float) -> bool:
        """Pivots rover in place: deg > 0 right, deg < 0 left."""
        pass

    @abstractmethod
    def blade_down(self) -> bool:
        """Lowers front cutting blades into working position."""
        pass

    @abstractmethod
    def blade_up(self) -> bool:
        """Lifts front cutting blades to safe travel position."""
        pass

    @abstractmethod
    def blade_on(self) -> bool:
        """Activates cutting blade motor."""
        pass

    @abstractmethod
    def blade_off(self) -> bool:
        """Stops cutting blade motor."""
        pass

    @abstractmethod
    def stop(self) -> bool:
        """Normal smooth deceleration stop."""
        pass

    @abstractmethod
    def estop(self) -> bool:
        """Emergency immediate stop for motors and blades."""
        pass

    @abstractmethod
    def get_pose(self) -> Tuple[float, float, float]:
        """Returns current estimated (x_cm, y_cm, heading_deg)."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Returns controller operational telemetry."""
        pass

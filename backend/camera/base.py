"""
Base interface for camera capture sources.
"""
from abc import ABC, abstractmethod
import numpy as np


class CameraSource(ABC):
    """Abstract Camera Source interface."""

    @abstractmethod
    def capture_frame(self) -> np.ndarray:
        """
        Captures a single frame as a BGR numpy array.
        Raises RuntimeError if the frame cannot be captured.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the camera source is connected and operational."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Releases camera hardware / connection resources."""
        pass

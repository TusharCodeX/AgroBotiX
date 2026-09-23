"""
PiCameraSource: Hardware camera interface for Raspberry Pi 4/5 (Picamera2 / V4L2 / OpenCV).
"""
import cv2
import numpy as np
from typing import Optional
from .base import CameraSource


class PiCameraSource(CameraSource):
    """
    Direct hardware camera source for Raspberry Pi.
    Uses Picamera2 if available, with OpenCV VideoCapture fallback.
    """

    def __init__(self, device_id: int = 0, width: int = 1280, height: int = 720):
        self.device_id = device_id
        self.width = width
        self.height = height
        self._picam2 = None
        self._cv_cap: Optional[cv2.VideoCapture] = None
        self._init_camera()

    def _init_camera(self) -> None:
        # Try Picamera2 first (standard on Pi Bullseye / Bookworm)
        try:
            from picam2 import Picamera2  # type: ignore
            picam = Picamera2()
            config = picam.create_preview_configuration(
                main={"format": "RGB888", "size": (self.width, self.height)}
            )
            picam.configure(config)
            picam.start()
            self._picam2 = picam
            return
        except (ImportError, Exception):
            self._picam2 = None

        # Fallback to cv2.VideoCapture (e.g. USB cam or simulated v4l2loopback)
        try:
            cap = cv2.VideoCapture(self.device_id)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self._cv_cap = cap
        except Exception:
            self._cv_cap = None

    def capture_frame(self) -> np.ndarray:
        if self._picam2 is not None:
            rgb_frame = self._picam2.capture_array()
            return cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)

        if self._cv_cap is not None and self._cv_cap.isOpened():
            ret, frame = self._cv_cap.read()
            if ret and frame is not None:
                return frame
            raise RuntimeError(f"Failed to grab frame from VideoCapture device {self.device_id}.")

        raise RuntimeError(
            "PiCamera hardware is not available. Please verify Picamera2 or USB camera connection."
        )

    def is_available(self) -> bool:
        if self._picam2 is not None:
            return True
        if self._cv_cap is not None and self._cv_cap.isOpened():
            return True
        return False

    def release(self) -> None:
        if self._picam2 is not None:
            try:
                self._picam2.stop()
                self._picam2.close()
            except Exception:
                pass
            self._picam2 = None

        if self._cv_cap is not None:
            self._cv_cap.release()
            self._cv_cap = None

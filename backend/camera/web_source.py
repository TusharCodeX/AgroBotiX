"""
WebUploadSource: handles uploaded images, camera frames received from browser,
EXIF orientation correction, file validation, and resolution guarantees.
"""
import io
import cv2
import numpy as np
from PIL import Image, ImageOps
from typing import Tuple, Optional
from .base import CameraSource


class WebUploadSource(CameraSource):
    """Camera source fed by Web/Client uploads and browser webcam captures."""

    def __init__(self, initial_image: Optional[np.ndarray] = None):
        self._current_frame = initial_image

    def set_frame(self, frame: np.ndarray) -> None:
        """Sets the current frame."""
        self._current_frame = frame

    def capture_frame(self) -> np.ndarray:
        if self._current_frame is None:
            raise RuntimeError("No image frame has been uploaded or received yet.")
        return self._current_frame.copy()

    def is_available(self) -> bool:
        return self._current_frame is not None

    def release(self) -> None:
        self._current_frame = None

    @staticmethod
    def load_from_bytes(image_bytes: bytes) -> np.ndarray:
        """
        Validates, corrects EXIF orientation, and decodes image bytes into a BGR numpy array.
        Enforces resolution integrity (never shrinks long side below 640px).
        """
        if not image_bytes or len(image_bytes) < 10:
            raise ValueError("Corrupt or empty image data received.")

        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            pil_img.verify()
            # Reopen after verify()
            pil_img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted image file: {str(e)}")

        # Transpose according to EXIF orientation
        try:
            pil_img = ImageOps.exif_transpose(pil_img)
        except Exception:
            pass

        # Convert to RGB then BGR numpy array
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")

        rgb_arr = np.array(pil_img)
        bgr_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2BGR)

        h, w = bgr_arr.shape[:2]
        long_side = max(h, w)
        if long_side < 640:
            # Upscale proportionally so long side is at least 640 px
            scale = 640.0 / long_side
            new_w = int(round(w * scale))
            new_h = int(round(h * scale))
            bgr_arr = cv2.resize(bgr_arr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        return bgr_arr

    @staticmethod
    def letterbox(
        image: np.ndarray,
        target_size: int = 640,
        color: Tuple[int, int, int] = (114, 114, 114)
    ) -> Tuple[np.ndarray, float, Tuple[float, float]]:
        """
        Pads and resizes image to target square maintaining aspect ratio.
        Returns: (padded_image, scale_ratio, (pad_left, pad_top))
        """
        h, w = image.shape[:2]
        ratio = min(target_size / h, target_size / w)
        new_unpad_w, new_unpad_h = int(round(w * ratio)), int(round(h * ratio))

        dw = (target_size - new_unpad_w) / 2
        dh = (target_size - new_unpad_h) / 2

        if (w, h) != (new_unpad_w, new_unpad_h):
            resized = cv2.resize(image, (new_unpad_w, new_unpad_h), interpolation=cv2.INTER_LINEAR)
        else:
            resized = image

        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))

        padded = cv2.copyMakeBorder(
            resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
        )
        return padded, ratio, (dw, dh)

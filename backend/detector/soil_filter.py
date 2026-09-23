"""
Secondary Soil, Stone, Residue, and Shadow Rejection Filter.
Implements spectral vegetative indices (ExG, VARI) and texture analysis
to validate that candidate detections are genuine living plants rather than:
- dry soil, cracked clay, mud clods
- field stones and gravel
- crop residue, dry stubble, straw mulch
- deep shadows and high-contrast cracks
"""
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any


class IndianSoilVegetationValidator:
    """
    Secondary validator for candidate plant detections in Indian field conditions.
    Uses trained neural network as primary classifier; applies spectral indices
    and texture analysis as secondary barrier against soil false positives.
    """

    def __init__(
        self,
        min_exg_threshold: float = -5.0,     # ExG = 2G - R - B
        min_vari_threshold: float = -0.15,   # VARI = (G - R) / (G + R - B)
        min_green_pixel_ratio: float = 0.08, # At least 8% of pixels must exhibit leaf characteristics
        shadow_intensity_max: float = 45.0,  # Below this V-channel is considered pure shadow
    ):
        self.min_exg_threshold = min_exg_threshold
        self.min_vari_threshold = min_vari_threshold
        self.min_green_pixel_ratio = min_green_pixel_ratio
        self.shadow_intensity_max = shadow_intensity_max

    def validate_roi(
        self,
        image_bgr: np.ndarray,
        bbox_px: Tuple[float, float, float, float],
    ) -> Tuple[bool, float, Optional[str]]:
        """
        Validates whether the bounding box region contains genuine vegetative tissue.
        Returns:
            (is_vegetation, vegetation_score, rejection_reason)
        """
        h_img, w_img = image_bgr.shape[:2]
        x1 = max(0, int(bbox_px[0]))
        y1 = max(0, int(bbox_px[1]))
        x2 = min(w_img, int(bbox_px[2]))
        y2 = min(h_img, int(bbox_px[3]))

        if (x2 - x1) < 4 or (y2 - y1) < 4:
            return False, 0.0, "Rejected: Bounding box area too small (< 16 px)"

        roi_bgr = image_bgr[y1:y2, x1:x2]
        if roi_bgr.size == 0:
            return False, 0.0, "Rejected: Empty ROI slice"

        b = roi_bgr[:, :, 0].astype(np.float32)
        g = roi_bgr[:, :, 1].astype(np.float32)
        r = roi_bgr[:, :, 2].astype(np.float32)

        # 1. Excess Green Index: ExG = 2G - R - B
        exg_map = 2.0 * g - r - b
        mean_exg = float(np.mean(exg_map))

        # 2. Visible Atmospherically Resistant Index: VARI = (G - R) / (G + R - B + 1e-5)
        denom = g + r - b
        denom[np.abs(denom) < 1e-4] = 1e-4
        vari_map = (g - r) / denom
        mean_vari = float(np.mean(vari_map))

        # 3. HSV Leaf Pigment & Shadow Analysis
        roi_hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        h_chan = roi_hsv[:, :, 0]
        s_chan = roi_hsv[:, :, 1]
        v_chan = roi_hsv[:, :, 2]

        # Shadow test: if ROI is predominantly deep black shadow (V < 45, S < 40)
        shadow_pixels = np.count_nonzero((v_chan < self.shadow_intensity_max) & (s_chan < 60))
        total_pixels = float(roi_bgr.shape[0] * roi_bgr.shape[1])
        shadow_ratio = shadow_pixels / total_pixels
        if shadow_ratio > 0.85:
            return False, 0.05, f"Rejected: Shadow artifact ({shadow_ratio*100:.0f}% deep shadow)"

        # Vegetative Green Pixels: Hue in 25..95 (OpenCV 18..48), Saturation >= 30, ExG > 0
        green_mask = (h_chan >= 20) & (h_chan <= 85) & (s_chan >= 30) & (exg_map > 0)
        green_ratio = float(np.count_nonzero(green_mask)) / total_pixels

        # 4. Dry Soil / Cracked Earth / Stone check:
        # Bare cracked earth has high red/yellow tones, ExG < -10, or zero green pixel concentration
        if green_ratio < self.min_green_pixel_ratio and mean_exg < self.min_exg_threshold:
            # Check if this is dry cracked soil with high edge contrast
            gray_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray_roi, cv2.CV_64F).var()

            if laplacian_var > 150:
                reason = "Rejected: Cracked soil / high-contrast dry clod texture"
            elif np.mean(v_chan) < 60:
                reason = "Rejected: Deep soil shadow / depression"
            else:
                reason = "Rejected: Bare dry soil / stone without active chlorophyll"
            return False, round(green_ratio, 3), reason

        # Crop residue / dry straw check: yellow/brown dried stems with very negative VARI
        if mean_vari < -0.35 and green_ratio < 0.05:
            return False, round(green_ratio, 3), "Rejected: Crop residue / dry straw stubble"

        # Calculate combined vegetation confidence score (0.0 to 1.0)
        # Scaled by green ratio, normalized ExG, and positive VARI
        norm_exg = np.clip((mean_exg + 20.0) / 60.0, 0.0, 1.0)
        norm_vari = np.clip((mean_vari + 0.2) / 0.6, 0.0, 1.0)
        veg_score = float(0.4 * green_ratio + 0.3 * norm_exg + 0.3 * norm_vari)
        veg_score = max(0.1, min(1.0, veg_score))

        return True, round(veg_score, 3), None

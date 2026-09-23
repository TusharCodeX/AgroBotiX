"""
Calibrator: Maps image pixel coordinates to real-world centimetres in the ROBOT FRAME.
Robot Frame: Origin (0,0) at robot center, +Y forward, +X right.
"""
import cv2
import numpy as np
from typing import Tuple, List, Optional, Dict, Any


class RobotCalibrator:
    """Handles manual, 2-point, and ArUco homography calibration for AgriPath."""

    def __init__(
        self,
        cm_per_pixel: float = 0.15,
        robot_length_cm: float = 30.0,
        ground_y_offset_cm: float = 10.0,
        camera_mount: str = "robot_front_down",
        status: str = "uncalibrated",
        homography_matrix: Optional[List[List[float]]] = None,
    ):
        self.cm_per_pixel = cm_per_pixel
        self.robot_length_cm = robot_length_cm
        self.ground_y_offset_cm = ground_y_offset_cm
        self.camera_mount = camera_mount
        self.status = status
        self.homography_matrix = (
            np.array(homography_matrix, dtype=np.float64) if homography_matrix else None
        )

    def is_calibrated(self) -> bool:
        return self.status == "calibrated"

    def calibrate_two_points(
        self, pt1: Tuple[float, float], pt2: Tuple[float, float], real_distance_cm: float
    ) -> float:
        """Calibrates scale from two clicked pixel points and their true distance."""
        px_dist = float(np.hypot(pt2[0] - pt1[0], pt2[1] - pt1[1]))
        if px_dist < 1e-4:
            raise ValueError("Clicked points are too close together.")
        self.cm_per_pixel = real_distance_cm / px_dist
        self.status = "calibrated"
        self.homography_matrix = None
        return self.cm_per_pixel

    def calibrate_manual(self, cm_per_pixel: float) -> None:
        if cm_per_pixel <= 0:
            raise ValueError("Scale factor cm_per_pixel must be positive.")
        self.cm_per_pixel = cm_per_pixel
        self.status = "calibrated"
        self.homography_matrix = None

    def calibrate_aruco(
        self,
        image: np.ndarray,
        marker_size_cm: float = 5.0,
        known_marker_coords_cm: Optional[Dict[int, Tuple[float, float]]] = None,
    ) -> bool:
        """
        Detects ArUco markers on the ground plane and calculates scale or full homography.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        parameters = cv2.aruco.DetectorParameters()
        detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        corners, ids, _ = detector.detectMarkers(gray)

        if ids is None or len(ids) == 0:
            return False

        # If 4 or more known markers provided, solve homography
        if known_marker_coords_cm and len(ids) >= 4:
            img_pts = []
            obj_pts = []
            for i, mid in enumerate(ids.flatten()):
                if int(mid) in known_marker_coords_cm:
                    c = corners[i][0]
                    # Center of marker
                    mcx = float(np.mean(c[:, 0]))
                    mcy = float(np.mean(c[:, 1]))
                    img_pts.append([mcx, mcy])
                    obj_pts.append(known_marker_coords_cm[int(mid)])

            if len(img_pts) >= 4:
                H, _ = cv2.findHomography(
                    np.array(img_pts, dtype=np.float32), np.array(obj_pts, dtype=np.float32)
                )
                if H is not None:
                    self.homography_matrix = H
                    self.status = "calibrated"
                    return True

        # Fallback to single/multi marker perimeter scale calculation
        scales = []
        for c in corners:
            pts = c[0]
            # Average of 4 edges
            edge_lens = [
                np.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]),
                np.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1]),
                np.hypot(pts[3][0] - pts[2][0], pts[3][1] - pts[2][1]),
                np.hypot(pts[0][0] - pts[3][0], pts[0][1] - pts[3][1]),
            ]
            avg_edge_px = np.mean(edge_lens)
            if avg_edge_px > 5:
                scales.append(marker_size_cm / avg_edge_px)

        if scales:
            self.cm_per_pixel = float(np.mean(scales))
            self.status = "calibrated"
            return True

        return False

    def pixel_to_robot_cm(
        self, px: float, py: float, image_shape: Tuple[int, int]
    ) -> Tuple[float, float]:
        """
        Converts pixel (px, py) to robot frame (x_cm, y_cm).
        Origin = robot centre (0,0), +Y = forward, +X = right.
        """
        if self.homography_matrix is not None:
            pt = np.array([[[px, py]]], dtype=np.float64)
            trans = cv2.perspectiveTransform(pt, self.homography_matrix)
            return float(trans[0][0][0]), float(trans[0][0][1])

        h, w = image_shape[:2]
        # X: center of image is X=0 (robot centerline)
        x_cm = (px - w / 2.0) * self.cm_per_pixel

        # Y: bottom of image (py=h) is closest to rover front edge
        # Distance from robot center to front edge = robot_length_cm / 2
        front_edge_y = self.robot_length_cm / 2.0 + self.ground_y_offset_cm
        dist_from_bottom_px = max(0.0, float(h - py))
        y_cm = front_edge_y + dist_from_bottom_px * self.cm_per_pixel

        return round(x_cm, 2), round(y_cm, 2)

    def robot_cm_to_pixel(
        self, x_cm: float, y_cm: float, image_shape: Tuple[int, int]
    ) -> Tuple[float, float]:
        """
        Inverse projection from robot coordinates (x_cm, y_cm) to pixel coordinates.
        """
        if self.homography_matrix is not None:
            H_inv = np.linalg.inv(self.homography_matrix)
            pt = np.array([[[x_cm, y_cm]]], dtype=np.float64)
            trans = cv2.perspectiveTransform(pt, H_inv)
            return float(trans[0][0][0]), float(trans[0][0][1])

        h, w = image_shape[:2]
        px = (x_cm / self.cm_per_pixel) + w / 2.0

        front_edge_y = self.robot_length_cm / 2.0 + self.ground_y_offset_cm
        dist_from_bottom_px = (y_cm - front_edge_y) / self.cm_per_pixel
        py = h - dist_from_bottom_px

        return px, py

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "mode": "homography" if self.homography_matrix is not None else "scale",
            "cm_per_pixel": round(self.cm_per_pixel, 4),
            "camera_mount": self.camera_mount,
            "ground_y_offset_cm": self.ground_y_offset_cm,
            "has_homography": self.homography_matrix is not None,
        }

"""
Occupancy Grid and Kinematic Collision Checker for 6-Wheel Skid-Steer Rover with Front Blades.
Coordinates: Robot frame (cm), Origin (0,0), +Y forward, +X right.
"""
import math
import numpy as np
from typing import Tuple, List, Dict, Optional, Set
from ..detector.base import PlantDetection, PlantStatus


class OccupancyGrid:
    """
    2D Occupancy Grid in real-world centimetres.
    Manages obstacle inflation, robot footprint collision checks,
    turn-circle safety radius, and blade cutting zone validation.
    """

    def __init__(
        self,
        grid_cell_size_cm: float = 2.0,
        x_min_cm: float = -60.0,
        x_max_cm: float = 60.0,
        y_min_cm: float = -30.0,
        y_max_cm: float = 140.0,
        robot_length_cm: float = 30.0,
        robot_width_cm: float = 25.0,
        safety_margin_cm: float = 4.0,
        blade_offset_forward_cm: float = 18.0,
        blade_total_width_cm: float = 16.0,
        blade_pass_cm: float = 8.0,
    ):
        self.cell_size = grid_cell_size_cm
        self.x_min = x_min_cm
        self.x_max = x_max_cm
        self.y_min = y_min_cm
        self.y_max = y_max_cm

        self.robot_length = robot_length_cm
        self.robot_width = robot_width_cm
        self.safety_margin = safety_margin_cm

        self.blade_offset = blade_offset_forward_cm
        self.blade_width = blade_total_width_cm
        self.blade_pass = blade_pass_cm

        # Circumscribed radius during in-place rotation
        front_reach = max(self.robot_length / 2.0, self.blade_offset + self.blade_pass / 2.0)
        half_w = max(self.robot_width / 2.0, self.blade_width / 2.0)
        self.turn_radius = math.hypot(front_reach, half_w)

        self.cols = int(math.ceil((self.x_max - self.x_min) / self.cell_size))
        self.rows = int(math.ceil((self.y_max - self.y_min) / self.cell_size))

        # 0 = free, 1 = obstacle (crop / uncertain)
        self.grid = np.zeros((self.rows, self.cols), dtype=np.uint8)
        self.obstacle_polys: List[Tuple[float, float, float, float]] = []

        # High performance collision lookup caches (cleared on obstacle update)
        self._translation_cache: Dict[Tuple[int, int, int], bool] = {}
        self._turn_cache: Dict[Tuple[int, int], bool] = {}

    def world_to_grid(self, x_cm: float, y_cm: float) -> Tuple[int, int]:
        """Maps (x_cm, y_cm) to grid (row, col)."""
        col = int((x_cm - self.x_min) / self.cell_size)
        row = int((y_cm - self.y_min) / self.cell_size)
        return row, col

    def grid_to_world(self, row: int, col: int) -> Tuple[float, float]:
        """Maps grid (row, col) to (x_cm, y_cm) center."""
        x_cm = self.x_min + (col + 0.5) * self.cell_size
        y_cm = self.y_min + (row + 0.5) * self.cell_size
        return round(x_cm, 2), round(y_cm, 2)

    def is_in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_world_in_bounds(self, x_cm: float, y_cm: float) -> bool:
        return self.x_min <= x_cm <= self.x_max and self.y_min <= y_cm <= self.y_max

    def populate_obstacles(self, detections: List[PlantDetection]) -> None:
        """
        Rasters crops and uncertain plants as obstacles with safety margin inflation.
        """
        self.grid.fill(0)
        self.obstacle_polys.clear()
        self._translation_cache.clear()
        self._turn_cache.clear()

        for det in detections:
            if not det.is_obstacle or det.center_cm is None:
                continue

            cx, cy = det.center_cm
            if det.bbox_cm:
                bx1, by1, bx2, by2 = det.bbox_cm
            else:
                # Default 10x10 cm plant box if bbox_cm not provided
                bx1, by1, bx2, by2 = cx - 5.0, cy - 5.0, cx + 5.0, cy + 5.0

            # Inflate obstacle by safety_margin_cm
            inf_x1 = bx1 - self.safety_margin
            inf_y1 = by1 - self.safety_margin
            inf_x2 = bx2 + self.safety_margin
            inf_y2 = by2 + self.safety_margin

            self.obstacle_polys.append((inf_x1, inf_y1, inf_x2, inf_y2))

            # Mark cells in grid
            r1, c1 = self.world_to_grid(inf_x1, inf_y1)
            r2, c2 = self.world_to_grid(inf_x2, inf_y2)

            r_start = max(0, min(r1, r2))
            r_end = min(self.rows - 1, max(r1, r2))
            c_start = max(0, min(c1, c2))
            c_end = min(self.cols - 1, max(c1, c2))

            self.grid[r_start : r_end + 1, c_start : c_end + 1] = 1

    def is_point_occupied(self, x_cm: float, y_cm: float) -> bool:
        """Returns True if (x_cm, y_cm) intersects an obstacle."""
        r, c = self.world_to_grid(x_cm, y_cm)
        if not self.is_in_bounds(r, c):
            return False
        return self.grid[r, c] == 1

    def is_translation_safe(self, x_cm: float, y_cm: float, heading_deg: int) -> bool:
        """
        Checks whether placing the rover at (x_cm, y_cm) with heading_deg collides with crops.
        Evaluates body footprint rectangle + blades with memoization cache.
        """
        if not self.is_world_in_bounds(x_cm, y_cm):
            return False

        if not self.obstacle_polys:
            return True

        r_idx, c_idx = self.world_to_grid(x_cm, y_cm)
        cache_key = (r_idx, c_idx, heading_deg % 360)
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]

        corners = self.get_rover_footprint(x_cm, y_cm, heading_deg)
        min_x = min(pt[0] for pt in corners)
        max_x = max(pt[0] for pt in corners)
        min_y = min(pt[1] for pt in corners)
        max_y = max(pt[1] for pt in corners)

        r1, c1 = self.world_to_grid(min_x, min_y)
        r2, c2 = self.world_to_grid(max_x, max_y)

        r_start = max(0, min(r1, r2))
        r_end = min(self.rows - 1, max(r1, r2))
        c_start = max(0, min(c1, c2))
        c_end = min(self.cols - 1, max(c1, c2))

        safe = True
        if r_start <= r_end and c_start <= c_end:
            sub_grid = self.grid[r_start : r_end + 1, c_start : c_end + 1]
            if np.any(sub_grid == 1):
                samples = self._sample_footprint_points(x_cm, y_cm, heading_deg)
                for sx, sy in samples:
                    if self.is_point_occupied(sx, sy):
                        safe = False
                        break

        self._translation_cache[cache_key] = safe
        return safe

    def is_turn_safe(self, x_cm: float, y_cm: float) -> bool:
        """
        Checks whether an in-place pivot at (x_cm, y_cm) is safe.
        Uses circumscribed circle radius around center: R = turn_radius with memoization.
        """
        if not self.is_world_in_bounds(x_cm, y_cm):
            return False

        if not self.obstacle_polys:
            return True

        r_idx, c_idx = self.world_to_grid(x_cm, y_cm)
        cache_key = (r_idx, c_idx)
        if cache_key in self._turn_cache:
            return self._turn_cache[cache_key]

        r = self.turn_radius
        r1, c1 = self.world_to_grid(x_cm - r, y_cm - r)
        r2, c2 = self.world_to_grid(x_cm + r, y_cm + r)

        r_start = max(0, min(r1, r2))
        r_end = min(self.rows - 1, max(r1, r2))
        c_start = max(0, min(c1, c2))
        c_end = min(self.cols - 1, max(c1, c2))

        safe = True
        for row in range(r_start, r_end + 1):
            for col in range(c_start, c_end + 1):
                if self.grid[row, col] == 1:
                    cell_x, cell_y = self.grid_to_world(row, col)
                    if math.hypot(cell_x - x_cm, cell_y - y_cm) <= r:
                        safe = False
                        break
            if not safe:
                break

        self._turn_cache[cache_key] = safe
        return safe

    def is_blade_zone_safe(self, x_cm: float, y_cm: float, heading_deg: int) -> bool:
        """
        Checks whether the cutting blade zone in front of the robot overlaps any crop obstacle.
        """
        if not self.obstacle_polys:
            return True

        blade_corners = self.get_blade_zone(x_cm, y_cm, heading_deg)
        min_x = min(pt[0] for pt in blade_corners)
        max_x = max(pt[0] for pt in blade_corners)
        min_y = min(pt[1] for pt in blade_corners)
        max_y = max(pt[1] for pt in blade_corners)

        r1, c1 = self.world_to_grid(min_x, min_y)
        r2, c2 = self.world_to_grid(max_x, max_y)

        r_start = max(0, min(r1, r2))
        r_end = min(self.rows - 1, max(r1, r2))
        c_start = max(0, min(c1, c2))
        c_end = min(self.cols - 1, max(c1, c2))

        for row in range(r_start, r_end + 1):
            for col in range(c_start, c_end + 1):
                if self.grid[row, col] == 1:
                    cell_x, cell_y = self.grid_to_world(row, col)
                    if self._is_point_in_polygon((cell_x, cell_y), blade_corners):
                        return False

        return True

    def get_rover_footprint(
        self, x_cm: float, y_cm: float, heading_deg: int
    ) -> List[Tuple[float, float]]:
        """Returns 4 corners of the rover chassis rectangle at (x_cm, y_cm, heading_deg)."""
        rad = math.radians(heading_deg)
        cos_t = math.cos(rad)
        sin_t = math.sin(rad)

        hl = self.robot_length / 2.0
        hw = self.robot_width / 2.0

        # Local corners: (+hw, +hl), (-hw, +hl), (-hw, -hl), (+hw, -hl)
        local_pts = [(hw, hl), (-hw, hl), (-hw, -hl), (+hw, -hl)]
        world_pts = []
        for lx, ly in local_pts:
            wx = x_cm + lx * cos_t + ly * sin_t
            wy = y_cm - lx * sin_t + ly * cos_t
            world_pts.append((round(wx, 2), round(wy, 2)))

        return world_pts

    def get_blade_zone(
        self, x_cm: float, y_cm: float, heading_deg: int
    ) -> List[Tuple[float, float]]:
        """Returns 4 corners of front cutting blade zone."""
        rad = math.radians(heading_deg)
        cos_t = math.cos(rad)
        sin_t = math.sin(rad)

        hw = self.blade_width / 2.0
        front_edge = self.robot_length / 2.0
        cutting_reach = self.blade_offset + self.blade_pass

        local_pts = [
            (hw, front_edge),
            (-hw, front_edge),
            (-hw, cutting_reach),
            (hw, cutting_reach),
        ]
        world_pts = []
        for lx, ly in local_pts:
            wx = x_cm + lx * cos_t + ly * sin_t
            wy = y_cm - lx * sin_t + ly * cos_t
            world_pts.append((round(wx, 2), round(wy, 2)))

        return world_pts

    def _sample_footprint_points(
        self, x_cm: float, y_cm: float, heading_deg: int
    ) -> List[Tuple[float, float]]:
        """Dense sampling across robot body for collision testing."""
        rad = math.radians(heading_deg)
        cos_t = math.cos(rad)
        sin_t = math.sin(rad)

        hl = self.robot_length / 2.0
        hw = self.robot_width / 2.0

        pts = []
        for ly in np.linspace(-hl, hl, num=int(self.robot_length / 4) + 1):
            for lx in np.linspace(-hw, hw, num=int(self.robot_width / 4) + 1):
                wx = x_cm + lx * cos_t + ly * sin_t
                wy = y_cm - lx * sin_t + ly * cos_t
                pts.append((wx, wy))
        return pts

    @staticmethod
    def _is_point_in_polygon(
        pt: Tuple[float, float], poly: List[Tuple[float, float]]
    ) -> bool:
        """Ray-casting algorithm for point in polygon test."""
        x, y = pt
        inside = False
        n = len(poly)
        p1x, p1y = poly[0]
        for i in range(n + 1):
            p2x, p2y = poly[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

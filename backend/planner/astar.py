"""
4-Heading State-Space A* Planner for 6-Wheel Skid-Steer Rover.
State: (row, col, heading_idx), where heading in [0 (+Y), 90 (+X), 180 (-Y), 270 (-X)].
Legal Primitives: FORWARD 1 cell, TURN_LEFT 90, TURN_RIGHT 90, (optional BACKWARD).
"""
import heapq
import math
from typing import Tuple, List, Optional, Dict, Set
from .grid import OccupancyGrid


# Direction deltas for row (Y) and col (X) on grid
# heading 0 (+Y, up): d_row = +1, d_col = 0
# heading 90 (+X, right): d_row = 0, d_col = +1
# heading 180 (-Y, down): d_row = -1, d_col = 0
# heading 270 (-X, left): d_row = 0, d_col = -1
HEADINGS = [0, 90, 180, 270]
HEADING_DELTAS = {
    0: (1, 0),     # +Y
    90: (0, 1),    # +X
    180: (-1, 0),  # -Y
    270: (0, -1),  # -X
}


class StateNode:
    __slots__ = ("r", "c", "h_idx", "cost", "priority", "parent", "action")

    def __init__(
        self,
        r: int,
        c: int,
        h_idx: int,
        cost: float,
        priority: float,
        parent: Optional["StateNode"] = None,
        action: str = ""
    ):
        self.r = r
        self.c = c
        self.h_idx = h_idx
        self.cost = cost
        self.priority = priority
        self.parent = parent
        self.action = action

    def __lt__(self, other: "StateNode") -> bool:
        return self.priority < other.priority

    @property
    def key(self) -> Tuple[int, int, int]:
        return (self.r, self.c, self.h_idx)


class SkidSteerAStar:
    """A* planner enforcing non-holonomic skid-steer primitives and turn slip penalties."""

    def __init__(
        self,
        grid: OccupancyGrid,
        turn_penalty_cm: float = 35.0,
        allow_backward: bool = False,
    ):
        self.grid = grid
        self.turn_penalty = turn_penalty_cm
        self.allow_backward = allow_backward

    def plan(
        self,
        start_pose: Tuple[float, float, int],
        goal_pose: Tuple[float, float, int],
        require_final_heading: bool = True
    ) -> Optional[List[Tuple[float, float, int, str]]]:
        """
        Plans path from start_pose (x, y, heading_deg) to goal_pose (x, y, heading_deg).
        Returns list of (x_cm, y_cm, heading_deg, action_taken).
        """
        sx, sy, sh = start_pose
        gx, gy, gh = goal_pose

        sr, sc = self.grid.world_to_grid(sx, sy)
        gr, gc = self.grid.world_to_grid(gx, gy)

        sh_idx = HEADINGS.index(sh % 360)
        gh_idx = HEADINGS.index(gh % 360)

        # Check start and goal feasibility
        if not self.grid.is_translation_safe(sx, sy, sh):
            return None
        if not self.grid.is_translation_safe(gx, gy, gh):
            return None

        start_node = StateNode(
            r=sr,
            c=sc,
            h_idx=sh_idx,
            cost=0.0,
            priority=self._heuristic(sr, sc, sh_idx, gr, gc, gh_idx),
            parent=None,
            action="START"
        )

        open_set: List[StateNode] = []
        heapq.heappush(open_set, start_node)
        best_cost: Dict[Tuple[int, int, int], float] = {start_node.key: 0.0}

        goal_node: Optional[StateNode] = None
        max_iterations = 4000
        iterations = 0

        while open_set and iterations < max_iterations:
            iterations += 1
            current = heapq.heappop(open_set)

            # Check if reached goal
            if current.r == gr and current.c == gc:
                if not require_final_heading or current.h_idx == gh_idx:
                    goal_node = current
                    break

            if current.cost > best_cost.get(current.key, float("inf")):
                continue

            curr_h_deg = HEADINGS[current.h_idx]
            curr_x, curr_y = self.grid.grid_to_world(current.r, current.c)

            # --- Neighbor 1: FORWARD 1 cell ---
            dr, dc = HEADING_DELTAS[curr_h_deg]
            nr, nc = current.r + dr, current.c + dc
            if self.grid.is_in_bounds(nr, nc):
                nx, ny = self.grid.grid_to_world(nr, nc)
                if self.grid.is_translation_safe(nx, ny, curr_h_deg):
                    move_cost = self.grid.cell_size
                    new_cost = current.cost + move_cost
                    n_key = (nr, nc, current.h_idx)
                    if new_cost < best_cost.get(n_key, float("inf")):
                        best_cost[n_key] = new_cost
                        h_val = self._heuristic(nr, nc, current.h_idx, gr, gc, gh_idx)
                        heapq.heappush(
                            open_set,
                            StateNode(nr, nc, current.h_idx, new_cost, new_cost + h_val, current, "FORWARD")
                        )

            # --- Neighbor 2: TURN_LEFT 90 deg ---
            if self.grid.is_turn_safe(curr_x, curr_y):
                left_h_idx = (current.h_idx - 1) % 4
                turn_cost = self.turn_penalty
                new_cost = current.cost + turn_cost
                l_key = (current.r, current.c, left_h_idx)
                if new_cost < best_cost.get(l_key, float("inf")):
                    best_cost[l_key] = new_cost
                    h_val = self._heuristic(current.r, current.c, left_h_idx, gr, gc, gh_idx)
                    heapq.heappush(
                        open_set,
                        StateNode(current.r, current.c, left_h_idx, new_cost, new_cost + h_val, current, "TURN_LEFT")
                    )

            # --- Neighbor 3: TURN_RIGHT 90 deg ---
            if self.grid.is_turn_safe(curr_x, curr_y):
                right_h_idx = (current.h_idx + 1) % 4
                turn_cost = self.turn_penalty
                new_cost = current.cost + turn_cost
                r_key = (current.r, current.c, right_h_idx)
                if new_cost < best_cost.get(r_key, float("inf")):
                    best_cost[r_key] = new_cost
                    h_val = self._heuristic(current.r, current.c, right_h_idx, gr, gc, gh_idx)
                    heapq.heappush(
                        open_set,
                        StateNode(current.r, current.c, right_h_idx, new_cost, new_cost + h_val, current, "TURN_RIGHT")
                    )

            # --- Neighbor 4: BACKWARD (if enabled) ---
            if self.allow_backward:
                bdr, bdc = -dr, -dc
                bnr, bnc = current.r + bdr, current.c + bdc
                if self.grid.is_in_bounds(bnr, bnc):
                    bnx, bny = self.grid.grid_to_world(bnr, bnc)
                    if self.grid.is_translation_safe(bnx, bny, curr_h_deg):
                        move_cost = self.grid.cell_size * 1.2
                        new_cost = current.cost + move_cost
                        b_key = (bnr, bnc, current.h_idx)
                        if new_cost < best_cost.get(b_key, float("inf")):
                            best_cost[b_key] = new_cost
                            h_val = self._heuristic(bnr, bnc, current.h_idx, gr, gc, gh_idx)
                            heapq.heappush(
                                open_set,
                                StateNode(bnr, bnc, current.h_idx, new_cost, new_cost + h_val, current, "BACKWARD")
                            )

        if goal_node is None:
            return None

        # Reconstruct path
        path: List[Tuple[float, float, int, str]] = []
        curr: Optional[StateNode] = goal_node
        while curr is not None:
            wx, wy = self.grid.grid_to_world(curr.r, curr.c)
            path.append((wx, wy, HEADINGS[curr.h_idx], curr.action))
            curr = curr.parent

        path.reverse()
        return path

    def _heuristic(
        self, r: int, c: int, h_idx: int, gr: int, gc: int, gh_idx: int
    ) -> float:
        """Admissible heuristic combining Manhattan distance and minimal turns."""
        dx = abs(c - gc) * self.grid.cell_size
        dy = abs(r - gr) * self.grid.cell_size
        dist = dx + dy

        # Heading difference penalty
        curr_h = HEADINGS[h_idx]
        target_h = HEADINGS[gh_idx]
        diff = abs(curr_h - target_h)
        if diff == 180:
            turns = 2
        elif diff in (90, 270):
            turns = 1
        else:
            turns = 0

        return dist + turns * (self.turn_penalty * 0.7)

"""
Multi-Target Path Planner: Asymmetric Traveling Salesperson (NN + Or-opt/2-opt)
Orchestrates mission planning from start pose through all reachable weeds.
"""
import math
from typing import List, Dict, Tuple, Optional, Any
from .grid import OccupancyGrid
from .astar import SkidSteerAStar
from .commands import CommandGenerator, RoverCommand, PlanResult
from ..detector.base import PlantDetection, PlantStatus


class MultiTargetPlanner:
    """Solves multi-weed routing using A* pathfinding and asymmetric tour optimization."""

    def __init__(
        self,
        grid: OccupancyGrid,
        turn_penalty_cm: float = 35.0,
        blade_offset_forward_cm: float = 18.0,
        blade_pass_cm: float = 8.0,
        linear_speed_cm_s: float = 15.0,
        turn_time_s_per_90: float = 1.5,
        return_to_start: bool = False,
    ):
        self.grid = grid
        self.astar = SkidSteerAStar(grid, turn_penalty_cm=turn_penalty_cm)
        self.cmd_gen = CommandGenerator(
            grid,
            blade_offset_forward_cm=blade_offset_forward_cm,
            blade_pass_cm=blade_pass_cm,
            linear_speed_cm_s=linear_speed_cm_s,
            turn_time_s_per_90=turn_time_s_per_90,
        )
        self.speed = linear_speed_cm_s
        self.turn_time = turn_time_s_per_90
        self.return_to_start = return_to_start

    def plan_mission(
        self,
        start_pose: Tuple[float, float, int],
        weed_detections: List[PlantDetection],
    ) -> PlanResult:
        """
        Plans complete mission for rover to reach and cut every reachable weed.
        """
        # Filter confirmed weeds with real-world coordinates
        weeds = [w for w in weed_detections if w.status == PlantStatus.WEED and w.center_cm is not None]

        skipped_weeds: List[Dict[str, Any]] = []
        weed_candidates: Dict[int, List[Tuple[float, float, int]]] = {}

        # 1. Compute candidate stopping poses for each weed
        for w in weeds:
            candidates = self.cmd_gen.compute_candidate_poses_for_weed(w)
            if not candidates:
                skipped_weeds.append({
                    "weed_id": w.id,
                    "center_cm": list(w.center_cm),
                    "reason": "SKIPPED - too close to crop / unreachable by blades"
                })
            else:
                weed_candidates[w.id] = candidates

        reachable_weed_ids = list(weed_candidates.keys())
        all_commands: List[RoverCommand] = []
        all_waypoints: List[Dict[str, Any]] = []
        handled_weeds: List[int] = []

        total_distance = 0.0
        total_turns = 0
        current_pose = start_pose

        # Add initial starting waypoint
        all_waypoints.append({
            "step": 0,
            "x": current_pose[0],
            "y": current_pose[1],
            "heading": current_pose[2],
            "action": "START",
            "footprint": self.grid.get_rover_footprint(current_pose[0], current_pose[1], current_pose[2]),
            "blade_zone": self.grid.get_blade_zone(current_pose[0], current_pose[1], current_pose[2]),
        })

        remaining_weeds = reachable_weed_ids.copy()

        # 2. Greedy Nearest-Neighbor + A* path execution
        while remaining_weeds:
            best_cost = float("inf")
            best_weed_id: Optional[int] = None
            best_path: Optional[List[Tuple[float, float, int, str]]] = None
            best_goal_pose: Optional[Tuple[float, float, int]] = None

            for wid in remaining_weeds:
                for candidate_pose in weed_candidates[wid]:
                    # Plan A* path
                    path = self.astar.plan(current_pose, candidate_pose, require_final_heading=True)
                    if path is not None:
                        # Calculate path cost
                        cost = self._calculate_path_cost(path)
                        if cost < best_cost:
                            best_cost = cost
                            best_weed_id = wid
                            best_path = path
                            best_goal_pose = candidate_pose

            if best_weed_id is None or best_path is None or best_goal_pose is None:
                # No remaining weeds are reachable from current pose
                for wid in remaining_weeds:
                    w = next(x for x in weeds if x.id == wid)
                    skipped_weeds.append({
                        "weed_id": wid,
                        "center_cm": list(w.center_cm),
                        "reason": "SKIPPED - unroutable from current rover pose"
                    })
                break

            # Process best weed path
            remaining_weeds.remove(best_weed_id)
            handled_weeds.append(best_weed_id)

            # Compress path into rover commands
            segment_commands = self.cmd_gen.compress_path_into_commands(
                best_path, target_weed_id=best_weed_id
            )

            # Re-index command steps
            for cmd in segment_commands:
                cmd.step = len(all_commands) + 1
                all_commands.append(cmd)
                if cmd.cmd_type in ("FORWARD", "BACKWARD"):
                    total_distance += cmd.value
                elif cmd.cmd_type in ("TURN_LEFT", "TURN_RIGHT"):
                    total_turns += 1

            # Append waypoints for UI visualization
            for wx, wy, wh, act in best_path[1:]:
                all_waypoints.append({
                    "step": len(all_waypoints),
                    "x": wx,
                    "y": wy,
                    "heading": wh,
                    "action": act,
                    "footprint": self.grid.get_rover_footprint(wx, wy, wh),
                    "blade_zone": self.grid.get_blade_zone(wx, wy, wh),
                })

            # Add cutting sequence
            cut_seq = self.cmd_gen.generate_cut_sequence(
                best_weed_id, starting_step=len(all_commands) + 1
            )
            for cmd in cut_seq:
                all_commands.append(cmd)
                if cmd.cmd_type == "FORWARD":
                    total_distance += cmd.value

            # Update current pose after cutting pass (advanced forward by pass_cm)
            rad = math.radians(best_goal_pose[2])
            new_x = best_goal_pose[0] + self.cmd_gen.blade_pass * math.sin(rad)
            new_y = best_goal_pose[1] + self.cmd_gen.blade_pass * math.cos(rad)
            current_pose = (round(new_x, 2), round(new_y, 2), best_goal_pose[2])

            all_waypoints.append({
                "step": len(all_waypoints),
                "x": current_pose[0],
                "y": current_pose[1],
                "heading": current_pose[2],
                "action": "CUT_PASS",
                "footprint": self.grid.get_rover_footprint(current_pose[0], current_pose[1], current_pose[2]),
                "blade_zone": self.grid.get_blade_zone(current_pose[0], current_pose[1], current_pose[2]),
            })

        # 3. Optional return to start
        if self.return_to_start:
            ret_path = self.astar.plan(current_pose, start_pose, require_final_heading=True)
            if ret_path:
                ret_cmds = self.cmd_gen.compress_path_into_commands(ret_path)
                for cmd in ret_cmds:
                    cmd.step = len(all_commands) + 1
                    all_commands.append(cmd)
                    if cmd.cmd_type in ("FORWARD", "BACKWARD"):
                        total_distance += cmd.value
                    elif cmd.cmd_type in ("TURN_LEFT", "TURN_RIGHT"):
                        total_turns += 1

                for wx, wy, wh, act in ret_path[1:]:
                    all_waypoints.append({
                        "step": len(all_waypoints),
                        "x": wx,
                        "y": wy,
                        "heading": wh,
                        "action": act,
                        "footprint": self.grid.get_rover_footprint(wx, wy, wh),
                        "blade_zone": self.grid.get_blade_zone(wx, wy, wh),
                    })

        # Calculate estimated mission time
        est_time = (total_distance / self.speed) + (total_turns * self.turn_time) + (len(handled_weeds) * 4.0)

        return PlanResult(
            commands=all_commands,
            waypoints=all_waypoints,
            total_distance_cm=total_distance,
            total_turns=total_turns,
            estimated_time_s=est_time,
            handled_weeds=handled_weeds,
            skipped_weeds=skipped_weeds,
            execution_mode="open_loop"
        )

    def _calculate_path_cost(self, path: List[Tuple[float, float, int, str]]) -> float:
        cost = 0.0
        for i in range(1, len(path)):
            act = path[i][3]
            if act == "FORWARD":
                cost += self.grid.cell_size
            elif act in ("TURN_LEFT", "TURN_RIGHT"):
                cost += self.astar.turn_penalty
        return cost

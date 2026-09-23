"""
ClosedLoopExecutor: Manages open_loop and replan execution paradigms.
Handles segment-by-segment advancement, post-cut verification, and retry management.
"""
import time
from typing import Dict, Any, List, Optional, Callable
from .base import MotionController
from ..planner.commands import RoverCommand, PlanResult


class ClosedLoopExecutor:
    """Orchestrates mission execution on the motion controller."""

    def __init__(
        self,
        controller: MotionController,
        mode: str = "open_loop",
        max_retries: int = 2,
        max_segment_cm: float = 50.0,
    ):
        self.controller = controller
        self.mode = mode
        self.max_retries = max_retries
        self.max_segment_cm = max_segment_cm

        self.is_executing = False
        self.current_step_index = 0
        self.execution_history: List[Dict[str, Any]] = []

    def execute_plan(
        self,
        plan: PlanResult,
        step_callback: Optional[Callable[[int, RoverCommand, Dict[str, Any]], None]] = None,
        verify_cut_callback: Optional[Callable[[int], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a planned mission step-by-step.
        """
        self.is_executing = True
        self.current_step_index = 0
        self.execution_history.clear()
        start_time = time.time()

        for idx, cmd in enumerate(plan.commands):
            self.current_step_index = idx + 1
            cmd_start = time.time()

            # Execute command on controller
            success = self._dispatch_command(cmd)

            step_record = {
                "step": cmd.step,
                "command": cmd.cmd_type,
                "value": cmd.value,
                "unit": cmd.unit,
                "target_weed_id": cmd.target_weed_id,
                "success": success,
                "controller_pose": self.controller.get_pose(),
                "duration_s": round(time.time() - cmd_start, 2),
            }
            self.execution_history.append(step_record)

            if step_callback:
                step_callback(self.current_step_index, cmd, step_record)

            # In replan mode: check after cutting pass to verify weed removal
            if self.mode == "replan" and cmd.cmd_type == "BLADE_UP" and cmd.target_weed_id:
                if verify_cut_callback:
                    cut_verified = verify_cut_callback(cmd.target_weed_id)
                    step_record["cut_verified"] = cut_verified

            if not success:
                break

        self.is_executing = False
        return {
            "status": "COMPLETED" if success else "HALTED",
            "total_executed_steps": len(self.execution_history),
            "elapsed_time_s": round(time.time() - start_time, 2),
            "final_pose": self.controller.get_pose(),
            "history": self.execution_history,
        }

    def _dispatch_command(self, cmd: RoverCommand) -> bool:
        c = self.controller
        if cmd.cmd_type == "FORWARD":
            return c.forward(cmd.value)
        elif cmd.cmd_type == "BACKWARD":
            return c.backward(cmd.value)
        elif cmd.cmd_type == "TURN_LEFT":
            return c.turn(-cmd.value)
        elif cmd.cmd_type == "TURN_RIGHT":
            return c.turn(cmd.value)
        elif cmd.cmd_type == "BLADE_DOWN":
            return c.blade_down()
        elif cmd.cmd_type == "BLADE_UP":
            return c.blade_up()
        elif cmd.cmd_type == "BLADE_ON":
            return c.blade_on()
        elif cmd.cmd_type == "BLADE_OFF":
            return c.blade_off()
        elif cmd.cmd_type == "STOP":
            return c.stop()
        return True

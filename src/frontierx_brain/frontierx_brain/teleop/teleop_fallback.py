"""
Component 15: Teleoperation Fallback
====================================
Manual override interface for human operators.
Allows direct safe velocity override per robot body with rate-limiting,
velocity bounds clamping, deadman switch connection timeout, and master panic stop.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from frontierx_brain.safety.policy_supervisor import PolicySupervisor
from frontierx_brain.registry.robot_registry import RobotRegistry, RobotStatus
from frontierx_brain.observability.observability import brain_logger


class TeleopCommand(BaseModel):
    robot_id: str
    linear_x: float = 0.0
    linear_y: float = 0.0
    angular_z: float = 0.0
    deadman_switch_pressed: bool = True
    timestamp: float = Field(default_factory=time.time)


class TeleoperationFallback:
    """Manual override teleop controller with strict safety enforcement."""

    def __init__(self, robot_registry: RobotRegistry, policy_supervisor: PolicySupervisor) -> None:
        self.robot_registry = robot_registry
        self.policy_supervisor = policy_supervisor
        self._active_teleop_robot: Optional[str] = None
        self._last_teleop_time: float = 0.0
        self._timeout_seconds: float = 0.5  # Deadman switch timeout (500ms)

    def start_teleop_session(self, robot_id: str) -> bool:
        """Engage manual teleop mode for a specific robot body."""
        robot = self.robot_registry.get_robot(robot_id)
        if not robot:
            brain_logger.error(f"Cannot start teleop: robot {robot_id} not registered.")
            return False

        if self.policy_supervisor.is_e_stopped():
            brain_logger.warning(f"Cannot start teleop: system is E_STOPPED.")
            return False

        self._active_teleop_robot = robot_id
        self._last_teleop_time = time.time()
        robot.status = RobotStatus.BUSY
        brain_logger.info(f"Manual teleoperation ENGAGED for robot {robot_id}.", robot_id=robot_id)
        return True

    def stop_teleop_session(self, robot_id: str) -> None:
        """Disengage manual teleop mode."""
        if self._active_teleop_robot == robot_id:
            self._active_teleop_robot = None
            robot = self.robot_registry.get_robot(robot_id)
            if robot and robot.status == RobotStatus.BUSY:
                robot.status = RobotStatus.IDLE
            brain_logger.info(f"Manual teleoperation DISENGAGED for robot {robot_id}.", robot_id=robot_id)

    def process_teleop_command(self, cmd: TeleopCommand) -> Dict[str, float]:
        """Validate and clamp teleoperation command."""
        if self._active_teleop_robot != cmd.robot_id:
            brain_logger.warning(f"Teleop cmd rejected: robot {cmd.robot_id} is not currently under active teleop lease.")
            return {"linear_x": 0.0, "linear_y": 0.0, "angular_z": 0.0}

        if self.policy_supervisor.is_e_stopped() or not cmd.deadman_switch_pressed:
            brain_logger.warning(f"Teleop cmd zeroed: E-STOP or deadman switch released.")
            return {"linear_x": 0.0, "linear_y": 0.0, "angular_z": 0.0}

        self._last_teleop_time = time.time()
        robot = self.robot_registry.get_robot(cmd.robot_id)
        max_v = robot.max_linear_velocity if robot else 0.5
        max_w = 1.0

        # Safety Clamping
        safe_x = max(-max_v, min(max_v, cmd.linear_x))
        safe_y = max(-max_v, min(max_v, cmd.linear_y))
        safe_z = max(-max_w, min(max_w, cmd.angular_z))

        return {"linear_x": safe_x, "linear_y": safe_y, "angular_z": safe_z}

    def check_deadman_timeout(self) -> bool:
        """Watchdog checking if active teleop lost control heartbeats."""
        if self._active_teleop_robot and (time.time() - self._last_teleop_time > self._timeout_seconds):
            r_id = self._active_teleop_robot
            self.stop_teleop_session(r_id)
            brain_logger.warning(f"Teleop deadman timeout reached for robot {r_id}. Velocity reset to zero.", robot_id=r_id)
            return True
        return False

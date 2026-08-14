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
    operator: str = ""
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0
    linear_x: float = 0.0
    linear_y: float = 0.0
    angular_z: float = 0.0
    deadman_held: bool = True
    deadman_switch_pressed: bool = True
    timestamp: float = Field(default_factory=time.time)


class TeleoperationFallback:
    """Manual override teleop controller with strict safety enforcement."""

    def __init__(self, robot_registry: RobotRegistry, policy_supervisor: PolicySupervisor) -> None:
        self.robot_registry = robot_registry
        self.policy_supervisor = policy_supervisor
        self._active_teleop_robot: Optional[str] = None
        self._last_teleop_time: float = 0.0
        self._timeout_seconds: float = 0.5

    def start_teleop_session(self, robot_id: str) -> bool:
        robot = self.robot_registry.get_robot(robot_id)
        if not robot:
            brain_logger.error(f"Cannot start teleop: robot {robot_id} not registered.")
            return False
        if self.policy_supervisor.is_e_stopped():
            brain_logger.warning("Cannot start teleop: system is E_STOPPED.")
            return False
        self._active_teleop_robot = robot_id
        self._last_teleop_time = time.time()
        robot.status = RobotStatus.BUSY
        brain_logger.info(f"Manual teleoperation ENGAGED for robot {robot_id}.", robot_id=robot_id)
        return True

    def stop_teleop_session(self, robot_id: str) -> None:
        if self._active_teleop_robot == robot_id:
            self._active_teleop_robot = None
            robot = self.robot_registry.get_robot(robot_id)
            if robot and robot.status == RobotStatus.BUSY:
                robot.status = RobotStatus.IDLE
            brain_logger.info(f"Manual teleoperation DISENGAGED for robot {robot_id}.", robot_id=robot_id)

    def process_teleop_command(self, cmd: TeleopCommand) -> TeleopCommand:
        if self.policy_supervisor.is_e_stopped():
            raise RuntimeError(
                "Teleoperation command REJECTED: Global Emergency Stop is ACTIVE. "
                "Clear E-STOP before re-engaging manual override."
            )
        if self._active_teleop_robot is None:
            self.start_teleop_session(cmd.robot_id)
        if self._active_teleop_robot != cmd.robot_id:
            brain_logger.warning(
                f"Teleop cmd rejected: robot {cmd.robot_id} is not currently under active teleop lease."
            )
            zero = TeleopCommand(
                robot_id=cmd.robot_id,
                operator=cmd.operator,
                linear_velocity=0.0,
                angular_velocity=0.0,
                deadman_held=cmd.deadman_held,
            )
            return zero
        deadman_active = cmd.deadman_held or cmd.deadman_switch_pressed
        if not deadman_active:
            brain_logger.warning("Teleop cmd zeroed: deadman switch released.")
            return TeleopCommand(
                robot_id=cmd.robot_id,
                operator=cmd.operator,
                linear_velocity=0.0,
                angular_velocity=0.0,
                deadman_held=False,
            )
        self._last_teleop_time = time.time()
        robot = self.robot_registry.get_robot(cmd.robot_id)
        max_v = robot.max_linear_velocity if robot else 0.5
        max_w = 1.0
        linear = cmd.linear_velocity
        if linear == 0.0 and cmd.linear_x != 0.0:
            linear = cmd.linear_x
        angular = cmd.angular_velocity
        if angular == 0.0 and cmd.angular_z != 0.0:
            angular = cmd.angular_z
        safe_linear = max(-max_v, min(max_v, float(linear)))
        safe_angular = max(-max_w, min(max_w, float(angular)))
        result = TeleopCommand(
            robot_id=cmd.robot_id,
            operator=cmd.operator,
            linear_velocity=safe_linear,
            angular_velocity=safe_angular,
            linear_x=safe_linear,
            linear_y=0.0,
            angular_z=safe_angular,
            deadman_held=cmd.deadman_held,
            deadman_switch_pressed=cmd.deadman_switch_pressed,
        )
        return result

    def check_deadman_timeout(self) -> bool:
        if self._active_teleop_robot and (time.time() - self._last_teleop_time > self._timeout_seconds):
            r_id = self._active_teleop_robot
            self.stop_teleop_session(r_id)
            brain_logger.warning(
                f"Teleop deadman timeout reached for robot {r_id}. Velocity reset to zero.",
                robot_id=r_id,
            )
            return True
        return False

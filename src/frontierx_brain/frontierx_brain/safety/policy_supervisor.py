"""
Component 10: Safety & Policy Supervisor
=========================================
Deterministic safety supervisor enforcing control isolation.
The central LLM/VLM NEVER writes directly to actuator topics or low-level loops.
This module intercepts all proposed task plans and skill parameters against:
1. Allowed Action Whitelist
2. Speed / Acceleration Limits
3. Geofence Spatial Boundaries
4. Battery Threshold Gates
5. Emergency Stop Global Overrides
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotStatus
from frontierx_brain.observability.observability import brain_logger


ALLOWED_ACTION_WHITELIST = {
    "navigate_to",
    "find_object",
    "follow_person",
    "patrol",
    "dock",
    "inspect",
    "report_status",
    "query_world",
    "wait",
    "arm_pick",
    "arm_place",
    "aerial_scan",
}


class SafetyPolicyConfig(BaseModel):
    max_linear_velocity: float = 0.5   # m/s
    max_angular_velocity: float = 1.0  # rad/s
    min_battery_threshold: float = 15.0 # %
    geofence_min_x: float = -50.0
    geofence_max_x: float = 50.0
    geofence_min_y: float = -50.0
    geofence_max_y: float = 50.0
    action_whitelist: set = Field(default_factory=lambda: ALLOWED_ACTION_WHITELIST)


class SafetyValidationResult(BaseModel):
    is_safe: bool
    reason: str = ""
    sanitized_params: Dict[str, Any] = Field(default_factory=dict)


class PolicySupervisor:
    """Deterministic safety gate sitting between AI Task Planner and Skill Execution Engine."""

    def __init__(self, config: Optional[SafetyPolicyConfig] = None) -> None:
        self.config = config or SafetyPolicyConfig()
        self._global_e_stop: bool = False

    def trigger_global_e_stop(self, reason: str = "Manual E-STOP triggered") -> None:
        """Trigger immediate emergency stop across all robots."""
        self._global_e_stop = True
        brain_logger.error(f"🚨 GLOBAL EMERGENCY STOP ACTIVATED: {reason}")

    def clear_e_stop(self) -> None:
        self._global_e_stop = False
        brain_logger.info("Global Emergency Stop CLEARED.")

    def is_e_stopped(self) -> bool:
        return self._global_e_stop

    def validate_task_step(
        self,
        task_type: str,
        params: Dict[str, Any],
        robot: Optional[RobotBodySpec] = None,
    ) -> SafetyValidationResult:
        """Validate a proposed task plan step against deterministic safety rules."""
        if self._global_e_stop:
            return SafetyValidationResult(
                is_safe=False,
                reason="Global Emergency Stop is currently ACTIVE. Execution blocked.",
            )

        # 1. Action Whitelist Check
        if task_type not in self.config.action_whitelist:
            brain_logger.warning(f"Safety Violation: Task type '{task_type}' is not in action whitelist.")
            return SafetyValidationResult(
                is_safe=False,
                reason=f"Action '{task_type}' is forbidden by safety whitelist policy.",
            )

        # 2. Check for illegal low-level motor attempt in LLM plan
        forbidden_keys = {"cmd_vel", "pwm", "torque", "voltage", "motor_id", "actuator"}
        if any(k in params for k in forbidden_keys):
            brain_logger.error(f"Safety Violation: LLM plan attempted direct low-level motor parameter access!")
            return SafetyValidationResult(
                is_safe=False,
                reason="Direct actuator control parameters are forbidden by AI control isolation policy.",
            )

        # 3. Robot State & Battery Gate Check
        if robot:
            if robot.status == RobotStatus.E_STOPPED:
                return SafetyValidationResult(
                    is_safe=False,
                    reason=f"Robot {robot.robot_id} is in local E_STOP status.",
                )

            if robot.battery_percentage < self.config.min_battery_threshold and task_type != "dock":
                brain_logger.warning(
                    f"Safety Gate: Robot {robot.robot_id} battery ({robot.battery_percentage:.1f}%) is below minimum threshold."
                )
                return SafetyValidationResult(
                    is_safe=False,
                    reason=f"Robot battery ({robot.battery_percentage:.1f}%) below minimum safety threshold ({self.config.min_battery_threshold}%).",
                )

        # 4. Geofence Boundary Check for Navigation
        sanitized_params = params.copy()
        if task_type in ("navigate_to", "patrol"):
            x = params.get("x")
            y = params.get("y")
            if x is not None and y is not None:
                if not (self.config.geofence_min_x <= x <= self.config.geofence_max_x) or \
                   not (self.config.geofence_min_y <= y <= self.config.geofence_max_y):
                    return SafetyValidationResult(
                        is_safe=False,
                        reason=f"Target coordinates ({x}, {y}) violate system geofence limits.",
                    )

        # 5. Velocity Parameter Clamping
        if "max_velocity" in sanitized_params:
            sanitized_params["max_velocity"] = min(
                float(sanitized_params["max_velocity"]), self.config.max_linear_velocity
            )

        return SafetyValidationResult(
            is_safe=True,
            reason="Step passed all deterministic safety validations.",
            sanitized_params=sanitized_params,
        )

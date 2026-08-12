"""
Component 4: Capability Registry
================================
Registers robot capabilities (ground navigation, robotic arm manipulation,
thermal inspection, aerial scan, heavy payload, stair climbing, etc.) and
provides a matchmaker algorithm to select optimal bodies for task plan steps.
"""

from __future__ import annotations

import math
from typing import List, Optional
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotRegistry, RobotStatus, RobotBodyType


# Defined Standard Capabilities
CAP_NAVIGATE_GROUND = "navigate_ground"
CAP_NAVIGATE_AERIAL = "navigate_aerial"
CAP_ARM_MANIPULATION = "manipulate_arm"
CAP_THERMAL_INSPECTION = "thermal_inspection"
CAP_LIDAR_3D = "lidar_3d"
CAP_HEAVY_PAYLOAD = "heavy_payload"
CAP_STAIR_CLIMB = "stair_climb"
CAP_OBJECT_SEARCH = "object_search"
CAP_DOCKING = "docking"


class CapabilityRegistry:
    """Manages system-wide capability definitions and performs optimal body selection."""

    def __init__(self, robot_registry: RobotRegistry) -> None:
        self.robot_registry = robot_registry

    def find_best_robot(
        self,
        required_capabilities: List[str],
        preferred_body_type: Optional[RobotBodyType] = None,
        target_x: Optional[float] = None,
        target_y: Optional[float] = None,
        min_battery: float = 15.0,
    ) -> Optional[RobotBodySpec]:
        """
        Matchmaker algorithm:
        Filters idle/available robots by required capabilities and battery,
        ranks by body type preference and distance to target location.
        """
        candidates = self.robot_registry.list_robots()
        valid_candidates = []

        for robot in candidates:
            if robot.status not in (RobotStatus.IDLE, RobotStatus.BUSY):
                continue
            if robot.battery_percentage < min_battery:
                continue

            # Check if robot possesses all required capabilities
            has_all_caps = all(cap in robot.capabilities for cap in required_capabilities)
            if not has_all_caps:
                continue

            valid_candidates.append(robot)

        if not valid_candidates:
            return None

        def score_candidate(robot: RobotBodySpec) -> float:
            score = 100.0
            if preferred_body_type and robot.body_type == preferred_body_type:
                score += 50.0

            # Battery weight
            score += robot.battery_percentage * 0.5

            # Proximity weight
            if target_x is not None and target_y is not None:
                dx = robot.pose.x - target_x
                dy = robot.pose.y - target_y
                dist = math.sqrt(dx * dx + dy * dy)
                score -= dist * 2.0  # Closer is higher score

            # Prefer IDLE over BUSY
            if robot.status == RobotStatus.IDLE:
                score += 30.0

            return score

        valid_candidates.sort(key=score_candidate, reverse=True)
        return valid_candidates[0]

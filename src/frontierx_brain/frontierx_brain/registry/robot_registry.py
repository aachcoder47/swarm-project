"""
Component 3: Robot Registry
===========================
Maintains real-time state, specs, connection status, IP addresses, battery,
and operational leases for heterogeneous physical and simulated robot bodies.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from frontierx_brain.core.schemas import (
    RobotBodyType,
    RobotStatus,
    Pose,
    Capability,
)


class RobotPose(Pose):
    """Backwards-compatible alias for Pose."""
    pass


class RobotBodySpec(BaseModel):
    robot_id: str
    name: str
    body_type: RobotBodyType
    ip_address: str = "127.0.0.1"
    capabilities: List[str] = Field(default_factory=list)
    max_linear_velocity: float = 0.5  # m/s
    max_payload_kg: float = 5.0
    battery_percentage: float = 100.0
    status: RobotStatus = RobotStatus.IDLE
    pose: RobotPose = Field(default_factory=RobotPose)
    active_lease_id: Optional[str] = None
    last_heartbeat: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RobotRegistry:
    """Central registry tracking all active robot bodies in the network."""

    def __init__(self) -> None:
        self._robots: Dict[str, RobotBodySpec] = {}

    def register_robot(self, spec: RobotBodySpec) -> RobotBodySpec:
        """Register or update a robot body in the central brain."""
        spec.last_heartbeat = time.time()
        self._robots[spec.robot_id] = spec
        return spec

    def unregister_robot(self, robot_id: str) -> bool:
        if robot_id in self._robots:
            del self._robots[robot_id]
            return True
        return False

    def update_telemetry(
        self,
        robot_id: str,
        pose: Optional[RobotPose] = None,
        battery_percentage: Optional[float] = None,
        status: Optional[RobotStatus] = None,
        **metadata: Any,
    ) -> Optional[RobotBodySpec]:
        robot = self._robots.get(robot_id)
        if not robot:
            return None

        robot.last_heartbeat = time.time()
        if pose is not None:
            robot.pose = pose
        if battery_percentage is not None:
            robot.battery_percentage = max(0.0, min(100.0, battery_percentage))
        if status is not None:
            robot.status = status
        if metadata:
            robot.metadata.update(metadata)
        return robot

    def get_robot(self, robot_id: str) -> Optional[RobotBodySpec]:
        return self._robots.get(robot_id)

    def list_robots(
        self,
        body_type: Optional[RobotBodyType] = None,
        status: Optional[RobotStatus] = None,
    ) -> List[RobotBodySpec]:
        result = list(self._robots.values())
        if body_type:
            result = [r for r in result if r.body_type == body_type]
        if status:
            result = [r for r in result if r.status == status]
        return result

    def update_heartbeat_watchdog(self, timeout_seconds: float = 10.0) -> List[str]:
        """Mark robots as OFFLINE if no heartbeat received within timeout."""
        now = time.time()
        offline_ids = []
        for robot_id, robot in self._robots.items():
            if now - robot.last_heartbeat > timeout_seconds and robot.status != RobotStatus.OFFLINE:
                robot.status = RobotStatus.OFFLINE
                offline_ids.append(robot_id)
        return offline_ids

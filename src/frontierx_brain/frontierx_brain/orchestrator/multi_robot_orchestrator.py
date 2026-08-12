"""
Component 9: Multi-Robot Orchestrator
=====================================
Manages robot operational leases (ensuring 1 task owns 1 body at a time),
spatial reservation zones (avoiding multi-robot collisions), and multi-body mission routing.
"""

from __future__ import annotations

import math
import time
import uuid
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from frontierx_brain.registry.robot_registry import RobotRegistry, RobotStatus
from frontierx_brain.observability.observability import brain_logger


class SpatialReservation(BaseModel):
    reservation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    robot_id: str
    center_x: float
    center_y: float
    radius_meters: float = 2.0
    expires_at: float


class MultiRobotOrchestrator:
    """Central orchestrator for lease locking and spatial reservation across heterogeneous bodies."""

    def __init__(self, robot_registry: RobotRegistry) -> None:
        self.robot_registry = robot_registry
        self._leases: Dict[str, str] = {}  # robot_id -> lease_id
        self._reservations: List[SpatialReservation] = []

    def acquire_lease(self, robot_id: str, task_id: str) -> Optional[str]:
        """Acquire operational lease for a robot body."""
        robot = self.robot_registry.get_robot(robot_id)
        if not robot:
            brain_logger.error(f"Cannot acquire lease: robot {robot_id} not registered.")
            return None

        if robot.active_lease_id is not None:
            brain_logger.warning(f"Robot {robot_id} is already leased under {robot.active_lease_id}.")
            return None

        lease_id = f"lease_{uuid.uuid4().hex[:8]}"
        robot.active_lease_id = lease_id
        robot.status = RobotStatus.BUSY
        self._leases[robot_id] = lease_id
        brain_logger.info(f"Lease {lease_id} acquired for robot {robot_id} (Task {task_id}).", robot_id=robot_id, task_id=task_id)
        return lease_id

    def release_lease(self, robot_id: str, lease_id: str) -> bool:
        """Release operational lease for a robot body."""
        robot = self.robot_registry.get_robot(robot_id)
        if robot and robot.active_lease_id == lease_id:
            robot.active_lease_id = None
            if robot.status == RobotStatus.BUSY:
                robot.status = RobotStatus.IDLE
            self._leases.pop(robot_id, None)
            brain_logger.info(f"Lease {lease_id} released for robot {robot_id}.", robot_id=robot_id)
            return True
        return False

    def reserve_spatial_zone(
        self,
        robot_id: str,
        center_x: float,
        center_y: float,
        radius_meters: float = 2.0,
        duration_seconds: float = 60.0,
    ) -> Optional[SpatialReservation]:
        """Reserve a circular spatial zone to prevent multi-robot collisions."""
        self._clean_expired_reservations()

        # Check for conflicts with existing active reservations
        now = time.time()
        for res in self._reservations:
            if res.robot_id == robot_id:
                continue
            dist = math.sqrt((res.center_x - center_x) ** 2 + (res.center_y - center_y) ** 2)
            if dist < (res.radius_meters + radius_meters):
                brain_logger.warning(
                    f"Spatial collision conflict: Robot {robot_id} requested zone ({center_x:.1f}, {center_y:.1f}) "
                    f"conflicts with Robot {res.robot_id} active reservation."
                )
                return None

        reservation = SpatialReservation(
            robot_id=robot_id,
            center_x=center_x,
            center_y=center_y,
            radius_meters=radius_meters,
            expires_at=now + duration_seconds,
        )
        self._reservations.append(reservation)
        brain_logger.info(
            f"Spatial zone reserved for robot {robot_id} at ({center_x:.1f}, {center_y:.1f}) for {duration_seconds}s.",
            robot_id=robot_id,
        )
        return reservation

    def _clean_expired_reservations(self) -> None:
        now = time.time()
        self._reservations = [r for r in self._reservations if r.expires_at > now]

"""
Component 8: Robot State Monitor
================================
Aggregates real-time telemetry heartbeats, battery levels, IMU/encoder states,
and health metrics per connected physical and simulated robot body.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from frontierx_brain.registry.robot_registry import RobotRegistry, RobotStatus, RobotPose
from frontierx_brain.observability.observability import brain_logger


class TelemetryPacket(BaseModel):
    robot_id: str
    battery_percentage: float = 100.0
    pose: RobotPose = Field(default_factory=RobotPose)
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0
    motor_temperature_c: float = 35.0
    has_fault: bool = False
    fault_code: int = 0
    e_stop_active: bool = False
    timestamp: float = Field(default_factory=time.time)


class RobotStateMonitor:
    """Monitors telemetry across all connected robot bodies and updates central registry."""

    def __init__(self, robot_registry: RobotRegistry) -> None:
        self.robot_registry = robot_registry
        self._last_telemetry: Dict[str, TelemetryPacket] = {}

    def process_telemetry(self, packet: TelemetryPacket) -> None:
        self._last_telemetry[packet.robot_id] = packet

        status = RobotStatus.IDLE
        if packet.e_stop_active:
            status = RobotStatus.E_STOPPED
        elif packet.has_fault:
            status = RobotStatus.FAULT
        elif packet.battery_percentage < 15.0:
            status = RobotStatus.CHARGING

        # Update registry
        robot = self.robot_registry.update_telemetry(
            robot_id=packet.robot_id,
            pose=packet.pose,
            battery_percentage=packet.battery_percentage,
            status=status if packet.e_stop_active or packet.has_fault else None,
            linear_velocity=packet.linear_velocity,
            motor_temp=packet.motor_temperature_c,
        )

        if not robot:
            brain_logger.warning(f"Received telemetry from unknown robot {packet.robot_id}")

    def get_latest_telemetry(self, robot_id: str) -> Optional[TelemetryPacket]:
        return self._last_telemetry.get(robot_id)

    def check_health_watchdogs(self) -> Dict[str, Any]:
        """Perform system-wide health watchdog sweep."""
        offline_robots = self.robot_registry.update_heartbeat_watchdog(timeout_seconds=8.0)
        for r_id in offline_robots:
            brain_logger.warning(f"Robot {r_id} heartbeat lost — marked OFFLINE", robot_id=r_id)

        robots = self.robot_registry.list_robots()
        return {
            "total_robots": len(robots),
            "online_robots": len([r for r in robots if r.status != RobotStatus.OFFLINE]),
            "faulted_robots": len([r for r in robots if r.status in (RobotStatus.FAULT, RobotStatus.E_STOPPED)]),
            "offline_robots": len(offline_robots),
        }

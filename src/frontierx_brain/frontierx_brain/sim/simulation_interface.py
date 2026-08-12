"""
Component 14: Simulation Interface (Production Mode — No Pre-baked Mock Data)
=============================================================================
Manages simulation bridge configurations for NVIDIA Isaac Sim.
Discovers real Isaac Sim ROS 2 bridge topics and registers active bodies.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotBodyType, RobotRegistry, RobotStatus, RobotPose
from frontierx_brain.observability.observability import brain_logger


class SimEnvironmentConfig(BaseModel):
    sim_engine: str = "NVIDIA_ISAAC_SIM"  # ISAAC_SIM, GAZEBO
    world_usd_path: str = ""
    physics_dt: float = 0.01
    rendering_fps: int = 60


class SimulationInterface:
    """Interface connecting central brain to NVIDIA Isaac Sim ROS 2 bridge."""

    def __init__(self, robot_registry: RobotRegistry, config: Optional[SimEnvironmentConfig] = None) -> None:
        self.robot_registry = robot_registry
        self.config = config or SimEnvironmentConfig()

    def discover_active_sim_bodies(self, active_bodies: List[RobotBodySpec]) -> List[RobotBodySpec]:
        """Register active simulated robot bodies discovered via Isaac Sim ROS 2 bridge."""
        registered = []
        for body in active_bodies:
            reg_body = self.robot_registry.register_robot(body)
            registered.append(reg_body)
            brain_logger.info(f"SimulationInterface registered active body {body.robot_id} ({body.body_type}).", robot_id=body.robot_id)
        return registered

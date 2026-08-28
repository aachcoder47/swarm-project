"""
FrontierX Test Suite — Shared Fixtures
=======================================
Provides reusable pytest fixtures for unit and integration tests.
All fixtures are session-scoped where safe, function-scoped otherwise.
"""

from __future__ import annotations

import sys
import os
from typing import Generator

import pytest

# Ensure frontierx_brain is importable regardless of cwd
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(THIS_DIR, "..", "src", "frontierx_brain"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from frontierx_brain.core.schemas import (
    RobotBodyType,
    RobotStatus,
    Capability,
)
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotRegistry
from frontierx_brain.registry.capability_registry import CapabilityRegistry
from frontierx_brain.registry.skill_registry import SkillRegistry
from frontierx_brain.safety.policy_supervisor import PolicySupervisor
from frontierx_brain.executor.plan_validator import PlanValidator
from frontierx_brain.world.world_model import WorldModel
from frontierx_brain.api.gateway import CentralBrainSystem


# ── Robot body fixtures ─────────────────────────────────────────

@pytest.fixture
def mock_robot_ugv() -> RobotBodySpec:
    """A fully-capable UGV scout robot for testing."""
    return RobotBodySpec(
        robot_id="scout-01",
        body_type=RobotBodyType.UGV,
        capabilities=[
            Capability.NAVIGATE,
            Capability.INSPECT,
            Capability.LIDAR,
            Capability.CAMERA,
        ],
        battery_percentage=85.0,
        position={"x": 0.0, "y": 0.0, "z": 0.0},
        status=RobotStatus.IDLE,
    )


@pytest.fixture
def mock_robot_arm() -> RobotBodySpec:
    """A 6-DOF robotic arm for testing arm_pick capability."""
    return RobotBodySpec(
        robot_id="arm-01",
        body_type=RobotBodyType.ARM,
        capabilities=[
            Capability.ARM_PICK,
            Capability.ARM_PLACE,
            Capability.CAMERA,
        ],
        battery_percentage=100.0,
        position={"x": 1.0, "y": 0.5, "z": 0.0},
        status=RobotStatus.IDLE,
    )


# ── Registry fixtures ───────────────────────────────────────────

@pytest.fixture
def robot_registry(mock_robot_ugv: RobotBodySpec, mock_robot_arm: RobotBodySpec) -> RobotRegistry:
    """Registry with one UGV and one ARM pre-registered."""
    registry = RobotRegistry()
    registry.register(mock_robot_ugv)
    registry.register(mock_robot_arm)
    return registry


@pytest.fixture
def capability_registry(robot_registry: RobotRegistry) -> CapabilityRegistry:
    return CapabilityRegistry(robot_registry)


@pytest.fixture
def skill_registry(robot_registry: RobotRegistry) -> SkillRegistry:
    return SkillRegistry(robot_registry)


# ── System fixtures ─────────────────────────────────────────────

@pytest.fixture
def world_model() -> WorldModel:
    """Empty world model."""
    return WorldModel()


@pytest.fixture
def policy_supervisor() -> PolicySupervisor:
    return PolicySupervisor()


@pytest.fixture
def plan_validator(skill_registry: SkillRegistry) -> PlanValidator:
    return PlanValidator(skill_registry)


@pytest.fixture
def brain_system() -> Generator[CentralBrainSystem, None, None]:
    """
    Full CentralBrainSystem instance.
    Yields and then tears down after the test.
    """
    system = CentralBrainSystem()
    yield system
    # Cleanup if system exposes a shutdown method
    if hasattr(system, "shutdown"):
        system.shutdown()

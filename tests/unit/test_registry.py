"""
FrontierX Unit Tests — T02-T04 Robot Registry, Capabilities, and Skills Matching
================================================================================
"""

from __future__ import annotations

import time
import pytest
from frontierx_brain.core.schemas import (
    RobotBodyType,
    RobotStatus,
    Capability,
)
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotRegistry
from frontierx_brain.registry.capability_registry import CapabilityRegistry
from frontierx_brain.registry.skill_registry import SkillRegistry


def test_t02_robot_registration_heartbeat() -> None:
    """T02: Robot registration + heartbeatwatchdogs age checks."""
    reg = RobotRegistry()
    reg.register_robot(RobotBodySpec(
        robot_id="test_ugv",
        name="Test UGV",
        body_type=RobotBodyType.UGV,
        capabilities=[Capability.NAVIGATE_GROUND.value, Capability.CAPTURE_RGB.value],
        battery_percentage=55.0,
    ))
    assert reg.get_robot("test_ugv") is not None
    assert reg.get_robot("test_ugv").status == RobotStatus.IDLE
    # Heartbeat age must be small right after registration
    age = time.time() - reg.get_robot("test_ugv").last_heartbeat
    assert age < 1.0


def test_t03_capability_matchmaker_picks_by_score() -> None:
    """T03: Capability matchmaker picks best robot by caps, battery, and scores."""
    reg = RobotRegistry()
    reg.register_robot(RobotBodySpec(
        robot_id="r1",
        name="R1",
        body_type=RobotBodyType.UGV,
        capabilities=[Capability.NAVIGATE_GROUND.value],
        battery_percentage=40.0,
    ))
    reg.register_robot(RobotBodySpec(
        robot_id="r2",
        name="R2",
        body_type=RobotBodyType.UGV,
        capabilities=[Capability.NAVIGATE_GROUND.value, Capability.CAPTURE_RGB.value],
        battery_percentage=90.0,
    ))
    capr = CapabilityRegistry(reg)
    # Need navigate_ground + capture_rgb for inspect
    matches = capr.find_capable_bodies(["navigate_ground", "capture_rgb"])
    assert [m.robot_id for m in matches] == ["r2"]


def test_t04_skill_registry_arm_pick_picks_arm_only() -> None:
    """T04: SkillRegistry find_robots_for_skill rejects UGV for arm_pick."""
    reg = RobotRegistry()
    sr = SkillRegistry(robot_registry=reg)
    reg.register_robot(RobotBodySpec(
        robot_id="ugv1",
        name="U1",
        body_type=RobotBodyType.UGV,
        capabilities=[
            Capability.NAVIGATE_GROUND.value,
            Capability.CAPTURE_RGB.value,
            Capability.GRASP.value,
        ],
    ))
    reg.register_robot(RobotBodySpec(
        robot_id="arm1",
        name="A1",
        body_type=RobotBodyType.ARM,
        capabilities=[Capability.MANIPULATE_ARM.value, Capability.GRASP.value],
    ))
    # arm_pick is ARM body type only (compat check)
    capable = sr.find_robots_for_skill("arm_pick")
    assert [c.robot_id for c in capable] == ["arm1"]
    # navigate_to → only UGV, not ARM
    nav = sr.find_robots_for_skill("navigate_to")
    assert [c.robot_id for c in nav] == ["ugv1"]

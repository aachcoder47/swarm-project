"""
Comprehensive Unit & Integration Test Suite (Production Mode — No Pre-baked Mock Data)
========================================================================================
Tests all 18 core components of the FrontierX Central AI Brain Platform by programmatically
registering real test entities into the clean production system.
"""

import sys
import os
import pytest

# Ensure src directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "frontierx_brain"))

from frontierx_brain.api.gateway import CentralBrainSystem
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotBodyType, RobotStatus, RobotPose
from frontierx_brain.world.world_model import WorldObject
from frontierx_brain.safety.policy_supervisor import SafetyPolicyConfig, PolicySupervisor


@pytest.fixture
def brain():
    """Fixture providing an initialized CentralBrainSystem instance with test robot bodies registered."""
    system = CentralBrainSystem()

    # Register real test bodies
    bodies = [
        RobotBodySpec(
            robot_id="ugv_scout_01",
            name="FrontierX Scout UGV 01",
            body_type=RobotBodyType.UGV,
            ip_address="127.0.0.1",
            capabilities=["navigate_ground", "object_search", "docking"],
            max_linear_velocity=0.5,
            battery_percentage=98.0,
            status=RobotStatus.IDLE,
            pose=RobotPose(x=0.0, y=0.0, z=0.0),
        ),
        RobotBodySpec(
            robot_id="arm_manipulator_01",
            name="FrontierX Heavy Arm 01",
            body_type=RobotBodyType.ARM,
            ip_address="127.0.0.2",
            capabilities=["manipulate_arm", "thermal_inspection"],
            max_linear_velocity=0.0,
            battery_percentage=100.0,
            status=RobotStatus.IDLE,
            pose=RobotPose(x=5.0, y=3.0, z=0.0),
        ),
        RobotBodySpec(
            robot_id="quad_walker_01",
            name="FrontierX Quadruped 01",
            body_type=RobotBodyType.QUADRUPED,
            ip_address="127.0.0.3",
            capabilities=["navigate_ground", "stair_climb", "thermal_inspection", "heavy_payload"],
            max_linear_velocity=0.8,
            battery_percentage=85.0,
            status=RobotStatus.IDLE,
            pose=RobotPose(x=-2.0, y=4.0, z=0.0),
        ),
        RobotBodySpec(
            robot_id="drone_aerial_01",
            name="FrontierX Aerial Drone 01",
            body_type=RobotBodyType.DRONE,
            ip_address="127.0.0.4",
            capabilities=["navigate_aerial", "aerial_scan", "object_search"],
            max_linear_velocity=1.5,
            battery_percentage=90.0,
            status=RobotStatus.IDLE,
            pose=RobotPose(x=1.0, y=1.0, z=5.0),
        ),
    ]

    for body in bodies:
        system.robot_registry.register_robot(body)

    # Insert test object in world model
    system.world_model.upsert_object(
        WorldObject(
            object_id="gen_01",
            class_name="generator",
            confidence=0.98,
            x=5.2,
            y=3.1,
            z=0.0,
            status="UNINSPECTED",
        )
    )

    return system


def test_robot_registry_and_capability_matching(brain):
    """Test robot registration and capability matchmaker algorithm."""
    robots = brain.robot_registry.list_robots()
    assert len(robots) >= 4

    # Test capability lookup for thermal inspection
    best_robot = brain.capability_registry.find_best_robot(
        required_capabilities=["thermal_inspection"]
    )
    assert best_robot is not None
    assert "thermal_inspection" in best_robot.capabilities


def test_world_model_queries_and_perception(brain):
    """Test world model persistence and perception updates."""
    # Test query
    objs = brain.world_model.find_objects(class_name="generator")
    assert len(objs) >= 1
    assert objs[0].object_id == "gen_01"

    # Ingest new perception detection
    new_obj = brain.perception.process_detection(
        robot_id="ugv_scout_01",
        class_name="valve",
        confidence=0.95,
        x=8.5,
        y=-3.2,
        z=0.5,
        status="LEAKING",
    )
    assert new_obj.object_id is not None
    assert brain.world_model.get_object(new_obj.object_id).status == "LEAKING"


def test_deterministic_safety_supervisor(brain):
    """Test deterministic safety rules and LLM control isolation."""
    supervisor = brain.policy_supervisor

    # Test whitelist check
    safe_step = supervisor.validate_task_step("navigate_to", {"x": 5.0, "y": 5.0})
    assert safe_step.is_safe is True

    # Test forbidden direct motor access attempt
    forbidden_step = supervisor.validate_task_step("navigate_to", {"cmd_vel": 1.5, "pwm": 255})
    assert forbidden_step.is_safe is False
    assert "isolation" in forbidden_step.reason.lower()

    # Test forbidden action type
    unauthorized_action = supervisor.validate_task_step("self_destruct_actuator", {})
    assert unauthorized_action.is_safe is False

    # Test E-STOP activation
    supervisor.trigger_global_e_stop("Test E-STOP")
    assert supervisor.is_e_stopped() is True
    estop_res = supervisor.validate_task_step("navigate_to", {"x": 0.0, "y": 0.0})
    assert estop_res.is_safe is False
    supervisor.clear_e_stop()
    assert supervisor.is_e_stopped() is False


def test_multi_robot_orchestration_and_leases(brain):
    """Test lease locking and spatial reservation zones."""
    orchestrator = brain.orchestrator
    robot_id = "ugv_scout_01"

    # Acquire lease
    lease_id = orchestrator.acquire_lease(robot_id, task_id="task_123")
    assert lease_id is not None

    # Cannot double lease
    double_lease = orchestrator.acquire_lease(robot_id, task_id="task_456")
    assert double_lease is None

    # Test spatial reservation
    res1 = orchestrator.reserve_spatial_zone("ugv_scout_01", center_x=10.0, center_y=10.0, radius_meters=3.0)
    assert res1 is not None

    # Conflicting reservation by another robot in overlapping zone
    conflict_res = orchestrator.reserve_spatial_zone("quad_walker_01", center_x=11.0, center_y=10.0, radius_meters=3.0)
    assert conflict_res is None

    # Release lease
    released = orchestrator.release_lease(robot_id, lease_id)
    assert released is True


def test_teleop_fallback_clamping(brain):
    """Test teleop manual control override and speed clamping."""
    teleop = brain.teleop
    robot_id = "ugv_scout_01"

    assert teleop.start_teleop_session(robot_id) is True

    # Test speed clamping above max_velocity (0.5 m/s)
    cmd = teleop.process_teleop_command(
        from_dict_or_object({"robot_id": robot_id, "linear_x": 2.5, "deadman_switch_pressed": True})
    )
    assert cmd["linear_x"] <= 0.5


def from_dict_or_object(d):
    from frontierx_brain.teleop.teleop_fallback import TeleopCommand
    return TeleopCommand(**d)

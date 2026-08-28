"""
FrontierX Unit Tests — T06 & T18 Safety Supervisor & Teleop Fallback
=====================================================================
"""

from __future__ import annotations

import pytest
from frontierx_brain.core.schemas import RobotBodyType, Capability
from frontierx_brain.registry.robot_registry import RobotBodySpec
from frontierx_brain.safety.policy_supervisor import PolicySupervisor
from frontierx_brain.teleop.teleop_fallback import TeleoperationFallback, TeleopCommand
from frontierx_brain.api.gateway import CentralBrainSystem


def test_t06_policy_blocks_low_level() -> None:
    """T06: Policy safety supervisor blocks low-level control command attempts (cmd_vel, pwm)."""
    ps = PolicySupervisor()
    ugv = RobotBodySpec(
        robot_id="u1",
        name="U1",
        body_type=RobotBodyType.UGV,
        capabilities=[],
        max_linear_velocity=0.5,
    )
    # cmd_vel parameter attempt → blocked
    bad_step = {"task_type": "navigate_to", "params": {"cmd_vel": "true", "x": 1.0, "y": 2.0, "linear": 3.0}}
    r = ps.validate_task_step(task_type="navigate_to", params=bad_step, robot=ugv)
    assert not r.is_safe
    assert "unsafe parameter" in r.reason.lower() or "cmd_vel" in r.reason.lower()

    # PWM attempt in task_type → blocked
    r2 = ps.validate_task_step(task_type="send_pwm_cmd", params={}, robot=ugv)
    assert not r2.is_safe


def test_t18_teleop_clamping(brain_system: CentralBrainSystem) -> None:
    """T18: Teleoperation speed clamping rejects velocities exceeding limit."""
    brain_system.register_demo_robots_and_objects()
    ugv = brain_system.robot_registry.get_robot("ugv_scout_01")
    ugv.max_linear_velocity = 0.5
    cmd = TeleopCommand(
        robot_id="ugv_scout_01",
        operator="test",
        linear_velocity=2.0,  # way over max
        angular_velocity=3.0,
        deadman_held=True,
    )
    safe = brain_system.teleop.process_teleop_command(cmd)
    assert 0.0 <= safe.linear_velocity <= 0.501, f"Linear not clamped: {safe.linear_velocity}"

    # Global e-stop → command rejected
    brain_system.policy_supervisor.trigger_global_e_stop("test")
    cmd2 = TeleopCommand(
        robot_id="ugv_scout_01",
        operator="test",
        linear_velocity=0.1,
        angular_velocity=0.0,
        deadman_held=True,
    )
    with pytest.raises(Exception):
        brain_system.teleop.process_teleop_command(cmd2)

"""
FrontierX Integration Tests — T12-T13 End-to-End Demo 2 (Two-Body Coordination)
================================================================================
"""

from __future__ import annotations

import pytest
from frontierx_brain.ai.task_planner import TaskPlan
from frontierx_brain.api.gateway import CentralBrainSystem


@pytest.fixture
def seeded_brain() -> CentralBrainSystem:
    """Return a CentralBrainSystem with the 2 demo robots + 4 objects seeded."""
    brain = CentralBrainSystem(use_mock_llm=True)
    brain.register_demo_robots_and_objects()
    return brain


def test_t12_demo2_two_body_coordination(seeded_brain: CentralBrainSystem) -> None:
    """
    T12: Demo 2 e2e - two-body coordination with inspect (UGV) and arm_pick (ARM).
    Demonstrates "INTELLIGENCE IS NOT LOCKED TO THE BODY".
    """
    session, plan = seeded_brain.command_interface.process_command(
        "Inspect the generator and pick up the damaged component.", source="TEST"
    )
    assert plan is not None
    step_types = [s.task_type for s in plan.steps]
    for needed in ("inspect", "arm_pick", "report_status"):
        assert needed in step_types, (needed, step_types)

    results = seeded_brain.skill_engine.execute_plan(plan)
    step_map = {r.task_type: r for r in results}
    # Each step succeeded
    for tt, res in step_map.items():
        assert res.success, f"{tt} failed: {res.message}"
    # Thesis check: TWO different robot IDs in use
    robots_in_use = {r.robot_id for r in results if r.task_type in ("inspect", "arm_pick")}
    assert robots_in_use == {"ugv_scout_01", "arm_manipulator_01"}, (
        "Demo 2 thesis broken — both tasks should run on different bodies. "
        f"Got (task → robot_id): {{r.task_type: r.robot_id for r in results}}"
    )
    inspect_r = step_map["inspect"]
    assert inspect_r.robot_id == "ugv_scout_01"
    pick_r = step_map["arm_pick"]
    assert pick_r.robot_id == "arm_manipulator_01"
    # Damaged component should be HELD after arm_pick
    comp = seeded_brain.world_model.get_object("comp_damaged_01")
    assert comp is not None
    assert comp.status in ("HELD", "PLACED"), comp.status


def test_t13_inspect_standoff_check(seeded_brain: CentralBrainSystem) -> None:
    """T13: Standoff check - inspect from 4m fails; navigate then inspect succeeds."""
    # Place UGV at (0,0), inspect gen_01 at (10,2) → 10m away → fail standoff
    ugv = seeded_brain.robot_registry.get_robot("ugv_scout_01")
    ugv.pose.x = 0.0
    ugv.pose.y = 0.0
    plan = TaskPlan(
        natural_language="inspect generator from far",
        total_timeout_seconds=30.0,
        steps=[{
            "step_id": 0,
            "task_type": "inspect",
            "params": {"object_id": "gen_01", "inspection_mode": "VISUAL"},
            "description": "inspect from 10m away",
            "timeout_seconds": 15.0,
            "required_capabilities": ["capture_rgb", "visual_inspection"],
        }],
    )
    res = seeded_brain.skill_engine.execute_plan(plan)
    assert not res[0].success, res[0]
    assert "standoff" in res[0].message.lower() or "closer" in res[0].message.lower()

    # Now navigate near gen_01 first → inspect should succeed
    plan2 = TaskPlan(
        natural_language="navigate then inspect",
        total_timeout_seconds=120.0,
        steps=[
            {
                "step_id": 0,
                "task_type": "navigate_to",
                "params": {"x": 9.0, "y": 2.0, "yaw": 0.0},
                "required_capabilities": ["navigate_ground"],
                "description": "navigate near gen_01",
                "timeout_seconds": 30.0,
            },
            {
                "step_id": 1,
                "task_type": "inspect",
                "params": {"object_id": "gen_01"},
                "required_capabilities": ["capture_rgb", "visual_inspection"],
                "description": "inspect gen_01",
                "timeout_seconds": 20.0,
            },
        ],
    )
    res2 = seeded_brain.skill_engine.execute_plan(plan2)
    assert all(r.success for r in res2), [r.message for r in res2]

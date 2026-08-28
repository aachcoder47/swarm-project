"""
FrontierX Integration Tests — T10-T11 End-to-End Demo 1 (Single Body)
=====================================================================
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


def test_t10_demo1_find_generator_and_inspect(seeded_brain: CentralBrainSystem) -> None:
    """T10: Demo 1 e2e - single-body task execution of 'Find the generator and inspect it'."""
    session, plan = seeded_brain.command_interface.process_command(
        "Find the generator and inspect it.", source="TEST"
    )
    assert plan is not None, "Plan failed to generate"
    # At minimum: query_world + navigate + inspect + report steps
    step_types = [s.task_type for s in plan.steps]
    for needed in ("navigate_to", "inspect", "report_status"):
        assert needed in step_types, f"Missing step {needed}: {step_types}"

    # Execute the plan
    results = seeded_brain.skill_engine.execute_plan(plan)
    # All steps should be successful
    success_ids = [r.step_id for r in results if r.success]
    failed_msgs = [r.message for r in results if not r.success]
    assert all(r.success for r in results), (
        f"Failures: {failed_msgs}\nFull results: {[r.dict() for r in results]}"
    )

    # Inspect step: should use UGV (ugv_scout_01)
    inspect_steps = [r for r in results if r.task_type == "inspect"]
    assert len(inspect_steps) == 1
    assert inspect_steps[0].robot_id == "ugv_scout_01"
    # World model should mark gen_01 as inspected
    gen = seeded_brain.world_model.get_object("gen_01")
    assert gen is not None
    assert gen.status in ("INSPECTED", "DAMAGED", "ABNORMAL")
    # Inspection findings persisted in task memory
    report = seeded_brain.task_memory.generate_inspection_report(plan.plan_id)
    assert report is not None
    assert "status" in report
    assert report["status"] in ("COMPLETED", "IN_PROGRESS")


def test_t11_inspect_overheating_generator(seeded_brain: CentralBrainSystem) -> None:
    """T11: Inspection of gen_02 yields status DAMAGED and temperature > 70 C."""
    # Force inspect on gen_02 via explicit command
    session, plan = seeded_brain.command_interface.process_command(
        "Find the backup generator and inspect it for damage.", source="TEST"
    )
    # If the planner targets gen_01 by default, fall back: manually re-route inspect to gen_02
    if plan is None:
        pytest.fail("No plan generated")
    for step in plan.steps:
        if step.task_type in ("inspect", "analyze_observation"):
            step.params["object_id"] = "gen_02"
        if step.task_type == "navigate_to":
            step.params["x"] = 9.0
            step.params["y"] = -2.0  # near gen_02

    results = seeded_brain.skill_engine.execute_plan(plan)
    inspect_res = [r for r in results if r.task_type == "inspect"]
    if not inspect_res:
        pytest.fail(f"No inspect step executed, results: {[r.task_type for r in results]}")
    data = inspect_res[0].output_data
    # Temperature from overheating generator is always >= 87°C (62 base + 25 overheat)
    assert "temperature_c" in data, data
    assert data["temperature_c"] >= 70.0, f"gen_02 expected hot, got {data}"
    assert data["object_status"] in ("DAMAGED", "ABNORMAL"), data

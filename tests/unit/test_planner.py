"""
FrontierX Unit Tests — T05, T07, T08 Task Planner, Validator, and Gateway Invariants
=====================================================================================
"""

from __future__ import annotations

import json
import pytest
from frontierx_brain.ai.task_planner import TaskPlan
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotRegistry
from frontierx_brain.registry.skill_registry import SkillRegistry
from frontierx_brain.safety.policy_supervisor import PolicySupervisor
from frontierx_brain.executor.plan_validator import PlanValidator
from frontierx_brain.ai.llm_provider import MockLLMProvider
from frontierx_brain.api.gateway import CentralBrainSystem


def test_t05_plan_validator() -> None:
    """T05: PlanValidator validates correct plans, rejects invalid task types, and warns if no robots exist."""
    reg = RobotRegistry()
    sr = SkillRegistry(robot_registry=reg)
    ps = PolicySupervisor()
    pv = PlanValidator(sr, reg, ps)

    # Valid 2-step plan, but robot registry empty → warning + valid
    plan_ok = TaskPlan(
        natural_language="test plan",
        steps=[
            {
                "step_id": 0,
                "task_type": "navigate_to",
                "params": {"x": 5.0, "y": 0.0},
                "required_capabilities": ["navigate_ground"],
                "description": "move",
                "timeout_seconds": 10.0,
            },
            {
                "step_id": 1,
                "task_type": "inspect",
                "params": {"object_id": "gen_01"},
                "required_capabilities": ["capture_rgb"],
                "description": "inspect",
                "timeout_seconds": 10.0,
            },
        ],
        total_timeout_seconds=60.0,
    )
    res = pv.validate(plan_ok)
    assert res.is_valid, res.errors  # warning but valid
    assert len(res.warnings) >= 1  # no robots registered yet

    # Invalid plan: unknown task_type
    plan_bad = TaskPlan(
        natural_language="bad plan",
        steps=[{
            "step_id": 0,
            "task_type": "definitely_not_a_skill",
            "params": {},
            "required_capabilities": [],
            "description": "x",
            "timeout_seconds": 10.0,
        }],
        total_timeout_seconds=60.0,
    )
    res2 = pv.validate(plan_bad)
    assert not res2.is_valid
    assert any("definitely_not_a_skill" in e for e in res2.errors)


def test_t07_mock_llm_producer() -> None:
    """T07: MockLLMProvider parses prompt and produces a task plan containing correct steps."""
    provider = MockLLMProvider()
    prompt = (
        "You are a planner. User Request: 'Find the generator and inspect it.'\n"
        "Current World Objects: [{\"object_id\":\"gen_01\"}]"
    )
    resp = provider.generate("", prompt)
    plan_json = json.loads(resp.raw_text)
    assert "steps" in plan_json
    step_types = [s["task_type"] for s in plan_json["steps"]]
    # find and inspect → expect query_world, find_object, navigate_to, inspect, analyze_observation, report_status
    for required in ("query_world", "navigate_to", "inspect", "report_status"):
        assert required in step_types, (required, step_types)
    assert len(plan_json["steps"]) >= 5


def test_t08_brain_command_interface_always_initialized() -> None:
    """T08: CentralBrainSystem invariant ensures CommandInterface and dependencies are never None."""
    brain = CentralBrainSystem(use_mock_llm=True)
    brain.register_demo_robots_and_objects()
    assert brain.command_interface is not None
    assert brain.task_planner is not None
    assert brain.skill_registry is not None
    assert brain.plan_validator is not None
    assert len(brain.skill_registry.all_skill_ids()) == 13
    assert len(brain.robot_registry.list_robots()) == 2
    assert len(brain.world_model.get_all_objects()) >= 4


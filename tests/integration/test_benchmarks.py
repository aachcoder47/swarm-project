"""
FrontierX Integration Tests — T17 Benchmarks
=============================================
"""

from __future__ import annotations

import time
import pytest
from frontierx_brain.ai.task_planner import TaskPlan
from frontierx_brain.api.gateway import CentralBrainSystem


@pytest.fixture
def seeded_brain() -> CentralBrainSystem:
    """Return a CentralBrainSystem with the 2 demo robots + 4 objects seeded."""
    brain = CentralBrainSystem(use_mock_llm=True)
    brain.register_demo_robots_and_objects()
    return brain


def test_t17_benchmarks(seeded_brain: CentralBrainSystem) -> None:
    """T17: Benchmark planning latency, validation latency, and step execution speed."""
    N = 25
    # Plan latency
    t0 = time.perf_counter()
    plans = []
    for _ in range(N):
        _, p = seeded_brain.command_interface.process_command(
            "Find the generator and inspect it.", source="BENCH"
        )
        plans.append(p)
    t_plan = (time.perf_counter() - t0) / N
    assert all(p is not None for p in plans)
    assert t_plan < 1.0, f"Avg plan latency {t_plan*1000:.1f}ms > 1000ms"  # generous (rule-based planner is fast)

    # Pre-validation latency
    pv = seeded_brain.plan_validator
    t0 = time.perf_counter()
    for p in plans:
        pv.validate(p)
    t_val = (time.perf_counter() - t0) / N
    assert t_val < 0.5, f"Plan validation {t_val*1000:.1f}ms > 500ms"

    # Step exec: query_world (very fast)
    plan_q = TaskPlan(
        natural_language="q",
        total_timeout_seconds=10.0,
        steps=[{"step_id": 0, "task_type": "query_world",
                "params": {"class_name": "generator"},
                "required_capabilities": [], "description": "q", "timeout_seconds": 5.0}],
    )
    t0 = time.perf_counter()
    for _ in range(N):
        seeded_brain.skill_engine.execute_plan(plan_q)
    t_step = (time.perf_counter() - t0) / N
    assert t_step < 5.0, f"Step exec avg {t_step*1000:.0f}ms > 5000ms (generous)"
    print(f"\nBENCHMARKS (n={N}):")
    print(f"  plan_latency_avg:       {t_plan*1000:6.1f} ms")
    print(f"  pre_validation_avg:    {t_val*1000:6.1f} ms")
    print(f"  step_exec_query_avg:   {t_step*1000:6.1f} ms")

"""
FrontierX Integration Tests — T14, T15, T16 Safety & Network Resilience
======================================================================
"""

from __future__ import annotations

import time
from typing import Generator
import pytest
from frontierx_brain.ai.task_planner import TaskPlan
from frontierx_brain.api.gateway import CentralBrainSystem
from frontierx_brain.sim.simulation_bridge import SimulationBridge


@pytest.fixture
def seeded_brain() -> CentralBrainSystem:
    """Return a CentralBrainSystem with the 2 demo robots + 4 objects seeded."""
    brain = CentralBrainSystem(use_mock_llm=True)
    brain.register_demo_robots_and_objects()
    return brain


@pytest.fixture
def sim_bridge() -> Generator[SimulationBridge, None, None]:
    sim = SimulationBridge(use_gazebo_ros2=False)
    sim.seed_demo_factory()
    sim.start()
    yield sim
    sim.stop()


def test_t14_t15_network_failure_safe_state_and_recovery(sim_bridge: SimulationBridge) -> None:
    """T14 & T15: Network disconnect triggers UGV safe state; network restoration clears it."""
    sim = sim_bridge.python_sim
    ugv = sim.robots["ugv_scout_01"]
    # Give it some non-zero velocity (as if navigating)
    ugv.v = 0.6
    ugv.w = 0.1
    # Confirm not in safe state
    assert not ugv.safe_state
    assert sim_bridge.python_sim._last_brain_heartbeat_at > 0.0

    # Simulate network disconnect → deadman fires
    affected = sim_bridge.simulate_network_disconnect(1.0)
    assert "ugv_scout_01" in affected, (
        f"UGV should have entered safe state after disconnect. Affected={affected}"
    )
    assert ugv.safe_state
    assert ugv.v == 0.0 and ugv.w == 0.0  # SAFE STATE: zeroed velocities

    # T15 — Recovery: heartbeat restored → safe state clears
    sim_bridge.restore_network()
    time.sleep(0.05)
    sim_bridge.python_sim.publish_brain_heartbeat()
    sim_bridge.python_sim.check_deadman_safe_state()
    assert not ugv.safe_state, "UGV should exit safe state after heartbeat restored"


def test_t16_arm_pick_retries(seeded_brain: CentralBrainSystem) -> None:
    """T16: arm_pick retries when target repositioned within reach."""
    # Place damaged component far from arm → attempt 1 fails
    comp = seeded_brain.world_model.get_object("comp_damaged_01")
    comp.x = -5.0
    comp.y = -5.0  # 3m away from arm pedestal (-2,-6)
    seeded_brain.world_model.upsert_object(comp)

    plan = TaskPlan(
        natural_language="pick broken component",
        total_timeout_seconds=30.0,
        steps=[{
            "step_id": 0,
            "task_type": "arm_pick",
            "params": {"object_id": "comp_damaged_01"},
            "required_capabilities": ["manipulate_arm", "grasp"],
            "description": "pick",
            "timeout_seconds": 10.0,
        }],
    )
    res0 = seeded_brain.skill_engine.execute_plan(plan)
    # Retry max for arm_pick is 2; we have 1 robot → should fail (no robot to retry)
    assert not res0[0].success

    # Reposition the object within reach
    comp.x = -2.0
    comp.y = -5.5
    comp.z = 0.0
    seeded_brain.world_model.upsert_object(comp)
    res1 = seeded_brain.skill_engine.execute_plan(plan)
    assert res1[0].success, res1[0].message

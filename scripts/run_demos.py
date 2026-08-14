"""
FrontierX Demo Runner
=======================
Runs both product demos end-to-end, then prints a summary suitable for
capturing as demo proof. Uses SimulationBridge (pure-python physics,
no Gazebo/ROS2 required) OR Gazebo Sim (when FRONTIERX_USE_GAZEBO=1 is set).

Demos:
  DEMO 1 — Single Body:
    Command:  "Find the generator and inspect it."
    Thesis:   Central intelligence selects UGV (only body with inspection +
              navigate capabilities), navigates to generator, inspects it,
              produces a structured report with real temperature readings,
              distance, sensor_fusion_type, findings.

  DEMO 2 — Two-Body Coordination:
    Command:  "Inspect the generator and pick up the damaged component."
    Thesis:   The intelligence is NOT locked to one body. The inspect step
              executes on ugv_scout_01 while the arm_pick step executes on
              arm_manipulator_01. Bodies are interchangeable — the same
              central brain plans and coordinates for both.

Output: prints structured results then exits 0 on success.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict

# Force UTF-8 stdout/stderr so unicode arrows render on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(THIS_DIR, "..", "src", "frontierx_brain"))
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from frontierx_brain.api.gateway import CentralBrainSystem
from frontierx_brain.sim.simulation_bridge import SimulationBridge


SEPARATOR = "=" * 78


def _print_section(title: str) -> None:
    print()
    print(SEPARATOR)
    print(f"  {title}")
    print(SEPARATOR)


def run_demo1(brain: CentralBrainSystem) -> Dict[str, Any]:
    _print_section("DEMO 1 — SINGLE BODY: 'Find the generator and inspect it.'")

    # Step 1: User submits command
    user_command = "Find the generator and inspect it."
    print(f"\n[1] User command: '{user_command}'")

    # Step 2: Plan generation
    session, plan = brain.command_interface.process_command(user_command, source="DEMO1")
    assert plan is not None, "Failed to generate plan"
    step_types = [s.task_type for s in plan.steps]
    print(f"[2] AI TaskPlanner produced a plan with {len(plan.steps)} steps:")
    for s in plan.steps:
        print(f"    Step {s.step_id:>2d}  {s.task_type:<22s}  {s.description}")

    # Step 3: Show capable robots
    inspect_candidates = brain.skill_registry.find_robots_for_skill("inspect")
    print(f"\n[3] Capability matchmaker selects inspect-capable bodies: "
          f"{[r.robot_id for r in inspect_candidates]}")

    # Step 4: Validate plan
    val = brain.plan_validator.validate(plan)
    print(f"[4] PlanValidator: VALID={val.is_valid}  ({len(val.errors)} errors, {len(val.warnings)} warnings)")

    # Step 5: Execute
    print(f"\n[5] Executing plan {plan.plan_id[:8]}...")
    t0 = time.perf_counter()
    results = brain.skill_engine.execute_plan(plan)
    elapsed = time.perf_counter() - t0

    # Step 6: Report per-step results
    print(f"\n[6] Execution completed in {elapsed*1000:.1f} ms. Step-by-step results:")
    step_info: Dict[str, Any] = {}
    for r in results:
        tag = "OK" if r.success else "FAIL"
        print(f"    Step {r.step_id:>2d} [{tag}] {r.task_type:<22s} robot={r.robot_id:<18s} msg={r.message[:60]}")
        step_info[r.task_type] = {"robot": r.robot_id, "success": r.success, "data": r.output_data}

    # Step 7: Inspection findings
    insp = step_info.get("inspect", {})
    insp_data = insp.get("data", {})
    gen01 = brain.world_model.get_object("gen_01")
    print(f"\n[7] World Model update — gen_01.status = {gen01.status if gen01 else None}")
    print(f"    Latest inspection: temperature_c={insp_data.get('temperature_c')}  "
          f"distance_m={insp_data.get('distance_m')}  "
          f"sensor={insp_data.get('sensor_type')}")
    if insp_data.get("findings"):
        for f in insp_data["findings"]:
            print(f"    Finding: {f}")

    # Step 8: Formal report
    report = brain.task_memory.generate_inspection_report(plan.plan_id)
    print(f"\n[8] Final mission report: status={report.get('status')}  "
          f"total_findings={report.get('total_findings')}")

    # Thesis check: inspect ran on ugv_scout_01
    assert insp.get("robot") == "ugv_scout_01", (
        f"Demo1 thesis broken: inspect should run on ugv_scout_01, got {insp}"
    )
    assert all(r.success for r in results), "Demo1 had step failures"
    return {
        "demo": 1,
        "command": user_command,
        "plan_steps": step_types,
        "all_successful": all(r.success for r in results),
        "inspect_robot": insp.get("robot"),
        "gen01_status": gen01.status if gen01 else None,
        "inspection_temp_c": insp_data.get("temperature_c"),
        "total_findings": report.get("total_findings"),
        "elapsed_ms": round(elapsed * 1000, 1),
    }


def run_demo2(brain: CentralBrainSystem) -> Dict[str, Any]:
    _print_section("DEMO 2 — TWO-BODY COORDINATION: 'Inspect the generator and pick up the damaged component.'")

    user_command = "Inspect the generator and pick up the damaged component."
    print(f"\n[1] User command: '{user_command}'")

    session, plan = brain.command_interface.process_command(user_command, source="DEMO2")
    assert plan is not None
    step_types = [s.task_type for s in plan.steps]
    assert "inspect" in step_types and "arm_pick" in step_types, f"Missing steps: {step_types}"
    print(f"[2] Plan produced ({len(plan.steps)} steps): {step_types}")

    print(f"\n[3] Per-step body-type constraints:")
    insp_candidates = brain.skill_registry.find_robots_for_skill("inspect")
    pick_candidates = brain.skill_registry.find_robots_for_skill("arm_pick")
    print(f"    inspect  compatible: {[r.robot_id for r in insp_candidates]}")
    print(f"    arm_pick compatible: {[r.robot_id for r in pick_candidates]}")

    t0 = time.perf_counter()
    results = brain.skill_engine.execute_plan(plan)
    elapsed = time.perf_counter() - t0
    step_info = {r.task_type: r for r in results}

    print(f"\n[4] Execution ({elapsed*1000:.1f} ms):")
    for r in results:
        tag = "OK" if r.success else "FAIL"
        print(f"    Step {r.step_id:>2d} [{tag}] {r.task_type:<22s} robot={r.robot_id}")

    # THESES CHECKS: different bodies, both success
    inspect_r = step_info.get("inspect")
    pick_r = step_info.get("arm_pick")
    assert inspect_r is not None and pick_r is not None, (
        f"Missing steps: {list(step_info.keys())}"
    )
    assert inspect_r.robot_id != pick_r.robot_id, (
        f"DEMO 2 THESIS BROKEN: inspect and arm_pick both ran on {inspect_r.robot_id}."
    )
    assert inspect_r.robot_id == "ugv_scout_01", inspect_r
    assert pick_r.robot_id == "arm_manipulator_01", pick_r
    assert inspect_r.success, f"inspect failed: {inspect_r.message}"
    assert pick_r.success, f"arm_pick failed: {pick_r.message}"

    comp = brain.world_model.get_object("comp_damaged_01")
    gen02 = brain.world_model.get_object("gen_02") or brain.world_model.get_object("gen_01")
    report = brain.task_memory.generate_inspection_report(plan.plan_id)

    print(f"\n[5] Thesis proven:")
    print(f"    inspect  ran on {inspect_r.robot_id} (UGV)        → success={inspect_r.success}")
    print(f"    arm_pick ran on {pick_r.robot_id} (ROBOTIC ARM)  → success={pick_r.success}")
    print(f"    → INTELLIGENCE IS NOT LOCKED TO THE BODY.")
    print(f"    comp_damaged_01 status = {comp.status if comp else 'MISSING'}")
    print(f"    final mission report status = {report.get('status')}")

    return {
        "demo": 2,
        "command": user_command,
        "plan_steps": step_types,
        "inspect_robot": inspect_r.robot_id,
        "arm_pick_robot": pick_r.robot_id,
        "different_bodies_used": inspect_r.robot_id != pick_r.robot_id,
        "all_successful": all(r.success for r in results),
        "component_status": comp.status if comp else None,
        "elapsed_ms": round(elapsed * 1000, 1),
    }


def main() -> int:
    use_gazebo = os.environ.get("FRONTIERX_USE_GAZEBO") == "1"
    sim_bridge: SimulationBridge | None = None
    dispatch_cb = None

    if use_gazebo:
        print("FRONTIERX_USE_GAZEBO=1 → attempting Gazebo/ROS2 bridge.")
        from frontierx_brain.ros.ros2_bridge import ROS2MultiRobotBridge
        from frontierx_brain.monitor.state_monitor import RobotStateMonitor
        from frontierx_brain.registry.robot_registry import RobotRegistry
        rr = RobotRegistry()
        mon = RobotStateMonitor(rr)
        ros_bridge = ROS2MultiRobotBridge(mon)
        ros_bridge.start_bridge()
        dispatch_cb = ros_bridge.dispatch_skill_to_body
    else:
        print("Using pure-Python SimulationBridge physics.  (Set FRONTIERX_USE_GAZEBO=1 to use Gazebo Sim.)")
        sim_bridge = SimulationBridge(use_gazebo_ros2=False)
        sim_bridge.seed_demo_factory()
        sim_bridge.start()
        dispatch_cb = sim_bridge.dispatch_skill

    brain = CentralBrainSystem(use_mock_llm=True, skill_dispatch_callback=dispatch_cb)
    brain.register_demo_robots_and_objects()
    # Sync sim state → registry pose/battery
    if sim_bridge:
        for r in brain.robot_registry.list_robots():
            spr = sim_bridge.python_sim.robots.get(r.robot_id)
            if spr:
                spr.x, spr.y, spr.yaw = r.pose.x, r.pose.y, r.pose.yaw
                spr.battery = r.battery_percentage

    try:
        r1 = run_demo1(brain)
        print()
        r2 = run_demo2(brain)

        _print_section("SUMMARY")
        print(json.dumps({"demo1": r1, "demo2": r2}, indent=2, default=str))
        assert r1["all_successful"]
        assert r2["all_successful"]
        assert r2["different_bodies_used"]
        print()
        print("✅  Both demos passed.")
        print("   Product thesis proven: ONE CENTRAL INTELLIGENCE coordinates MANY HETEROGENEOUS BODIES.")
        return 0
    finally:
        if sim_bridge:
            sim_bridge.stop()


if __name__ == "__main__":
    sys.exit(main())

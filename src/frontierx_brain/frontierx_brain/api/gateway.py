"""
Component 18 & 1: API Gateway & FastAPI Server (Production Mode)
===============================================================
Central web API gateway unifying REST endpoints and WebSockets for real-time dashboard interaction,
telemetry streaming, task submission, safety control, and world model queries.

Always-on: CommandInterface and TaskPlanner never None.
Deterministic rule-based planner used if no OpenAI/Ollama backend available
(no mock data — just rule-based intent parsing → canonical skill plans).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from frontierx_brain.ai.command_interface import CommandInterface
from frontierx_brain.ai.llm_provider import get_llm_provider
from frontierx_brain.ai.task_planner import TaskPlanner
from frontierx_brain.executor.skill_engine import SkillExecutionEngine
from frontierx_brain.executor.plan_validator import PlanValidator
from frontierx_brain.memory.task_memory import TaskMemory
from frontierx_brain.monitor.state_monitor import RobotStateMonitor
from frontierx_brain.orchestrator.multi_robot_orchestrator import MultiRobotOrchestrator
from frontierx_brain.perception.perception_interface import PerceptionInterface
from frontierx_brain.registry.capability_registry import CapabilityRegistry
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotRegistry, RobotStatus
from frontierx_brain.registry.skill_registry import SkillRegistry
from frontierx_brain.ros.ros2_bridge import ROS2MultiRobotBridge
from frontierx_brain.safety.policy_supervisor import PolicySupervisor
from frontierx_brain.sensors.sensor_pipeline import SensorDataPipeline
from frontierx_brain.sim.simulation_interface import SimulationInterface
from frontierx_brain.teleop.teleop_fallback import TeleoperationFallback, TeleopCommand
from frontierx_brain.world.world_model import WorldModel, WorldObject
from frontierx_brain.observability.observability import brain_logger


class CommandRequest(BaseModel):
    command: str
    source: str = "WEB_DASHBOARD"
    preferred_robot_id: Optional[str] = None


class CentralBrainSystem:
    """Master orchestrator class assembling all 18+ Central Brain components.

    Initialization order:
      1. State stores: WorldModel, TaskMemory, RobotRegistry
      2. Policy/Supervisors: PolicySupervisor, CapabilityRegistry, SkillRegistry
      3. Orchestrators: MultiRobotOrchestrator, PlanValidator
      4. AI: LLM provider (always-available fallback) → TaskPlanner → CommandInterface
      5. I/O: Monitor, Perception, Sensors, Sim/ROS, Teleop
      6. SkillExecutionEngine (ties them all together)
    """

    def __init__(
        self,
        use_mock_llm: Optional[bool] = None,
        skill_dispatch_callback: Optional[Any] = None,
    ) -> None:
        # 1. Core state stores
        self.world_model = WorldModel()
        self.task_memory = TaskMemory()
        self.robot_registry = RobotRegistry()

        # 2. Registries + policy
        self.capability_registry = CapabilityRegistry(self.robot_registry)
        self.policy_supervisor = PolicySupervisor()
        # SkillRegistry is new — wraps canonical skill definitions (single source of truth)
        self.skill_registry = SkillRegistry(robot_registry=self.robot_registry)

        # 3. Orchestration / validation
        self.orchestrator = MultiRobotOrchestrator(self.robot_registry)
        self.plan_validator = PlanValidator(
            skill_registry=self.skill_registry,
            robot_registry=self.robot_registry,
            policy_supervisor=self.policy_supervisor,
        )
        self.state_monitor = RobotStateMonitor(self.robot_registry)

        # 4. Perception / sensors
        self.perception = PerceptionInterface(self.world_model)
        self.sensor_pipeline = SensorDataPipeline()

        # 5. Simulation / ROS2 bridge
        self.sim_interface = SimulationInterface(self.robot_registry)
        self.teleop = TeleoperationFallback(self.robot_registry, self.policy_supervisor)
        self.ros_bridge = ROS2MultiRobotBridge(self.state_monitor)

        # 6. AI: always initialize (never None — fixes B3/B4)
        #    If env or caller forces mock, use the deterministic rule-based planner.
        #    Else fall back through OpenAI → Ollama → deterministic rule-based.
        preferred = "mock" if use_mock_llm else "auto"
        try:
            llm_provider = get_llm_provider(preferred)
        except Exception as e:
            brain_logger.warning(f"LLM provider init failed, forcing deterministic planner: {e}")
            llm_provider = get_llm_provider("mock")

        self.task_planner = TaskPlanner(
            world_model=self.world_model,
            llm_provider=llm_provider,
            skill_registry=self.skill_registry,
            capability_registry=self.capability_registry,
        )
        self.command_interface = CommandInterface(self.task_planner)
        assert self.command_interface is not None, "CommandInterface initialization invariant failed."

        # 7. Skill execution engine — dispatches to callback OR internal handlers.
        #    If user passes a custom skill_dispatch_callback use that (tests/simulation),
        #    otherwise default to ROS2 bridge dispatch.
        dispatch_cb = skill_dispatch_callback
        if dispatch_cb is None:
            dispatch_cb = self.ros_bridge.dispatch_skill_to_body
        self.skill_engine = SkillExecutionEngine(
            robot_registry=self.robot_registry,
            capability_registry=self.capability_registry,
            skill_registry=self.skill_registry,
            orchestrator=self.orchestrator,
            policy_supervisor=self.policy_supervisor,
            plan_validator=self.plan_validator,
            task_memory=self.task_memory,
            world_model=self.world_model,
            skill_dispatch_callback=dispatch_cb,
        )

        # Start ROS 2 DDS Multi-Robot Bridge (graceful fallback if ROS2 not installed)
        self.ros_bridge.start_bridge()
        brain_logger.info(
            "Central Brain System initialized in Production Mode "
            f"(LLM={type(llm_provider).__name__}, robots={len(self.robot_registry.list_robots())})."
        )

    # ── Convenience helpers ────────────────────────────────────────────────
    def register_demo_robots_and_objects(self) -> None:
        """Seed the canonical demo factory: 1 UGV + 1 RoboticArm + generator + damaged_component."""
        from frontierx_brain.core.schemas import RobotBodyType, Capability

        # 1. Wheeled Scout UGV: navigation + visual inspection
        self.robot_registry.register_robot(RobotBodySpec(
            robot_id="ugv_scout_01",
            name="Scout UGV 01",
            body_type=RobotBodyType.UGV,
            ip_address="10.0.0.10",
            capabilities=[
                Capability.NAVIGATE_GROUND.value,
                Capability.OBJECT_SEARCH.value,
                Capability.CAPTURE_RGB.value,
                Capability.CAPTURE_DEPTH.value,
                Capability.VISUAL_INSPECTION.value,
                Capability.THERMAL_INSPECTION.value,
                Capability.LIDAR_3D.value,
            ],
            max_linear_velocity=1.0,
            max_payload_kg=5.0,
            battery_percentage=94.0,
            status=RobotStatus.IDLE,
        ))

        # 2. Robotic Arm (fixed pedestal near workbench): manipulation only
        self.robot_registry.register_robot(RobotBodySpec(
            robot_id="arm_manipulator_01",
            name="Arm Manipulator 01",
            body_type=RobotBodyType.ARM,
            ip_address="10.0.0.20",
            capabilities=[
                Capability.MANIPULATE_ARM.value,
                Capability.GRASP.value,
                Capability.CAPTURE_RGB.value,
                Capability.VISUAL_INSPECTION.value,
            ],
            max_linear_velocity=0.0,
            max_payload_kg=3.0,
            battery_percentage=100.0,  # Mains-powered pedestal arm
            status=RobotStatus.IDLE,
            # Fixed pedestal at (x=-2, y=-6) in Gazebo world near workbench
            pose={"x": -2.0, "y": -6.0, "z": 0.0, "yaw": 1.57},
        ))

        # 3. Factory objects in world model: Generator + damaged component
        self.world_model.upsert_object(WorldObject(
            object_id="gen_01",
            class_name="generator",
            name="Main Diesel Generator #1",
            x=10.0, y=2.0, z=0.0,
            confidence=0.95,
            status="UNINSPECTED",
            metadata={
                "manufacturer": "Caterpillar",
                "model": "3512E",
                "rated_power_kw": 1000,
                "overheating": False,
                "damaged": False,
                "temperature_c_ambient": 24.0,
                "workbench_x": -2.0, "workbench_y": -5.0,
            },
        ))
        # A second, damaged generator for richer scenarios:
        self.world_model.upsert_object(WorldObject(
            object_id="gen_02",
            class_name="generator",
            name="Backup Generator #2",
            x=10.0, y=-2.0, z=0.0,
            confidence=0.95,
            status="UNINSPECTED",
            metadata={
                "manufacturer": "Cummins",
                "model": "QSK78",
                "overheating": True,    # hot! → will trigger inspection anomaly
                "damaged": True,        # has cracks visible
                "temperature_c_ambient": 25.0,
                "workbench_x": -2.0, "workbench_y": -5.0,
            },
        ))
        # Damaged component to be picked up by the arm in Demo 2
        self.world_model.upsert_object(WorldObject(
            object_id="comp_damaged_01",
            class_name="damaged_component",
            name="Broken Shaft — Generator",
            x=-2.0, y=-4.5, z=0.0,       # on the workbench, within Arm 01 reach
            confidence=0.98,
            status="WAITING_REMOVAL",
            metadata={
                "mass_kg": 1.2,
                "origin_object_id": "gen_02",
                "warm": True,               # recently removed from hot generator
                "target_discard_pose": {"x": -8.0, "y": -8.0, "z": 0.0},
            },
        ))
        # Charging dock
        self.world_model.upsert_object(WorldObject(
            object_id="dock_01",
            class_name="charging_dock",
            name="Charging Dock A",
            x=-10.0, y=0.0, z=0.0,
            confidence=1.0,
            status="AVAILABLE",
        ))
        brain_logger.info(
            f"Demo factory seeded: {len(self.robot_registry.list_robots())} robots, "
            f"{len(self.world_model.get_all_objects())} world objects."
        )


def create_app() -> Any:
    """Factory creating FastAPI server app."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI is not installed in current Python environment.")

    brain = CentralBrainSystem()
    brain.register_demo_robots_and_objects()

    app = FastAPI(
        title="FrontierX Central AI Brain Platform",
        description="Unified Centralized AI Brain & Multi-Robot Orchestration API (Production Mode)",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── REST ENDPOINTS ───────────────────────────────────────

    @app.get("/")
    def root():
        return {
            "platform": "FrontierX Central AI Brain",
            "version": "0.2.0",
            "status": "OPERATIONAL",
            "active_robots": len(brain.robot_registry.list_robots()),
            "tracked_world_objects": len(brain.world_model.get_all_objects()),
            "e_stop_status": brain.policy_supervisor.is_e_stopped(),
            "llm_provider": type(brain.task_planner.llm_provider).__name__,
            "skill_count": len(brain.skill_registry.all_skill_ids()),
        }

    @app.post("/api/v1/command")
    def submit_command(req: CommandRequest):
        # command_interface is NEVER None (see CentralBrainSystem init invariant)
        session, plan = brain.command_interface.process_command(req.command, source=req.source)
        if not plan:
            raise HTTPException(status_code=400, detail="Failed to generate a valid task plan.")
        plan_id = plan.plan_id

        # Optional: run plan validation BEFORE execution to surface errors to user
        val = brain.plan_validator.validate(plan)
        if not val.is_valid:
            return {
                "session_id": session.session_id,
                "plan_id": plan_id,
                "reasoning": plan.reasoning,
                "steps": [s.model_dump() for s in plan.steps],
                "validation": val.model_dump(),
                "execution_results": [],
                "inspection_report": None,
                "error": f"Plan rejected before execution: {val.errors}",
            }

        results = brain.skill_engine.execute_plan(plan, preferred_robot_id=req.preferred_robot_id)
        report = brain.task_memory.generate_inspection_report(plan_id)

        # Post-step: update world objects from gen_02 inspection → damage → flag for arm Demo2
        all_succ = all(r.success for r in results)
        return {
            "session_id": session.session_id,
            "plan_id": plan_id,
            "reasoning": plan.reasoning,
            "validation": val.model_dump(),
            "steps": [s.model_dump() for s in plan.steps],
            "execution_results": [r.model_dump() for r in results],
            "all_steps_successful": all_succ,
            "inspection_report": report,
        }

    @app.post("/api/v1/robots/register")
    def register_robot(robot_spec: RobotBodySpec):
        reg = brain.robot_registry.register_robot(robot_spec)
        return reg.model_dump()

    @app.get("/api/v1/robots")
    def list_robots():
        brain.state_monitor.check_health_watchdogs()
        return [r.model_dump() for r in brain.robot_registry.list_robots()]

    @app.get("/api/v1/robots/capable")
    def list_robots_capable(task_type: str, target_x: Optional[float] = None, target_y: Optional[float] = None):
        candidates = brain.skill_registry.find_robots_for_skill(
            task_type, target_x=target_x, target_y=target_y,
        )
        return [r.model_dump() for r in candidates]

    @app.post("/api/v1/world/object")
    def add_world_object(obj: WorldObject):
        saved = brain.world_model.upsert_object(obj)
        return saved.model_dump()

    @app.get("/api/v1/world")
    def get_world_model():
        return [o.model_dump() for o in brain.world_model.get_all_objects()]

    @app.get("/api/v1/world/find")
    def find_world_objects(class_name: Optional[str] = None, status: Optional[str] = None):
        return [o.model_dump() for o in brain.world_model.find_objects(class_name=class_name, status=status)]

    @app.get("/api/v1/skills")
    def list_skills():
        return [s.model_dump() for s in brain.skill_registry.all_definitions()]

    @app.get("/api/v1/tasks")
    def get_task_history():
        return [t.model_dump() for t in brain.task_memory.get_all_tasks()]

    @app.get("/api/v1/tasks/{task_id}/report")
    def get_task_report(task_id: str):
        return brain.task_memory.generate_inspection_report(task_id)

    @app.post("/api/v1/safety/e_stop")
    def trigger_e_stop(reason: str = Query("Emergency Stop Button pressed from Web UI")):
        brain.policy_supervisor.trigger_global_e_stop(reason)
        return {"status": "E_STOP_ACTIVATED", "reason": reason}

    @app.post("/api/v1/safety/clear_e_stop")
    def clear_e_stop():
        brain.policy_supervisor.clear_e_stop()
        return {"status": "E_STOP_CLEARED"}

    @app.get("/api/v1/metrics")
    def get_metrics():
        return brain_logger.get_metrics()

    @app.get("/api/v1/logs")
    def get_logs(limit: int = Query(50)):
        return brain_logger.get_recent_logs(limit)

    @app.post("/api/v1/teleop/command")
    def teleop_command(cmd: TeleopCommand):
        safe_cmd = brain.teleop.process_teleop_command(cmd)
        return {"robot_id": cmd.robot_id, "command_sent": safe_cmd}

    # ── WEBSOCKET REALTIME FEED ──────────────────────────────

    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                robots = [r.model_dump() for r in brain.robot_registry.list_robots()]
                world = [o.model_dump() for o in brain.world_model.get_all_objects()]
                metrics = brain_logger.get_metrics()
                tasks = [t.model_dump() for t in brain.task_memory.get_all_tasks()[-20:]]
                payload = {
                    "timestamp": time.time(),
                    "robots": robots,
                    "world_objects": world,
                    "metrics": metrics,
                    "e_stop": brain.policy_supervisor.is_e_stopped(),
                    "recent_tasks": tasks,
                }
                await websocket.send_json(payload)
                await asyncio.sleep(0.5)
        except WebSocketDisconnect:
            pass

    return app

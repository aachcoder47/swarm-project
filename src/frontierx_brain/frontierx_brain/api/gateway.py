"""
Component 18 & 1: API Gateway & FastAPI Server (Production Mode)
===============================================================
Central web API gateway unifying REST endpoints and WebSockets for real-time dashboard interaction,
telemetry streaming, task submission, safety control, and world model queries.
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
from frontierx_brain.memory.task_memory import TaskMemory
from frontierx_brain.monitor.state_monitor import RobotStateMonitor
from frontierx_brain.orchestrator.multi_robot_orchestrator import MultiRobotOrchestrator
from frontierx_brain.perception.perception_interface import PerceptionInterface
from frontierx_brain.registry.capability_registry import CapabilityRegistry
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotRegistry, RobotStatus
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
    """Master orchestrator class assembling all 18 Central Brain components."""

    def __init__(self) -> None:
        self.world_model = WorldModel()
        self.task_memory = TaskMemory()
        self.robot_registry = RobotRegistry()
        self.capability_registry = CapabilityRegistry(self.robot_registry)
        self.policy_supervisor = PolicySupervisor()
        self.orchestrator = MultiRobotOrchestrator(self.robot_registry)
        self.state_monitor = RobotStateMonitor(self.robot_registry)
        self.perception = PerceptionInterface(self.world_model)
        self.sensor_pipeline = SensorDataPipeline()
        self.sim_interface = SimulationInterface(self.robot_registry)
        self.teleop = TeleoperationFallback(self.robot_registry, self.policy_supervisor)
        self.ros_bridge = ROS2MultiRobotBridge(self.state_monitor)

        # Initialize TaskPlanner (Will attempt OpenAI API or Ollama local backend)
        try:
            llm_provider = get_llm_provider("auto")
        except Exception as e:
            brain_logger.warning(f"LLM Provider Initialization Notice: {e}")
            llm_provider = None

        self.task_planner = TaskPlanner(self.world_model, llm_provider) if llm_provider else None
        self.command_interface = CommandInterface(self.task_planner) if self.task_planner else None

        self.skill_engine = SkillExecutionEngine(
            robot_registry=self.robot_registry,
            capability_registry=self.capability_registry,
            orchestrator=self.orchestrator,
            policy_supervisor=self.policy_supervisor,
            task_memory=self.task_memory,
            ros_bridge_callback=self.ros_bridge.dispatch_skill_to_body,
        )

        # Start ROS 2 DDS Multi-Robot Bridge
        self.ros_bridge.start_bridge()
        brain_logger.info("Central Brain System initialized in Production Mode.")


def create_app() -> Any:
    """Factory creating FastAPI server app."""
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI is not installed in current Python environment.")

    brain = CentralBrainSystem()
    app = FastAPI(
        title="FrontierX Central AI Brain Platform",
        description="Unified Centralized AI Brain & Multi-Robot Orchestration API (Production Mode)",
        version="0.1.0",
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
            "version": "0.1.0",
            "status": "OPERATIONAL",
            "active_robots": len(brain.robot_registry.list_robots()),
            "tracked_world_objects": len(brain.world_model.get_all_objects()),
            "e_stop_status": brain.policy_supervisor.is_e_stopped(),
        }

    @app.post("/api/v1/command")
    def submit_command(req: CommandRequest):
        if not brain.command_interface:
            raise HTTPException(
                status_code=503,
                detail="AI Task Planner is unavailable. Please configure OPENAI_API_KEY environment variable or start local Ollama server."
            )

        session, plan = brain.command_interface.process_command(req.command, source=req.source)
        if not plan:
            raise HTTPException(status_code=400, detail="Failed to generate a valid task plan.")

        results = brain.skill_engine.execute_plan(plan, preferred_robot_id=req.preferred_robot_id)
        report = brain.task_memory.generate_inspection_report(plan.plan_id)

        return {
            "session_id": session.session_id,
            "plan_id": plan.plan_id,
            "reasoning": plan.reasoning,
            "steps": [s.dict() for s in plan.steps],
            "execution_results": [r.dict() for r in results],
            "inspection_report": report,
        }

    @app.post("/api/v1/robots/register")
    def register_robot(robot_spec: RobotBodySpec):
        reg = brain.robot_registry.register_robot(robot_spec)
        return reg.dict()

    @app.get("/api/v1/robots")
    def list_robots():
        brain.state_monitor.check_health_watchdogs()
        return [r.dict() for r in brain.robot_registry.list_robots()]

    @app.post("/api/v1/world/object")
    def add_world_object(obj: WorldObject):
        saved = brain.world_model.upsert_object(obj)
        return saved.dict()

    @app.get("/api/v1/world")
    def get_world_model():
        return [o.dict() for o in brain.world_model.get_all_objects()]

    @app.get("/api/v1/tasks")
    def get_task_history():
        return [t.dict() for t in brain.task_memory.get_all_tasks()]

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
                robots = [r.dict() for r in brain.robot_registry.list_robots()]
                world = [o.dict() for o in brain.world_model.get_all_objects()]
                metrics = brain_logger.get_metrics()
                payload = {
                    "timestamp": time.time(),
                    "robots": robots,
                    "world_objects": world,
                    "metrics": metrics,
                    "e_stop": brain.policy_supervisor.is_e_stopped(),
                }
                await websocket.send_json(payload)
                await asyncio.sleep(1.0)
        except WebSocketDisconnect:
            pass

    return app

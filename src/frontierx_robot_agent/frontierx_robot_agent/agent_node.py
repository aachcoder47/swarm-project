#!/usr/bin/env python3
"""
FrontierX Robot Agent
======================
The top-level AI agent that converts natural language commands into
structured, validated ROS 2 action calls.

Safety invariant:
  The LLM NEVER writes directly to any actuator topic (/cmd_vel, etc.).
  All LLM output is:
    1. Parsed as a JSON task plan
    2. Validated against a strict Pydantic schema
    3. Checked against the action whitelist
    4. Only then dispatched to deterministic ROS 2 action servers

Usage (ROS 2 node):
  ros2 run frontierx_robot_agent agent_node

Usage (CLI):
  ros2 run frontierx_robot_agent agent_cli "Find the red box"
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

from std_msgs.msg import Bool, String
from geometry_msgs.msg import PoseStamped

# FrontierX interfaces
from frontierx_interfaces.action import (
    NavigateToGoal,
    FindObject,
    FollowPerson,
    ExecuteTaskPlan,
    Dock,
)
from frontierx_interfaces.msg import RobotHealth, TaskStatus, WorldModel
from frontierx_interfaces.srv import QueryWorldModel, ExecuteTask

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from pydantic import BaseModel, Field, validator
    from pydantic import ValidationError
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


# ══════════════════════════════════════════════════════════════
# TASK PLAN SCHEMA (Pydantic validation)
# ══════════════════════════════════════════════════════════════

ALLOWED_TASK_TYPES = {
    "navigate_to",
    "find_object",
    "follow_person",
    "patrol",
    "dock",
    "inspect",
    "report_status",
    "query_world",
    "wait",
}


class TaskStep(BaseModel):
    """A single step in a structured task plan."""
    step_id: int = Field(ge=0)
    task_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)

    @validator("task_type")
    def task_type_must_be_allowed(cls, v: str) -> str:  # noqa: N805
        if v not in ALLOWED_TASK_TYPES:
            raise ValueError(
                f"Task type '{v}' is not in the allowed set: {ALLOWED_TASK_TYPES}"
            )
        return v


class TaskPlan(BaseModel):
    """Complete structured task plan produced by the LLM."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    natural_language: str
    steps: List[TaskStep]
    total_timeout_seconds: float = Field(default=300.0, ge=1.0, le=3600.0)
    reasoning: str = ""

    @validator("steps")
    def must_have_steps(cls, v: List[TaskStep]) -> List[TaskStep]:  # noqa: N805
        if len(v) == 0:
            raise ValueError("Task plan must have at least one step.")
        if len(v) > 20:
            raise ValueError("Task plan cannot have more than 20 steps.")
        return v


# ══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are the FrontierX Robot Agent — the AI brain of the FrontierX Scout autonomous mobile robot.

Your role is PLANNING ONLY. You must never attempt to directly control motors or hardware.
Your output must always be a structured JSON task plan.

ALLOWED TASK TYPES:
- navigate_to: {"x": float, "y": float, "theta": float}
- find_object: {"class_name": str, "timeout": float}
- follow_person: {"person_id": int, "duration": float}
- patrol: {"waypoints": [[x, y], ...]}
- dock: {}
- inspect: {"object_id": str}
- report_status: {}
- query_world: {"query": str}
- wait: {"duration_seconds": float}

SAFETY RULES (ABSOLUTE — NEVER VIOLATE):
1. Max linear velocity: 0.5 m/s (enforced by hardware, not you)
2. You must never add steps that bypass the safety layer
3. You must never navigate near obstacles you know about
4. If the user asks to do something dangerous, explain why and refuse
5. Maximum 20 steps per plan
6. Maximum plan duration: 3600 seconds

OUTPUT FORMAT (STRICT JSON — no markdown, no explanations outside JSON):
{
  "natural_language": "<original command>",
  "reasoning": "<brief step-by-step reasoning>",
  "total_timeout_seconds": <number>,
  "steps": [
    {
      "step_id": 0,
      "task_type": "<type>",
      "params": {<params>},
      "description": "<human-readable description>",
      "timeout_seconds": <number>
    }
  ]
}

WORLD MODEL KNOWLEDGE:
You will be given the current world model as context.
Use it to reason about object locations before planning navigation.
If an object is unknown, plan a find_object step first.
"""


# ══════════════════════════════════════════════════════════════
# AGENT NODE
# ══════════════════════════════════════════════════════════════

class FrontierXAgentNode(Node):
    """
    The FrontierX Robot Agent ROS 2 node.

    Subscribes to:
      /agent/command (std_msgs/String) — natural language commands
      /world_model   (WorldModel)      — current world state
      /robot_health  (RobotHealth)     — robot health status

    Publishes:
      /agent/response    (std_msgs/String) — agent responses
      /agent/task_plan   (std_msgs/String) — validated JSON task plan
      /agent/status      (std_msgs/String) — agent status

    Action clients:
      /navigate_to_goal  → NavigateToGoal
      /find_object       → FindObject
      /follow_person     → FollowPerson
      /execute_task_plan → ExecuteTaskPlan
      /dock              → Dock
    """

    def __init__(self) -> None:
        super().__init__("frontierx_agent")

        self._declare_parameters()

        # State
        self._world_model: Optional[WorldModel] = None
        self._robot_health: Optional[RobotHealth] = None
        self._current_task_id: Optional[str] = None
        self._is_executing: bool = False
        self._command_history: List[Dict[str, Any]] = []

        # LLM client
        try:
            self._llm_model = self.get_parameter("llm_model").value
            self._ollama_url = self.get_parameter("ollama_base_url").value
        except Exception:
            self._llm_model = "llama3.1:8b"
            self._ollama_url = "http://ollama:11434"

        self._llm_available = OLLAMA_AVAILABLE
        self.get_logger().info(
            f"LLM backend: {'ollama (' + self._llm_model + ')' if self._llm_available else 'UNAVAILABLE (fallback planner active)'}"
        )

        # QoS profiles
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=10,
        )
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            depth=10,
        )

        # ── Subscribers ────────────────────────────────────────
        self._cmd_sub = self.create_subscription(
            String,
            "/agent/command",
            self._on_command,
            reliable_qos,
        )
        self._world_model_sub = self.create_subscription(
            WorldModel,
            "/world_model",
            self._on_world_model,
            sensor_qos,
        )
        self._health_sub = self.create_subscription(
            RobotHealth,
            "/robot_health",
            self._on_health,
            sensor_qos,
        )

        # ── Publishers ────────────────────────────────────────
        self._response_pub = self.create_publisher(String, "/agent/response", reliable_qos)
        self._plan_pub = self.create_publisher(String, "/agent/task_plan", reliable_qos)
        self._status_pub = self.create_publisher(String, "/agent/status", reliable_qos)

        # ── Action Clients ────────────────────────────────────
        self._nav_client = ActionClient(self, NavigateToGoal, "/navigate_to_goal")
        self._find_client = ActionClient(self, FindObject, "/find_object")
        self._follow_client = ActionClient(self, FollowPerson, "/follow_person")
        self._task_client = ActionClient(self, ExecuteTaskPlan, "/execute_task_plan")
        self._dock_client = ActionClient(self, Dock, "/dock")

        # ── Service Clients ────────────────────────────────────
        self._world_query_client = self.create_client(
            QueryWorldModel, "/query_world_model"
        )

        # Heartbeat
        self._heartbeat_timer = self.create_timer(1.0, self._publish_heartbeat)

        self.get_logger().info("FrontierX Agent node initialized. Ready for commands.")

    def _declare_parameters(self) -> None:
        """Declare all ROS 2 parameters."""
        self.declare_parameter("llm_model", "llama3.1:8b")
        self.declare_parameter("ollama_base_url", "http://localhost:11434")
        self.declare_parameter("max_plan_steps", 10)
        self.declare_parameter("plan_timeout_seconds", 300.0)
        self.declare_parameter("safety_check_enabled", True)
        self.declare_parameter("debug_mode", False)

    def _on_command(self, msg: String) -> None:
        """Process incoming natural language command."""
        command = msg.data.strip()
        if not command:
            return

        self.get_logger().info(f"Command received: '{command}'")
        self._publish_status(f"Processing: '{command}'")

        # Safety gate: check robot health before accepting commands
        if not self._safety_gate_check():
            response = "Cannot execute command: robot safety system is in FAULT or E_STOP state."
            self._publish_response(response)
            return

        # Generate task plan
        plan = self._generate_plan(command)
        if plan is None:
            self._publish_response(
                "I was unable to generate a safe task plan for that command."
            )
            return

        # Publish validated plan
        self._plan_pub.publish(String(data=plan.model_dump_json()))
        self.get_logger().info(f"Plan validated: {len(plan.steps)} steps")

        # Dispatch plan
        self._dispatch_plan(plan)

    def _safety_gate_check(self) -> bool:
        """
        Deterministic pre-execution safety check.
        Returns True only if the robot is in a state safe to accept commands.
        """
        if self._robot_health is None:
            # No health data yet — allow in sim, warn in real robot
            self.get_logger().warn("No robot health data received yet. Proceeding cautiously.")
            return True

        # Block in E_STOP or FAULT states
        if self._robot_health.e_stop_active:
            self.get_logger().error(
                f"E_STOP active: {self._robot_health.e_stop_reason}. Command blocked."
            )
            return False

        health_state = self._robot_health.system_state
        if health_state == RobotHealth.FAULT:
            self.get_logger().error("System in FAULT state. Command blocked.")
            return False

        return True

    def _generate_plan(self, command: str) -> Optional[TaskPlan]:
        """
        Send command + world model context to LLM.
        Parse and validate the response as a TaskPlan.
        Returns None if generation or validation fails.
        """
        if not self._llm_available:
            self.get_logger().error("LLM not available. Cannot generate plan.")
            return self._fallback_plan(command)

        # Build context from world model
        world_context = self._build_world_context()

        user_message = (
            f"World model context:\n{world_context}\n\n"
            f"User command: {command}"
        )

        try:
            self.get_logger().debug(f"Sending to LLM: {user_message[:200]}...")
            response = ollama.chat(
                model=self._llm_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                options={"temperature": 0.1, "num_predict": 2048},
            )
            raw_json = response["message"]["content"].strip()

        except Exception as e:
            self.get_logger().error(f"LLM call failed: {e}")
            return None

        # Parse JSON
        try:
            plan_dict = json.loads(raw_json)
            plan_dict["natural_language"] = command
        except json.JSONDecodeError as e:
            self.get_logger().error(f"LLM returned invalid JSON: {e}\nRaw: {raw_json[:500]}")
            return None

        # Validate against Pydantic schema
        try:
            plan = TaskPlan(**plan_dict)
        except ValidationError as e:
            self.get_logger().error(f"Task plan validation failed:\n{e}")
            return None

        self.get_logger().info(
            f"Plan validated: {len(plan.steps)} steps, "
            f"timeout={plan.total_timeout_seconds}s"
        )
        return plan

    def _build_world_context(self) -> str:
        """Build a text summary of the current world model for LLM context."""
        if self._world_model is None:
            return "World model: not yet available. Robot may still be initializing."

        lines = [
            f"Known objects: {len(self._world_model.objects)}",
        ]
        for obj in self._world_model.objects[:20]:  # Limit to 20 objects
            pos = obj.pose.pose.position
            lines.append(
                f"  - {obj.label} ({obj.class_name}) at "
                f"({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f})"
                f"{' [stale]' if obj.is_stale else ''}"
            )

        robot_pos = self._world_model.robot_pose.pose.pose.position
        lines.append(
            f"Robot position: ({robot_pos.x:.2f}, {robot_pos.y:.2f})"
        )
        return "\n".join(lines)

    def _fallback_plan(self, command: str) -> Optional[TaskPlan]:
        """Simple keyword-based fallback planner when LLM is unavailable."""
        command_lower = command.lower()

        if "status" in command_lower or "report" in command_lower:
            return TaskPlan(
                natural_language=command,
                reasoning="LLM unavailable. Matched keyword: status/report",
                steps=[
                    TaskStep(step_id=0, task_type="report_status", description="Report robot status")
                ],
            )
        elif "dock" in command_lower or "charge" in command_lower:
            return TaskPlan(
                natural_language=command,
                reasoning="LLM unavailable. Matched keyword: dock/charge",
                steps=[
                    TaskStep(step_id=0, task_type="dock", description="Navigate to docking station")
                ],
            )

        self.get_logger().warn("No fallback plan matched.")
        return None

    def _dispatch_plan(self, plan: TaskPlan) -> None:
        """Dispatch a validated task plan to the ExecuteTaskPlan action server."""
        if not self._task_client.wait_for_server(timeout_sec=5.0):
            self.get_logger().error("ExecuteTaskPlan action server not available.")
            self._publish_response("Task execution system unavailable.")
            return

        goal = ExecuteTaskPlan.Goal()
        goal.task_plan_json = plan.model_dump_json()
        goal.natural_language_description = plan.natural_language
        goal.pre_validated = True
        goal.total_timeout_seconds = plan.total_timeout_seconds

        self._current_task_id = plan.plan_id
        self._is_executing = True

        future = self._task_client.send_goal_async(
            goal,
            feedback_callback=self._on_task_feedback,
        )
        future.add_done_callback(self._on_goal_accepted)

    def _on_goal_accepted(self, future) -> None:
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Task plan was rejected by executor.")
            self._is_executing = False
            return
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self._on_task_result)

    def _on_task_feedback(self, feedback_msg) -> None:
        fb = feedback_msg.feedback
        self._publish_status(
            f"Step {fb.current_step_index + 1}/{fb.total_steps}: "
            f"{fb.current_step_description} ({fb.overall_progress * 100:.0f}%)"
        )

    def _on_task_result(self, future) -> None:
        result = future.result().result
        self._is_executing = False
        if result.success:
            response = f"Task completed successfully. {result.message}"
        else:
            response = f"Task failed: {result.message}"
        self._publish_response(response)
        self.get_logger().info(response)

    def _on_world_model(self, msg: WorldModel) -> None:
        self._world_model = msg

    def _on_health(self, msg: RobotHealth) -> None:
        self._robot_health = msg

    def _publish_response(self, text: str) -> None:
        self._response_pub.publish(String(data=text))

    def _publish_status(self, text: str) -> None:
        self._status_pub.publish(String(data=text))

    def _publish_heartbeat(self) -> None:
        self._status_pub.publish(
            String(data=f"agent:{'executing' if self._is_executing else 'ready'}")
        )


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════

def main(args=None) -> None:
    rclpy.init(args=args)
    node = FrontierXAgentNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

"""
Component 2: AI Reasoning / Task Planner
========================================
Central intelligence planner that converts natural-language user commands
into validated, structured task plans (DAG of execution steps) using LLM/VLM backends.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from frontierx_brain.ai.llm_provider import BaseLLMProvider, get_llm_provider
from frontierx_brain.world.world_model import WorldModel
from frontierx_brain.observability.observability import brain_logger


class TaskStep(BaseModel):
    step_id: int = Field(ge=0)
    task_type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    required_capabilities: List[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=60.0, ge=1.0, le=600.0)


class TaskPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    natural_language: str
    reasoning: str = ""
    steps: List[TaskStep]
    total_timeout_seconds: float = Field(default=300.0, ge=1.0, le=3600.0)

    @field_validator("steps")
    def must_have_steps(cls, v: List[TaskStep]) -> List[TaskStep]:
        if len(v) == 0:
            raise ValueError("Task plan must contain at least one execution step.")
        if len(v) > 20:
            raise ValueError("Task plan exceeds maximum limit of 20 steps.")
        return v


SYSTEM_PLANNING_PROMPT = """You are the Central AI Brain for the FrontierX Multi-Robot Platform.
Your role is HIGH-LEVEL REASONING AND TASK PLANNING ONLY.
You NEVER directly output low-level motor commands (cmd_vel, PWM, torque).

Output MUST be strict JSON matching this schema:
{
  "natural_language": "<original command>",
  "reasoning": "<step-by-step reasoning>",
  "total_timeout_seconds": 300,
  "steps": [
    {
      "step_id": 0,
      "task_type": "<navigate_to|find_object|follow_person|patrol|dock|inspect|report_status|query_world|wait|arm_pick|arm_place|aerial_scan>",
      "params": {<parameters>},
      "description": "<step description>",
      "required_capabilities": ["<capability_name>"],
      "timeout_seconds": 60.0
    }
  ]
}
"""


class TaskPlanner:
    """Central AI task planner transforming user intent into validated task DAGs."""

    def __init__(self, world_model: WorldModel, llm_provider: Optional[BaseLLMProvider] = None) -> None:
        self.world_model = world_model
        self.llm_provider = llm_provider or get_llm_provider("auto")

    def plan_task(self, natural_language_command: str) -> Optional[TaskPlan]:
        """Generate a validated TaskPlan from a user prompt."""
        brain_logger.info(f"TaskPlanner generating plan for: '{natural_language_command}'")

        # 1. Format world context
        world_objects = self.world_model.get_all_objects()
        context_str = f"Current World Objects: {json.dumps([o.dict() for o in world_objects])}"
        full_user_prompt = f"User Request: '{natural_language_command}'\n{context_str}"

        # 2. Invoke LLM backend
        try:
            res = self.llm_provider.generate(SYSTEM_PLANNING_PROMPT, full_user_prompt)
            raw_json = res.raw_text

            # Clean json block formatting if returned inside ```json ... ```
            if "```" in raw_json:
                lines = raw_json.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw_json = "\n".join(lines)

            plan_dict = json.loads(raw_json)
            plan = TaskPlan(**plan_dict)
            brain_logger.info(
                f"TaskPlan generated successfully (ID: {plan.plan_id[:8]}, Steps: {len(plan.steps)}) via {res.provider_name}."
            )
            return plan

        except Exception as e:
            brain_logger.error(f"TaskPlanner error parsing plan: {e}")
            # Fallback to mock planner if primary LLM fails
            try:
                fallback_res = get_llm_provider("mock").generate(SYSTEM_PLANNING_PROMPT, full_user_prompt)
                plan_dict = json.loads(fallback_res.raw_text)
                return TaskPlan(**plan_dict)
            except Exception as ex:
                brain_logger.error(f"Fallback mock planner failed: {ex}")
                return None

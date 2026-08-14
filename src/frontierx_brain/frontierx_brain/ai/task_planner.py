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
from frontierx_brain.registry.skill_registry import SkillRegistry
from frontierx_brain.registry.capability_registry import CapabilityRegistry
from frontierx_brain.core.schemas import SkillType, ALLOWED_ACTION_WHITELIST
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


def _build_system_planning_prompt(skill_registry: Optional[SkillRegistry] = None) -> str:
    """Build system prompt from canonical skill registry — single source of truth."""
    valid_skills = sorted(ALLOWED_ACTION_WHITELIST)
    skill_info_lines = []
    if skill_registry:
        for s in skill_registry.all_definitions():
            caps = sorted(c.value for c in s.required_capabilities)
            bodies = sorted(b.value for b in s.compatible_body_types)
            skill_info_lines.append(
                f"  - {s.skill_id.value}: {s.description} "
                f"required_capabilities={caps} compatible_body_types={bodies}"
            )
    skills_enum = "|".join(valid_skills)
    skill_info_block = "\n".join(skill_info_lines)
    return f"""You are the Central AI Brain for the FrontierX Multi-Robot Platform.
Your role is HIGH-LEVEL REASONING AND TASK PLANNING ONLY.
You NEVER directly output low-level motor commands (cmd_vel, PWM, torque).

Valid task_type values (canonical enum): {skills_enum}

Canonical Skill Registry:
{skill_info_block}

Output MUST be strict JSON matching this schema:
{{
  "natural_language": "<original command>",
  "reasoning": "<step-by-step reasoning>",
  "total_timeout_seconds": 300,
  "steps": [
    {{
      "step_id": 0,
      "task_type": "<{skills_enum}>",
      "params": {{<parameters — use _resolve_from_object: "class_name" when a step needs world-model object data injected before execution>}},
      "description": "<step description>",
      "required_capabilities": ["<capability_name>"],
      "timeout_seconds": 60.0
    }}
  ]
}}
"""


class TaskPlanner:
    """Central AI task planner transforming user intent into validated task DAGs."""

    def __init__(
        self,
        world_model: WorldModel,
        llm_provider: Optional[BaseLLMProvider] = None,
        skill_registry: Optional[SkillRegistry] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
    ) -> None:
        self.world_model = world_model
        self.llm_provider = llm_provider or get_llm_provider("auto")
        self.skill_registry = skill_registry
        self.capability_registry = capability_registry
        self._system_prompt = _build_system_planning_prompt(skill_registry)

    def plan_task(self, natural_language_command: str) -> Optional[TaskPlan]:
        """Generate a validated TaskPlan from a user prompt."""
        brain_logger.info(f"TaskPlanner generating plan for: '{natural_language_command}'")

        # 1. Format world context
        world_objects = self.world_model.get_all_objects()
        context_str = f"Current World Objects: {json.dumps([o.model_dump() for o in world_objects])}"
        full_user_prompt = f"User Request: '{natural_language_command}'\n{context_str}"

        # 2. Invoke LLM backend (use registry-aware system prompt)
        try:
            res = self.llm_provider.generate(self._system_prompt, full_user_prompt)
            raw_json = res.raw_text

            # Clean json block formatting if returned inside ```json ... ```
            if "```" in raw_json:
                lines = raw_json.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw_json = "\n".join(lines)

            plan_dict = json.loads(raw_json)
            plan = TaskPlan(**plan_dict)

            # 2b. Post-validation: auto-add required capabilities from canonical skill registry
            if self.skill_registry:
                for step in plan.steps:
                    canon_req = self.skill_registry.required_capabilities(step.task_type)
                    if canon_req:
                        for cap in canon_req:
                            if cap not in step.required_capabilities:
                                step.required_capabilities.append(cap)
                    # Default step timeout from skill definition
                    sd = self.skill_registry.get_by_name(step.task_type)
                    if sd and step.timeout_seconds == 60.0 and sd.default_timeout_seconds != 60.0:
                        step.timeout_seconds = sd.default_timeout_seconds

            brain_logger.info(
                f"TaskPlan generated successfully (ID: {plan.plan_id[:8]}, Steps: {len(plan.steps)}) via {res.provider_name}."
            )
            return plan

        except Exception as e:
            brain_logger.error(f"TaskPlanner error parsing plan: {e}")
            # Fallback to deterministic mock planner if primary LLM fails (B2 fix)
            try:
                fallback_res = get_llm_provider("mock").generate(self._system_prompt, full_user_prompt)
                plan_dict = json.loads(fallback_res.raw_text)
                plan = TaskPlan(**plan_dict)
                if self.skill_registry:
                    for step in plan.steps:
                        canon_req = self.skill_registry.required_capabilities(step.task_type)
                        if canon_req:
                            for cap in canon_req:
                                if cap not in step.required_capabilities:
                                    step.required_capabilities.append(cap)
                brain_logger.info(f"Fallback deterministic planner succeeded (ID: {plan.plan_id[:8]}).")
                return plan
            except Exception as ex:
                brain_logger.error(f"Fallback deterministic planner failed: {ex}")
                return None

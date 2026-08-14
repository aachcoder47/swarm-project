"""
Component 3b: Plan Validator (Deterministic, Pre-Execution)
=============================================================
Runs a series of deterministic checks against a task plan BEFORE the skill
engine executes it. Rejects plans that reference unknown skill types, have
unmatched required capabilities, reference unavailable robots, or violate
geofence/safety constraints. Never catches exceptions at runtime.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from frontierx_brain.ai.task_planner import TaskPlan, TaskStep
from frontierx_brain.core.schemas import (
    SkillType,
    ALLOWED_ACTION_WHITELIST,
)
from frontierx_brain.registry.skill_registry import SkillRegistry
from frontierx_brain.registry.robot_registry import RobotRegistry
from frontierx_brain.safety.policy_supervisor import PolicySupervisor
from frontierx_brain.observability.observability import brain_logger


class PlanValidationResult(BaseModel):
    plan_id: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    step_errors: Dict[int, List[str]] = Field(default_factory=dict)
    per_step_robots: Dict[int, Optional[str]] = Field(default_factory=dict)


class PlanValidator:
    """Deterministic pre-execution plan validator."""

    def __init__(
        self,
        skill_registry: SkillRegistry,
        robot_registry: RobotRegistry,
        policy_supervisor: PolicySupervisor,
    ) -> None:
        self.skill_registry = skill_registry
        self.robot_registry = robot_registry
        self.policy_supervisor = policy_supervisor

    def validate(self, plan: TaskPlan) -> PlanValidationResult:
        errors: List[str] = []
        warnings: List[str] = []
        step_errors: Dict[int, List[str]] = {}
        per_step_robots: Dict[int, Optional[str]] = {}

        # 1. Plan-level basic checks
        if not plan.steps:
            errors.append("Plan has 0 steps. Must contain >= 1 step.")
        if plan.total_timeout_seconds < 1.0:
            errors.append("Plan total_timeout_seconds must be >= 1.0.")

        # 2. Per-step validation
        for step in plan.steps:
            serrs: List[str] = []

            # 2a. Skill must exist in canonical registry
            if not self.skill_registry.is_valid_skill(step.task_type):
                serrs.append(
                    f"Unknown task_type '{step.task_type}'. "
                    f"Must be one of: {sorted(ALLOWED_ACTION_WHITELIST)}."
                )
                step_errors[step.step_id] = serrs
                errors.extend(serrs)
                per_step_robots[step.step_id] = None
                continue

            # 2b. Check that skill definition exists
            sd = self.skill_registry.get_by_name(step.task_type)
            if sd is None:
                serrs.append(f"No SkillDefinition for '{step.task_type}'.")
                step_errors[step.step_id] = serrs
                errors.extend(serrs)
                per_step_robots[step.step_id] = None
                continue

            # 2c. Required capabilities declared on step must match skill definition (auto-correct silently)
            req_declared = set(step.required_capabilities)
            req_canonical = set(self.skill_registry.required_capabilities(step.task_type))
            if not req_canonical.issubset(req_declared):
                # Auto-correct: fill in missing capabilities on the step (safe & deterministic)
                step.required_capabilities = sorted(req_declared | req_canonical)
                warnings.append(
                    f"Step {step.step_id} ({step.task_type}): auto-added required capabilities: "
                    f"{sorted(req_canonical - req_declared)}"
                )

            # 2d. Pre-check safety supervisor on this step (no robot yet → general rules only)
            safety = self.policy_supervisor.validate_task_step(
                task_type=step.task_type, params=step.params, robot=None
            )
            if not safety.is_safe:
                serrs.append(f"Safety supervisor rejected step: {safety.reason}")

            # 2e. Check at least one registered robot CAN do this step
            candidate_robots = self.skill_registry.find_robots_for_skill(
                step.task_type,
                target_x=step.params.get("x"),
                target_y=step.params.get("y"),
            )
            if not candidate_robots:
                # Non-fatal if robot registry is empty (e.g. Gazebo hasn't discovered bodies yet)
                if len(self.robot_registry.list_robots()) == 0:
                    warnings.append(
                        f"Step {step.step_id} ({step.task_type}): no robots are registered yet. "
                        "Assuming robots will be registered via Gazebo discovery before execution."
                    )
                    per_step_robots[step.step_id] = None
                else:
                    serrs.append(
                        f"Step {step.step_id} ({step.task_type}): no registered robot has "
                        f"the required capabilities {sorted(req_canonical)} AND compatible body type. "
                        f"Robots registered: {[(r.robot_id, r.body_type.value, r.capabilities) for r in self.robot_registry.list_robots()]}"
                    )
            else:
                per_step_robots[step.step_id] = candidate_robots[0].robot_id

            if serrs:
                step_errors[step.step_id] = serrs
                errors.extend(serrs)

        result = PlanValidationResult(
            plan_id=plan.plan_id,
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            step_errors=step_errors,
            per_step_robots=per_step_robots,
        )

        if result.is_valid:
            brain_logger.info(
                f"Plan {plan.plan_id[:8]} VALIDATED ({len(plan.steps)} steps, "
                f"{len(result.warnings)} warnings)."
            )
        else:
            brain_logger.warning(
                f"Plan {plan.plan_id[:8]} REJECTED by validator. "
                f"{len(result.errors)} error(s): {result.errors[:3]}"
            )
        return result

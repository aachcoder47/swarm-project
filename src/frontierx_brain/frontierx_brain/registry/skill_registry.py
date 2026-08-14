"""
Component 4b: Skill Registry
=============================
Formal, validated, single-source-of-truth for every skill/task type.
Every skill has: canonical id, human description, required capability list,
typed input/output schemas, compatible robot body types, default timeout,
retry policy, cancellation behavior, and safety constraints.

The task planner emits steps referencing SkillType ids. The plan validator
checks each step against this registry before execution. The capability
matchmaker uses required_capabilities from skill definitions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from frontierx_brain.core.schemas import (
    SkillDefinition,
    SkillType,
    CANONICAL_SKILL_DEFINITIONS,
    get_skill_definition,
    Capability,
    RobotBodyType,
    ALLOWED_ACTION_WHITELIST,
)
from frontierx_brain.registry.robot_registry import RobotBodySpec, RobotRegistry
from frontierx_brain.observability.observability import brain_logger


class SkillRegistry:
    """Canonical registry & validator for every skill known to the platform."""

    def __init__(self, robot_registry: Optional[RobotRegistry] = None) -> None:
        self._definitions: Dict[SkillType, SkillDefinition] = {
            s.skill_id: s for s in CANONICAL_SKILL_DEFINITIONS
        }
        self.robot_registry = robot_registry

    def get(self, skill_id: SkillType) -> Optional[SkillDefinition]:
        return self._definitions.get(skill_id)

    def get_by_name(self, task_type_name: str) -> Optional[SkillDefinition]:
        try:
            sk = SkillType(task_type_name)
        except ValueError:
            return None
        return self._definitions.get(sk)

    def all_skill_ids(self) -> List[SkillType]:
        return list(self._definitions.keys())

    def all_definitions(self) -> List[SkillDefinition]:
        return list(self._definitions.values())

    def is_valid_skill(self, task_type_name: str) -> bool:
        return task_type_name in ALLOWED_ACTION_WHITELIST

    def required_capabilities(self, task_type_name: str) -> List[str]:
        sd = self.get_by_name(task_type_name)
        if not sd:
            return []
        return [c.value for c in sd.required_capabilities]

    def compatible_body_types(self, task_type_name: str) -> List[RobotBodyType]:
        sd = self.get_by_name(task_type_name)
        if not sd:
            return []
        return sd.compatible_body_types

    def find_robots_for_skill(
        self,
        task_type_name: str,
        target_x: Optional[float] = None,
        target_y: Optional[float] = None,
        min_battery: float = 15.0,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[RobotBodySpec]:
        """Return all registered robots capable of executing this skill, ordered by suitability."""
        if not self.robot_registry:
            return []
        sd = self.get_by_name(task_type_name)
        if not sd:
            return []
        exclude_set = set(exclude_ids or [])
        required = set(c.value for c in sd.required_capabilities)
        compat_bodies = set(sd.compatible_body_types)
        candidates = []
        for r in self.robot_registry.list_robots():
            if r.robot_id in exclude_set:
                continue
            if r.status not in ("IDLE", "BUSY"):
                continue
            if r.battery_percentage < min_battery and task_type_name != "dock":
                continue
            if r.body_type not in compat_bodies and compat_bodies:
                continue
            caps = set(r.capabilities)
            if not required.issubset(caps):
                continue
            candidates.append(r)
        # Sort: prefer IDLE, then higher battery, then closer to target if given
        # Special handling: for tasks requiring movement to target (inspect, find, navigate),
        # heavily penalize non-navigating robots (ARM) that are far from the target
        movement_heavy_tasks = {"inspect", "find_object", "analyze_observation"}
        task_is_movement_heavy = task_type_name in movement_heavy_tasks

        def score(r: RobotBodySpec) -> float:
            s = 100.0
            if r.status == "IDLE":
                s += 30.0
            s += r.battery_percentage * 0.5
            can_navigate = "navigate_ground" in r.capabilities or "navigate_aerial" in r.capabilities
            if target_x is not None and target_y is not None:
                dx = r.pose.x - target_x
                dy = r.pose.y - target_y
                dist = (dx * dx + dy * dy) ** 0.5
                s -= dist * 2.0
                # For movement-heavy tasks: if robot can't navigate and is >3m from target,
                # heavily penalize (standoff check will fail anyway for inspect)
                if task_is_movement_heavy and not can_navigate and dist > 3.0:
                    s -= 500.0
            return s
        candidates.sort(key=score, reverse=True)
        return candidates

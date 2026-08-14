"""
Component 1: AI Command Interface
=================================
Ingests natural-language commands (text or voice transcripts),
normalizes input, generates task sessions, and routes commands to the Task Planner.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from frontierx_brain.ai.task_planner import TaskPlan, TaskPlanner
from frontierx_brain.observability.observability import brain_logger


class CommandSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    raw_command: str
    cleaned_command: str
    source: str = "REST_API"  # REST_API, VOICE, DASHBOARD, CLI
    timestamp: float = Field(default_factory=time.time)
    status: str = "ACCEPTED"
    plan_id: Optional[str] = None


class CommandInterface:
    """Entry point for natural-language command ingestion."""

    def __init__(self, task_planner: TaskPlanner) -> None:
        self.task_planner = task_planner
        self._sessions: Dict[str, CommandSession] = {}

    def process_command(
        self,
        raw_command: str,
        source: str = "REST_API",
    ) -> Tuple[CommandSession, Optional[TaskPlan]]:
        """Process incoming natural language prompt and return session + generated task plan."""
        cleaned = raw_command.strip()
        session = CommandSession(
            raw_command=raw_command,
            cleaned_command=cleaned,
            source=source,
        )
        self._sessions[session.session_id] = session

        brain_logger.info(f"CommandInterface ingested command from {source}: '{cleaned}'", task_id=session.session_id)
        brain_logger.increment_metric("total_commands_received")

        if not cleaned:
            session.status = "REJECTED_EMPTY"
            return session, None

        plan = self.task_planner.plan_task(cleaned)
        if plan:
            session.status = "PLANNED"
            session.plan_id = plan.plan_id
            brain_logger.increment_metric("tasks_planned_successfully")
        else:
            session.status = "PLANNING_FAILED"

        return session, plan

    def get_session(self, session_id: str) -> Optional[CommandSession]:
        return self._sessions.get(session_id)

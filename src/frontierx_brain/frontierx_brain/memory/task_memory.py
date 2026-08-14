"""
Component 7: Task Memory
========================
Stores task execution logs, plan traces, sensor observation history,
evaluation outcomes, and generates structured inspection reports.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecutionRecord(BaseModel):
    task_id: str
    user_command: str
    selected_robot_id: str
    plan_steps: List[Dict[str, Any]]
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "IN_PROGRESS"  # COMPLETED, FAILED, REPLANNING, CANCELLED
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None


class TaskMemory:
    """Central persistent task memory and report generator."""

    def __init__(self) -> None:
        self._history: Dict[str, ExecutionRecord] = {}

    def record_start(
        self,
        task_id: str,
        user_command: str,
        selected_robot_id: str,
        plan_steps: List[Dict[str, Any]],
    ) -> ExecutionRecord:
        record = ExecutionRecord(
            task_id=task_id,
            user_command=user_command,
            selected_robot_id=selected_robot_id,
            plan_steps=plan_steps,
        )
        self._history[task_id] = record
        return record

    def add_observation(self, task_id: str, observation: Dict[str, Any]) -> None:
        record = self._history.get(task_id)
        if record:
            record.observations.append(observation)

    def add_finding(self, task_id: str, finding: str) -> None:
        record = self._history.get(task_id)
        if record:
            record.findings.append(finding)

    def record_complete(self, task_id: str, status: str = "COMPLETED", error_message: Optional[str] = None) -> Optional[ExecutionRecord]:
        record = self._history.get(task_id)
        if record:
            record.end_time = time.time()
            record.status = status
            record.error_message = error_message
        return record

    def get_task(self, task_id: str) -> Optional[ExecutionRecord]:
        return self._history.get(task_id)

    def get_all_tasks(self) -> List[ExecutionRecord]:
        return list(self._history.values())

    def generate_inspection_report(self, task_id: str) -> Dict[str, Any]:
        """Generate a formal inspection report from recorded task observations."""
        record = self._history.get(task_id)
        if not record:
            return {"error": f"Task {task_id} not found."}

        duration = (record.end_time - record.start_time) if record.end_time else (time.time() - record.start_time)

        report = {
            "report_title": f"Autonomous Inspection Report — Task {task_id[:8]}",
            "task_id": task_id,
            "original_command": record.user_command,
            "assigned_robot_body": record.selected_robot_id,
            "status": record.status,
            "execution_status": record.status,
            "duration_seconds": round(duration, 2),
            "findings_summary": record.findings if record.findings else ["Inspection completed normally. No critical anomalies detected."],
            "total_steps_executed": len(record.plan_steps),
            "raw_observations_count": len(record.observations),
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        }
        return report

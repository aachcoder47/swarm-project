"""
Component 16: Logging & Observability
=====================================
Structured JSON logging, OpenTelemetry context tracking, metrics recording,
and ROS 2 diagnostics exporter for the FrontierX Central AI Brain.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LogEvent:
    timestamp: float = field(default_factory=time.time)
    level: str = "INFO"
    component: str = "CentralBrain"
    message: str = ""
    trace_id: Optional[str] = None
    robot_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp)),
            "level": self.level,
            "component": self.component,
            "message": self.message,
            "trace_id": self.trace_id,
            "robot_id": self.robot_id,
            "task_id": self.task_id,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class BrainLogger:
    """Central structured JSON logger with in-memory buffer for Web UI observation."""

    def __init__(self, component_name: str = "CentralBrain", max_buffer_size: int = 500) -> None:
        self.component_name = component_name
        self.max_buffer_size = max_buffer_size
        self._buffer: List[LogEvent] = []
        self._metrics: Dict[str, float] = {
            "total_commands_received": 0,
            "tasks_planned_successfully": 0,
            "tasks_executed": 0,
            "safety_violations_blocked": 0,
            "active_robots_count": 0,
            "system_uptime_seconds": 0,
        }
        self.start_time = time.time()

        # Configure standard library logger
        self.std_logger = logging.getLogger(f"FrontierX.{component_name}")
        self.std_logger.setLevel(logging.INFO)
        if not self.std_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"))
            self.std_logger.addHandler(handler)

    def log(
        self,
        level: str,
        message: str,
        robot_id: Optional[str] = None,
        task_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        **metadata: Any,
    ) -> LogEvent:
        event = LogEvent(
            level=level.upper(),
            component=self.component_name,
            message=message,
            robot_id=robot_id,
            task_id=task_id,
            trace_id=trace_id,
            metadata=metadata,
        )
        self._buffer.append(event)
        if len(self._buffer) > self.max_buffer_size:
            self._buffer.pop(0)

        formatted_msg = f"[{self.component_name}] {message}"
        if robot_id:
            formatted_msg += f" (Robot: {robot_id})"
        if task_id:
            formatted_msg += f" (Task: {task_id})"

        log_fn = getattr(self.std_logger, level.lower(), self.std_logger.info)
        log_fn(formatted_msg)
        return event

    def info(self, message: str, **kwargs: Any) -> LogEvent:
        return self.log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> LogEvent:
        return self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> LogEvent:
        return self.log("ERROR", message, **kwargs)

    def increment_metric(self, metric_name: str, amount: float = 1.0) -> None:
        self._metrics[metric_name] = self._metrics.get(metric_name, 0.0) + amount

    def set_metric(self, metric_name: str, value: float) -> None:
        self._metrics[metric_name] = value

    def get_metrics(self) -> Dict[str, Any]:
        self._metrics["system_uptime_seconds"] = round(time.time() - self.start_time, 2)
        return self._metrics.copy()

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [event.to_dict() for event in self._buffer[-limit:]]


# Global singleton instance
brain_logger = BrainLogger("CentralBrain")

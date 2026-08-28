"""
FrontierX Brain — Structured JSON Logger
=========================================
Replaces all bare print() / unstructured logging.getLogger() calls
with a structured JSON logger that emits machine-parseable log lines
suitable for ingestion by Loki, Datadog, CloudWatch, or Splunk.

Log line format (JSON, one per line):
    {
        "timestamp": "2026-08-29T00:00:00.000Z",
        "level": "INFO",
        "service": "frontierx.brain.planner",
        "event": "plan_generated",
        "robot_id": "scout-01",
        "correlation_id": "c4b2f1a9",
        "duration_ms": 42.3,
        "extra": { ... }
    }

Usage:
    from frontierx_brain.observability.logger import get_logger

    log = get_logger("frontierx.brain.executor", robot_id="scout-01")
    log.info("skill_started", skill_type="navigate", goal_x=1.0, goal_y=2.0)
    log.error("skill_failed", error="timeout", duration_ms=5000)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional


class _StructuredFormatter(logging.Formatter):
    """Format log records as single-line JSON objects."""

    SERVICE_PREFIX = "frontierx"

    def format(self, record: logging.LogRecord) -> str:
        # Base structured fields
        doc: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "service": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }

        # Optional correlation / robot context fields
        for field in ("correlation_id", "robot_id", "robot_type", "skill_type", "task_id"):
            val = getattr(record, field, None)
            if val is not None:
                doc[field] = val

        # Duration if provided
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            doc["duration_ms"] = round(float(duration_ms), 3)

        # Exception info
        if record.exc_info:
            doc["exception"] = self.formatException(record.exc_info)

        # Extra arbitrary fields (anything not already captured)
        extra = getattr(record, "_extra", None)
        if extra:
            doc["extra"] = extra

        # Stack info
        if record.stack_info:
            doc["stack_info"] = record.stack_info

        return json.dumps(doc, default=str)


class StructuredLogger:
    """
    Thin wrapper around stdlib logging that adds structured context fields
    and a convenient keyword-argument API.

    Example:
        log = StructuredLogger("frontierx.brain.planner")
        log.info("plan_generated", robot_id="scout-01", steps=6, duration_ms=45.2)
    """

    def __init__(
        self,
        name: str,
        robot_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        self._logger = logging.getLogger(name)
        self._default_context: dict[str, Any] = {}
        if robot_id:
            self._default_context["robot_id"] = robot_id
        if correlation_id:
            self._default_context["correlation_id"] = correlation_id

    def _log(
        self,
        level: int,
        event: str,
        **kwargs: Any,
    ) -> None:
        extra: dict[str, Any] = {**self._default_context}
        # Pull known fields out of kwargs into top-level, rest → _extra
        top_level_fields = {
            "robot_id", "robot_type", "skill_type", "task_id",
            "correlation_id", "duration_ms",
        }
        reserved: dict[str, Any] = {}
        overflow: dict[str, Any] = {}
        for k, v in kwargs.items():
            if k in top_level_fields:
                reserved[k] = v
            else:
                overflow[k] = v

        extra.update(reserved)
        if overflow:
            extra["_extra"] = overflow
        extra["event"] = event

        self._logger.log(level, event, extra=extra)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._log(logging.INFO, event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        self._log(logging.CRITICAL, event, **kwargs)

    def bind(self, **context: Any) -> "StructuredLogger":
        """Return a child logger with additional default context fields."""
        child = StructuredLogger(self._logger.name)
        child._default_context = {**self._default_context, **context}
        return child

    def new_correlation_id(self) -> str:
        """Generate and bind a fresh correlation ID for a request/task span."""
        cid = uuid.uuid4().hex[:8]
        self._default_context["correlation_id"] = cid
        return cid


# ── Module-level setup ──────────────────────────────────────────

def _configure_root_logger() -> None:
    """
    Configure the root logger with structured JSON output.
    Called once at import time. Safe to call multiple times (idempotent).
    """
    root = logging.getLogger()

    # Avoid double-adding handlers
    if any(isinstance(h, logging.StreamHandler) and
           isinstance(h.formatter, _StructuredFormatter)
           for h in root.handlers):
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StructuredFormatter())
    root.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("urllib3", "asyncio", "websockets.server"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


_configure_root_logger()


def get_logger(
    name: str,
    robot_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
) -> StructuredLogger:
    """
    Factory function — returns a StructuredLogger bound with optional context.

    Args:
        name: Logger name (e.g. "frontierx.brain.planner")
        robot_id: Optional robot ID to attach to every log line
        correlation_id: Optional correlation ID (auto-generated if None)
    """
    return StructuredLogger(name, robot_id=robot_id, correlation_id=correlation_id)

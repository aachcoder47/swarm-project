"""
FrontierX Brain — Prometheus Metrics Exporter
=============================================
Exposes operational metrics for the central AI brain, robot fleet,
and skill execution engine. Scraped by Prometheus at /metrics on port 9090.

Usage:
    from frontierx_brain.observability.metrics import FrontierXMetrics, start_metrics_server

    metrics = FrontierXMetrics()
    start_metrics_server(port=9090)

    # Record events
    metrics.tasks_total.labels(status="success").inc()
    with metrics.plan_latency.time():
        plan = planner.generate_plan(command)
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

logger = logging.getLogger("frontierx.observability.metrics")

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        start_http_server,
        REGISTRY,
    )
    _PROMETHEUS_AVAILABLE = True
except (ImportError, AttributeError, Exception) as e:
    _PROMETHEUS_AVAILABLE = False
    logger.warning(
        f"prometheus_client not available ({e}) — metrics will be no-ops. "
        "Install with: pip install prometheus-client"
    )

# ── Singleton guard ─────────────────────────────────────────────
_metrics_server_started = False
_metrics_lock = threading.Lock()


def start_metrics_server(port: int = 9090) -> None:
    """Start the Prometheus HTTP server (idempotent — safe to call multiple times)."""
    global _metrics_server_started
    with _metrics_lock:
        if _metrics_server_started or not _PROMETHEUS_AVAILABLE:
            return
        start_http_server(port)
        _metrics_server_started = True
        logger.info(f"Prometheus metrics server started on :{port}/metrics")


class _NoOpMetric:
    """Stub metric that silently discards all calls when prometheus_client is absent."""
    def labels(self, **_: object) -> "_NoOpMetric":
        return self
    def inc(self, _: float = 1) -> None: pass
    def dec(self, _: float = 1) -> None: pass
    def set(self, _: float) -> None: pass
    def observe(self, _: float) -> None: pass
    def time(self) -> "_NoOpContext":
        return _NoOpContext()

class _NoOpContext:
    def __enter__(self) -> "_NoOpContext": return self
    def __exit__(self, *_: object) -> None: pass


def _make_counter(name: str, doc: str, labels: list[str]) -> object:
    if not _PROMETHEUS_AVAILABLE:
        return _NoOpMetric()
    return Counter(name, doc, labels)

def _make_gauge(name: str, doc: str, labels: Optional[list[str]] = None) -> object:
    if not _PROMETHEUS_AVAILABLE:
        return _NoOpMetric()
    return Gauge(name, doc, labels or [])

def _make_histogram(
    name: str, doc: str, labels: list[str], buckets: Optional[list[float]] = None
) -> object:
    if not _PROMETHEUS_AVAILABLE:
        return _NoOpMetric()
    kwargs = {"labelnames": labels}
    if buckets:
        kwargs["buckets"] = buckets
    return Histogram(name, doc, **kwargs)


class FrontierXMetrics:
    """
    Central metrics registry for the FrontierX robotics platform.

    Metrics exposed:
        frontierx_tasks_total{status}             - Task throughput counter
        frontierx_plan_latency_seconds{model}     - LLM planning latency histogram
        frontierx_skill_exec_seconds{skill_type}  - Skill execution duration histogram
        frontierx_robots_online                   - Live robot count gauge
        frontierx_robot_battery{robot_id}         - Per-robot battery percentage
        frontierx_safety_violations_total{type}   - Safety event counter
        frontierx_ros2_messages_total{topic}      - ROS 2 message throughput
        frontierx_build_info                      - Static build metadata
    """

    def __init__(self) -> None:
        # ── Task execution ─────────────────────────────────────
        self.tasks_total = _make_counter(
            "frontierx_tasks_total",
            "Total task executions by status (success, failure, cancelled)",
            ["status"],  # success | failure | cancelled | timeout
        )

        # ── Planning latency ───────────────────────────────────
        self.plan_latency = _make_histogram(
            "frontierx_plan_latency_seconds",
            "LLM task planning latency in seconds",
            ["model"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # ── Pre-validation latency ─────────────────────────────
        self.validation_latency = _make_histogram(
            "frontierx_plan_validation_seconds",
            "Plan pre-validation latency in seconds",
            [],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
        )

        # ── Skill execution duration ───────────────────────────
        self.skill_exec_duration = _make_histogram(
            "frontierx_skill_exec_seconds",
            "Skill execution duration by skill type",
            ["skill_type"],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )

        # ── Robot fleet ────────────────────────────────────────
        self.robots_online = _make_gauge(
            "frontierx_robots_online",
            "Number of robots currently connected and reporting heartbeat",
        )

        self.robot_battery = _make_gauge(
            "frontierx_robot_battery_percentage",
            "Battery state of charge per robot (0-100)",
            ["robot_id", "robot_type"],
        )

        # ── Safety ────────────────────────────────────────────
        self.safety_violations = _make_counter(
            "frontierx_safety_violations_total",
            "Safety policy violations by type",
            ["type"],  # blocked_cmd | policy_reject | watchdog_timeout | estop
        )

        # ── ROS 2 messaging ───────────────────────────────────
        self.ros2_messages = _make_counter(
            "frontierx_ros2_messages_total",
            "ROS 2 messages published by topic",
            ["topic"],
        )

        # ── Build info (static labels for version tracking) ───
        if _PROMETHEUS_AVAILABLE:
            self.build_info = Info(
                "frontierx_build",
                "FrontierX build metadata",
            )
        else:
            self.build_info = _NoOpMetric()

    def record_build_info(self, version: str, revision: str, ros_distro: str) -> None:
        """Call once at startup to record build metadata."""
        try:
            self.build_info.info({
                "version": version,
                "revision": revision,
                "ros_distro": ros_distro,
            })
        except Exception:
            pass  # Info metric may already be registered


# ── Module-level singleton ─────────────────────────────────────
_default_metrics: Optional[FrontierXMetrics] = None

def get_metrics() -> FrontierXMetrics:
    """Return the module-level singleton FrontierXMetrics instance."""
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = FrontierXMetrics()
    return _default_metrics

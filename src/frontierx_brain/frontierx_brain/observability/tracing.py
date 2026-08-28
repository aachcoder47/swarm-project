"""
FrontierX Brain — OpenTelemetry Tracing (Production Hardened)
=============================================================
Enables distributed tracing for planning, execution, and ROS callbacks.
Gracefully degrades to no-op if opentelemetry is not installed.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger("frontierx.observability.tracing")

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    _TRACING_AVAILABLE = True
except ImportError:
    _TRACING_AVAILABLE = False
    logger.warning("opentelemetry-api or SDK not installed. Tracing is disabled.")

F = TypeVar("F", bound=Callable[..., Any])
_tracer_initialized = False


def init_tracer(service_name: str = "frontierx-brain", endpoint: Optional[str] = None) -> None:
    """Initialize OpenTelemetry tracer provider with OTLP exporter."""
    global _tracer_initialized
    if not _TRACING_AVAILABLE or _tracer_initialized:
        return

    try:
        # Define Resource
        resource = Resource.create(attributes={
            "service.name": service_name,
            "project": "frontierx"
        })

        provider = TracerProvider(resource=resource)

        # Connect to Jaeger / OpenTelemetry Collector if endpoint is supplied
        otlp_endpoint = endpoint or "http://localhost:4317"
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        _tracer_initialized = True
        logger.info(f"OpenTelemetry tracing initialized (endpoint: {otlp_endpoint})")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry tracing: {e}", exc_info=True)


def get_tracer() -> Any:
    """Get the active OpenTelemetry tracer."""
    if _TRACING_AVAILABLE:
        return trace.get_tracer("frontierx.brain")
    return None


def trace_span(name: str) -> Callable[[F], F]:
    """Decorator to trace a function call as a span."""
    def decorator(func: F) -> F:
        if not _TRACING_AVAILABLE:
            return func

        import functools

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            if not tracer:
                return func(*args, **kwargs)

            with tracer.start_as_current_span(name) as span:
                # Log function arguments as attributes safely
                try:
                    if args:
                        span.set_attribute("args.count", len(args))
                    for k, v in kwargs.items():
                        if isinstance(v, (str, bool, int, float)):
                            span.set_attribute(f"param.{k}", v)
                except Exception:
                    pass

                try:
                    result = func(*args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(trace.StatusCode.ERROR, description=str(e))
                    span.record_exception(e)
                    raise
        return wrapper  # type: ignore
    return decorator

"""OpenTelemetry tracing helpers with optional dependencies.

This module is intentionally dependency-soft: if OpenTelemetry packages are not
installed, tracing functions become no-ops and the application continues to run.

Environment variables supported:
- `OTLP_ENDPOINT` or `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` or
  `OTEL_EXPORTER_OTLP_ENDPOINT`
- `OTLP_AUTH_HEADER`: e.g. "Bearer <token>"
- `OTLP_PROJECT_NAME`: optional grouping label

OpenInference tracing controls (read by `openinference.instrumentation.TraceConfig`):
- `OPENINFERENCE_HIDE_INPUTS`, `OPENINFERENCE_HIDE_OUTPUTS`
- `OPENINFERENCE_HIDE_INPUT_MESSAGES`, `OPENINFERENCE_HIDE_OUTPUT_MESSAGES`
- `OPENINFERENCE_HIDE_INPUT_TEXT`, `OPENINFERENCE_HIDE_OUTPUT_TEXT`
- `OPENINFERENCE_HIDE_LLM_INVOCATION_PARAMETERS`
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

_tracer_provider: Any | None = None
_tracing_enabled: bool = False


def _normalize_otlp_http_traces_endpoint(raw: str) -> str:
    endpoint = raw.rstrip("/")
    if endpoint.endswith("/v1/traces"):
        return endpoint
    return f"{endpoint}/v1/traces"


def init_tracing(
    *,
    otlp_endpoint: str | None = None,
    otlp_auth_header: str | None = None,
    project_name: str | None = None,
    service_name: str = "vibe4trading",
) -> None:
    """Initialize OpenTelemetry tracing if dependencies are available."""
    global _tracer_provider, _tracing_enabled

    if not otlp_endpoint:
        _tracing_enabled = False
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:
        _tracing_enabled = False
        return

    headers = {"Authorization": otlp_auth_header} if otlp_auth_header else None

    resource_attrs: dict[str, Any] = {"service.name": service_name}
    if project_name:
        resource_attrs["service.namespace"] = project_name
        try:
            from openinference.semconv.resource import ResourceAttributes

            resource_attrs[ResourceAttributes.PROJECT_NAME] = project_name
        except Exception:
            pass

    existing_provider = trace.get_tracer_provider()
    if hasattr(existing_provider, "add_span_processor"):
        provider = existing_provider
    else:
        provider = TracerProvider(resource=Resource.create(resource_attrs))
        trace.set_tracer_provider(provider)

    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=_normalize_otlp_http_traces_endpoint(otlp_endpoint),
                headers=headers,
                timeout=30,
            ),
            max_queue_size=2048,
            schedule_delay_millis=5000,
            max_export_batch_size=512,
            export_timeout_millis=10000,
        )
    )

    try:
        from openinference.instrumentation import TraceConfig

        config = TraceConfig()

        try:
            from openinference.instrumentation.openai import OpenAIInstrumentor

            OpenAIInstrumentor().instrument(tracer_provider=provider, config=config)
        except Exception:
            pass

    except Exception:
        pass

    _tracer_provider = provider
    _tracing_enabled = True


def shutdown_tracing() -> None:
    """Shutdown the configured tracer provider (if any)."""
    global _tracer_provider, _tracing_enabled

    if not _tracing_enabled or _tracer_provider is None:
        return

    try:
        if hasattr(_tracer_provider, "shutdown"):
            _tracer_provider.shutdown()
    except Exception:
        pass
    finally:
        _tracer_provider = None
        _tracing_enabled = False


def is_tracing_enabled() -> bool:
    return _tracing_enabled


@contextmanager
def create_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[Any | None]:
    """Create a span if tracing is enabled; otherwise behave as a no-op."""
    if not _tracing_enabled or _tracer_provider is None:
        yield None
        return

    try:
        from opentelemetry import trace
    except Exception:
        yield None
        return

    tracer = trace.get_tracer("vibe4trading")
    span_name = f"vibe4trading.{name}"

    with tracer.start_as_current_span(span_name) as span:
        if attributes and hasattr(span, "set_attribute"):
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def record_exception(exc: BaseException) -> None:
    """Record an exception on the current span (if tracing is enabled)."""
    if not _tracing_enabled:
        return

    try:
        from opentelemetry import trace
    except Exception:
        return

    span = trace.get_current_span()
    if span is None:
        return

    if hasattr(span, "record_exception"):
        span.record_exception(exc)
    if hasattr(span, "set_status"):
        try:
            from opentelemetry.trace.status import Status, StatusCode

            span.set_status(Status(StatusCode.ERROR))
        except Exception:
            return


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    """Add an event to the current span (if any)."""
    if not _tracing_enabled:
        return

    try:
        from opentelemetry import trace
    except Exception:
        return

    span = trace.get_current_span()
    if span is None:
        return

    if hasattr(span, "add_event"):
        span.add_event(name, attributes=attributes or {})


def set_span_attributes(attributes: dict[str, Any]) -> None:
    """Set attributes on the current span (if any)."""
    if not _tracing_enabled:
        return

    try:
        from opentelemetry import trace
    except Exception:
        return

    span = trace.get_current_span()
    if span is None:
        return

    if hasattr(span, "set_attribute"):
        for key, value in attributes.items():
            span.set_attribute(key, value)


def capture_context() -> Any:
    """Capture the current context for cross-thread span propagation.

    Returns a ``contextvars.Context`` snapshot.  Use ``ctx.run(fn, *args,
    **kwargs)`` in the worker thread so that child spans are correctly
    parented to the caller's active span.

    Usage with ThreadPoolExecutor::

        ctx = capture_context()
        executor.submit(ctx.run, target_fn, arg1, key=val)
    """
    import contextvars

    return contextvars.copy_context()

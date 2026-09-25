from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import Status, StatusCode

from evidence_graph import __version__
from evidence_graph.config import Settings

TRACER_NAME = "evidencegraph"
_configured = False
_memory = InMemorySpanExporter()

F = TypeVar("F", bound=Callable[..., Any])


def memory_exporter() -> InMemorySpanExporter:
    return _memory


def configure_tracing(
    settings: Settings | None = None, *, force: bool = False
) -> InMemorySpanExporter:
    """Install a process-wide tracer. Always keeps an in-memory exporter for tests."""
    global _configured
    if _configured and not force:
        return _memory
    settings = settings or Settings(_env_file=None)
    resource = Resource.create({"service.name": TRACER_NAME, "service.version": __version__})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(_memory))
    if settings.otel_exporter == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif settings.otel_exporter == "otlp":
        provider.add_span_processor(SimpleSpanProcessor(_otlp_exporter(settings)))
    trace.set_tracer_provider(provider)
    _configured = True
    return _memory


def _otlp_exporter(settings: Settings):
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    except ImportError as exc:
        raise RuntimeError("OTLP export needs `uv sync --extra obs`") from exc
    if settings.otel_endpoint:
        return OTLPSpanExporter(endpoint=settings.otel_endpoint)
    return OTLPSpanExporter()


def tracer() -> trace.Tracer:
    return trace.get_tracer(TRACER_NAME)


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    with tracer().start_as_current_span(name) as current:
        for key, value in attributes.items():
            if value is not None:
                current.set_attribute(key, value)
        try:
            yield current
        except Exception as exc:
            current.record_exception(exc)
            current.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
            raise


def traced_node(name: str, fn: F) -> F:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):
        attrs: dict[str, Any] = {}
        first = args[0] if args else None
        if isinstance(first, dict) and first.get("country") is not None:
            attrs["country"] = str(first["country"])
        with span(f"node.{name}", **attrs):
            return fn(*args, **kwargs)

    return wrapper  # type: ignore[return-value]

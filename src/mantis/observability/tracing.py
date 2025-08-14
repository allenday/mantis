"""
OpenTelemetry Distributed Tracing for Mantis Agent Coordination

This module provides distributed tracing capabilities across the multi-agent system,
enabling end-to-end observability of agent coordination workflows.
"""

import os
from typing import Optional, Dict, Any, Callable, Generator
from contextlib import contextmanager
from functools import wraps

# Import logger here to avoid E402 - must be before try/except block
from .logger import get_structured_logger

# Optional OpenTelemetry imports - gracefully handle missing dependencies
try:
    from opentelemetry import trace, baggage  # type: ignore[import-untyped]
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore[import-untyped,import-not-found]
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-untyped,import-not-found]
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter  # type: ignore[import-untyped,import-not-found]
    from opentelemetry.sdk.resources import Resource  # type: ignore[import-untyped,import-not-found]
    from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor  # type: ignore[import-untyped,import-not-found]
    from opentelemetry.instrumentation.requests import RequestsInstrumentor  # type: ignore[import-untyped,import-not-found]
    from opentelemetry.propagators.b3 import B3MultiFormat  # type: ignore[import-untyped,import-not-found]
    from opentelemetry.propagate import set_global_textmap  # type: ignore[import-untyped]

    OTEL_AVAILABLE = True
except ImportError:
    # OpenTelemetry not available - create stub classes and functions
    OTEL_AVAILABLE = False

    # Create minimal stub classes for type hints
    class trace:  # type: ignore[no-redef]
        class Tracer:
            def start_as_current_span(self, *args: Any, **kwargs: Any) -> "_NoOpContextManager":
                return _NoOpContextManager()

        class StatusCode:  # type: ignore[no-redef]
            OK = "OK"
            ERROR = "ERROR"

        class Status:  # type: ignore[no-redef]
            def __init__(self, status_code: Any, description: Any = None) -> None:
                pass

        @staticmethod
        def set_tracer_provider(*args: Any, **kwargs: Any) -> None:
            pass

        @staticmethod
        def get_tracer(*args: Any, **kwargs: Any) -> "trace.Tracer":
            return trace.Tracer()  # type: ignore[abstract]

        @staticmethod
        def get_current_span(*args: Any, **kwargs: Any) -> "_NoOpContextManager":
            return _NoOpContextManager()

    class baggage:  # type: ignore[no-redef]
        @staticmethod
        def set_baggage(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {}

        @staticmethod
        def get_baggage(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {}

    # Stub classes for OpenTelemetry components
    class TracerProvider:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def add_span_processor(self, *args: Any, **kwargs: Any) -> None:
            pass

    class Resource:  # type: ignore[no-redef]
        def __init__(self) -> None:
            pass

        @staticmethod
        def create(*args: Any, **kwargs: Any) -> "Resource":
            return Resource()  # type: ignore[call-arg]

    class BatchSpanProcessor:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class ConsoleSpanExporter:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class OTLPSpanExporter:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class AioHttpClientInstrumentor:  # type: ignore[no-redef]
        @staticmethod
        def instrument() -> None:
            pass

        @staticmethod
        def uninstrument() -> None:
            pass

    class RequestsInstrumentor:  # type: ignore[no-redef]
        @staticmethod
        def instrument() -> None:
            pass

        @staticmethod
        def uninstrument() -> None:
            pass

    class B3MultiFormat:  # type: ignore[no-redef]
        pass

    def set_global_textmap(*args: Any, **kwargs: Any) -> None:  # type: ignore[no-redef,misc]
        pass


class _NoOpContextManager:
    """No-op context manager for when OpenTelemetry is not available."""

    def __enter__(self) -> "_NoOpContextManager":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def set_attribute(self, *args: Any, **kwargs: Any) -> None:
        pass

    def add_event(self, *args: Any, **kwargs: Any) -> None:
        pass

    def record_exception(self, *args: Any, **kwargs: Any) -> None:
        pass

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        pass


logger = get_structured_logger(__name__)


class MantisTracer:
    """
    Mantis-specific OpenTelemetry tracer configuration.

    Provides distributed tracing across agent coordination workflows with:
    - Cross-service trace propagation
    - Agent-specific span attributes
    - Integration with existing structured logging
    - Support for multiple exporters (OTLP, Jaeger, Console)
    """

    def __init__(self, service_name: str, service_version: str = "1.0.0"):
        """Initialize Mantis tracer with service identification."""
        self.service_name = service_name
        self.service_version = service_version
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer: Optional[trace.Tracer] = None
        self._initialize_tracing()

    def _initialize_tracing(self) -> None:
        """Initialize OpenTelemetry tracing with Mantis-specific configuration."""
        if not OTEL_AVAILABLE:
            logger.warning("OpenTelemetry not available - tracing disabled")
            self.tracer = trace.get_tracer(self.service_name)  # Will be no-op stub
            return

        try:
            # Create resource with service identification
            resource = Resource.create(
                {
                    "service.name": self.service_name,
                    "service.version": self.service_version,
                    "service.namespace": "mantis.ai",
                    "deployment.environment": os.environ.get("MANTIS_ENV", "development"),
                }
            )

            # Create tracer provider
            self.tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self.tracer_provider)

            # Configure exporters based on environment
            self._configure_exporters()

            # Set up trace propagation
            set_global_textmap(B3MultiFormat())

            # Get tracer instance
            self.tracer = trace.get_tracer(
                instrumenting_module_name="mantis.observability.tracing",
                instrumenting_library_version=self.service_version,
            )

            # Auto-instrument HTTP clients for agent-to-agent communication
            AioHttpClientInstrumentor().instrument()
            RequestsInstrumentor().instrument()

            logger.info(
                "OpenTelemetry tracing initialized for Mantis",
                structured_data={
                    "service_name": self.service_name,
                    "service_version": self.service_version,
                    "environment": os.environ.get("MANTIS_ENV", "development"),
                },
            )

        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry tracing: {e}")
            # Continue without tracing rather than failing
            self.tracer = trace.get_tracer("mantis.no-op")

    def _configure_exporters(self) -> None:
        """Configure span exporters based on environment variables."""
        if not self.tracer_provider:
            return

        # OTLP Exporter (preferred for production)
        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers={
                    "Authorization": f"Bearer {os.environ.get('OTEL_EXPORTER_OTLP_TOKEN', '')}",
                },
            )
            self.tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP exporter configured: {otlp_endpoint}")

        # Jaeger Exporter removed due to Python 3.13 compatibility issues
        # Use OTLP exporter instead for Jaeger integration via collector
        jaeger_endpoint = os.environ.get("JAEGER_COLLECTOR_ENDPOINT")
        if jaeger_endpoint:
            logger.info("Jaeger exporter disabled - use OTLP exporter with collector instead")

        # Console Exporter (development/debugging)
        if os.environ.get("OTEL_CONSOLE_EXPORTER", "false").lower() == "true":
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("Console exporter enabled for debugging")

        # Default to console if no other exporters configured
        if not any([otlp_endpoint, jaeger_endpoint]):
            console_exporter = ConsoleSpanExporter()
            self.tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("No exporters configured, using console exporter as default")

    @contextmanager
    def start_span(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[Any, None, None]:
        """Start a new span with Mantis-specific attributes."""
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(name) as span:
            # Add default Mantis attributes
            span.set_attribute("mantis.service", self.service_name)
            span.set_attribute("mantis.version", self.service_version)

            # Add custom attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)

            yield span

    def trace_agent_call(self, agent_name: str, operation: str = "process") -> Callable:
        """Decorator for tracing agent method calls."""

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.start_span(
                    f"agent.{operation}",
                    attributes={
                        "agent.name": agent_name,
                        "agent.operation": operation,
                        "mantis.component": "agent",
                    },
                ) as span:
                    try:
                        result = await func(*args, **kwargs)
                        if span:
                            span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        if span:
                            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                            span.record_exception(e)
                        raise

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with self.start_span(
                    f"agent.{operation}",
                    attributes={
                        "agent.name": agent_name,
                        "agent.operation": operation,
                        "mantis.component": "agent",
                    },
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        if span:
                            span.set_status(trace.Status(trace.StatusCode.OK))
                        return result
                    except Exception as e:
                        if span:
                            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                            span.record_exception(e)
                        raise

            return async_wrapper if hasattr(func, "__code__") and func.__code__.co_flags & 0x80 else sync_wrapper

        return decorator

    def add_agent_context(self, agent_id: str, agent_name: str, context_id: str) -> None:
        """Add agent context to current trace baggage."""
        baggage.set_baggage("agent.id", agent_id)
        baggage.set_baggage("agent.name", agent_name)
        baggage.set_baggage("context.id", context_id)

    def get_trace_context(self) -> Dict[str, str]:
        """Get current trace context for propagation to other services."""
        carrier: Dict[str, str] = {}
        trace.get_current_span().get_span_context()
        # TODO: Implement proper trace context extraction
        return carrier


# Global tracer instances
_tracers: Dict[str, MantisTracer] = {}


def get_tracer(service_name: str, service_version: str = "1.0.0") -> MantisTracer:
    """Get or create a tracer for the specified service."""
    tracer_key = f"{service_name}:{service_version}"

    if tracer_key not in _tracers:
        _tracers[tracer_key] = MantisTracer(service_name, service_version)

    return _tracers[tracer_key]


def trace_simulation(context_id: str, execution_strategy: str = "unknown") -> Callable:
    """Decorator for tracing complete simulation workflows."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer("mantis.orchestrator")
            with tracer.start_span(
                "simulation.execute",
                attributes={
                    "simulation.context_id": context_id,
                    "simulation.execution_strategy": execution_strategy,
                    "mantis.component": "orchestrator",
                },
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    if span:
                        span.set_status(trace.Status(trace.StatusCode.OK))
                        # Add result metadata
                        if hasattr(result, "final_state"):
                            span.set_attribute("simulation.final_state", str(result.final_state))
                        if hasattr(result, "team_size"):
                            span.set_attribute("simulation.team_size", result.team_size)
                    return result
                except Exception as e:
                    if span:
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer("mantis.orchestrator")
            with tracer.start_span(
                "simulation.execute",
                attributes={
                    "simulation.context_id": context_id,
                    "simulation.execution_strategy": execution_strategy,
                    "mantis.component": "orchestrator",
                },
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    if span:
                        span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as e:
                    if span:
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                    raise

        return async_wrapper if hasattr(func, "__code__") and func.__code__.co_flags & 0x80 else sync_wrapper

    return decorator

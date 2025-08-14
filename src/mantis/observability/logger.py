"""
Structured logging infrastructure for comprehensive observability.

This module provides structured logging with JSON serialization, trace context
integration, and configurable filtering for the Mantis observability system.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel

# OpenTelemetry trace correlation (optional import)
try:
    from opentelemetry import trace
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

from .context import get_current_trace_id, get_execution_context
from .models import ToolInvocation, LLMInteraction, ExecutionTrace


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self) -> None:
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""

        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add trace context if available
        trace_id = get_current_trace_id()
        if trace_id:
            log_data["trace_id"] = trace_id

        # Add OpenTelemetry trace correlation
        if OTEL_AVAILABLE:
            span = trace.get_current_span()
            if span.is_recording():
                span_context = span.get_span_context()
                log_data["otel_trace_id"] = f"{span_context.trace_id:032x}"
                log_data["otel_span_id"] = f"{span_context.span_id:016x}"

        # Add execution context
        exec_context = get_execution_context()
        if exec_context:
            log_data["execution_context"] = exec_context

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add structured data if present
        if hasattr(record, "structured_data"):
            log_data["structured_data"] = record.structured_data

        # Add observability event data if present
        if hasattr(record, "observability_event"):
            event_data = record.observability_event
            if isinstance(event_data, BaseModel):
                log_data["observability_event"] = event_data.model_dump()
            else:
                log_data["observability_event"] = event_data

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ObservabilityLogger:
    """Enhanced logger for observability with structured data support."""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(f"mantis.observability.{name}")
        self.logger.setLevel(level)

        # Remove existing handlers to avoid duplicates
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        # Add structured handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)

        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False

    def _log_with_data(
        self,
        level: int,
        message: str,
        structured_data: Optional[Dict[str, Any]] = None,
        observability_event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ) -> None:
        """Log with structured data."""
        extra: Dict[str, Any] = {}
        if structured_data:
            extra["structured_data"] = structured_data
        if observability_event:
            extra["observability_event"] = observability_event

        self.logger.log(level, message, extra=extra)

    def debug(
        self,
        message: str,
        structured_data: Optional[Dict[str, Any]] = None,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ) -> None:
        """Log debug message with structured data."""
        self._log_with_data(logging.DEBUG, message, structured_data, event)

    def info(
        self,
        message: str,
        structured_data: Optional[Dict[str, Any]] = None,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ) -> None:
        """Log info message with structured data."""
        self._log_with_data(logging.INFO, message, structured_data, event)

    def warning(
        self,
        message: str,
        structured_data: Optional[Dict[str, Any]] = None,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ) -> None:
        """Log warning message with structured data."""
        self._log_with_data(logging.WARNING, message, structured_data, event)

    def error(
        self,
        message: str,
        structured_data: Optional[Dict[str, Any]] = None,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
        exc_info: bool = False,
    ) -> None:
        """Log error message with structured data."""
        self._log_with_data(logging.ERROR, message, structured_data, event)
        if exc_info:
            self.logger.error(message, exc_info=True)

    def critical(
        self,
        message: str,
        structured_data: Optional[Dict[str, Any]] = None,
        event: Optional[Union[BaseModel, Dict[str, Any]]] = None,
    ) -> None:
        """Log critical message with structured data."""
        self._log_with_data(logging.CRITICAL, message, structured_data, event)

    def log_execution_trace(self, trace: ExecutionTrace) -> None:
        """Log an execution trace."""
        self.info(
            f"Execution trace: {trace.operation} [{trace.status.value}]",
            structured_data={
                "trace_id": trace.trace_id,
                "parent_trace_id": trace.parent_trace_id,
                "duration_ms": trace.duration_ms,
                "component": trace.component,
            },
            event=trace,
        )

    def log_tool_invocation(self, invocation: ToolInvocation) -> None:
        """Log a tool invocation with explicit markers."""
        # Use CRITICAL level for actual tool invocations to ensure visibility
        log_level = logging.CRITICAL if invocation.invocation_type == "ACTUAL" else logging.INFO

        message = f"TOOL_INVOKED: {invocation.tool_name}.{invocation.method} [{invocation.invocation_type.value}]"

        self._log_with_data(
            log_level,
            message,
            structured_data={
                "tool_name": invocation.tool_name,
                "method": invocation.method,
                "invocation_type": invocation.invocation_type.value,
                "execution_time_ms": invocation.execution_time_ms,
                "trace_id": invocation.trace_id,
            },
            observability_event=invocation,
        )

    def log_llm_interaction(self, interaction: LLMInteraction) -> None:
        """Log an LLM interaction."""
        self.info(
            f"LLM interaction: {interaction.model_spec} [{interaction.execution_time_ms:.2f}ms]",
            structured_data={
                "model_spec": interaction.model_spec,
                "provider": interaction.provider,
                "execution_time_ms": interaction.execution_time_ms,
                "token_count": interaction.token_count,
                "trace_id": interaction.trace_id,
                "system_prompt_length": len(interaction.system_prompt),
                "user_prompt_length": len(interaction.user_prompt),
                "response_length": len(interaction.response),
            },
            event=interaction,
        )


# Global logger instances
_loggers: Dict[str, ObservabilityLogger] = {}


def get_structured_logger(name: str, level: int = logging.INFO) -> ObservabilityLogger:
    """Get or create a structured logger instance."""
    if name not in _loggers:
        _loggers[name] = ObservabilityLogger(name, level)
    return _loggers[name]


def configure_observability_logging(level: int = logging.INFO, enable_debug: bool = False) -> None:
    """Configure global observability logging settings."""
    if enable_debug:
        level = logging.DEBUG

    # Configure root logger for mantis.observability
    root_logger = logging.getLogger("mantis.observability")
    root_logger.setLevel(level)

    # Update all existing loggers
    for logger in _loggers.values():
        logger.logger.setLevel(level)

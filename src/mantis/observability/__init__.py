"""
Observability infrastructure for comprehensive execution tracing and monitoring.

This module provides structured logging, execution tracing, and performance monitoring
for the Mantis system to enable full visibility into tool invocations, LLM interactions,
and execution flows.
"""

from .models import (
    ExecutionTrace,
    ToolInvocation,
    LLMInteraction,
    PromptComposition,
    ExecutionMetadata,
    ExecutionStatus,
    InvocationType,
)
from .logger import get_structured_logger, ObservabilityLogger, configure_observability_logging
from .tracer import trace_execution, trace_tool_invocation, trace_llm_interaction, get_current_trace_id
from .context import ExecutionContext, get_execution_context, set_execution_context

__all__ = [
    # Models
    "ExecutionTrace",
    "ToolInvocation",
    "LLMInteraction",
    "PromptComposition",
    "ExecutionMetadata",
    "ExecutionStatus",
    "InvocationType",
    # Logger
    "get_structured_logger",
    "ObservabilityLogger",
    "configure_observability_logging",
    # Tracer
    "trace_execution",
    "trace_tool_invocation",
    "trace_llm_interaction",
    "get_current_trace_id",
    # Context
    "ExecutionContext",
    "get_execution_context",
    "set_execution_context",
]

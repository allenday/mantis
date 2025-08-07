"""
Execution context management for tracing across async operations.

This module provides context variables and utilities to propagate execution
context and trace information across async boundaries in the Mantis system.
"""

import contextvars
from typing import Optional, Dict, Any
from .models import ExecutionTrace


# Context variable for the current execution trace
_current_trace: contextvars.ContextVar[Optional[ExecutionTrace]] = contextvars.ContextVar("current_trace", default=None)

# Context variable for execution metadata
_execution_metadata: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar("execution_metadata", default={})


class ExecutionContext:
    """Execution context manager for tracing operations."""

    def __init__(self, trace: ExecutionTrace, metadata: Optional[Dict[str, Any]] = None):
        self.trace = trace
        self.metadata = metadata or {}
        self._trace_token: Optional[contextvars.Token] = None
        self._metadata_token: Optional[contextvars.Token] = None

    def __enter__(self):
        """Enter the execution context."""
        self._trace_token = _current_trace.set(self.trace)
        self._metadata_token = _execution_metadata.set(self.metadata)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the execution context."""
        if self._trace_token:
            _current_trace.reset(self._trace_token)
        if self._metadata_token:
            _execution_metadata.reset(self._metadata_token)

        # Mark trace as complete if there was an exception
        if exc_type is not None:
            from .models import ExecutionStatus

            self.trace.mark_complete(status=ExecutionStatus.FAILED, error=f"{exc_type.__name__}: {exc_val}")


def get_current_trace() -> Optional[ExecutionTrace]:
    """Get the current execution trace from context."""
    return _current_trace.get(None)


def set_current_trace(trace: ExecutionTrace) -> contextvars.Token:
    """Set the current execution trace in context."""
    return _current_trace.set(trace)


def get_execution_context() -> Dict[str, Any]:
    """Get the current execution metadata context."""
    return _execution_metadata.get({}).copy()


def set_execution_context(metadata: Dict[str, Any]) -> contextvars.Token:
    """Set execution metadata in context."""
    return _execution_metadata.set(metadata)


def update_execution_context(updates: Dict[str, Any]) -> None:
    """Update the current execution context with new metadata."""
    current = _execution_metadata.get({})
    current.update(updates)
    _execution_metadata.set(current)


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID from context."""
    trace = get_current_trace()
    return trace.trace_id if trace else None


def create_child_trace(operation: str, component: str, metadata: Optional[Dict[str, Any]] = None) -> ExecutionTrace:
    """Create a child trace from the current trace context."""
    parent_trace = get_current_trace()
    parent_trace_id = parent_trace.trace_id if parent_trace else None

    return ExecutionTrace(
        parent_trace_id=parent_trace_id, operation=operation, component=component, metadata=metadata or {}
    )

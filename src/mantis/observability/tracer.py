"""
Tracing decorators and utilities for execution flow monitoring.

This module provides decorators and context managers for automatic tracing
of function calls, tool invocations, and LLM interactions.
"""

import functools
import asyncio
from typing import Callable, Any, Dict, Optional, TypeVar, cast, Union

from .models import ToolInvocation, LLMInteraction, ExecutionStatus, InvocationType
from .context import ExecutionContext, create_child_trace, get_current_trace_id
from .logger import get_structured_logger

F = TypeVar("F", bound=Callable[..., Any])

# Global logger for tracing
tracer_logger = get_structured_logger("tracer")


def trace_execution(
    operation: str, component: str, include_args: bool = False, include_result: bool = False
) -> Callable[[F], F]:
    """
    Decorator to trace function execution with timing and context.

    Args:
        operation: Name of the operation being traced
        component: Component performing the operation
        include_args: Whether to include function arguments in trace
        include_result: Whether to include function result in trace
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create child trace from current context
            trace = create_child_trace(operation, component)

            # Add function arguments if requested
            if include_args:
                trace.metadata["args"] = {
                    "args": [str(arg)[:100] for arg in args],  # Truncate long args
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
                }

            tracer_logger.debug(f"Starting execution: {operation}", event=trace)

            try:
                with ExecutionContext(trace):
                    result = await func(*args, **kwargs)

                    # Add result if requested
                    if include_result and result is not None:
                        trace.metadata["result"] = str(result)[:200]  # Truncate long results

                    trace.mark_complete(ExecutionStatus.SUCCESS)
                    tracer_logger.debug(f"Completed execution: {operation}", event=trace)
                    return result

            except Exception as e:
                trace.mark_complete(ExecutionStatus.FAILED, str(e))
                tracer_logger.error(f"Failed execution: {operation}", event=trace, exc_info=True)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create child trace from current context
            trace = create_child_trace(operation, component)

            # Add function arguments if requested
            if include_args:
                trace.metadata["args"] = {
                    "args": [str(arg)[:100] for arg in args],
                    "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
                }

            tracer_logger.debug(f"Starting execution: {operation}", event=trace)

            try:
                with ExecutionContext(trace):
                    result = func(*args, **kwargs)

                    # Add result if requested
                    if include_result and result is not None:
                        trace.metadata["result"] = str(result)[:200]

                    trace.mark_complete(ExecutionStatus.SUCCESS)
                    tracer_logger.debug(f"Completed execution: {operation}", event=trace)
                    return result

            except Exception as e:
                trace.mark_complete(ExecutionStatus.FAILED, str(e))
                tracer_logger.error(f"Failed execution: {operation}", event=trace, exc_info=True)
                raise

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


def trace_tool_invocation(tool_name: str, method: str, parameters: Optional[Dict[str, Any]] = None) -> ToolInvocation:
    """
    Create and start tracking a tool invocation.

    Args:
        tool_name: Name of the tool being invoked
        method: Method being called on the tool
        parameters: Parameters passed to the tool method

    Returns:
        ToolInvocation object for tracking the invocation
    """
    trace_id = get_current_trace_id() or "no-trace"

    invocation = ToolInvocation(
        trace_id=trace_id,
        tool_name=tool_name,
        method=method,
        parameters=parameters or {},
        invocation_type=InvocationType.ACTUAL,  # Assume actual unless marked otherwise
    )

    tracer_logger.info(f"Starting tool invocation: {tool_name}.{method}")
    return invocation


def complete_tool_invocation(
    invocation: ToolInvocation, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None
) -> None:
    """
    Complete a tool invocation and log the result.

    Args:
        invocation: ToolInvocation object to complete
        result: Result data from the tool invocation
        error: Error message if the invocation failed
    """
    invocation.mark_complete(result, error)
    tracer_logger.log_tool_invocation(invocation)


def trace_llm_interaction(
    model_spec: str, provider: str, system_prompt: str, user_prompt: str, **metadata: Any
) -> LLMInteraction:
    """
    Create and start tracking an LLM interaction.

    Args:
        model_spec: LLM model specification
        provider: LLM provider name
        system_prompt: System prompt sent to LLM
        user_prompt: User prompt sent to LLM
        **metadata: Additional metadata for the interaction

    Returns:
        LLMInteraction object for tracking the interaction
    """
    trace_id = get_current_trace_id() or "no-trace"

    interaction = LLMInteraction(
        trace_id=trace_id,
        model_spec=model_spec,
        provider=provider,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response="",  # Will be filled when completed
        **metadata,
    )

    tracer_logger.info(f"Starting LLM interaction: {model_spec}")
    return interaction


def complete_llm_interaction(
    interaction: LLMInteraction, response: str, error: Optional[str] = None, token_count: Optional[int] = None
) -> None:
    """
    Complete an LLM interaction and log the result.

    Args:
        interaction: LLMInteraction object to complete
        response: Response from the LLM
        error: Error message if the interaction failed
        token_count: Token count if available
    """
    interaction.mark_complete(response, error, token_count)
    tracer_logger.log_llm_interaction(interaction)


class ToolInvocationContext:
    """Context manager for tool invocation tracing."""

    def __init__(self, tool_name: str, method: str, parameters: Optional[Dict[str, Any]] = None):
        self.invocation = trace_tool_invocation(tool_name, method, parameters)

    def __enter__(self) -> ToolInvocation:
        return self.invocation

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        if exc_type is not None:
            complete_tool_invocation(self.invocation, error=f"{exc_type.__name__}: {exc_val}")
        else:
            complete_tool_invocation(self.invocation)


class LLMInteractionContext:
    """Context manager for LLM interaction tracing."""

    def __init__(self, model_spec: str, provider: str, system_prompt: str, user_prompt: str, **metadata: Any) -> None:
        self.interaction = trace_llm_interaction(model_spec, provider, system_prompt, user_prompt, **metadata)

    def __enter__(self) -> LLMInteraction:
        return self.interaction

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        if exc_type is not None:
            complete_llm_interaction(self.interaction, "", error=f"{exc_type.__name__}: {exc_val}")

"""
Pydantic models for observability data structures.

These models define the structured data formats for execution tracing,
tool invocation tracking, LLM interaction logging, and performance metrics.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Execution status enumeration."""

    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class InvocationType(str, Enum):
    """Tool invocation type enumeration."""

    ACTUAL = "ACTUAL"  # Tool was actually called
    SIMULATED = "SIMULATED"  # Tool call was simulated
    FAILED = "FAILED"  # Tool call failed
    CACHED = "CACHED"  # Result from cache


class ExecutionTrace(BaseModel):
    """Main execution trace for tracking operations."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique trace identifier")
    parent_trace_id: Optional[str] = Field(None, description="Parent trace ID for nested operations")
    operation: str = Field(..., description="Operation being traced")
    component: str = Field(..., description="Component performing the operation")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Operation start time")
    end_time: Optional[datetime] = Field(None, description="Operation end time")
    duration_ms: Optional[float] = Field(None, description="Operation duration in milliseconds")
    status: ExecutionStatus = Field(ExecutionStatus.IN_PROGRESS, description="Execution status")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def mark_complete(self, status: ExecutionStatus = ExecutionStatus.SUCCESS, error: Optional[str] = None) -> None:
        """Mark trace as complete with timing information."""
        self.end_time = datetime.utcnow()
        self.status = status
        if error:
            self.error = error
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000


class ToolInvocation(BaseModel):
    """Detailed tracking of tool invocations."""

    trace_id: str = Field(..., description="Associated trace ID")
    tool_name: str = Field(..., description="Name of the tool")
    method: str = Field(..., description="Tool method being called")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    invocation_type: InvocationType = Field(..., description="Type of invocation")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Invocation start time")
    end_time: Optional[datetime] = Field(None, description="Invocation end time")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional tool metadata")

    def mark_complete(self, result: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        """Mark tool invocation as complete."""
        self.end_time = datetime.utcnow()
        if result is not None:
            self.result = result
        if error:
            self.error = error
            self.invocation_type = InvocationType.FAILED
        if self.start_time and self.end_time:
            self.execution_time_ms = (self.end_time - self.start_time).total_seconds() * 1000


class LLMInteraction(BaseModel):
    """Comprehensive LLM interaction logging."""

    trace_id: str = Field(..., description="Associated trace ID")
    model_spec: str = Field(..., description="LLM model specification")
    provider: str = Field(..., description="LLM provider")
    system_prompt: str = Field(..., description="System prompt sent to LLM")
    user_prompt: str = Field(..., description="User prompt sent to LLM")
    response: str = Field(..., description="LLM response")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Interaction start time")
    end_time: Optional[datetime] = Field(None, description="Interaction end time")
    execution_time_ms: Optional[float] = Field(None, description="LLM call duration in milliseconds")
    token_count: Optional[int] = Field(None, description="Token count if available")
    temperature: Optional[float] = Field(None, description="Model temperature setting")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens setting")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional LLM metadata")

    def mark_complete(self, response: str, error: Optional[str] = None, token_count: Optional[int] = None) -> None:
        """Mark LLM interaction as complete."""
        self.end_time = datetime.utcnow()
        self.response = response
        if error:
            self.error = error
        if token_count:
            self.token_count = token_count
        if self.start_time and self.end_time:
            self.execution_time_ms = (self.end_time - self.start_time).total_seconds() * 1000


class PromptComposition(BaseModel):
    """Track prompt composition and module usage."""

    trace_id: str = Field(..., description="Associated trace ID")
    strategy: str = Field(..., description="Composition strategy used")
    modules_used: List[str] = Field(default_factory=list, description="List of prompt modules used")
    variables_resolved: int = Field(0, description="Number of variables resolved")
    final_prompt_length: int = Field(0, description="Length of final composed prompt")
    composition_time_ms: float = Field(..., description="Time spent composing prompt")
    agent_card_name: Optional[str] = Field(None, description="Name of agent card used")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional composition metadata")


class ExecutionMetadata(BaseModel):
    """High-level execution metadata and performance metrics."""

    trace_id: str = Field(..., description="Root trace ID")
    total_execution_time_ms: float = Field(..., description="Total execution time")
    tool_invocations: int = Field(0, description="Number of tool invocations")
    llm_interactions: int = Field(0, description="Number of LLM interactions")
    prompt_compositions: int = Field(0, description="Number of prompt compositions")
    team_size: int = Field(1, description="Size of agent team")
    recursion_depth: int = Field(0, description="Maximum recursion depth reached")
    execution_strategy: str = Field(..., description="Execution strategy used")
    success: bool = Field(..., description="Overall execution success")
    error: Optional[str] = Field(None, description="Overall error message if failed")
    performance_metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics")
    resource_usage: Dict[str, Any] = Field(default_factory=dict, description="Resource usage information")


class ObservabilityEvent(BaseModel):
    """Generic observability event for structured logging."""

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    trace_id: Optional[str] = Field(None, description="Associated trace ID")
    component: str = Field(..., description="Component generating the event")
    event_type: str = Field(..., description="Type of observability event")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured event data")
    tags: List[str] = Field(default_factory=list, description="Event tags for filtering")

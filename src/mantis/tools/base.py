"""
Base tool class for Mantis tools with agent attribution and observability.

Provides consistent logging and agent context tracking across all tools.
"""

import contextvars
from typing import Dict, Any, Optional
from abc import ABC

# Observability imports
try:
    from ..observability import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

# Context variable for agent attribution - matches orchestrator
current_agent_context: contextvars.ContextVar[Dict[str, str]] = contextvars.ContextVar('current_agent_context', default={})


class BaseTool(ABC):
    """
    Base class for all Mantis tools providing consistent agent attribution.
    
    Handles:
    - Agent context extraction from contextvars
    - Structured logging with agent attribution
    - Tool invocation tracking
    - Error handling with observability
    """
    
    def __init__(self, tool_name: str):
        """Initialize base tool with consistent logging."""
        self.tool_name = tool_name
        if OBSERVABILITY_AVAILABLE:
            self.logger = get_structured_logger(f"tools.{tool_name}")
        else:
            self.logger = None
    
    def get_agent_context(self) -> Dict[str, str]:
        """Get current agent context for attribution."""
        return current_agent_context.get({})
    
    def log_tool_invocation(self, method_name: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Log tool invocation with agent attribution."""
        if not self.logger:
            return
            
        agent_ctx = self.get_agent_context()
        log_data = {
            "agent_id": agent_ctx.get('agent_id', 'unknown'),
            "agent_name": agent_ctx.get('agent_name', 'unknown'),
            "task_id": agent_ctx.get('task_id', 'unknown'),
            "context_id": agent_ctx.get('context_id', 'unknown'),
            "tool_name": self.tool_name,
            "method_name": method_name
        }
        
        if params:
            log_data["tool_params"] = params
            
        self.logger.info(
            f"🎯 TOOL_INVOKED: {method_name} by {agent_ctx.get('agent_name', 'unknown')}",
            structured_data=log_data
        )
    
    def log_tool_result(self, method_name: str, result_info: Optional[Dict[str, Any]] = None) -> None:
        """Log tool result with agent attribution."""
        if not self.logger:
            return
            
        agent_ctx = self.get_agent_context()
        log_data = {
            "agent_id": agent_ctx.get('agent_id', 'unknown'),
            "agent_name": agent_ctx.get('agent_name', 'unknown'),
            "task_id": agent_ctx.get('task_id', 'unknown'),
            "context_id": agent_ctx.get('context_id', 'unknown'),
            "tool_name": self.tool_name,
            "method_name": method_name
        }
        
        if result_info:
            log_data.update(result_info)
            
        self.logger.info(
            f"✅ TOOL_COMPLETED: {method_name} by {agent_ctx.get('agent_name', 'unknown')}",
            structured_data=log_data
        )
    
    def log_tool_error(self, method_name: str, error: Exception) -> None:
        """Log tool error with agent attribution."""
        if not self.logger:
            return
            
        agent_ctx = self.get_agent_context()
        self.logger.error(
            f"❌ TOOL_ERROR: {method_name} by {agent_ctx.get('agent_name', 'unknown')}",
            structured_data={
                "agent_id": agent_ctx.get('agent_id', 'unknown'),
                "agent_name": agent_ctx.get('agent_name', 'unknown'),
                "task_id": agent_ctx.get('task_id', 'unknown'),
                "context_id": agent_ctx.get('context_id', 'unknown'),
                "tool_name": self.tool_name,
                "method_name": method_name,
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        )


# Standalone functions for tools that can't inherit from BaseTool
def log_tool_invocation(tool_name: str, method_name: str, params: Optional[Dict[str, Any]] = None) -> None:
    """Standalone function to log tool invocation with agent attribution."""
    if not OBSERVABILITY_AVAILABLE:
        return
        
    logger = get_structured_logger(f"tools.{tool_name}")
    agent_ctx = current_agent_context.get({})
    
    log_data = {
        "agent_id": agent_ctx.get('agent_id', 'unknown'),
        "agent_name": agent_ctx.get('agent_name', 'unknown'),
        "task_id": agent_ctx.get('task_id', 'unknown'),
        "context_id": agent_ctx.get('context_id', 'unknown'),
        "tool_name": tool_name,
        "method_name": method_name
    }
    
    if params:
        log_data["tool_params"] = params
        
    logger.info(
        f"🎯 TOOL_INVOKED: {method_name} by {agent_ctx.get('agent_name', 'unknown')}",
        structured_data=log_data
    )


def log_tool_result(tool_name: str, method_name: str, result_info: Optional[Dict[str, Any]] = None) -> None:
    """Standalone function to log tool result with agent attribution."""
    if not OBSERVABILITY_AVAILABLE:
        return
        
    logger = get_structured_logger(f"tools.{tool_name}")
    agent_ctx = current_agent_context.get({})
    
    log_data = {
        "agent_id": agent_ctx.get('agent_id', 'unknown'),
        "agent_name": agent_ctx.get('agent_name', 'unknown'),
        "task_id": agent_ctx.get('task_id', 'unknown'),
        "context_id": agent_ctx.get('context_id', 'unknown'),
        "tool_name": tool_name,
        "method_name": method_name
    }
    
    if result_info:
        log_data.update(result_info)
        
    logger.info(
        f"✅ TOOL_COMPLETED: {method_name} by {agent_ctx.get('agent_name', 'unknown')}",
        structured_data=log_data
    )
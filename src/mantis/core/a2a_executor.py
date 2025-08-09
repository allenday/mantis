"""
A2A executor for distributed agent execution.

This is a stub implementation that will be fully implemented when A2A integration is complete.
For now, it prevents import errors in the abstract patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from ..proto.mantis.v1 import mantis_core_pb2
from .executor import ExecutionStrategy


class A2AExecutor(ExecutionStrategy):
    """A2A execution using distributed agents via A2A protocol."""

    def __init__(self):
        self._a2a_client = None
        self._registry_client = None
        
    async def execute_agent(
        self, simulation_input: mantis_core_pb2.SimulationInput, agent_spec: mantis_core_pb2.AgentSpec, agent_index: int
    ) -> mantis_core_pb2.AgentResponse:
        """Execute agent using A2A protocol - stub implementation."""
        # TODO: Implement A2A distributed execution
        # This would:
        # 1. Use A2A registry to find appropriate agent
        # 2. Send message via A2A protocol
        # 3. Wait for response and convert to AgentResponse
        
        raise NotImplementedError("A2A execution not yet implemented - use EXECUTION_STRATEGY_DIRECT for now")

    def get_strategy_type(self) -> mantis_core_pb2.ExecutionStrategy:
        """Return the A2A strategy type."""
        return mantis_core_pb2.EXECUTION_STRATEGY_A2A
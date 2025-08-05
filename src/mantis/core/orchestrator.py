"""
Core simulation orchestrator for executing multi-agent scenarios.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..proto.mantis.v1 import mantis_core_pb2
from ..config import DEFAULT_MODEL, DEFAULT_TEMPERATURE


class ExecutionStrategy(ABC):
    """Abstract base class for execution strategies."""
    
    @abstractmethod
    async def execute_agent(
        self, 
        simulation_input: mantis_core_pb2.SimulationInput,
        agent_spec: mantis_core_pb2.AgentSpec,
        agent_index: int
    ) -> mantis_core_pb2.AgentResponse:
        """Execute a single agent and return its response."""
        pass
    
    @abstractmethod
    def get_strategy_type(self) -> mantis_core_pb2.ExecutionStrategy:
        """Return the strategy type enum value."""
        pass


class DirectExecutor(ExecutionStrategy):
    """Direct execution using local pydantic-ai agents."""
    
    def __init__(self):
        self._model_cache: Dict[str, Any] = {}
    
    async def execute_agent(
        self, 
        simulation_input: mantis_core_pb2.SimulationInput,
        agent_spec: mantis_core_pb2.AgentSpec,
        agent_index: int
    ) -> mantis_core_pb2.AgentResponse:
        """Execute agent directly using pydantic-ai."""
        # TODO: This is where we'll integrate with existing pydantic-ai infrastructure
        # For now, return a placeholder response
        
        response = mantis_core_pb2.AgentResponse()
        response.text_response = f"[DirectExecutor] Processed query: {simulation_input.query}"
        response.output_modes.append("text/markdown")
        
        return response
    
    def get_strategy_type(self) -> mantis_core_pb2.ExecutionStrategy:
        return mantis_core_pb2.EXECUTION_STRATEGY_DIRECT


class A2AExecutor(ExecutionStrategy):
    """A2A execution using remote agents via FastA2A protocol."""
    
    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = registry_url
    
    async def execute_agent(
        self, 
        simulation_input: mantis_core_pb2.SimulationInput,
        agent_spec: mantis_core_pb2.AgentSpec,
        agent_index: int
    ) -> mantis_core_pb2.AgentResponse:
        """Execute agent via A2A protocol."""
        # TODO: Implement FastA2A integration (Issue #25-27)
        # For now, return a placeholder response
        
        response = mantis_core_pb2.AgentResponse()
        response.text_response = f"[A2AExecutor] Would execute via A2A: {simulation_input.query}"
        response.output_modes.append("text/markdown")
        
        return response
    
    def get_strategy_type(self) -> mantis_core_pb2.ExecutionStrategy:
        return mantis_core_pb2.EXECUTION_STRATEGY_A2A


@dataclass
class ExecutionContext:
    """Context information for a simulation execution."""
    start_time: float
    strategy: ExecutionStrategy
    simulation_input: mantis_core_pb2.SimulationInput
    current_depth: int = 0


class SimulationOrchestrator:
    """
    Core orchestrator for multi-agent simulations.
    
    Handles the complete lifecycle from UserRequest to SimulationOutput,
    coordinating between different execution strategies and managing
    recursive agent interactions.
    """
    
    def __init__(self):
        self._strategies: Dict[mantis_core_pb2.ExecutionStrategy, ExecutionStrategy] = {
            mantis_core_pb2.EXECUTION_STRATEGY_DIRECT: DirectExecutor(),
            mantis_core_pb2.EXECUTION_STRATEGY_A2A: A2AExecutor(),
        }
    
    def user_request_to_simulation_input(self, user_request: mantis_core_pb2.UserRequest) -> mantis_core_pb2.SimulationInput:
        """Convert UserRequest to SimulationInput with execution strategy."""
        simulation_input = mantis_core_pb2.SimulationInput()
        
        # Copy all fields from UserRequest
        simulation_input.query = user_request.query
        
        if user_request.HasField("context"):
            simulation_input.context = user_request.context
            
        if user_request.HasField("structured_data"):
            simulation_input.structured_data = user_request.structured_data
            
        if user_request.HasField("model_spec"):
            simulation_input.model_spec.CopyFrom(user_request.model_spec)
            
        if user_request.HasField("max_depth"):
            simulation_input.max_depth = user_request.max_depth
        
        # Copy agent specifications
        for agent_spec in user_request.agents:
            simulation_input.agents.append(agent_spec)
        
        # Set execution strategy (default to A2A for multi-agent scenarios)
        if len(user_request.agents) > 1 or any(
            agent.HasField("recursion_policy") and 
            agent.recursion_policy in [mantis_core_pb2.RECURSION_POLICY_MAY, mantis_core_pb2.RECURSION_POLICY_MUST]
            for agent in user_request.agents
        ):
            simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_A2A
        else:
            simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
        
        return simulation_input
    
    async def execute_simulation(self, user_request: mantis_core_pb2.UserRequest) -> mantis_core_pb2.SimulationOutput:
        """
        Execute a complete simulation from UserRequest to SimulationOutput.
        
        Args:
            user_request: The user's simulation request
            
        Returns:
            SimulationOutput with results, timing, and status
        """
        start_time = time.time()
        
        try:
            # Convert to SimulationInput
            simulation_input = self.user_request_to_simulation_input(user_request)
            
            # Create execution context
            context = ExecutionContext(
                start_time=start_time,
                strategy=self._strategies[simulation_input.execution_strategy],
                simulation_input=simulation_input,
                current_depth=0
            )
            
            # Execute simulation
            simulation_output = await self._execute_simulation_internal(context)
            
            # Set execution metadata
            simulation_output.total_time = time.time() - start_time
            simulation_output.execution_strategies.append(simulation_input.execution_strategy)
            simulation_output.team_size = len(simulation_input.agents)
            simulation_output.recursion_depth = 0
            
            # Set success status
            execution_result = mantis_core_pb2.ExecutionResult()
            execution_result.status = mantis_core_pb2.EXECUTION_STATUS_SUCCESS
            simulation_output.execution_result.CopyFrom(execution_result)
            
            return simulation_output
            
        except Exception as e:
            # Create error response
            simulation_output = mantis_core_pb2.SimulationOutput()
            simulation_output.total_time = time.time() - start_time
            simulation_output.team_size = len(user_request.agents) if user_request.agents else 0
            
            # Create error info
            error_info = mantis_core_pb2.ErrorInfo()
            error_info.error_type = mantis_core_pb2.ERROR_TYPE_MODEL  # Default error type
            error_info.error_message = str(e)
            
            # Set error status
            execution_result = mantis_core_pb2.ExecutionResult()
            execution_result.status = mantis_core_pb2.EXECUTION_STATUS_FAILED
            execution_result.error_info.CopyFrom(error_info)
            simulation_output.execution_result.CopyFrom(execution_result)
            
            # Create error response
            error_response = mantis_core_pb2.AgentResponse()
            error_response.text_response = f"Simulation failed: {str(e)}"
            error_response.output_modes.append("text/plain")
            simulation_output.response.CopyFrom(error_response)
            
            return simulation_output
    
    async def _execute_simulation_internal(self, context: ExecutionContext) -> mantis_core_pb2.SimulationOutput:
        """Internal simulation execution logic."""
        simulation_input = context.simulation_input
        strategy = context.strategy
        
        # For now, execute all agents independently (no recursion yet)
        agent_responses: List[mantis_core_pb2.AgentResponse] = []
        
        for i, agent_spec in enumerate(simulation_input.agents):
            try:
                response = await strategy.execute_agent(simulation_input, agent_spec, i)
                agent_responses.append(response)
            except Exception as e:
                # Create error response for this agent
                error_response = mantis_core_pb2.AgentResponse()
                error_response.text_response = f"Agent {i} failed: {str(e)}"
                error_response.output_modes.append("text/plain")
                agent_responses.append(error_response)
        
        # Create simulation output
        simulation_output = mantis_core_pb2.SimulationOutput()
        
        # For single agent, use its response directly
        if len(agent_responses) == 1:
            simulation_output.response.CopyFrom(agent_responses[0])
        else:
            # For multiple agents, aggregate responses
            aggregated_response = self._aggregate_responses(agent_responses)
            simulation_output.response.CopyFrom(aggregated_response)
        
        return simulation_output
    
    def _aggregate_responses(self, responses: List[mantis_core_pb2.AgentResponse]) -> mantis_core_pb2.AgentResponse:
        """Aggregate multiple agent responses into a single response."""
        aggregated = mantis_core_pb2.AgentResponse()
        
        # Combine text responses
        text_parts = []
        for i, response in enumerate(responses):
            text_parts.append(f"**Agent {i+1}:**\n{response.text_response}")
        
        aggregated.text_response = "\n\n".join(text_parts)
        aggregated.output_modes.append("text/markdown")
        
        # TODO: More sophisticated aggregation logic for:
        # - Extension merging
        # - Skill combination
        # - Confidence scoring
        # This will be enhanced in later issues
        
        return aggregated
    
    def get_available_strategies(self) -> List[mantis_core_pb2.ExecutionStrategy]:
        """Get list of available execution strategies."""
        return list(self._strategies.keys())
    
    def set_strategy(self, strategy_type: mantis_core_pb2.ExecutionStrategy, strategy: ExecutionStrategy):
        """Register or override an execution strategy."""
        self._strategies[strategy_type] = strategy
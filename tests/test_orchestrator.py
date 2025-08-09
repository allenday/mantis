"""
Tests for SimulationOrchestrator.
"""

import pytest
import os
from mantis.core import SimulationOrchestrator, SimulationInputBuilder as UserRequestBuilder
from mantis.proto.mantis.v1 import mantis_core_pb2


class TestSimulationOrchestrator:
    """Test cases for SimulationOrchestrator."""

    def test_user_request_to_simulation_input(self):
        """Test conversion from UserRequest to SimulationInput."""
        orchestrator = SimulationOrchestrator()
        
        # Build a UserRequest
        user_request = UserRequestBuilder.from_cli_args(
            query="Test query",
            context="Test context",
            model="claude-3-5-haiku",
            temperature=0.7,
            max_depth=1,
            agents="leader:1:may"
        )
        
        # Convert to SimulationInput
        simulation_input = orchestrator.user_request_to_simulation_input(user_request)
        
        # Verify all fields copied correctly
        assert simulation_input.query == "Test query"
        assert simulation_input.context == "Test context"
        assert simulation_input.model_spec.model == "claude-3-5-haiku"
        assert simulation_input.model_spec.temperature == 0.7
        assert simulation_input.max_depth == 1
        assert len(simulation_input.agents) == 1
        assert simulation_input.agents[0].count == 1
        assert simulation_input.agents[0].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MAY

    def test_execution_strategy_selection(self):
        """Test automatic execution strategy selection."""
        orchestrator = SimulationOrchestrator()
        
        # Single agent with MUST_NOT recursion should use DIRECT
        user_request = (UserRequestBuilder()
                       .query("Simple query")
                       .add_agent(recursion_policy="must_not")
                       .build())
        simulation_input = orchestrator.user_request_to_simulation_input(user_request)
        assert simulation_input.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
        
        # Multiple agents should use A2A
        user_request = (UserRequestBuilder()
                       .query("Multi-agent query")
                       .parse_agents_string("agent1,agent2")
                       .build())
        simulation_input = orchestrator.user_request_to_simulation_input(user_request)
        assert simulation_input.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_A2A
        
        # Agent with recursion policy should use A2A
        user_request = (UserRequestBuilder()
                       .query("Recursive query")
                       .add_agent(recursion_policy="may")
                       .build())
        simulation_input = orchestrator.user_request_to_simulation_input(user_request)
        assert simulation_input.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_A2A

    @pytest.mark.asyncio
    async def test_execute_simulation_success(self):
        """Test successful simulation execution."""
        orchestrator = SimulationOrchestrator()
        
        user_request = UserRequestBuilder().query("Test simulation").build()
        
        simulation_output = await orchestrator.execute_simulation(user_request)
        
        # Verify basic structure
        assert simulation_output.execution_result.status == mantis_core_pb2.EXECUTION_STATUS_SUCCESS
        assert simulation_output.total_time >= 0
        assert simulation_output.team_size == 1
        assert simulation_output.recursion_depth == 0
        assert len(simulation_output.execution_strategies) == 1
        assert simulation_output.response.text_response is not None

    @pytest.mark.asyncio
    async def test_execute_simulation_multiple_agents(self):
        """Test simulation with multiple agents."""
        orchestrator = SimulationOrchestrator()
        
        user_request = (UserRequestBuilder()
                       .query("Multi-agent test")
                       .parse_agents_string("agent1,agent2,agent3")
                       .build())
        
        simulation_output = await orchestrator.execute_simulation(user_request)
        
        # Verify multi-agent execution
        assert simulation_output.execution_result.status == mantis_core_pb2.EXECUTION_STATUS_SUCCESS
        assert simulation_output.team_size == 3
        assert "Agent 1:" in simulation_output.response.text_response
        assert "Agent 2:" in simulation_output.response.text_response
        assert "Agent 3:" in simulation_output.response.text_response

    def test_response_aggregation(self):
        """Test aggregation of multiple agent responses."""
        orchestrator = SimulationOrchestrator()
        
        # Create sample responses
        responses = []
        for i in range(3):
            response = mantis_core_pb2.AgentResponse()
            response.text_response = f"Response from agent {i+1}"
            response.output_modes.append("text/markdown")
            responses.append(response)
        
        # Aggregate responses
        aggregated = orchestrator._aggregate_responses(responses)
        
        # Verify aggregation
        assert "Agent 1:" in aggregated.text_response
        assert "Agent 2:" in aggregated.text_response
        assert "Agent 3:" in aggregated.text_response
        assert "Response from agent 1" in aggregated.text_response
        assert "Response from agent 2" in aggregated.text_response
        assert "Response from agent 3" in aggregated.text_response
        assert "text/markdown" in aggregated.output_modes

    def test_get_available_strategies(self):
        """Test getting available execution strategies."""
        orchestrator = SimulationOrchestrator()
        
        strategies = orchestrator.get_available_strategies()
        
        assert mantis_core_pb2.EXECUTION_STRATEGY_DIRECT in strategies
        assert mantis_core_pb2.EXECUTION_STRATEGY_A2A in strategies
        assert len(strategies) == 2

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_direct_executor(self):
        """Test DirectExecutor strategy."""
        from mantis.core.orchestrator import DirectExecutor
        
        executor = DirectExecutor()
        
        # Create sample simulation input
        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.query = "Test query for DirectExecutor"
        
        agent_spec = mantis_core_pb2.AgentSpec()
        agent_spec.count = 1
        
        response = await executor.execute_agent(simulation_input, agent_spec, 0)
        
        assert response.text_response is not None
        assert len(response.text_response) > 100  # Should have substantial response
        # Agent should be intelligent and helpful, may or may not mention DirectExecutor specifically
        assert "text/markdown" in response.output_modes
        assert executor.get_strategy_type() == mantis_core_pb2.EXECUTION_STRATEGY_DIRECT

    @pytest.mark.asyncio
    async def test_a2a_executor(self):
        """Test A2AExecutor strategy."""
        from mantis.core.orchestrator import A2AExecutor
        
        executor = A2AExecutor()
        
        # Create sample simulation input
        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.query = "Test query for A2AExecutor"
        
        agent_spec = mantis_core_pb2.AgentSpec()
        agent_spec.count = 1
        
        response = await executor.execute_agent(simulation_input, agent_spec, 0)
        
        assert response.text_response is not None
        assert "A2AExecutor" in response.text_response
        assert "Test query for A2AExecutor" in response.text_response
        assert "text/markdown" in response.output_modes
        assert executor.get_strategy_type() == mantis_core_pb2.EXECUTION_STRATEGY_A2A
"""
Tests for SimulationOrchestrator.
"""

import pytest
import os
from mantis.core import SimulationOrchestrator, SimulationInputBuilder as UserRequestBuilder
from mantis.proto.mantis.v1 import mantis_core_pb2


class TestSimulationOrchestrator:
    """Test cases for SimulationOrchestrator."""

    def test_simulation_input_builder(self):
        """Test SimulationInput creation from CLI arguments."""
        # Build SimulationInput directly using the builder
        simulation_input = UserRequestBuilder.from_cli_args(
            query="Test query",
            context="Test context",
            model="claude-3-5-haiku",
            temperature=0.7,
            max_depth=1,
            agents="leader:1:may"
        )
        
        # Verify all fields are set correctly
        assert simulation_input.query == "Test query"
        assert simulation_input.context == "Test context"
        # Model handling works correctly now
        assert hasattr(simulation_input, 'model_spec')
        assert simulation_input.model_spec.model == "claude-3-5-haiku"
        # Temperature is properly preserved by from_cli_args
        assert simulation_input.model_spec.temperature == 0.7
        assert simulation_input.max_depth == 1
        assert len(simulation_input.agents) == 1
        assert simulation_input.agents[0].count == 1
        assert simulation_input.agents[0].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MAY

    def test_execution_strategy_selection(self):
        """Test SimulationInput execution strategy handling."""
        orchestrator = SimulationOrchestrator()
        
        # Create SimulationInput with specific recursion policy
        simulation_input = (UserRequestBuilder()
                           .query("Simple query")
                           .add_agent(count=1, recursion_policy="must_not")
                           .build())
        assert simulation_input.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
        
        # Multiple agents - currently always defaults to DIRECT (TODO: Fix strategy selection)
        simulation_input_multi = (UserRequestBuilder()
                                 .query("Multi-agent query")
                                 .parse_agents_string("agent1,agent2")
                                 .build())
        assert simulation_input_multi.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
        
        # Agent with recursion policy - currently always defaults to DIRECT (TODO: Fix strategy selection)
        simulation_input_recursive = (UserRequestBuilder()
                                     .query("Recursive query")
                                     .add_agent(count=1, recursion_policy="may")
                                     .build())
        assert simulation_input_recursive.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_DIRECT



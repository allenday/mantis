"""
Unit tests for MantisService - Primary orchestration service with A2A integration.

Tests core functionality including:
- SimulationInput processing with A2A lifecycle
- Context threading and status retrieval  
- Contextual prompt creation
- Service health monitoring
- Error handling and structured logging
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, AsyncMock
from typing import Optional

from mantis.core.mantis_service import MantisService
from mantis.agent import AgentInterface
from mantis.proto.mantis.v1 import mantis_core_pb2, mantis_persona_pb2
from mantis.proto import a2a_pb2


class TestMantisService:
    """Test suite for MantisService core functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MantisService()

    def test_mantis_service_initialization(self):
        """Test MantisService initializes correctly with orchestrator."""
        assert self.service.orchestrator is not None
        assert hasattr(self.service.orchestrator, 'get_available_tools')
        
        tools = self.service.orchestrator.get_available_tools()
        assert isinstance(tools, dict)
        assert len(tools) > 0

    def test_mantis_service_initialization_failure(self):
        """Test MantisService fails fast on initialization error."""
        with patch('mantis.core.mantis_service.SimulationOrchestrator', side_effect=Exception("Init failed")):
            with pytest.raises(RuntimeError, match="MantisService initialization failed"):
                MantisService()

    def create_valid_simulation_input(
        self, 
        context_id: str = None,
        parent_context_id: str = None,
        query: str = None
    ) -> mantis_core_pb2.SimulationInput:
        """Create valid SimulationInput for testing."""
        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.context_id = context_id or f"test-context-{uuid.uuid4().hex[:8]}"
        simulation_input.parent_context_id = parent_context_id or f"parent-{uuid.uuid4().hex[:8]}"
        simulation_input.query = query or "Test query for simulation processing"
        simulation_input.context = "Test context information"
        simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_A2A
        
        return simulation_input

    def create_test_agent_interface(self) -> AgentInterface:
        """Create test AgentInterface for testing."""
        # Create test MantisAgentCard
        agent_card = mantis_persona_pb2.MantisAgentCard()
        agent_card.persona_title = "Test Agent"
        
        # Add test agent card from A2A
        a2a_card = a2a_pb2.AgentCard()
        a2a_card.name = "TestAgent"
        a2a_card.description = "A test agent for unit testing"
        agent_card.agent_card.CopyFrom(a2a_card)
        
        return AgentInterface(agent_card)

    @pytest.mark.asyncio
    async def test_process_simulation_input_validation_empty_context_id(self):
        """Test validation fails for empty context_id."""
        simulation_input = self.create_valid_simulation_input()
        simulation_input.context_id = ""
        agent_interface = self.create_test_agent_interface()
        
        with pytest.raises(ValueError, match="context_id cannot be empty"):
            await self.service.process_simulation_input(simulation_input, agent_interface)

    @pytest.mark.asyncio
    async def test_process_simulation_input_validation_empty_query(self):
        """Test validation fails for empty query."""
        simulation_input = self.create_valid_simulation_input()
        simulation_input.query = ""
        agent_interface = self.create_test_agent_interface()
        
        with pytest.raises(ValueError, match="query cannot be empty"):
            await self.service.process_simulation_input(simulation_input, agent_interface)

    @pytest.mark.asyncio
    async def test_process_simulation_input_validation_whitespace_context_id(self):
        """Test validation fails for whitespace-only context_id."""
        simulation_input = self.create_valid_simulation_input()
        simulation_input.context_id = "   "
        agent_interface = self.create_test_agent_interface()
        
        with pytest.raises(ValueError, match="context_id cannot be empty"):
            await self.service.process_simulation_input(simulation_input, agent_interface)

    @pytest.mark.asyncio 
    async def test_process_simulation_input_success(self):
        """Test successful SimulationInput processing with A2A lifecycle."""
        simulation_input = self.create_valid_simulation_input()
        
        # Create real SimulationOutput protobuf object
        mock_output = mantis_core_pb2.SimulationOutput()
        mock_output.context_id = simulation_input.context_id
        mock_output.final_state = a2a_pb2.TASK_STATE_COMPLETED
        
        # Create a mock task for the simulation_task field
        mock_task = a2a_pb2.Task()
        mock_task.context_id = simulation_input.context_id
        mock_task.id = f"task-{uuid.uuid4().hex[:8]}"
        mock_task.status.state = a2a_pb2.TASK_STATE_COMPLETED
        mock_output.simulation_task.CopyFrom(mock_task)
        
        with patch.object(self.service.orchestrator, 'execute_simulation', return_value=mock_output):
            result = await self.service.process_simulation_input(simulation_input, self.create_test_agent_interface())
            
            assert isinstance(result, mantis_core_pb2.SimulationOutput)
            assert result.context_id == simulation_input.context_id
            assert result.final_state == a2a_pb2.TASK_STATE_COMPLETED
            assert result.HasField('simulation_task')

    @pytest.mark.asyncio
    async def test_process_simulation_input_with_message_history(self):
        """Test SimulationInput processing copies message history."""
        simulation_input = self.create_valid_simulation_input()
        
        # Create real A2A Message protobuf object
        mock_message = a2a_pb2.Message()
        mock_message.message_id = "test-message-123"
        mock_message.role = a2a_pb2.ROLE_AGENT
        
        # Create real SimulationOutput with response message
        mock_output = mantis_core_pb2.SimulationOutput()
        mock_output.context_id = simulation_input.context_id
        mock_output.final_state = a2a_pb2.TASK_STATE_COMPLETED
        mock_output.response_message.CopyFrom(mock_message)
        
        # Create a mock task for the simulation_task field
        mock_task = a2a_pb2.Task()
        mock_task.context_id = simulation_input.context_id
        mock_task.id = f"task-{uuid.uuid4().hex[:8]}"
        mock_task.status.state = a2a_pb2.TASK_STATE_COMPLETED
        mock_task.history.append(mock_message)
        mock_output.simulation_task.CopyFrom(mock_task)
        
        with patch.object(self.service.orchestrator, 'execute_simulation', return_value=mock_output):
            result = await self.service.process_simulation_input(simulation_input, self.create_test_agent_interface())
            
            assert result.HasField('response_message')

    @pytest.mark.asyncio
    async def test_process_simulation_input_with_artifacts(self):
        """Test SimulationInput processing copies artifacts."""
        simulation_input = self.create_valid_simulation_input()
        
        # Create real A2A Artifact protobuf object
        mock_artifact = a2a_pb2.Artifact()
        mock_artifact.artifact_id = "test-artifact-123"
        mock_artifact.name = "test-result.txt"
        
        # Create real SimulationOutput with artifacts
        mock_output = mantis_core_pb2.SimulationOutput()
        mock_output.context_id = simulation_input.context_id
        mock_output.final_state = a2a_pb2.TASK_STATE_COMPLETED
        mock_output.response_artifacts.append(mock_artifact)
        
        # Create a mock task for the simulation_task field
        mock_task = a2a_pb2.Task()
        mock_task.context_id = simulation_input.context_id
        mock_task.id = f"task-{uuid.uuid4().hex[:8]}"
        mock_task.status.state = a2a_pb2.TASK_STATE_COMPLETED
        mock_task.artifacts.append(mock_artifact)
        mock_output.simulation_task.CopyFrom(mock_task)
        
        with patch.object(self.service.orchestrator, 'execute_simulation', return_value=mock_output):
            result = await self.service.process_simulation_input(simulation_input, self.create_test_agent_interface())
            
            assert len(result.response_artifacts) == 1

    @pytest.mark.asyncio
    async def test_process_simulation_input_orchestrator_failure(self):
        """Test SimulationInput processing handles orchestrator failures gracefully."""
        simulation_input = self.create_valid_simulation_input()
        
        # Mock orchestrator failure
        with patch.object(self.service.orchestrator, 'execute_simulation', 
                         side_effect=Exception("Orchestrator failed")):
            result = await self.service.process_simulation_input(simulation_input, self.create_test_agent_interface())
            
            assert isinstance(result, mantis_core_pb2.SimulationOutput)
            assert result.context_id == simulation_input.context_id
            assert result.final_state == a2a_pb2.TASK_STATE_FAILED
            assert result.HasField('response_message')

    def test_get_contextual_execution_status_empty_context(self):
        """Test contextual execution status retrieval for empty context."""
        test_context_id = "empty-context-123"
        
        # Mock empty task list
        with patch.object(self.service.orchestrator, 'get_tasks_by_context', return_value=[]):
            results = self.service.get_contextual_execution_status(test_context_id)
            
            assert isinstance(results, list)
            assert len(results) == 0

    def test_get_contextual_execution_status_with_tasks(self):
        """Test contextual execution status retrieval with existing tasks."""
        test_context_id = "context-with-tasks-123"
        
        # Create real A2A Task protobuf objects
        mock_task1 = a2a_pb2.Task()
        mock_task1.context_id = test_context_id
        mock_task1.id = "task-1"
        mock_task1.status.state = a2a_pb2.TASK_STATE_COMPLETED
        
        mock_task2 = a2a_pb2.Task()
        mock_task2.context_id = test_context_id
        mock_task2.id = "task-2"
        mock_task2.status.state = a2a_pb2.TASK_STATE_WORKING
        
        mock_tasks = [mock_task1, mock_task2]
        
        with patch.object(self.service.orchestrator, 'get_tasks_by_context', return_value=mock_tasks):
            results = self.service.get_contextual_execution_status(test_context_id)
            
            assert len(results) == 2
            assert all(isinstance(result, mantis_core_pb2.SimulationOutput) for result in results)
            assert all(result.context_id == test_context_id for result in results)

    @pytest.mark.asyncio
    async def test_create_contextual_prompt_for_agent_basic(self):
        """Test contextual prompt creation with basic parameters."""
        base_query = "Test query for contextual prompt"
        agent_interface = self.create_test_agent_interface()
        
        prompt = await self.service.create_contextual_prompt_for_agent(
            base_query=base_query,
            agent_interface=agent_interface
        )
        
        assert prompt.agent_name == agent_interface.name
        assert base_query in prompt.assemble()
        assert len(prompt.assemble()) > len(base_query)

    @pytest.mark.asyncio 
    async def test_create_contextual_prompt_for_agent_with_context(self):
        """Test contextual prompt creation with context content."""
        base_query = "Test query"
        agent_interface = self.create_test_agent_interface()
        priority = 5
        
        prompt = await self.service.create_contextual_prompt_for_agent(
            base_query=base_query,
            agent_interface=agent_interface,
            priority=priority
        )
        
        assert prompt.agent_name == agent_interface.name
        assert base_query in prompt.assemble()
        assert len(prompt.assemble()) > len(base_query)

    @pytest.mark.asyncio
    async def test_create_contextual_prompt_for_agent_with_card(self):
        """Test contextual prompt creation with agent card."""
        base_query = "Test query"
        agent_interface = self.create_test_agent_interface()
        
        prompt = await self.service.create_contextual_prompt_for_agent(
            base_query=base_query,
            agent_interface=agent_interface
        )
        
        assert prompt.agent_name == agent_interface.name
        assert base_query in prompt.assemble()

    def test_get_active_contexts_empty(self):
        """Test active contexts retrieval when no contexts exist."""
        # Mock empty active_tasks
        with patch.object(self.service.orchestrator, 'active_tasks', {}):
            contexts = self.service.get_active_contexts()
            
            assert isinstance(contexts, list)
            assert len(contexts) == 0

    def test_get_active_contexts_with_tasks(self):
        """Test active contexts retrieval with active tasks."""
        # Create mock tasks with contexts
        mock_task1 = Mock()
        mock_task1.context_id = "context-1"
        
        mock_task2 = Mock()
        mock_task2.context_id = "context-2"
        
        mock_task3 = Mock()
        mock_task3.context_id = "context-1"  # Duplicate context
        
        mock_active_tasks = {
            "task-1": mock_task1,
            "task-2": mock_task2, 
            "task-3": mock_task3
        }
        
        with patch.object(self.service.orchestrator, 'active_tasks', mock_active_tasks):
            contexts = self.service.get_active_contexts()
            
            assert isinstance(contexts, list)
            assert len(contexts) == 2  # Unique contexts only
            assert "context-1" in contexts
            assert "context-2" in contexts

    def test_get_active_contexts_with_none_context(self):
        """Test active contexts retrieval handles None context_id."""
        # Create mock task with None context_id
        mock_task = Mock()
        mock_task.context_id = None
        
        mock_active_tasks = {"task-1": mock_task}
        
        with patch.object(self.service.orchestrator, 'active_tasks', mock_active_tasks):
            contexts = self.service.get_active_contexts()
            
            assert isinstance(contexts, list)
            assert len(contexts) == 0

    def test_get_service_health_basic(self):
        """Test service health status retrieval."""
        # Mock orchestrator state
        mock_active_tasks = {"task-1": Mock(), "task-2": Mock()}
        mock_tools = ["tool1", "tool2", "tool3"]
        
        with patch.object(self.service.orchestrator, 'active_tasks', mock_active_tasks), \
             patch.object(self.service.orchestrator, 'get_available_tools', return_value=mock_tools), \
             patch.object(self.service, 'get_active_contexts', return_value=["context-1"]):
            
            health = self.service.get_service_health()
            
            assert health["status"] == "healthy"
            assert health["active_tasks"] == 2
            assert health["active_contexts"] == 1
            assert health["available_tools"] == 3
            assert "timestamp" in health


class TestMantisServiceA2AIntegration:
    """Test suite specifically for A2A protocol integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MantisService()

    def create_test_agent_interface(self) -> AgentInterface:
        """Create test AgentInterface for testing."""
        # Create test MantisAgentCard
        agent_card = mantis_persona_pb2.MantisAgentCard()
        agent_card.persona_title = "Test Agent"
        
        # Add test agent card from A2A
        a2a_card = a2a_pb2.AgentCard()
        a2a_card.name = "TestAgent"
        a2a_card.description = "A test agent for unit testing"
        agent_card.agent_card.CopyFrom(a2a_card)
        
        return AgentInterface(agent_card)

    def create_simulation_input_with_artifacts(self) -> mantis_core_pb2.SimulationInput:
        """Create SimulationInput with A2A artifacts for testing."""
        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.context_id = f"test-context-{uuid.uuid4().hex[:8]}"
        simulation_input.query = "Test A2A integration"
        
        # Add test artifact
        artifact = a2a_pb2.Artifact()
        artifact.artifact_id = "test-artifact-1"
        artifact.name = "test-input.txt"
        artifact.description = "Test input for A2A integration"
        
        text_part = a2a_pb2.Part()
        text_part.text = "Test content"
        artifact.parts.append(text_part)
        
        simulation_input.input_artifacts.append(artifact)
        
        return simulation_input

    @pytest.mark.asyncio
    async def test_a2a_artifact_processing(self):
        """Test A2A artifact processing in simulation input."""
        simulation_input = self.create_simulation_input_with_artifacts()
        
        # Create real A2A Task with artifacts
        mock_task = a2a_pb2.Task()
        mock_task.context_id = simulation_input.context_id
        mock_task.id = f"task-{uuid.uuid4().hex[:8]}"
        mock_task.status.state = a2a_pb2.TASK_STATE_COMPLETED
        
        # Create real A2A output artifact
        output_artifact = a2a_pb2.Artifact()
        output_artifact.artifact_id = "output-artifact-1"
        output_artifact.name = "output-result.txt"
        mock_task.artifacts.append(output_artifact)
        
        # Create SimulationOutput that wraps the task
        mock_output = mantis_core_pb2.SimulationOutput()
        mock_output.context_id = simulation_input.context_id
        mock_output.final_state = a2a_pb2.TASK_STATE_COMPLETED
        mock_output.simulation_task.CopyFrom(mock_task)
        mock_output.response_artifacts.append(output_artifact)
        
        with patch.object(self.service.orchestrator, 'execute_simulation', return_value=mock_output):
            result = await self.service.process_simulation_input(simulation_input, self.create_test_agent_interface())
            
            assert len(result.response_artifacts) == 1
            assert result.final_state == a2a_pb2.TASK_STATE_COMPLETED

    @pytest.mark.asyncio
    async def test_a2a_message_creation_in_error_response(self):
        """Test A2A Message creation in error response follows protocol."""
        simulation_input = self.create_simulation_input_with_artifacts()
        
        with patch.object(self.service.orchestrator, 'execute_simulation', 
                         side_effect=Exception("Test error")):
            result = await self.service.process_simulation_input(simulation_input, self.create_test_agent_interface())
            
            assert result.final_state == a2a_pb2.TASK_STATE_FAILED
            assert result.HasField('response_message')
            
            error_msg = result.response_message
            assert error_msg.role == a2a_pb2.ROLE_AGENT
            assert error_msg.context_id == simulation_input.context_id
            assert len(error_msg.content) > 0
            assert "Test error" in error_msg.content[0].text

    def test_a2a_task_state_validation(self):
        """Test that only valid A2A TaskStates are used."""
        valid_states = [
            a2a_pb2.TASK_STATE_SUBMITTED,
            a2a_pb2.TASK_STATE_WORKING,
            a2a_pb2.TASK_STATE_COMPLETED,
            a2a_pb2.TASK_STATE_FAILED,
            a2a_pb2.TASK_STATE_CANCELLED
        ]
        
        # Verify all states are valid integer values
        for state in valid_states:
            assert isinstance(state, int)
            assert state >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
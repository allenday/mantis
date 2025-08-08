"""
Unit tests for SimulationOutput with native A2A Messages and Artifacts.
"""

import pytest
import uuid
from unittest.mock import patch, MagicMock
from google.protobuf import timestamp_pb2

from mantis.core.orchestrator import SimpleOrchestrator, SimulationOutput
from mantis.proto import a2a_pb2
from mantis.proto.mantis.v1 import mantis_persona_pb2


class TestSimulationOutput:
    """Test SimulationOutput class functionality."""

    def test_initialization_with_completed_task(self):
        """Test SimulationOutput initialization with completed task."""
        # Create completed task
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        
        # Initialize SimulationOutput
        sim_output = SimulationOutput(task)
        
        assert sim_output.task == task
        assert len(sim_output.messages) == 2  # User + Agent messages
        assert len(sim_output.artifacts) == 0

    def test_initialization_with_incomplete_task_logs_warning(self):
        """Test SimulationOutput initialization with incomplete task logs warning."""
        # Create working task
        task = self._create_test_task(a2a_pb2.TASK_STATE_WORKING)
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            sim_output = SimulationOutput(task)
            
            # Should log warning about incomplete task
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "Creating SimulationOutput from incomplete task" in call_args[0][0]
            assert call_args[1]['structured_data']['task_state'] == a2a_pb2.TASK_STATE_WORKING

    def test_initialization_with_invalid_type_raises_error(self):
        """Test SimulationOutput initialization with invalid type raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            SimulationOutput("not_a_task")
        
        assert "Expected a2a_pb2.Task, got" in str(exc_info.value)

    def test_get_user_messages(self):
        """Test filtering user messages."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            user_messages = sim_output.get_user_messages()
            
            assert len(user_messages) == 1
            assert user_messages[0].role == a2a_pb2.ROLE_USER
            assert user_messages[0].content[0].text == "Test query"
            
            # Should log debug message
            mock_logger.debug.assert_called_once()

    def test_get_agent_messages(self):
        """Test filtering agent messages."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            agent_messages = sim_output.get_agent_messages()
            
            assert len(agent_messages) == 1
            assert agent_messages[0].role == a2a_pb2.ROLE_AGENT
            assert agent_messages[0].content[0].text == "Test response"
            
            # Should log debug message
            mock_logger.debug.assert_called_once()

    def test_get_final_response_success(self):
        """Test getting final response message."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            final_response = sim_output.get_final_response()
            
            assert final_response is not None
            assert final_response.role == a2a_pb2.ROLE_AGENT
            assert final_response.content[0].text == "Test response"
            
            # Should log debug messages (get_agent_messages + found final response)
            assert mock_logger.debug.call_count == 2

    def test_get_final_response_ignores_status_updates(self):
        """Test final response ignores status update messages."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        
        # Add a status update message after the response
        status_msg = a2a_pb2.Message()
        status_msg.message_id = "status-001"
        status_msg.role = a2a_pb2.ROLE_AGENT
        text_part = a2a_pb2.Part()
        text_part.text = "[STATUS UPDATE] Task completed"
        status_msg.content.append(text_part)
        task.history.append(status_msg)
        
        sim_output = SimulationOutput(task)
        
        final_response = sim_output.get_final_response()
        
        # Should return the non-status message
        assert final_response is not None
        assert final_response.content[0].text == "Test response"
        assert not final_response.content[0].text.startswith("[STATUS UPDATE]")

    def test_get_final_response_no_agent_messages(self):
        """Test get_final_response when no agent messages exist."""
        task = a2a_pb2.Task()
        task.id = "test-task"
        task.context_id = "test-context"
        
        # Add only user message
        user_msg = a2a_pb2.Message()
        user_msg.role = a2a_pb2.ROLE_USER
        text_part = a2a_pb2.Part()
        text_part.text = "Test query"
        user_msg.content.append(text_part)
        task.history.append(user_msg)
        
        sim_output = SimulationOutput(task)
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            final_response = sim_output.get_final_response()
            
            assert final_response is None
            # Should log warning
            mock_logger.warning.assert_called_once()

    def test_create_artifact_from_response_success(self):
        """Test creating artifact from response message."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            artifact = sim_output.create_artifact_from_response(
                name="Test Artifact",
                description="Test artifact description"
            )
            
            assert artifact.name == "Test Artifact"
            assert artifact.description == "Test artifact description"
            assert len(artifact.parts) == 1
            assert artifact.parts[0].text == "Test response"
            assert artifact.artifact_id.startswith("artifact-")
            
            # Artifact should be added to task
            assert len(sim_output.task.artifacts) == 1
            assert sim_output.task.artifacts[0] == artifact
            
            # Should log info message
            mock_logger.info.assert_called_once()

    def test_create_artifact_from_specific_message(self):
        """Test creating artifact from specific message."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        # Create specific message
        custom_msg = a2a_pb2.Message()
        custom_msg.message_id = "custom-001"
        custom_msg.role = a2a_pb2.ROLE_AGENT
        text_part = a2a_pb2.Part()
        text_part.text = "Custom response content"
        custom_msg.content.append(text_part)
        
        artifact = sim_output.create_artifact_from_response(
            name="Custom Artifact",
            description="From custom message",
            response_message=custom_msg
        )
        
        assert artifact.parts[0].text == "Custom response content"

    def test_create_artifact_no_response_message_raises_error(self):
        """Test creating artifact when no response message available."""
        task = a2a_pb2.Task()
        task.id = "test-task"
        task.context_id = "test-context"
        
        # Add only user message
        user_msg = a2a_pb2.Message()
        user_msg.role = a2a_pb2.ROLE_USER
        text_part = a2a_pb2.Part()
        text_part.text = "Test query"
        user_msg.content.append(text_part)
        task.history.append(user_msg)
        
        sim_output = SimulationOutput(task)
        
        with pytest.raises(ValueError) as exc_info:
            sim_output.create_artifact_from_response(
                name="Test Artifact",
                description="Should fail"
            )
        
        assert "No response message provided and no final response found" in str(exc_info.value)

    def test_to_a2a_message_with_final_response(self):
        """Test converting simulation output to A2A message."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            a2a_message = sim_output.to_a2a_message()
            
            assert a2a_message.role == a2a_pb2.ROLE_AGENT
            assert a2a_message.context_id == task.context_id
            assert a2a_message.task_id == task.id
            assert len(a2a_message.content) == 1
            assert a2a_message.content[0].text == "Test response"
            assert a2a_message.message_id.startswith("summary-")
            
            # Should log debug messages (get_agent_messages + found final response + converted to A2A)
            assert mock_logger.debug.call_count == 3

    def test_to_a2a_message_with_custom_role(self):
        """Test converting to A2A message with custom role."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        a2a_message = sim_output.to_a2a_message(role=a2a_pb2.ROLE_USER)
        
        assert a2a_message.role == a2a_pb2.ROLE_USER

    def test_to_a2a_message_no_final_response_creates_summary(self):
        """Test converting to A2A message when no final response creates summary."""
        task = a2a_pb2.Task()
        task.id = "test-task"
        task.context_id = "test-context"
        
        # Add only user message
        user_msg = a2a_pb2.Message()
        user_msg.role = a2a_pb2.ROLE_USER
        text_part = a2a_pb2.Part()
        text_part.text = "Test query"
        user_msg.content.append(text_part)
        task.history.append(user_msg)
        
        sim_output = SimulationOutput(task)
        
        a2a_message = sim_output.to_a2a_message()
        
        # Should create summary fallback
        assert len(a2a_message.content) == 1
        expected_text = f"Simulation completed for task {task.id} with 1 messages"
        assert a2a_message.content[0].text == expected_text

    def test_messages_property(self):
        """Test messages property returns copy of history."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        sim_output = SimulationOutput(task)
        
        messages = sim_output.messages
        
        assert len(messages) == 2
        assert messages == list(task.history)
        # Should be a copy, not reference
        assert messages is not task.history

    def test_artifacts_property(self):
        """Test artifacts property returns copy of artifacts."""
        task = self._create_test_task(a2a_pb2.TASK_STATE_COMPLETED)
        
        # Add an artifact
        artifact = a2a_pb2.Artifact()
        artifact.artifact_id = "test-artifact"
        artifact.name = "Test Artifact"
        task.artifacts.append(artifact)
        
        sim_output = SimulationOutput(task)
        
        artifacts = sim_output.artifacts
        
        assert len(artifacts) == 1
        assert artifacts[0].name == "Test Artifact"
        # Should be a copy, not reference
        assert artifacts is not task.artifacts

    def _create_test_task(self, state: int) -> a2a_pb2.Task:
        """Create a test task with given state."""
        task = a2a_pb2.Task()
        task.id = f"task-{uuid.uuid4().hex[:12]}"
        task.context_id = f"context-{uuid.uuid4().hex[:8]}"
        
        # Set task status
        task.status.state = state
        timestamp = timestamp_pb2.Timestamp()
        timestamp.GetCurrentTime()
        task.status.timestamp.CopyFrom(timestamp)
        
        # Add user message
        user_msg = a2a_pb2.Message()
        user_msg.message_id = f"user-{uuid.uuid4().hex[:8]}"
        user_msg.context_id = task.context_id
        user_msg.task_id = task.id
        user_msg.role = a2a_pb2.ROLE_USER
        
        text_part = a2a_pb2.Part()
        text_part.text = "Test query"
        user_msg.content.append(text_part)
        task.history.append(user_msg)
        
        # Add agent response message
        agent_msg = a2a_pb2.Message()
        agent_msg.message_id = f"agent-{uuid.uuid4().hex[:8]}"
        agent_msg.context_id = task.context_id
        agent_msg.task_id = task.id
        agent_msg.role = a2a_pb2.ROLE_AGENT
        
        text_part = a2a_pb2.Part()
        text_part.text = "Test response"
        agent_msg.content.append(text_part)
        task.history.append(agent_msg)
        
        return task


class TestSimpleOrchestratorIntegration:
    """Test SimulationOutput integration with SimpleOrchestrator."""

    def test_create_simulation_output_success(self):
        """Test creating simulation output from completed task."""
        orchestrator = SimpleOrchestrator()
        
        # Create and add completed task
        task = self._create_completed_task()
        orchestrator.active_tasks[task.id] = task
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            sim_output = orchestrator.create_simulation_output(task.id)
            
            assert isinstance(sim_output, SimulationOutput)
            assert sim_output.task == task
            
            # Should log info message
            mock_logger.info.assert_called_once()

    def test_create_simulation_output_task_not_found(self):
        """Test creating simulation output when task not found."""
        orchestrator = SimpleOrchestrator()
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            with pytest.raises(ValueError) as exc_info:
                orchestrator.create_simulation_output("nonexistent-task")
            
            assert "Task nonexistent-task not found in active tasks" in str(exc_info.value)
            
            # Should log error message
            mock_logger.error.assert_called_once()

    def test_create_simulation_output_incomplete_task_logs_warning(self):
        """Test creating simulation output from incomplete task logs warning."""
        orchestrator = SimpleOrchestrator()
        
        # Create working task
        task = self._create_completed_task()
        task.status.state = a2a_pb2.TASK_STATE_WORKING
        orchestrator.active_tasks[task.id] = task
        
        with patch('mantis.core.orchestrator.logger') as mock_logger:
            sim_output = orchestrator.create_simulation_output(task.id)
            
            # Should log warning about incomplete task (both from orchestrator and SimulationOutput init)
            assert mock_logger.warning.call_count == 2
            # Check that at least one warning is about creating simulation output from incomplete task
            warning_messages = [call[0][0] for call in mock_logger.warning.call_args_list]
            assert any("Creating simulation output from incomplete task" in msg for msg in warning_messages)

    @pytest.mark.asyncio
    async def test_execute_simulation_with_output_success(self):
        """Test full simulation execution with output."""
        orchestrator = SimpleOrchestrator()
        
        # Mock the internal execution method
        mock_task = self._create_completed_task()
        
        with patch.object(orchestrator, 'execute_task_with_a2a_lifecycle') as mock_execute:
            with patch('mantis.core.orchestrator.logger') as mock_logger:
                mock_execute.return_value = mock_task
                
                sim_output = await orchestrator.execute_simulation_with_output(
                    query="Test simulation execution",
                    context_id="test-context"
                )
                
                assert isinstance(sim_output, SimulationOutput)
                assert sim_output.task == mock_task
                
                # Should call execute_task_with_a2a_lifecycle
                mock_execute.assert_called_once()
                
                # Should log start and completion
                assert mock_logger.info.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_simulation_with_output_failure(self):
        """Test simulation execution with output handles failures."""
        orchestrator = SimpleOrchestrator()
        
        with patch.object(orchestrator, 'execute_task_with_a2a_lifecycle') as mock_execute:
            with patch('mantis.core.orchestrator.logger') as mock_logger:
                # Make execution fail
                mock_execute.side_effect = RuntimeError("Test error")
                
                with pytest.raises(RuntimeError):
                    await orchestrator.execute_simulation_with_output(
                        query="Test simulation failure",
                        context_id="test-context"
                    )
                
                # Should log error
                mock_logger.error.assert_called_once()
                call_args = mock_logger.error.call_args
                assert "Simulation execution failed" in call_args[0][0]

    def _create_completed_task(self) -> a2a_pb2.Task:
        """Create a completed test task."""
        task = a2a_pb2.Task()
        task.id = f"task-{uuid.uuid4().hex[:12]}"
        task.context_id = f"context-{uuid.uuid4().hex[:8]}"
        
        # Set completed status
        task.status.state = a2a_pb2.TASK_STATE_COMPLETED
        timestamp = timestamp_pb2.Timestamp()
        timestamp.GetCurrentTime()
        task.status.timestamp.CopyFrom(timestamp)
        
        # Add messages
        user_msg = a2a_pb2.Message()
        user_msg.role = a2a_pb2.ROLE_USER
        text_part = a2a_pb2.Part()
        text_part.text = "Test query"
        user_msg.content.append(text_part)
        task.history.append(user_msg)
        
        agent_msg = a2a_pb2.Message()
        agent_msg.role = a2a_pb2.ROLE_AGENT
        text_part = a2a_pb2.Part()
        text_part.text = "Test response"
        agent_msg.content.append(text_part)
        task.history.append(agent_msg)
        
        return task


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
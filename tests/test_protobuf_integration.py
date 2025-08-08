"""
Unit tests for protobuf integration and import resolution.

Tests the protobuf generation system and verifies that all A2A protocol
types are properly imported and can be used correctly.
"""

import pytest
from typing import Any

from mantis.proto.mantis.v1 import mantis_core_pb2, mantis_persona_pb2
from mantis.proto import a2a_pb2
from google.protobuf.message import Message


class TestProtobufImports:
    """Test suite for protobuf import resolution."""

    def test_mantis_core_protobuf_import(self):
        """Test that mantis_core_pb2 imports correctly."""
        assert hasattr(mantis_core_pb2, 'SimulationInput')
        assert hasattr(mantis_core_pb2, 'SimulationOutput')
        assert hasattr(mantis_core_pb2, 'TeamExecutionRequest')
        assert hasattr(mantis_core_pb2, 'AgentInterface')
        assert hasattr(mantis_core_pb2, 'MantisService')

    def test_mantis_persona_protobuf_import(self):
        """Test that mantis_persona_pb2 imports correctly."""
        assert hasattr(mantis_persona_pb2, 'MantisAgentCard')
        assert hasattr(mantis_persona_pb2, 'PersonaCharacteristics')
        assert hasattr(mantis_persona_pb2, 'CompetencyScores')
        assert hasattr(mantis_persona_pb2, 'DomainExpertise')
        assert hasattr(mantis_persona_pb2, 'SkillsSummary')

    def test_a2a_protobuf_import(self):
        """Test that a2a_pb2 imports correctly."""
        assert hasattr(a2a_pb2, 'Message')
        assert hasattr(a2a_pb2, 'Part')
        assert hasattr(a2a_pb2, 'Artifact')
        assert hasattr(a2a_pb2, 'Task')
        assert hasattr(a2a_pb2, 'TaskState')
        assert hasattr(a2a_pb2, 'AgentCard')

    def test_a2a_enums_available(self):
        """Test that A2A enums are properly defined."""
        # Role enum values
        assert hasattr(a2a_pb2, 'ROLE_USER')
        assert hasattr(a2a_pb2, 'ROLE_AGENT')
        
        # TaskState enum values
        assert hasattr(a2a_pb2, 'TASK_STATE_SUBMITTED')
        assert hasattr(a2a_pb2, 'TASK_STATE_WORKING')
        assert hasattr(a2a_pb2, 'TASK_STATE_COMPLETED')
        assert hasattr(a2a_pb2, 'TASK_STATE_FAILED')
        assert hasattr(a2a_pb2, 'TASK_STATE_CANCELLED')

    def test_mantis_core_enums_available(self):
        """Test that Mantis core enums are properly defined."""
        # ExecutionStrategy enum
        assert hasattr(mantis_core_pb2, 'EXECUTION_STRATEGY_UNSPECIFIED')
        assert hasattr(mantis_core_pb2, 'EXECUTION_STRATEGY_DIRECT')
        assert hasattr(mantis_core_pb2, 'EXECUTION_STRATEGY_A2A')
        
        # TeamFormationStrategy enum
        assert hasattr(mantis_core_pb2, 'TEAM_FORMATION_STRATEGY_UNSPECIFIED')
        assert hasattr(mantis_core_pb2, 'TEAM_FORMATION_STRATEGY_RANDOM')
        assert hasattr(mantis_core_pb2, 'TEAM_FORMATION_STRATEGY_HOMOGENEOUS')


class TestProtobufMessageCreation:
    """Test suite for protobuf message creation and field access."""

    def test_simulation_input_creation(self):
        """Test SimulationInput message creation."""
        sim_input = mantis_core_pb2.SimulationInput()
        
        assert isinstance(sim_input, Message)
        assert hasattr(sim_input, 'context_id')
        assert hasattr(sim_input, 'query')
        assert hasattr(sim_input, 'input_artifacts')
        assert hasattr(sim_input, 'execution_strategy')
        
        # Test field assignment
        sim_input.context_id = "test-context"
        sim_input.query = "test query"
        sim_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_A2A
        
        assert sim_input.context_id == "test-context"
        assert sim_input.query == "test query"
        assert sim_input.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_A2A

    def test_simulation_output_creation(self):
        """Test SimulationOutput message creation."""
        sim_output = mantis_core_pb2.SimulationOutput()
        
        assert isinstance(sim_output, Message)
        assert hasattr(sim_output, 'context_id')
        assert hasattr(sim_output, 'final_state')
        assert hasattr(sim_output, 'response_message')
        assert hasattr(sim_output, 'response_artifacts')
        assert hasattr(sim_output, 'simulation_task')
        
        # Test nested message fields
        sim_output.context_id = "test-context"
        sim_output.final_state = a2a_pb2.TASK_STATE_COMPLETED
        
        assert sim_output.context_id == "test-context"
        assert sim_output.final_state == a2a_pb2.TASK_STATE_COMPLETED

    def test_mantis_agent_card_creation(self):
        """Test MantisAgentCard message creation."""
        agent_card = mantis_persona_pb2.MantisAgentCard()
        
        assert isinstance(agent_card, Message)
        assert hasattr(agent_card, 'agent_card')
        assert hasattr(agent_card, 'persona_characteristics')
        assert hasattr(agent_card, 'competency_scores')
        assert hasattr(agent_card, 'domain_expertise')
        assert hasattr(agent_card, 'skills_summary')
        
        # Test nested A2A AgentCard
        a2a_card = a2a_pb2.AgentCard()
        a2a_card.id = "test-agent"
        a2a_card.name = "TestAgent"
        
        agent_card.agent_card.CopyFrom(a2a_card)
        assert agent_card.agent_card.id == "test-agent"
        assert agent_card.agent_card.name == "TestAgent"

    def test_a2a_message_creation(self):
        """Test A2A Message creation and content structure."""
        message = a2a_pb2.Message()
        
        assert isinstance(message, Message)
        assert hasattr(message, 'message_id')
        assert hasattr(message, 'context_id')
        assert hasattr(message, 'task_id')
        assert hasattr(message, 'role')
        assert hasattr(message, 'content')
        
        # Test message configuration
        message.message_id = "msg-123"
        message.context_id = "ctx-123"
        message.role = a2a_pb2.ROLE_USER
        
        # Add content part
        part = a2a_pb2.Part()
        part.text = "Test message content"
        message.content.append(part)
        
        assert message.message_id == "msg-123"
        assert message.context_id == "ctx-123"
        assert message.role == a2a_pb2.ROLE_USER
        assert len(message.content) == 1
        assert message.content[0].text == "Test message content"

    def test_a2a_artifact_creation(self):
        """Test A2A Artifact creation and parts structure."""
        artifact = a2a_pb2.Artifact()
        
        assert isinstance(artifact, Message)
        assert hasattr(artifact, 'artifact_id')
        assert hasattr(artifact, 'name')
        assert hasattr(artifact, 'description')
        assert hasattr(artifact, 'parts')
        
        # Test artifact configuration
        artifact.artifact_id = "art-123"
        artifact.name = "test-artifact.txt"
        artifact.description = "Test artifact for unit tests"
        
        # Add content part
        part = a2a_pb2.Part()
        part.text = "Test artifact content"
        artifact.parts.append(part)
        
        assert artifact.artifact_id == "art-123"
        assert artifact.name == "test-artifact.txt"
        assert artifact.description == "Test artifact for unit tests"
        assert len(artifact.parts) == 1
        assert artifact.parts[0].text == "Test artifact content"

    def test_a2a_task_creation(self):
        """Test A2A Task creation and status structure."""
        task = a2a_pb2.Task()
        
        assert isinstance(task, Message)
        assert hasattr(task, 'id')
        assert hasattr(task, 'context_id')
        assert hasattr(task, 'status')
        assert hasattr(task, 'history')
        assert hasattr(task, 'artifacts')
        
        # Test task configuration
        task.id = "task-123"
        task.context_id = "ctx-123"
        
        # Test status field access
        assert hasattr(task.status, 'state')
        task.status.state = a2a_pb2.TASK_STATE_WORKING
        
        assert task.id == "task-123"
        assert task.context_id == "ctx-123"
        assert task.status.state == a2a_pb2.TASK_STATE_WORKING


class TestProtobufFieldValidation:
    """Test suite for protobuf field validation and constraints."""

    def test_required_field_access(self):
        """Test that required fields can be accessed and set."""
        sim_input = mantis_core_pb2.SimulationInput()
        
        # These should not raise exceptions
        sim_input.context_id = "test"
        sim_input.query = "test query"
        
        assert sim_input.context_id == "test"
        assert sim_input.query == "test query"

    def test_optional_field_behavior(self):
        """Test optional field behavior and HasField() method."""
        sim_input = mantis_core_pb2.SimulationInput()
        
        # Optional fields should not be set by default
        assert not sim_input.HasField('context') if hasattr(sim_input, 'HasField') else True
        
        # Setting optional field should work
        sim_input.context = "optional context"
        assert sim_input.context == "optional context"

    def test_repeated_field_behavior(self):
        """Test repeated field behavior for lists."""
        sim_input = mantis_core_pb2.SimulationInput()
        
        # Repeated fields should be empty lists initially
        assert len(sim_input.input_artifacts) == 0
        
        # Adding to repeated field should work
        artifact = a2a_pb2.Artifact()
        artifact.artifact_id = "test-artifact"
        sim_input.input_artifacts.append(artifact)
        
        assert len(sim_input.input_artifacts) == 1
        assert sim_input.input_artifacts[0].artifact_id == "test-artifact"

    def test_enum_field_validation(self):
        """Test enum field validation and value assignment."""
        sim_input = mantis_core_pb2.SimulationInput()
        
        # Valid enum values should work
        valid_strategies = [
            mantis_core_pb2.EXECUTION_STRATEGY_UNSPECIFIED,
            mantis_core_pb2.EXECUTION_STRATEGY_DIRECT,
            mantis_core_pb2.EXECUTION_STRATEGY_A2A
        ]
        
        for strategy in valid_strategies:
            sim_input.execution_strategy = strategy
            assert sim_input.execution_strategy == strategy

    def test_nested_message_field_behavior(self):
        """Test nested message field behavior."""
        sim_output = mantis_core_pb2.SimulationOutput()
        
        # Nested message fields should be accessible
        assert hasattr(sim_output, 'response_message')
        assert hasattr(sim_output, 'simulation_task')
        
        # Should be able to access nested message without explicit creation
        sim_output.response_message.message_id = "nested-msg"
        assert sim_output.response_message.message_id == "nested-msg"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
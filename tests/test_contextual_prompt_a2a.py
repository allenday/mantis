"""
Unit tests for ContextualPrompt A2A Message integration.

Tests the enhanced ContextualPrompt functionality that generates A2A Messages
directly as required by the PRD, including:
- Message template creation
- A2A context threading
- Role assignment
- Part content assembly
"""

import pytest
import uuid
from unittest.mock import Mock

from mantis.core.contextual_prompt import ContextualPrompt
from mantis.proto.mantis.v1 import mantis_persona_pb2
from mantis.proto import a2a_pb2


class TestContextualPromptA2AIntegration:
    """Test suite for ContextualPrompt A2A Message generation."""

    def create_test_agent_card(self) -> mantis_persona_pb2.MantisAgentCard:
        """Create test MantisAgentCard for testing."""
        agent_card = mantis_persona_pb2.MantisAgentCard()
        agent_card.persona_title = "Test Persona"
        
        # Add test agent card from A2A
        a2a_card = a2a_pb2.AgentCard()
        a2a_card.id = "test-agent-123"
        a2a_card.name = "TestAgent"
        a2a_card.description = "A test agent for unit testing"
        agent_card.agent_card.CopyFrom(a2a_card)
        
        return agent_card

    def test_contextual_prompt_initialization_basic(self):
        """Test ContextualPrompt initializes correctly with basic parameters."""
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5
        )
        
        assert prompt.agent_name == "TestAgent"
        assert prompt.context_content == "Test context"
        assert prompt.priority == 5

    def test_contextual_prompt_initialization_with_agent_card(self):
        """Test ContextualPrompt initializes with agent card."""
        agent_card = self.create_test_agent_card()
        
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5,
            agent_card=agent_card
        )
        
        assert prompt.agent_card == agent_card
        assert prompt.agent_name == "TestAgent"

    def test_contextual_prompt_initialization_with_prefixes_suffixes(self):
        """Test ContextualPrompt initializes with prefix/suffix lists."""
        prefixes = ["Prefix 1", "Prefix 2"]
        suffixes = ["Suffix 1", "Suffix 2"]
        
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5,
            prefixes=prefixes,
            suffixes=suffixes
        )
        
        assert prompt.prefixes == prefixes
        assert prompt.suffixes == suffixes

    def test_create_message_template_basic(self):
        """Test create_message_template with basic parameters."""
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context content",
            priority=5
        )
        
        message = prompt.create_message_template()
        
        assert isinstance(message, a2a_pb2.Message)
        assert message.role == a2a_pb2.ROLE_USER  # Default role
        assert len(message.message_id) > 0
        assert message.message_id.startswith("ctx-")
        assert len(message.content) > 0

    def test_create_message_template_with_context_id(self):
        """Test create_message_template with explicit context_id."""
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5
        )
        
        test_context_id = "test-context-123"
        message = prompt.create_message_template(context_id=test_context_id)
        
        assert message.context_id == test_context_id

    def test_create_message_template_with_task_id(self):
        """Test create_message_template with explicit task_id."""
        prompt = ContextualPrompt(
            agent_name="TestAgent", 
            context_content="Test context",
            priority=5
        )
        
        test_task_id = "test-task-456"
        message = prompt.create_message_template(task_id=test_task_id)
        
        assert message.task_id == test_task_id

    def test_create_message_template_with_agent_role(self):
        """Test create_message_template with AGENT role."""
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5
        )
        
        message = prompt.create_message_template(role=a2a_pb2.ROLE_AGENT)
        
        assert message.role == a2a_pb2.ROLE_AGENT

    def test_create_message_template_content_assembly(self):
        """Test that create_message_template properly assembles content."""
        prefixes = ["System prompt: You are a helpful assistant."]
        core_content = "Main query: What is the weather like?"
        suffixes = ["Please provide a detailed response."]
        
        prompt = ContextualPrompt(
            agent_name="WeatherAgent",
            context_content="Location: San Francisco",
            priority=5,
            prefixes=prefixes,
            core_content=core_content,
            suffixes=suffixes
        )
        
        message = prompt.create_message_template()
        
        assert len(message.content) == 1  # Should be assembled into single part
        content_text = message.content[0].text
        
        # Verify all components are present
        assert "System prompt: You are a helpful assistant." in content_text
        assert "Main query: What is the weather like?" in content_text
        assert "Please provide a detailed response." in content_text
        assert "Location: San Francisco" in content_text

    def test_create_message_template_with_agent_card_info(self):
        """Test create_message_template incorporates agent card information."""
        agent_card = self.create_test_agent_card()
        
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5,
            agent_card=agent_card
        )
        
        message = prompt.create_message_template()
        
        content_text = message.content[0].text
        assert "TestAgent" in content_text  # Agent name should be present
        assert "Test Persona" in content_text  # Persona title should be present

    def test_create_message_template_preserves_priority_info(self):
        """Test create_message_template includes priority information."""
        high_priority_prompt = ContextualPrompt(
            agent_name="UrgentAgent", 
            context_content="Urgent task",
            priority=10
        )
        
        message = high_priority_prompt.create_message_template()
        
        content_text = message.content[0].text
        assert "Priority: 10" in content_text

    def test_create_message_template_unique_ids(self):
        """Test create_message_template generates unique message IDs."""
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5
        )
        
        message1 = prompt.create_message_template()
        message2 = prompt.create_message_template()
        
        assert message1.message_id != message2.message_id
        # Both messages should have proper ctx- prefix
        assert message1.message_id.startswith("ctx-")
        assert message2.message_id.startswith("ctx-")

    def test_assemble_method_backward_compatibility(self):
        """Test that assemble() method still works for backward compatibility."""
        prompt = ContextualPrompt(
            agent_name="TestAgent",
            context_content="Test context",
            priority=5,
            prefixes=["Prefix content"],
            core_content="Core content", 
            suffixes=["Suffix content"]
        )
        
        assembled = prompt.assemble()
        
        assert isinstance(assembled, str)
        assert "Prefix content" in assembled
        assert "Core content" in assembled
        assert "Suffix content" in assembled
        assert "Test context" in assembled

    def test_contextual_prompt_empty_content_handling(self):
        """Test ContextualPrompt handles empty content gracefully."""
        prompt = ContextualPrompt(
            agent_name="",
            context_content="",
            priority=0
        )
        
        message = prompt.create_message_template()
        
        assert isinstance(message, a2a_pb2.Message)
        assert len(message.content) > 0
        # Should still create a valid message even with empty content

    def test_contextual_prompt_none_values_handling(self):
        """Test ContextualPrompt handles None values safely."""
        prompt = ContextualPrompt(
            agent_name=None,
            context_content=None,
            priority=5,
            prefixes=None,
            suffixes=None,
            agent_card=None
        )
        
        message = prompt.create_message_template()
        
        assert isinstance(message, a2a_pb2.Message)
        assert len(message.content) > 0

    def test_a2a_message_template_protobuf_compliance(self):
        """Test that generated A2A Messages follow protobuf schema."""
        prompt = ContextualPrompt(
            agent_name="ComplianceAgent",
            context_content="Testing protobuf compliance",
            priority=5
        )
        
        message = prompt.create_message_template(
            context_id="ctx-123",
            task_id="task-456"
        )
        
        # Verify all required A2A Message fields are properly set
        assert hasattr(message, 'message_id')
        assert hasattr(message, 'context_id')
        assert hasattr(message, 'task_id')
        assert hasattr(message, 'role')
        assert hasattr(message, 'content')
        
        # Verify field types
        assert isinstance(message.message_id, str)
        assert isinstance(message.context_id, str)
        assert isinstance(message.task_id, str)
        assert isinstance(message.role, int)
        assert len(message.content) > 0
        assert isinstance(message.content[0], a2a_pb2.Part)

    def test_a2a_part_content_structure(self):
        """Test that A2A Part content is properly structured."""
        prompt = ContextualPrompt(
            agent_name="StructureAgent",
            context_content="Testing part structure",
            priority=5,
            core_content="Main content here"
        )
        
        message = prompt.create_message_template()
        
        assert len(message.content) == 1  # Should be single assembled part
        part = message.content[0]
        
        assert isinstance(part, a2a_pb2.Part)
        assert hasattr(part, 'text')
        assert len(part.text) > 0
        assert "Main content here" in part.text
        assert "Testing part structure" in part.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
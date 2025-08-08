"""
Unit tests for ContextualPrompt template assembly system.
"""

import pytest
from mantis.core.contextual_prompt import (
    ContextualPrompt,
    ContextualPromptBuilder,
    create_simulation_prompt,
    create_a2a_message_from_prompt
)
from mantis.proto.mantis.v1 import mantis_persona_pb2
from mantis.proto import a2a_pb2


class TestContextualPrompt:
    """Test ContextualPrompt class."""
    
    def test_basic_prompt_assembly(self):
        """Test basic prompt assembly without agent."""
        prompt = ContextualPrompt(
            prefixes=["System context prefix"],
            core_content="Main task content",
            suffixes=["Response guidelines"]
        )
        
        result = prompt.assemble()
        
        assert "System context prefix" in result
        assert "Main task content" in result
        assert "Response guidelines" in result
        assert result.count("\n\n") >= 2  # Should have separators
    
    def test_empty_components_handling(self):
        """Test handling of empty components."""
        prompt = ContextualPrompt(
            prefixes=[],
            core_content="Only core content",
            suffixes=[]
        )
        
        result = prompt.assemble()
        assert result.strip() == "Only core content"
    
    def test_agent_persona_extraction(self):
        """Test extraction of agent persona information."""
        # Create test agent card
        agent_card = mantis_persona_pb2.MantisAgentCard()
        
        # Basic agent info
        agent_card.agent_card.name = "Test Agent"
        agent_card.agent_card.description = "Test Description"
        
        # Persona characteristics
        persona = mantis_persona_pb2.PersonaCharacteristics()
        persona.core_principles.extend(["Principle 1", "Principle 2"])
        persona.decision_framework = "Test Framework"
        persona.communication_style = "Test Style"
        agent_card.persona_characteristics.CopyFrom(persona)
        
        # Domain expertise
        expertise = mantis_persona_pb2.DomainExpertise()
        expertise.primary_domains.extend(["Domain 1", "Domain 2"])
        expertise.methodologies.extend(["Method 1", "Method 2"])
        agent_card.domain_expertise.CopyFrom(expertise)
        
        # Skills summary
        skills = mantis_persona_pb2.SkillsSummary()
        skills.skill_overview = "Test skills overview"
        skills.signature_abilities.extend(["Ability 1", "Ability 2"])
        agent_card.skills_summary.CopyFrom(skills)
        
        prompt = ContextualPrompt(
            prefixes=[],
            core_content="Test content",
            suffixes=[],
            agent_card=agent_card
        )
        
        result = prompt.assemble()
        
        # Check agent context extraction
        assert "## Agent Context" in result
        assert "Agent: Test Agent" in result
        assert "Role: Test Description" in result
        assert "Core Principles: Principle 1, Principle 2" in result
        assert "Decision Framework: Test Framework" in result
        assert "Communication Style: Test Style" in result
        assert "Primary Domains: Domain 1, Domain 2" in result
        assert "Methodologies: Method 1, Method 2" in result
        assert "Skills: Test skills overview" in result
        assert "Signature Abilities: Ability 1, Ability 2" in result
    
    def test_task_context_formatting(self):
        """Test task context formatting."""
        prompt = ContextualPrompt(
            prefixes=[],
            core_content="Test content",
            suffixes=[],
            task_context={
                "priority": "high",
                "deadline": "2024-12-31",
                "team_size": 5,
                "empty_value": None
            }
        )
        
        result = prompt.assemble()
        
        assert "## Task Context" in result
        assert "Priority: high" in result
        assert "Deadline: 2024-12-31" in result
        assert "Team Size: 5" in result
        assert "empty_value" not in result  # None values should be excluded


class TestContextualPromptBuilder:
    """Test ContextualPromptBuilder class."""
    
    def test_builder_pattern_basic(self):
        """Test basic builder pattern usage."""
        prompt = (ContextualPromptBuilder()
                 .add_prefix("Prefix 1")
                 .add_prefix("Prefix 2")
                 .set_core_content("Core content")
                 .add_suffix("Suffix 1")
                 .add_suffix("Suffix 2")
                 .build())
        
        result = prompt.assemble()
        
        assert "Prefix 1" in result
        assert "Prefix 2" in result
        assert "Core content" in result
        assert "Suffix 1" in result
        assert "Suffix 2" in result
    
    def test_builder_with_agent_and_context(self):
        """Test builder with agent and task context."""
        # Create minimal agent card
        agent_card = mantis_persona_pb2.MantisAgentCard()
        agent_card.agent_card.name = "Builder Test Agent"
        
        prompt = (ContextualPromptBuilder()
                 .set_core_content("Builder test content")
                 .with_agent(agent_card)
                 .with_task_context(test_param="test_value", priority="medium")
                 .build())
        
        result = prompt.assemble()
        
        assert "Builder Test Agent" in result
        assert "Builder test content" in result
        assert "Test Param: test_value" in result
        assert "Priority: medium" in result
    
    def test_builder_method_chaining(self):
        """Test that all builder methods return self for chaining."""
        builder = ContextualPromptBuilder()
        
        # All methods should return the builder instance
        assert builder.add_prefix("test") is builder
        assert builder.set_core_content("test") is builder
        assert builder.add_suffix("test") is builder
        assert builder.with_task_context(test="value") is builder
        
        # with_agent requires an agent card, test separately
        agent_card = mantis_persona_pb2.MantisAgentCard()
        assert builder.with_agent(agent_card) is builder


class TestSimulationPromptCreation:
    """Test simulation prompt creation utilities."""
    
    def test_create_simulation_prompt_basic(self):
        """Test basic simulation prompt creation."""
        prompt = create_simulation_prompt(
            query="Test query",
            context_id="test-001",
            task_id="task-001"
        )
        
        result = prompt.assemble()
        
        assert "multi-agent simulation" in result
        assert "## Query" in result
        assert "Test query" in result
        assert "thoughtful response" in result
    
    def test_create_simulation_prompt_with_agent(self):
        """Test simulation prompt creation with agent card."""
        # Create test agent
        agent_card = mantis_persona_pb2.MantisAgentCard()
        agent_card.agent_card.name = "Simulation Test Agent"
        agent_card.agent_card.description = "Test agent for simulation"
        
        prompt = create_simulation_prompt(
            query="Analyze test scenario",
            agent_card=agent_card,
            context_id="sim-001"
        )
        
        result = prompt.assemble()
        
        assert "Simulation Test Agent" in result
        assert "Test agent for simulation" in result
        assert "Analyze test scenario" in result
        assert "multi-agent simulation" in result


class TestA2AMessageIntegration:
    """Test A2A Message integration."""
    
    def test_create_a2a_message_from_prompt(self):
        """Test creating A2A Message from ContextualPrompt."""
        prompt = ContextualPrompt(
            prefixes=["Test prefix"],
            core_content="Test core content", 
            suffixes=["Test suffix"]
        )
        
        message = create_a2a_message_from_prompt(
            prompt=prompt,
            context_id="test-context",
            task_id="test-task"
        )
        
        assert isinstance(message, a2a_pb2.Message)
        assert message.role == a2a_pb2.ROLE_USER
        assert message.context_id == "test-context"
        assert message.task_id == "test-task"
        assert len(message.content) == 1
        assert message.content[0].text == prompt.assemble()
    
    def test_create_a2a_message_optional_ids(self):
        """Test A2A Message creation with optional IDs."""
        prompt = ContextualPrompt(
            prefixes=[],
            core_content="Simple test",
            suffixes=[]
        )
        
        message = create_a2a_message_from_prompt(prompt=prompt)
        
        assert isinstance(message, a2a_pb2.Message)
        assert message.role == a2a_pb2.ROLE_USER
        assert message.context_id == ""  # Should be empty when not provided
        assert message.task_id == ""     # Should be empty when not provided


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_prompt_with_none_values(self):
        """Test prompt handling with None values."""
        prompt = ContextualPrompt(
            prefixes=["Valid prefix"],
            core_content="Valid content",
            suffixes=["Valid suffix"],
            agent_card=None,
            task_context=None
        )
        
        result = prompt.assemble()
        
        # Should not crash and should contain valid content
        assert "Valid prefix" in result
        assert "Valid content" in result
        assert "Valid suffix" in result
        assert "## Agent Context" not in result
        assert "## Task Context" not in result
    
    def test_empty_agent_card(self):
        """Test handling of empty agent card."""
        agent_card = mantis_persona_pb2.MantisAgentCard()
        # Don't set any fields
        
        prompt = ContextualPrompt(
            prefixes=[],
            core_content="Test",
            suffixes=[],
            agent_card=agent_card
        )
        
        result = prompt.assemble()
        
        # Should not crash, but may not have much agent context
        assert "Test" in result
        # Empty agent card should result in minimal or no agent context
    
    def test_builder_immutability(self):
        """Test that building doesn't affect the builder state."""
        builder = ContextualPromptBuilder()
        builder.add_prefix("Test prefix")
        builder.set_core_content("Test content")
        
        prompt1 = builder.build()
        prompt2 = builder.build()
        
        # Both prompts should be identical
        assert prompt1.assemble() == prompt2.assemble()
        
        # Modifying builder after building should not affect previous builds
        builder.add_suffix("New suffix")
        prompt3 = builder.build()
        
        assert "New suffix" not in prompt1.assemble()
        assert "New suffix" not in prompt2.assemble()
        assert "New suffix" in prompt3.assemble()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
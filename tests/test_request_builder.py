"""
Tests for UserRequestBuilder.
"""

import pytest
import json
from mantis.core import UserRequestBuilder
from mantis.proto.mantis.v1 import mantis_core_pb2


class TestUserRequestBuilder:
    """Test cases for UserRequestBuilder."""

    def test_basic_request(self):
        """Test building a basic request with just a query."""
        builder = UserRequestBuilder()
        request = builder.query("What is the meaning of life?").build()
        
        assert request.query == "What is the meaning of life?"
        assert len(request.agents) == 1  # Default agent added
        assert request.agents[0].count == 1
        assert request.agents[0].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MAY

    def test_full_request(self):
        """Test building a request with all fields."""
        builder = UserRequestBuilder()
        request = (builder
                  .query("Complex query")
                  .context("Some context")
                  .structured_data({"key": "value"})
                  .model_spec("claude-3-5-sonnet", 0.8)
                  .max_depth(1)
                  .add_agent(count=2, recursion_policy="may")
                  .build())
        
        assert request.query == "Complex query"
        assert request.context == "Some context"
        assert '"key": "value"' in request.structured_data
        assert request.model_spec.model == "claude-3-5-sonnet"
        assert request.model_spec.temperature == 0.8
        assert request.max_depth == 1
        assert len(request.agents) == 1
        assert request.agents[0].count == 2
        assert request.agents[0].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MAY

    def test_agent_parsing(self):
        """Test parsing agent specifications from strings."""
        builder = UserRequestBuilder()
        request = (builder
                  .query("Test")
                  .parse_agents_string("leader:1:may,follower:2:must_not")
                  .build())
        
        assert len(request.agents) == 2
        
        # First agent
        assert request.agents[0].count == 1
        assert request.agents[0].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MAY
        
        # Second agent
        assert request.agents[1].count == 2
        assert request.agents[1].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MUST_NOT

    def test_agent_parsing_simple(self):
        """Test simple agent parsing without counts or policies."""
        builder = UserRequestBuilder()
        request = (builder
                  .query("Test")
                  .parse_agents_string("agent1,agent2")
                  .build())
        
        assert len(request.agents) == 2
        # Both should have default count=1
        assert request.agents[0].count == 1
        assert request.agents[1].count == 1

    def test_agent_parsing_with_counts(self):
        """Test agent parsing with counts but no policies."""
        builder = UserRequestBuilder()
        request = (builder
                  .query("Test")
                  .parse_agents_string("agent1:3,agent2:1")
                  .build())
        
        assert len(request.agents) == 2
        assert request.agents[0].count == 3
        assert request.agents[1].count == 1

    def test_from_cli_args(self):
        """Test the convenience method for CLI args."""
        request = UserRequestBuilder.from_cli_args(
            query="CLI test",
            context="CLI context",
            model="claude-3-5-haiku",
            temperature=0.5,
            max_depth=1,
            agents="leader:1:may,follower:1:must_not"
        )
        
        assert request.query == "CLI test"
        assert request.context == "CLI context"
        assert request.model_spec.model == "claude-3-5-haiku"
        assert request.model_spec.temperature == 0.5
        assert request.max_depth == 1
        assert len(request.agents) == 2

    def test_validation_errors(self):
        """Test validation of various error conditions."""
        builder = UserRequestBuilder()
        
        # Empty query
        with pytest.raises(ValueError, match="Query cannot be empty"):
            builder.query("").build()
            
        # Invalid temperature
        with pytest.raises(ValueError, match="Temperature must be between"):
            builder.query("test").model_spec(temperature=3.0).build()
            
        # Invalid max depth
        with pytest.raises(ValueError, match="Max depth must be at least 1"):
            builder.query("test").max_depth(0).build()
            
        with pytest.raises(ValueError, match="Max depth cannot exceed 1 for safety"):
            builder.query("test").max_depth(15).build()
            
        # Invalid agent count
        with pytest.raises(ValueError, match="Agent count must be at least 1"):
            builder.query("test").add_agent(count=0).build()

    def test_invalid_agent_parsing(self):
        """Test error handling in agent string parsing."""
        builder = UserRequestBuilder()
        
        # Invalid count
        with pytest.raises(ValueError, match="not a number"):
            builder.query("test").parse_agents_string("agent:abc")
            
        # Invalid policy
        with pytest.raises(ValueError, match="Invalid recursion policy"):
            builder.query("test").parse_agents_string("agent:1:invalid")
            
        # Too many parts
        with pytest.raises(ValueError, match="Invalid agent specification format"):
            builder.query("test").parse_agents_string("agent:1:may:extra")

    def test_validation_method(self):
        """Test the validation method returns appropriate errors."""
        builder = UserRequestBuilder()
        
        # No query
        errors = builder.validate()
        assert "Query is required" in errors
        
        # Invalid max depth - set directly to bypass setter validation
        builder.query("test")
        builder._max_depth = -1
        errors = builder.validate()
        assert any("Max depth must be at least 1" in error for error in errors)
        
        # Valid builder
        builder = UserRequestBuilder().query("test")
        errors = builder.validate()
        assert len(errors) == 0

    def test_structured_data_dict(self):
        """Test structured data with dictionary input."""
        builder = UserRequestBuilder()
        data = {"users": ["alice", "bob"], "count": 42}
        request = builder.query("test").structured_data(data).build()
        
        # Should be JSON string
        parsed_data = json.loads(request.structured_data)
        assert parsed_data == data

    def test_recursion_policy_aliases(self):
        """Test recursion policy string aliases."""
        # Test "no" alias for "must_not"
        builder1 = UserRequestBuilder()
        request1 = builder1.query("test").parse_agents_string("agent:1:no").build()
        assert request1.agents[0].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MUST_NOT
        
        # Test case insensitivity
        builder2 = UserRequestBuilder()
        request2 = builder2.query("test").parse_agents_string("agent:1:MAY").build()
        assert request2.agents[0].recursion_policy == mantis_core_pb2.RECURSION_POLICY_MAY

    def test_optional_fields(self):
        """Test that optional fields are properly handled."""
        builder = UserRequestBuilder()
        request = builder.query("minimal test").build()
        
        # These should not be set
        assert not request.HasField("context")
        assert not request.HasField("structured_data")
        assert not request.HasField("model_spec")
        assert not request.HasField("max_depth")
        
        # But agents should be added by default
        assert len(request.agents) == 1
"""
Unit tests for the registry access tool.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mantis.tools import (
    RegistryTool,
    RegistryConfig,
    AgentCard,
    AgentSpec,
    RegistrySearchFilters as SearchFilters,
    RegistryError,
)


class MockAsyncContextManager:
    """Mock async context manager for aiohttp response."""
    
    def __init__(self, response):
        self.response = response
    
    async def __aenter__(self):
        return self.response
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestRegistryConfig:
    """Test RegistryConfig model."""

    def test_registry_config_defaults(self):
        """Test default configuration values."""
        config = RegistryConfig()
        
        assert config.registry_url == "http://localhost:8080"
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.user_agent == "Mantis-RegistryTool/1.0"
        assert config.enable_caching is True
        assert config.cache_ttl == 300

    def test_registry_config_custom_values(self):
        """Test custom configuration values."""
        config = RegistryConfig(
            registry_url="http://custom-registry:8080",
            timeout=60.0,
            max_retries=5,
            enable_caching=False
        )
        
        assert config.registry_url == "http://custom-registry:8080"
        assert config.timeout == 60.0
        assert config.max_retries == 5
        assert config.enable_caching is False


class TestAgentCard:
    """Test AgentCard model."""

    def test_agent_card_creation(self):
        """Test creating an agent card with minimum fields."""
        card = AgentCard(
            url="https://example.com/agent",
            name="Test Agent"
        )
        
        assert card.url == "https://example.com/agent"
        assert card.name == "Test Agent"
        assert card.version == "1.0.0"
        assert card.trust_level == "UNVERIFIED"
        assert card.status == "UNKNOWN"
        assert card.skills == []
        assert card.competencies == []

    def test_agent_card_full_data(self):
        """Test creating an agent card with full data."""
        skills = [
            {"name": "Python Programming", "description": "Advanced Python development"},
            {"name": "Machine Learning", "description": "ML model development"}
        ]
        
        card = AgentCard(
            url="https://example.com/agent",
            name="ML Agent",
            description="Expert machine learning agent",
            version="2.1.0",
            provider={"organization": "AI Corp"},
            skills=skills,
            competencies=["Python Programming", "Machine Learning"],
            trust_level="VERIFIED",
            health_score=95,
            status="ACTIVE"
        )
        
        assert card.name == "ML Agent"
        assert card.description == "Expert machine learning agent"
        assert card.version == "2.1.0"
        assert card.provider["organization"] == "AI Corp"
        assert len(card.skills) == 2
        assert card.competencies == ["Python Programming", "Machine Learning"]
        assert card.trust_level == "VERIFIED"
        assert card.health_score == 95
        assert card.status == "ACTIVE"


class TestAgentSpec:
    """Test AgentSpec model."""

    def test_agent_spec_creation(self):
        """Test creating an agent specification."""
        spec = AgentSpec(
            agent_url="https://example.com/agent",
            role="Data Analyst",
            capabilities=["data-analysis", "visualization"],
            priority=2,
            max_interactions=10
        )
        
        assert spec.agent_url == "https://example.com/agent"
        assert spec.role == "Data Analyst"
        assert spec.capabilities == ["data-analysis", "visualization"]
        assert spec.priority == 2
        assert spec.max_interactions == 10

    def test_agent_spec_defaults(self):
        """Test agent specification with default values."""
        spec = AgentSpec(
            agent_url="https://example.com/agent",
            role="Helper"
        )
        
        assert spec.priority == 1
        assert spec.max_interactions is None
        assert spec.capabilities == []


class TestSearchFilters:
    """Test SearchFilters model."""

    def test_search_filters_defaults(self):
        """Test default search filter values."""
        filters = SearchFilters()
        
        assert filters.required_capabilities == []
        assert filters.required_skills == []
        assert filters.trust_levels == ["VERIFIED", "OFFICIAL"]
        assert filters.min_health_score is None
        assert filters.max_response_time_ms is None
        assert filters.preferred_regions == []
        assert filters.require_domain_verified is False

    def test_search_filters_custom(self):
        """Test custom search filters."""
        filters = SearchFilters(
            required_capabilities=["python", "ml"],
            required_skills=["TensorFlow", "PyTorch"],
            trust_levels=["OFFICIAL"],
            min_health_score=80,
            require_domain_verified=True
        )
        
        assert filters.required_capabilities == ["python", "ml"]
        assert filters.required_skills == ["TensorFlow", "PyTorch"]
        assert filters.trust_levels == ["OFFICIAL"]
        assert filters.min_health_score == 80
        assert filters.require_domain_verified is True


class TestRegistryTool:
    """Test RegistryTool functionality."""

    @pytest.fixture
    def registry_tool(self):
        """Create a registry tool instance for testing."""
        config = RegistryConfig(registry_url="http://test-registry:8080")
        return RegistryTool(config)

    @pytest.fixture
    def sample_agent_data(self):
        """Sample agent data for testing."""
        return [
            {
                "url": "https://example.com/agent1",
                "name": "Python Agent",
                "description": "Expert Python developer agent",
                "version": "1.2.0",
                "provider": {"organization": "DevCorp"},
                "skills": [
                    {"name": "Python", "description": "Python programming"},
                    {"name": "FastAPI", "description": "Web framework"}
                ],
                "trust_level": "VERIFIED",
                "health_score": 95,
                "status": "ACTIVE"
            },
            {
                "url": "https://example.com/agent2",
                "name": "ML Specialist",
                "description": "Machine learning expert",
                "version": "2.0.0",
                "provider": {"organization": "AI Lab"},
                "skills": [
                    {"name": "TensorFlow", "description": "Deep learning"},
                    {"name": "Data Analysis", "description": "Statistical analysis"}
                ],
                "trust_level": "OFFICIAL",
                "health_score": 88,
                "status": "ACTIVE"
            }
        ]

    def test_registry_tool_initialization(self):
        """Test registry tool initialization."""
        tool = RegistryTool()
        assert tool.config.registry_url == "http://localhost:8080"
        assert tool._session is None
        assert tool._cache == {}

    def test_registry_tool_custom_config(self):
        """Test registry tool with custom config."""
        config = RegistryConfig(
            registry_url="http://custom:8080",
            timeout=45.0
        )
        tool = RegistryTool(config)
        
        assert tool.config.registry_url == "http://custom:8080"
        assert tool.config.timeout == 45.0

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test registry tool as async context manager."""
        tool = RegistryTool()
        
        async with tool as t:
            assert t is tool
            assert t._session is not None
        
        assert tool._session is None or tool._session.closed

    @pytest.mark.asyncio
    async def test_call_registry_jsonrpc_success(self, registry_tool):
        """Test successful JSON-RPC call."""
        mock_response_data = {"agents": [{"name": "test"}]}
        
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"result": mock_response_data})
        
        # Create the async context manager
        mock_context = MockAsyncContextManager(mock_response)
        
        # Mock the session - use MagicMock for post method to avoid coroutine issues
        mock_session = MagicMock()
        mock_session.post.return_value = mock_context
        
        registry_tool._session = mock_session
        
        with patch.object(registry_tool, '_ensure_session'):
            # Test the call
            result = await registry_tool._call_registry_jsonrpc("list_agents", {})
            
            assert result == mock_response_data
            mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_registry_jsonrpc_error(self, registry_tool):
        """Test JSON-RPC call with error response."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "error": {"message": "Test error", "code": -1}
        })
        
        # Create the async context manager
        mock_context = MockAsyncContextManager(mock_response)
        
        # Mock the session - use MagicMock for post method to avoid coroutine issues
        mock_session = MagicMock()
        mock_session.post.return_value = mock_context
        
        registry_tool._session = mock_session
        
        with patch.object(registry_tool, '_ensure_session'):
            with pytest.raises(RegistryError, match="Test error"):
                await registry_tool._call_registry_jsonrpc("list_agents", {})

    @pytest.mark.asyncio
    async def test_call_registry_jsonrpc_http_error(self, registry_tool):
        """Test JSON-RPC call with HTTP error."""
        # Mock the response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Internal Server Error")
        
        # Create the async context manager
        mock_context = MockAsyncContextManager(mock_response)
        
        # Mock the session - use MagicMock for post method to avoid coroutine issues
        mock_session = MagicMock()
        mock_session.post.return_value = mock_context
        
        registry_tool._session = mock_session
        
        with patch.object(registry_tool, '_ensure_session'):
            with pytest.raises(RegistryError, match="HTTP 500"):
                await registry_tool._call_registry_jsonrpc("list_agents", {})

    @pytest.mark.asyncio
    async def test_list_all_agents_success(self, registry_tool, sample_agent_data):
        """Test successfully listing all agents."""
        with patch.object(registry_tool, '_call_registry_jsonrpc') as mock_call:
            mock_call.return_value = {"agents": sample_agent_data}
            
            agents = await registry_tool.list_all_agents(limit=10)
            
            assert len(agents) == 2
            assert agents[0].name == "Python Agent"
            assert agents[0].url == "https://example.com/agent1"
            assert agents[0].trust_level == "VERIFIED"
            assert agents[0].health_score == 95
            assert agents[1].name == "ML Specialist"
            
            mock_call.assert_called_once_with("list_agents", {})

    @pytest.mark.asyncio
    async def test_list_all_agents_with_caching(self, registry_tool, sample_agent_data):
        """Test agent listing with caching enabled."""
        registry_tool.config.enable_caching = True
        
        with patch.object(registry_tool, '_call_registry_jsonrpc') as mock_call:
            mock_call.return_value = {"agents": sample_agent_data}
            
            # First call should hit the registry
            agents1 = await registry_tool.list_all_agents(limit=5)
            assert len(agents1) == 2
            assert mock_call.call_count == 1
            
            # Second call should use cache
            agents2 = await registry_tool.list_all_agents(limit=5)
            assert len(agents2) == 2
            assert mock_call.call_count == 1  # No additional calls
            
            # Verify cache was used
            assert agents1[0].name == agents2[0].name

    @pytest.mark.asyncio
    async def test_search_agents_text_matching(self, registry_tool, sample_agent_data):
        """Test agent search with text matching."""
        with patch.object(registry_tool, 'list_all_agents') as mock_list:
            # Convert sample data to AgentCard objects
            agent_cards = []
            for data in sample_agent_data:
                card = AgentCard(**data)
                card.competencies = [skill["name"] for skill in data["skills"]]
                agent_cards.append(card)
            
            mock_list.return_value = agent_cards
            
            # Search for "Python" should return Python Agent
            results = await registry_tool.search_agents("Python", limit=5)
            
            assert len(results) == 1
            assert results[0].name == "Python Agent"
            
            # Search for "machine learning" should return ML Specialist
            results = await registry_tool.search_agents("machine learning", limit=5)
            
            assert len(results) == 1
            assert results[0].name == "ML Specialist"

    @pytest.mark.asyncio
    async def test_search_agents_with_filters(self, registry_tool, sample_agent_data):
        """Test agent search with filters."""
        with patch.object(registry_tool, 'list_all_agents') as mock_list:
            # Convert sample data to AgentCard objects
            agent_cards = []
            for data in sample_agent_data:
                card = AgentCard(**data)
                card.competencies = [skill["name"] for skill in data["skills"]]
                agent_cards.append(card)
            
            mock_list.return_value = agent_cards
            
            # Filter by trust level - should only return OFFICIAL agents
            filters = SearchFilters(trust_levels=["OFFICIAL"])
            results = await registry_tool.search_agents("", limit=5, filters=filters)
            
            assert len(results) == 1
            assert results[0].name == "ML Specialist"
            assert results[0].trust_level == "OFFICIAL"
            
            # Filter by minimum health score
            filters = SearchFilters(min_health_score=90)
            results = await registry_tool.search_agents("", limit=5, filters=filters)
            
            assert len(results) == 1
            assert results[0].name == "Python Agent"
            assert results[0].health_score == 95

    @pytest.mark.asyncio
    async def test_get_agent_details_success(self, registry_tool, sample_agent_data):
        """Test getting agent details successfully."""
        with patch.object(registry_tool, 'list_all_agents') as mock_list:
            agent_cards = []
            for data in sample_agent_data:
                card = AgentCard(**data)
                card.competencies = [skill["name"] for skill in data["skills"]]
                agent_cards.append(card)
            
            mock_list.return_value = agent_cards
            
            agent = await registry_tool.get_agent_details("https://example.com/agent1")
            
            assert agent.name == "Python Agent"
            assert agent.url == "https://example.com/agent1"
            assert agent.trust_level == "VERIFIED"

    @pytest.mark.asyncio
    async def test_get_agent_details_not_found(self, registry_tool):
        """Test getting details for non-existent agent."""
        with patch.object(registry_tool, 'list_all_agents') as mock_list:
            mock_list.return_value = []
            
            with pytest.raises(RegistryError, match="Agent not found"):
                await registry_tool.get_agent_details("https://example.com/nonexistent")

    @pytest.mark.asyncio
    async def test_recruit_agent_success(self, registry_tool, sample_agent_data):
        """Test successful agent recruitment."""
        with patch.object(registry_tool, 'get_agent_details') as mock_get_details:
            # Mock agent details
            agent_card = AgentCard(**sample_agent_data[0])
            agent_card.competencies = [skill["name"] for skill in sample_agent_data[0]["skills"]]
            mock_get_details.return_value = agent_card
            
            spec = await registry_tool.recruit_agent(
                "https://example.com/agent1", 
                "Senior Developer",
                priority=2,
                max_interactions=20
            )
            
            assert spec.agent_url == "https://example.com/agent1"
            assert spec.role == "Senior Developer"
            assert spec.priority == 2
            assert spec.max_interactions == 20
            assert "Python" in spec.capabilities
            assert "FastAPI" in spec.capabilities

    @pytest.mark.asyncio
    async def test_recruit_agent_not_found(self, registry_tool):
        """Test recruiting non-existent agent."""
        with patch.object(registry_tool, 'get_agent_details') as mock_get_details:
            mock_get_details.side_effect = RegistryError("Agent not found")
            
            with pytest.raises(RegistryError, match="Agent not found"):
                await registry_tool.recruit_agent("https://example.com/nonexistent", "Helper")

    def test_get_tools_method(self, registry_tool):
        """Test get_tools method for pydantic-ai integration."""
        tools = registry_tool.get_tools()
        
        expected_tools = [
            "registry_search_agents",
            "registry_get_agent_details", 
            "registry_recruit_agent",
            "registry_list_agents"
        ]
        
        assert all(tool in tools for tool in expected_tools)
        assert all(tools[tool] is registry_tool for tool in expected_tools)

    @pytest.mark.asyncio
    async def test_matches_filters_method(self, registry_tool):
        """Test the _matches_filters method."""
        agent = AgentCard(
            url="https://example.com/agent",
            name="Test Agent",
            competencies=["python", "web-dev"],
            skills=[
                {"name": "Django", "description": "Web framework"},
                {"name": "PostgreSQL", "description": "Database"}
            ],
            trust_level="VERIFIED",
            health_score=85
        )
        
        # Should match - no restrictions
        filters = SearchFilters()
        assert registry_tool._matches_filters(agent, filters) is True
        
        # Should match - has required capabilities
        filters = SearchFilters(required_capabilities=["python"])
        assert registry_tool._matches_filters(agent, filters) is True
        
        # Should not match - missing required capability
        filters = SearchFilters(required_capabilities=["java"])
        assert registry_tool._matches_filters(agent, filters) is False
        
        # Should match - has required skill
        filters = SearchFilters(required_skills=["Django"])
        assert registry_tool._matches_filters(agent, filters) is True
        
        # Should not match - missing required skill
        filters = SearchFilters(required_skills=["React"])
        assert registry_tool._matches_filters(agent, filters) is False
        
        # Should match - trust level allowed
        filters = SearchFilters(trust_levels=["VERIFIED", "OFFICIAL"])
        assert registry_tool._matches_filters(agent, filters) is True
        
        # Should not match - trust level not allowed
        filters = SearchFilters(trust_levels=["OFFICIAL"])
        assert registry_tool._matches_filters(agent, filters) is False
        
        # Should match - health score above minimum
        filters = SearchFilters(min_health_score=80)
        assert registry_tool._matches_filters(agent, filters) is True
        
        # Should not match - health score below minimum
        filters = SearchFilters(min_health_score=90)
        assert registry_tool._matches_filters(agent, filters) is False

    @pytest.mark.asyncio
    async def test_close_method(self, registry_tool):
        """Test closing the registry tool."""
        # Create a mock session
        mock_session = AsyncMock()
        registry_tool._session = mock_session
        registry_tool._cache = {"key": "value"}
        
        await registry_tool.close()
        
        mock_session.close.assert_called_once()
        assert registry_tool._session is None
        assert registry_tool._cache == {}

    @pytest.mark.asyncio
    async def test_registry_tool_error_handling(self, registry_tool):
        """Test error handling in registry operations."""
        with patch.object(registry_tool, '_call_registry_jsonrpc') as mock_call:
            mock_call.side_effect = Exception("Connection failed")
            
            with pytest.raises(RegistryError, match="Failed to list agents"):
                await registry_tool.list_all_agents()


class TestRegistryError:
    """Test RegistryError exception."""

    def test_registry_error_creation(self):
        """Test creating registry error."""
        error = RegistryError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.status_code is None

    def test_registry_error_with_status_code(self):
        """Test registry error with status code."""
        error = RegistryError("HTTP error", status_code=404)
        
        assert str(error) == "HTTP error"
        assert error.status_code == 404
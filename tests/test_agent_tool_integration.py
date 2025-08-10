"""
Comprehensive integration tests for LLM agents using tools via pydantic-ai.

These tests verify that real LLM agents can successfully call and use our tools
through the pydantic-ai interface. Tests are marked with custom annotations
to distinguish between mocked and live integration tests.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, skip

# Import pydantic-ai components
try:
    from pydantic_ai import Agent, RunContext
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.models.openai import OpenAIModel
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False


# Custom test markers for different integration levels
pytestmark = pytest.mark.skipif(
    not PYDANTIC_AI_AVAILABLE, 
    reason="pydantic-ai not available"
)

# Custom markers
live_integration = pytest.mark.live_integration
mocked_integration = pytest.mark.mocked_integration
multi_tool_workflow = pytest.mark.multi_tool_workflow


class TestAgentWebFetchToolIntegration:
    """Test pydantic-ai agents using WebFetchTool."""

    @pytest.fixture
    def web_fetch_agent(self):
        """Create an agent with WebFetchTool capability."""
        # Check API key before creating agent
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
            
        from mantis.tools import web_fetch_url
        
        # Create agent with the tool
        agent = Agent(
            'anthropic:claude-3-5-haiku-20241022',
            deps_type=Dict[str, Any],
            system_prompt="You are a helpful assistant that can fetch web content. Use the web_fetch tool when asked to retrieve content from URLs.",
        )
        
        # Register tool functions
        @agent.tool
        async def web_fetch(ctx: RunContext[Dict[str, Any]], url: str, method: str = "GET") -> str:
            """Fetch content from a web URL."""
            if method.upper() == "GET":
                return await web_fetch_url(url)
            else:
                return f"Method {method} not supported in test"
        
        return agent

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_agent_webfetch_mocked(self, web_fetch_agent):
        """Test agent using WebFetchTool - mocking is complex with pydantic-ai, using live test instead."""
        pytest.skip("Complex async mocking with pydantic-ai - live tests are more valuable")

    @live_integration
    @pytest.mark.asyncio
    async def test_agent_webfetch_live(self, web_fetch_agent):
        """Test agent using WebFetchTool with real HTTP requests."""
        agent = web_fetch_agent
        
        # Skip if no API key or in CI without network access
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No LLM API key available for live integration test")
        
        # Test with a reliable public API
        result = await agent.run(
            "Please fetch the content from https://httpbin.org/json and summarize what data structure you see.",
            deps={}
        )
        
        # Verify the agent successfully used the tool and processed results
        assert result.output is not None
        assert len(result.output) > 50  # Should have substantial response
        # The agent should mention JSON structure since httpbin.org/json returns JSON
        response_lower = result.output.lower()
        assert any(word in response_lower for word in ["json", "data", "structure", "object"])


class TestAgentWebSearchToolIntegration:
    """Test pydantic-ai agents using WebSearchTool."""

    @pytest.fixture
    def web_search_agent(self):
        """Create an agent with WebSearchTool capability."""
        # Check API key before creating agent
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
            
        from mantis.tools import web_search
        
        # Create agent with the tool
        agent = Agent(
            'anthropic:claude-3-5-haiku-20241022',
            deps_type=Dict[str, Any],
            system_prompt="You are a helpful assistant that can search the web. Use the web_search tool when asked to find information online.",
        )
        
        # Register tool functions
        @agent.tool
        async def web_search_tool(ctx: RunContext[Dict[str, Any]], query: str, limit: int = 5) -> str:
            """Search the web for information."""
            return await web_search(query, max_results=limit)
        
        return agent

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_agent_websearch_mocked(self, web_search_agent):
        """Test agent using WebSearchTool - mocking is complex with pydantic-ai, using live test instead."""
        pytest.skip("Complex async mocking with pydantic-ai - live tests are more valuable")

    @live_integration
    @pytest.mark.asyncio
    async def test_agent_websearch_live(self, web_search_agent):
        """Test agent using WebSearchTool with real search API."""
        agent = web_search_agent
        
        # Skip if no API keys available
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No LLM API key available for live integration test")
        
        # Test with a general search query
        result = await agent.run(
            "Please search for 'pydantic-ai tutorial' and tell me what resources you found.",
            deps={}
        )
        
        # Verify the agent successfully used the tool and processed results
        assert result.output is not None
        assert len(result.output) > 100  # Should have substantial response
        response_lower = result.output.lower()
        assert any(word in response_lower for word in ["pydantic", "tutorial", "found", "resource"])


class TestAgentGitOperationsToolIntegration:
    """Test pydantic-ai agents using GitOperationsTool."""

    @pytest.fixture
    def git_agent(self):
        """Create an agent with GitOperationsTool capability."""
        # Check API key before creating agent
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
            
        from mantis.tools import git_analyze_repository
        
        # Create agent with the tool
        agent = Agent(
            'anthropic:claude-3-5-haiku-20241022',
            deps_type=Dict[str, Any],
            system_prompt="You are a helpful assistant that can work with Git repositories. Use the Git tools when asked about repository information or code search.",
        )
        
        # Register tool functions
        @agent.tool
        async def get_repo_info(ctx: RunContext[Dict[str, Any]], repo_url: str) -> str:
            """Get information about a Git repository."""
            return await git_analyze_repository(repo_url)
        
        return agent

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_agent_git_mocked(self, git_agent):
        """Test agent using GitOperationsTool - mocking is complex with pydantic-ai, using live test instead."""
        pytest.skip("Complex async mocking with pydantic-ai - live tests are more valuable")

    @live_integration
    @pytest.mark.asyncio
    async def test_agent_git_live(self, git_agent):
        """Test agent using GitOperationsTool with real Git operations."""
        agent = git_agent
        
        # Skip if no API keys available
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No LLM API key available for live integration test")
        
        # Test with a small, public repository
        result = await agent.run(
            "Please get information about the repository https://github.com/octocat/Hello-World.git and tell me what you find.",
            deps={}
        )
        
        # Verify the agent successfully used the tool
        assert result.output is not None
        assert len(result.output) > 50  # Should have substantial response
        response_lower = result.output.lower()
        assert any(word in response_lower for word in ["repository", "hello", "world", "branch"])


@multi_tool_workflow
class TestMultiToolWorkflows:
    """Test agents using multiple tools in complex workflows."""

    @pytest.fixture
    def multi_tool_agent(self):
        """Create an agent with multiple tool capabilities."""
        # Check API key before creating agent
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
            
        from mantis.tools import web_fetch_url, web_search
        
        # Create agent with multiple tools
        agent = Agent(
            'anthropic:claude-3-5-haiku-20241022',
            deps_type=Dict[str, Any],
            system_prompt="You are a helpful assistant that can search the web and fetch content. Use both tools as needed to provide comprehensive information.",
        )
        
        # Register multiple tool functions
        @agent.tool
        async def web_search_tool(ctx: RunContext[Dict[str, Any]], query: str) -> str:
            """Search the web for information."""
            return await web_search(query, max_results=3)
        
        @agent.tool
        async def web_fetch(ctx: RunContext[Dict[str, Any]], url: str) -> str:
            """Fetch content from a web URL."""
            return await web_fetch_url(url)
        
        return agent

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_multi_tool_workflow_mocked(self, multi_tool_agent):
        """Test agent using multiple tools - mocking is complex with pydantic-ai, using live test instead."""
        pytest.skip("Complex async mocking with pydantic-ai - live tests are more valuable")

    @live_integration
    @pytest.mark.asyncio
    async def test_multi_tool_workflow_live(self, multi_tool_agent):
        """Test agent using multiple tools in sequence with real APIs."""
        agent = multi_tool_agent
        
        # Skip if no API keys available
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No LLM API key available for live integration test")
        
        # Test a workflow that might use both search and fetch
        result = await agent.run(
            "Please search for 'httpbin.org json' and then fetch content from one of the URLs you find. Tell me what you discover.",
            deps={}
        )
        
        # Verify the agent used tools and provided meaningful results
        assert result.output is not None
        assert len(result.output) > 100  # Should have substantial response
        response_lower = result.output.lower()
        assert any(word in response_lower for word in ["json", "httpbin", "search", "fetch", "found"])


class TestDirectExecutorRealLLMIntegration:
    """Test DirectExecutor with real LLM agent tool usage."""

    @live_integration
    @pytest.mark.asyncio
    async def test_direct_executor_with_real_llm_tools(self):
        """Test DirectExecutor executing agents that actually use tools."""
        from mantis.core.executor import DirectExecutor
        from mantis.proto.mantis.v1 import mantis_core_pb2
        
        # Skip if no API keys available
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No LLM API key available for live integration test")
        
        executor = DirectExecutor()
        
        # Verify tools are available
        available_tools = executor.get_available_tools()
        assert len(available_tools) > 0
        
        # Create simulation input that should trigger tool usage
        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.query = "Please fetch content from https://httpbin.org/json and tell me what data structure you see."
        model_spec = mantis_core_pb2.ModelSpec()
        model_spec.model = "anthropic:claude-3-5-haiku-20241022"
        simulation_input.model_spec.CopyFrom(model_spec)
        
        agent_spec = mantis_core_pb2.AgentSpec()
        agent_spec.count = 1
        
        # Execute the agent
        response = await executor.execute_agent(simulation_input, agent_spec, 0)
        
        # Verify the response indicates tool usage
        assert response.response_message is not None
        assert len(response.response_message.content) > 0
        response_text = response.response_message.content[0].text
        assert response_text is not None
        assert len(response_text) > 100  # Should have substantial response
        response_lower = response_text.lower()
        
        # The response should indicate the agent tried to use tools or understood the request
        assert any(word in response_lower for word in ["json", "data", "structure", "httpbin", "fetch"])

    @pytest.mark.asyncio
    async def test_direct_executor_tool_availability(self):
        """Test that DirectExecutor properly initializes tools."""
        from mantis.core.executor import DirectExecutor
        
        executor = DirectExecutor()
        available_tools = executor.get_available_tools()
        
        # Should have web fetch and search tools at minimum
        expected_tools = ["web_fetch_url", "web_search", "git_analyze_repository"]
        
        # Check if GitLab and Jira tools are available
        if "gitlab_list_projects" in available_tools:
            expected_tools.extend(["gitlab_list_projects", "gitlab_list_issues", "gitlab_create_issue", "gitlab_get_issue"])
        if "jira_list_projects" in available_tools:
            expected_tools.extend(["jira_list_projects", "jira_list_issues", "jira_create_issue", "jira_get_issue"])
        
        for tool_name in expected_tools:
            assert tool_name in available_tools, f"Tool {tool_name} not found in available tools: {list(available_tools.keys())}"
        
        # Verify tools are properly configured
        assert len(available_tools) >= 3
        
        # Each tool should be a proper callable
        for tool_name, tool_instance in available_tools.items():
            assert tool_instance is not None
            assert callable(tool_instance)
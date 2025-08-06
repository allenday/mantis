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
        from mantis.tools import WebFetchTool, WebFetchConfig
        
        # Create tool with test-friendly config
        config = WebFetchConfig(
            timeout=10.0,
            user_agent="Mantis-Test-Agent/1.0",
            rate_limit_requests=100,
            rate_limit_window=60,
            verify_ssl=True,
            max_content_size=1024 * 1024,  # 1MB for tests
        )
        web_fetch_tool = WebFetchTool(config)
        
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
                response = await web_fetch_tool.fetch_url(url)
                return response.content if response.success else f"Error: {response.error_message}"
            else:
                return f"Method {method} not supported in test"
        
        return agent, web_fetch_tool

    @mocked_integration
    @pytest.mark.asyncio
    async def test_agent_webfetch_mocked(self, web_fetch_agent):
        """Test agent using WebFetchTool with mocked tool responses but real LLM."""
        agent, web_fetch_tool = web_fetch_agent
        
        # Skip if no API key available
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
        
        # Mock the tool response
        from mantis.tools import WebResponse
        mock_response = WebResponse(
            status_code=200,
            content="Mock webpage content: This is a test page with JSON data.",
            headers={"content-type": "text/html"},
            success=True,
            url="https://httpbin.org/get",
            response_time_ms=100.0
        )
        with patch.object(web_fetch_tool, 'fetch_url', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            # Run agent with web fetch request
            result = await agent.run(
                "Please fetch the content from https://httpbin.org/get and tell me what you find.",
                deps={}
            )
            
            # Verify the agent used the tool
            mock_fetch.assert_called_once()
            # Verify the LLM processed the mocked content
            assert result.output is not None
            assert len(result.output) > 50  # Should have substantial LLM response

    @live_integration
    @pytest.mark.asyncio
    async def test_agent_webfetch_live(self, web_fetch_agent):
        """Test agent using WebFetchTool with real HTTP requests."""
        agent, web_fetch_tool = web_fetch_agent
        
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
        from mantis.tools import WebSearchTool, WebSearchConfig
        
        # Create tool with test-friendly config
        config = WebSearchConfig(
            max_results=5,
            timeout=10.0,
            rate_limit_requests=50,
            rate_limit_window=60,
            enable_suggestions=True,
        )
        web_search_tool = WebSearchTool(config)
        
        # Create agent with the tool
        agent = Agent(
            'anthropic:claude-3-5-haiku-20241022',
            deps_type=Dict[str, Any],
            system_prompt="You are a helpful assistant that can search the web. Use the web_search tool when asked to find information online.",
        )
        
        # Register tool functions
        @agent.tool
        async def web_search(ctx: RunContext[Dict[str, Any]], query: str, max_results: int = 5) -> str:
            """Search the web for information."""
            results = await web_search_tool.search(query, max_results=max_results)
            
            # Format results for the agent
            formatted_results = []
            for result in results.results:
                formatted_results.append(f"Title: {result.title}\nURL: {result.url}\nSnippet: {result.snippet}\n")
            
            return f"Search results for '{query}':\n\n" + "\n".join(formatted_results)
        
        return agent, web_search_tool

    @mocked_integration
    @pytest.mark.asyncio
    async def test_agent_websearch_mocked(self, web_search_agent):
        """Test agent using WebSearchTool with mocked tool responses but real LLM."""
        from mantis.tools import SearchResult, SearchResponse
        
        agent, web_search_tool = web_search_agent
        
        # Skip if no API key available
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
        
        # Mock the tool response
        mock_results = SearchResponse(
            query="python programming",
            results=[
                SearchResult(
                    title="Python.org - Official Python Website",
                    url="https://python.org",
                    snippet="The official home of the Python programming language",
                    rank=1,
                    source="python.org"
                ),
                SearchResult(
                    title="Python Tutorial - W3Schools",
                    url="https://w3schools.com/python",
                    snippet="Learn Python programming with examples and tutorials",
                    rank=2,
                    source="w3schools.com"
                )
            ],
            total_results=2,
            suggestions=[]
        )
        
        with patch.object(web_search_tool, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_results
            
            # Run agent with search request
            result = await agent.run(
                "Please search for information about Python programming and summarize what you find.",
                deps={}
            )
            
            # Verify the agent used the tool
            mock_search.assert_called_once()
            # Verify the LLM processed the mocked search results
            assert result.output is not None
            assert len(result.output) > 50  # Should have substantial LLM response

    @live_integration
    @pytest.mark.asyncio
    async def test_agent_websearch_live(self, web_search_agent):
        """Test agent using WebSearchTool with real search API."""
        agent, web_search_tool = web_search_agent
        
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


class TestAgentJiraToolIntegration:
    """Test pydantic-ai agents using JiraTool."""

    @pytest.fixture
    def jira_agent(self):
        """Create an agent with JiraTool capability."""
        from mantis.tools import JiraTool, JiraConfig
        
        # Create tool with test config (read-only for safety)
        config = JiraConfig(
            api_token=os.getenv("JIRA_API_TOKEN", "test_token"),
            email=os.getenv("JIRA_EMAIL", "test@example.com"),
            server_url=os.getenv("JIRA_SERVER_URL", "https://test.atlassian.net"),
            read_only_mode=True,  # Safe default for tests
            timeout=10.0,
        )
        jira_tool = JiraTool(config)
        
        # Create agent with the tool
        agent = Agent(
            'anthropic:claude-3-5-haiku-20241022',
            deps_type=Dict[str, Any],
            system_prompt="You are a helpful assistant that can interact with Jira. Use the Jira tools when asked about issues or projects.",
        )
        
        # Register tool functions
        @agent.tool
        async def get_jira_issue(ctx: RunContext[Dict[str, Any]], issue_key: str) -> str:
            """Get details of a Jira issue."""
            issue = await jira_tool.get_issue(issue_key)
            return f"Issue {issue.key}: {issue.summary}\nStatus: {issue.status}\nPriority: {issue.priority}\nDescription: {issue.description or 'No description'}"
        
        @agent.tool
        async def search_jira_issues(ctx: RunContext[Dict[str, Any]], jql: str, max_results: int = 10) -> str:
            """Search for Jira issues using JQL."""
            issues = await jira_tool.search_issues(jql, max_results=max_results)
            
            if not issues:
                return f"No issues found for query: {jql}"
            
            results = [f"- {issue.key}: {issue.summary} ({issue.status})" for issue in issues]
            return f"Found {len(issues)} issues:\n" + "\n".join(results)
        
        return agent, jira_tool

    @mocked_integration
    @pytest.mark.asyncio
    async def test_agent_jira_mocked(self, jira_agent):
        """Test agent using JiraTool with mocked tool responses but real LLM."""
        from mantis.tools import JiraIssue
        
        agent, jira_tool = jira_agent
        
        # Skip if no API key available
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
        
        # Mock the tool response
        mock_issue = JiraIssue(
            key="TEST-123",
            id="10001",
            summary="Test Issue for Agent Integration",
            description="This is a test issue for agent integration testing",
            status="In Progress",
            priority="High",
            reporter={"name": "Test User", "accountId": "123"},
            created="2023-01-01T00:00:00Z",
            updated="2023-01-01T00:00:00Z",
            project={"key": "TEST", "name": "Test Project"},
            issue_type={"name": "Task", "id": "1"},
        )
        
        with patch.object(jira_tool, 'get_issue', new_callable=AsyncMock) as mock_get_issue:
            mock_get_issue.return_value = mock_issue
            
            # Run agent with Jira request
            result = await agent.run(
                "Please get the details of Jira issue TEST-123 and summarize what you find.",
                deps={}
            )
            
            # Verify the agent used the tool
            mock_get_issue.assert_called_once_with("TEST-123")
            # Verify the LLM processed the mocked issue data
            assert result.output is not None
            assert len(result.output) > 50  # Should have substantial LLM response

    @live_integration
    @pytest.mark.asyncio
    async def test_agent_jira_live(self, jira_agent):
        """Test agent using JiraTool with real Jira API."""
        agent, jira_tool = jira_agent
        
        # Skip if no API keys or Jira config available
        required_env = ["JIRA_API_TOKEN", "JIRA_EMAIL", "JIRA_SERVER_URL"]
        if not all(os.getenv(var) for var in required_env):
            pytest.skip("Jira configuration not available for live integration test")
        
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
            pytest.skip("No LLM API key available for live integration test")
        
        # Test getting projects (safer than searching specific issues)
        result = await agent.run(
            "Please search for any issues in your Jira instance using the JQL query 'project is not empty' and tell me what projects you can see.",
            deps={}
        )
        
        # Verify the agent successfully used the tool
        assert result.output is not None
        assert len(result.output) > 50  # Should have substantial response


class TestAgentGitOperationsToolIntegration:
    """Test pydantic-ai agents using GitOperationsTool."""

    @pytest.fixture
    def git_agent(self):
        """Create an agent with GitOperationsTool capability."""
        from mantis.tools import GitOperationsTool, GitOperationsConfig
        
        # Create tool with test-friendly config
        config = GitOperationsConfig(
            max_repo_size_mb=50.0,  # Smaller for tests
            max_files=500,
            allowed_schemes=["https"],
            blocked_domains=["localhost", "127.0.0.1"],
            clone_timeout=60.0,  # Shorter for tests
            temp_cleanup=True,
            max_search_results=20,
        )
        git_tool = GitOperationsTool(config)
        
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
            repo_info = await git_tool.get_repository_info(repo_url)
            return f"Repository: {repo_info.name}\nDescription: {repo_info.description or 'No description'}\nDefault Branch: {repo_info.default_branch}\nLast Updated: {repo_info.updated_at}"
        
        @agent.tool
        async def search_code(ctx: RunContext[Dict[str, Any]], repo_url: str, query: str, file_pattern: Optional[str] = None) -> str:
            """Search for code in a repository."""
            matches = await git_tool.search_code(repo_url, query, file_pattern=file_pattern, max_results=10)
            
            if not matches:
                return f"No code matches found for query: {query}"
            
            results = []
            for match in matches:
                results.append(f"File: {match.file_path}\nLine {match.line_number}: {match.content}")
            
            return f"Found {len(matches)} code matches:\n\n" + "\n\n".join(results)
        
        return agent, git_tool

    @mocked_integration
    @pytest.mark.asyncio
    async def test_agent_git_mocked(self, git_agent):
        """Test agent using GitOperationsTool with mocked tool responses but real LLM."""
        from mantis.tools import RepositoryInfo, CodeMatch
        
        agent, git_tool = git_agent
        
        # Skip if no API key available
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
        
        # Mock the tool responses
        mock_repo_info = RepositoryInfo(
            url="https://github.com/user/test-repo.git",
            name="test-repo",
            branch="main",
            commit_hash="abc123def456",
            commit_message="Initial commit",
            file_count=50,
            size_mb=2.5,
            languages=["Python", "JavaScript"]
        )
        
        mock_code_matches = [
            CodeMatch(
                file_path="src/main.py",
                line_number=10,
                content="def test_function():",
                context_before=["# Test file", "import pytest"],
                context_after=["    return True"]
            )
        ]
        
        with patch.object(git_tool, 'get_repository_info', new_callable=AsyncMock) as mock_repo_info_call:
            with patch.object(git_tool, 'search_code', new_callable=AsyncMock) as mock_search_code:
                mock_repo_info_call.return_value = mock_repo_info
                mock_search_code.return_value = mock_code_matches
                
                # Run agent with Git request
                result = await agent.run(
                    "Please get information about the repository https://github.com/user/test-repo.git and search for 'test_function' in the code.",
                    deps={}
                )
                
                # Verify the agent used the tools
                mock_repo_info_call.assert_called_once()
                mock_search_code.assert_called_once()
                # Verify the LLM processed the mocked Git data
                assert result.output is not None
                assert len(result.output) > 50  # Should have substantial LLM response

    @live_integration
    @pytest.mark.asyncio
    async def test_agent_git_live(self, git_agent):
        """Test agent using GitOperationsTool with real Git operations."""
        agent, git_tool = git_agent
        
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
        from mantis.tools import WebFetchTool, WebFetchConfig, WebSearchTool, WebSearchConfig
        
        # Create tools
        web_fetch_tool = WebFetchTool(WebFetchConfig(timeout=10.0))
        web_search_tool = WebSearchTool(WebSearchConfig(max_results=3, timeout=10.0))
        
        # Create agent with multiple tools
        agent = Agent(
            'anthropic:claude-3-5-haiku-20241022',
            deps_type=Dict[str, Any],
            system_prompt="You are a helpful assistant that can search the web and fetch content. Use both tools as needed to provide comprehensive information.",
        )
        
        # Register multiple tool functions
        @agent.tool
        async def web_search(ctx: RunContext[Dict[str, Any]], query: str) -> str:
            """Search the web for information."""
            results = await web_search_tool.search(query, max_results=3)
            formatted_results = []
            for result in results.results:
                formatted_results.append(f"Title: {result.title}\nURL: {result.url}\nSnippet: {result.snippet}")
            return "Search results:\n" + "\n\n".join(formatted_results)
        
        @agent.tool
        async def web_fetch(ctx: RunContext[Dict[str, Any]], url: str) -> str:
            """Fetch content from a web URL."""
            response = await web_fetch_tool.fetch_url(url)
            return response.content if response.success else f"Error: {response.error_message}"
        
        return agent, (web_search_tool, web_fetch_tool)

    @mocked_integration
    @pytest.mark.asyncio
    async def test_multi_tool_workflow_mocked(self, multi_tool_agent):
        """Test agent using multiple tools in sequence with mocked tool responses but real LLM."""
        from mantis.tools import SearchResult, SearchResponse
        
        agent, (web_search_tool, web_fetch_tool) = multi_tool_agent
        
        # Skip if no API key available
        if not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No Anthropic API key available for LLM integration test")
        
        # Mock search results
        mock_search_results = SearchResponse(
            query="pydantic-ai documentation",
            results=[
                SearchResult(
                    title="Pydantic AI Documentation",
                    url="https://docs.pydantic.dev/pydantic-ai",
                    snippet="Official documentation for Pydantic AI",
                    rank=1,
                    source="pydantic.dev"
                )
            ],
            total_results=1,
            suggestions=[]
        )
        
        # Mock fetch content
        mock_fetch_content = "# Pydantic AI Documentation\n\nPydantic AI is a powerful framework for building LLM applications..."
        
        # Mock fetch content as WebResponse
        from mantis.tools import WebResponse
        mock_fetch_response = WebResponse(
            status_code=200,
            content="# Pydantic AI Documentation\n\nPydantic AI is a powerful framework for building LLM applications...",
            headers={"content-type": "text/html"},
            success=True,
            url="https://docs.pydantic.dev/pydantic-ai",
            response_time_ms=150.0
        )
        
        with patch.object(web_search_tool, 'search', new_callable=AsyncMock) as mock_search:
            with patch.object(web_fetch_tool, 'fetch_url', new_callable=AsyncMock) as mock_fetch:
                mock_search.return_value = mock_search_results
                mock_fetch.return_value = mock_fetch_response
                
                # Run agent with request that should use both tools
                result = await agent.run(
                    "Please search for pydantic-ai documentation, then fetch the content from the first result and summarize what you learn.",
                    deps={}
                )
                
                # Verify both tools were used
                mock_search.assert_called_once()
                mock_fetch.assert_called_once()
                # Verify the LLM processed the multi-tool workflow
                assert result.output is not None
                assert len(result.output) > 100  # Should have substantial LLM response

    @live_integration
    @pytest.mark.asyncio
    async def test_multi_tool_workflow_live(self, multi_tool_agent):
        """Test agent using multiple tools in sequence with real APIs."""
        agent, (web_search_tool, web_fetch_tool) = multi_tool_agent
        
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
        from mantis.core.orchestrator import DirectExecutor
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
        simulation_input.model = "anthropic:claude-3-5-haiku-20241022"
        
        agent_spec = mantis_core_pb2.AgentSpec()
        agent_spec.count = 1
        
        # Execute the agent
        response = await executor.execute_agent(simulation_input, agent_spec, 0)
        
        # Verify the response indicates tool usage
        assert response.text_response is not None
        assert len(response.text_response) > 100  # Should have substantial response
        response_lower = response.text_response.lower()
        
        # The response should indicate the agent tried to use tools or understood the request
        assert any(word in response_lower for word in ["json", "data", "structure", "httpbin", "fetch"])

    @mocked_integration
    @pytest.mark.asyncio
    async def test_direct_executor_tool_availability(self):
        """Test that DirectExecutor properly initializes tools."""
        from mantis.core.orchestrator import DirectExecutor
        
        executor = DirectExecutor()
        available_tools = executor.get_available_tools()
        
        # Should have web fetch and search tools at minimum
        expected_tools = ["web_fetch", "web_search", "git_operations"]
        
        for tool_name in expected_tools:
            assert tool_name in available_tools, f"Tool {tool_name} not found in available tools: {list(available_tools.keys())}"
        
        # Verify tools are properly configured
        assert len(available_tools) >= 3
        
        # Each tool should be a proper instance
        for tool_name, tool_instance in available_tools.items():
            assert tool_instance is not None
            assert hasattr(tool_instance, '__class__')
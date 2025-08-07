"""
Live integration tests for WebSearchTool.
Tests against real search engines - fail fast if they don't work.
"""

import pytest
import asyncio

from mantis.tools.web_search import WebSearchTool, WebSearchConfig


class TestWebSearchToolLive:
    """Live integration tests for WebSearchTool."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return WebSearchConfig(
            max_results=5,
            timeout=15.0,
            user_agent="Mantis-Test/1.0",
            rate_limit_requests=3,
            rate_limit_window=60,
            enable_suggestions=True,
        )

    @pytest.mark.asyncio
    async def test_search_python_live(self, config):
        """Test searching for Python - live data."""
        async with WebSearchTool(config) as tool:
            response = await tool.search("Python programming language")
            
            assert response.success
            assert len(response.results) > 0
            assert response.results[0].title is not None
            assert response.results[0].url is not None
            assert response.results[0].snippet is not None
            
            # Check that results are relevant
            first_result = response.results[0]
            python_terms = ["python", "programming", "code", "development"]
            content_text = (first_result.title + " " + first_result.snippet).lower()
            assert any(term in content_text for term in python_terms)

    @pytest.mark.asyncio
    async def test_search_github_live(self, config):
        """Test searching for GitHub - live data."""
        async with WebSearchTool(config) as tool:
            response = await tool.search("GitHub repository hosting")
            
            assert response.success
            assert len(response.results) > 0
            
            # At least one result should be from github.com or mention GitHub
            github_mentioned = any(
                "github" in (result.title + " " + result.snippet + " " + result.url).lower()
                for result in response.results
            )
            assert github_mentioned

    @pytest.mark.asyncio
    async def test_search_empty_query_fails_fast(self, config):
        """Test that empty queries fail fast."""
        async with WebSearchTool(config) as tool:
            response = await tool.search("")
            
            assert not response.success
            assert response.error_message is not None

    @pytest.mark.asyncio
    async def test_search_rate_limiting_live(self, config):
        """Test rate limiting with live searches."""
        # Set aggressive rate limiting for test
        config.rate_limit_requests = 2
        config.rate_limit_window = 5
        
        async with WebSearchTool(config) as tool:
            # First two searches should succeed
            response1 = await tool.search("test query 1")
            response2 = await tool.search("test query 2")
            
            # Third search might be rate limited
            response3 = await tool.search("test query 3")
            
            # At least two should succeed
            successful_count = sum(1 for r in [response1, response2, response3] if r.success)
            assert successful_count >= 2
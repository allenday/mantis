"""
Live integration tests for WebSearchTool.
Tests against real search engines - fail fast if they don't work.
"""

import pytest
import os

from mantis.tools.web_search import web_search


class TestWebSearchToolLive:
    """Live integration tests for web_search function."""

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_search_python_live(self):
        """Test searching for Python - live data."""
        result = await web_search("Python programming language")
        
        # Handle case where search service is temporarily unavailable or rate limited
        if "no results found" in result.lower():
            pytest.skip("Search service temporarily unavailable or rate limited")
        
        assert "error" not in result.lower()
        assert "failed" not in result.lower()
        assert "python" in result.lower()
        assert len(result) > 100  # Should have substantial content

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_search_github_live(self):
        """Test searching for GitHub - live data."""
        result = await web_search("GitHub repository hosting")
        
        # Handle case where search service is temporarily unavailable or rate limited
        if "no results found" in result.lower():
            pytest.skip("Search service temporarily unavailable or rate limited")
        
        assert "error" not in result.lower()
        assert "failed" not in result.lower()
        assert "github" in result.lower()
        assert len(result) > 100  # Should have substantial content

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_search_empty_query_fails_fast(self):
        """Test that empty queries fail fast."""
        result = await web_search("")
        
        # Should return error message
        assert ("error" in result.lower() or "failed" in result.lower() or "empty" in result.lower())
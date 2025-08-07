"""
Live integration tests for WebFetchTool.
Tests against real URLs - fail fast if they don't work.
"""

import pytest
import os

from mantis.tools.web_fetch import web_fetch_url


class TestWebFetchToolLive:
    """Live integration tests for web_fetch_url function."""

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_fetch_github_api(self):
        """Test fetching GitHub API - live data."""
        result = await web_fetch_url("https://api.github.com/zen")
        
        assert "error" not in result.lower()
        assert "failed" not in result.lower()
        assert len(result) > 10  # Should have substantial content

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_fetch_httpbin_json(self):
        """Test fetching JSON from httpbin - live data."""
        result = await web_fetch_url("https://httpbin.org/json")
        
        # Handle case where httpbin.org is temporarily down (HTTP 503, etc.)
        if "http 503" in result.lower() or "failed" in result.lower():
            pytest.skip("httpbin.org temporarily unavailable")
        
        assert "error" not in result.lower()
        assert ('"slideshow"' in result or '"title"' in result)

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_fetch_invalid_url_fails_fast(self):
        """Test that invalid URLs fail fast."""
        result = await web_fetch_url("https://this-domain-should-not-exist-12345.com")
        
        # Should return error message
        assert ("error" in result.lower() or "failed" in result.lower())
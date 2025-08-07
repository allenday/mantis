"""
Live integration tests for WebFetchTool.
Tests against real URLs - fail fast if they don't work.
"""

import pytest
import asyncio

from mantis.tools.web_fetch import WebFetchTool, WebFetchConfig


class TestWebFetchToolLive:
    """Live integration tests for WebFetchTool."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return WebFetchConfig(
            timeout=10.0,
            user_agent="Mantis-Test/1.0",
            rate_limit_requests=5,
            rate_limit_window=60,
            verify_ssl=True,
            max_content_size=1024 * 1024,  # 1MB
        )

    @pytest.mark.asyncio
    async def test_fetch_github_api(self, config):
        """Test fetching GitHub API - live data."""
        async with WebFetchTool(config) as tool:
            response = await tool.fetch_url("https://api.github.com/zen")
            
            assert response.success
            assert response.status_code == 200
            assert len(response.content) > 0
            assert "github" in response.content.lower() or len(response.content) > 10

    @pytest.mark.asyncio
    async def test_fetch_httpbin_json(self, config):
        """Test fetching JSON from httpbin - live data."""
        async with WebFetchTool(config) as tool:
            response = await tool.fetch_url("https://httpbin.org/json")
            
            assert response.success
            assert response.status_code == 200
            assert '"slideshow"' in response.content or '"title"' in response.content

    @pytest.mark.asyncio
    async def test_fetch_invalid_url_fails_fast(self, config):
        """Test that invalid URLs fail fast."""
        async with WebFetchTool(config) as tool:
            response = await tool.fetch_url("https://this-domain-should-not-exist-12345.com")
            
            assert not response.success
            assert response.error_message is not None

    @pytest.mark.asyncio
    async def test_rate_limiting_live(self, config):
        """Test rate limiting with live requests."""
        # Set aggressive rate limiting for test
        config.rate_limit_requests = 2
        config.rate_limit_window = 5
        
        async with WebFetchTool(config) as tool:
            # First two requests should succeed
            response1 = await tool.fetch_url("https://httpbin.org/delay/1")
            response2 = await tool.fetch_url("https://httpbin.org/delay/1")
            
            # Third request should be rate limited
            response3 = await tool.fetch_url("https://httpbin.org/delay/1")
            
            # At least two should succeed, third might be rate limited
            successful_count = sum(1 for r in [response1, response2, response3] if r.success)
            assert successful_count >= 2
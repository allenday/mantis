"""
Tests for WebFetchTool with security features and rate limiting.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any
import aiohttp

from mantis.tools.web_fetch import (
    WebFetchTool,
    WebFetchConfig,
    WebResponse,
    RateLimiter,
)


class TestRateLimiter:
    """Test suite for RateLimiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self):
        """Test that rate limiter allows requests within the limit."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # First 5 requests should be allowed
        for _ in range(5):
            assert await limiter.acquire() is True
        
        # 6th request should be denied
        assert await limiter.acquire() is False

    @pytest.mark.asyncio
    async def test_rate_limiter_window_sliding(self):
        """Test that rate limiter window slides correctly."""
        limiter = RateLimiter(max_requests=2, window_seconds=1)
        
        # Use up the limit
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        assert await limiter.acquire() is False
        
        # Wait for window to slide
        await asyncio.sleep(1.1)
        
        # Should be able to make requests again
        assert await limiter.acquire() is True


class TestWebFetchTool:
    """Test suite for WebFetchTool."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return WebFetchConfig(
            timeout=10.0,
            rate_limit_requests=10,
            rate_limit_window=60,
            verify_ssl=True,
            max_content_size=1024 * 1024,  # 1MB for tests
        )

    @pytest.fixture
    def web_fetch_tool(self, config):
        """Create WebFetchTool instance."""
        return WebFetchTool(config)

    @pytest.fixture
    def mock_session_response(self):
        """Create mock aiohttp response."""
        mock_response = Mock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "text/html", "content-length": "100"}
        mock_response.url = "https://example.com"
        
        # Mock content iteration
        mock_content = Mock()
        
        # Create async iterator for iter_chunked
        async def mock_iter_chunked(chunk_size):
            yield b"test content"
        
        mock_content.iter_chunked = mock_iter_chunked
        mock_response.content = mock_content
        
        return mock_response

    def test_url_validation_valid_urls(self, web_fetch_tool):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://subdomain.example.com:8080/path?query=value",
        ]
        
        for url in valid_urls:
            assert web_fetch_tool._validate_url(url) is True

    def test_url_validation_invalid_urls(self, web_fetch_tool):
        """Test URL validation with invalid URLs."""
        invalid_urls = [
            "ftp://example.com",  # Invalid scheme
            "https://localhost",  # Blocked domain
            "http://127.0.0.1",   # Blocked IP
            "invalid-url",        # Invalid format
            "",                   # Empty URL
        ]
        
        for url in invalid_urls:
            assert web_fetch_tool._validate_url(url) is False

    def test_url_validation_with_allowed_domains(self):
        """Test URL validation with allowed domains."""
        config = WebFetchConfig(allowed_domains=["example.com", "trusted.org"])
        tool = WebFetchTool(config)
        
        assert tool._validate_url("https://example.com") is True
        assert tool._validate_url("https://trusted.org") is True
        assert tool._validate_url("https://untrusted.com") is False

    def test_url_validation_private_ips(self, web_fetch_tool):
        """Test URL validation blocks private IP ranges."""
        private_ips = [
            "http://10.0.0.1",
            "https://192.168.1.1",
            "http://172.16.0.1",
        ]
        
        for url in private_ips:
            assert web_fetch_tool._validate_url(url) is False

    @pytest.mark.asyncio
    async def test_context_manager(self, web_fetch_tool):
        """Test async context manager functionality."""
        async with web_fetch_tool as tool:
            assert tool is web_fetch_tool
            assert tool._session is not None
            assert isinstance(tool._session, aiohttp.ClientSession)

    @pytest.mark.asyncio
    async def test_fetch_url_without_session(self, web_fetch_tool):
        """Test fetch_url fails without initialized session."""
        response = await web_fetch_tool.fetch_url("https://example.com")
        
        assert response.success is False
        assert "Session not initialized" in response.error_message

    @pytest.mark.asyncio
    async def test_fetch_url_invalid_url(self, web_fetch_tool):
        """Test fetch_url with invalid URL."""
        async with web_fetch_tool:
            response = await web_fetch_tool.fetch_url("https://localhost")
        
        assert response.success is False
        assert "URL validation failed" in response.error_message

    @pytest.mark.asyncio
    async def test_fetch_url_success(self, web_fetch_tool, mock_session_response):
        """Test successful URL fetch."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            # Setup context manager for session
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Setup request method - create a proper async context manager mock
            mock_request_context = Mock()
            mock_request_context.__aenter__ = AsyncMock(return_value=mock_session_response)
            mock_request_context.__aexit__ = AsyncMock()
            mock_session.request = Mock(return_value=mock_request_context)
            
            async with web_fetch_tool:
                response = await web_fetch_tool.fetch_url("https://example.com")
            
            assert response.status_code == 200
            assert response.success is True
            assert "test content" in response.content
            assert response.response_time_ms > 0

    @pytest.mark.asyncio
    async def test_fetch_url_timeout(self, web_fetch_tool):
        """Test fetch_url timeout handling."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Make request raise timeout - create context manager that raises
            class TimeoutContextManager:
                async def __aenter__(self):
                    raise asyncio.TimeoutError()
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
            
            mock_session.request = Mock(return_value=TimeoutContextManager())
            
            async with web_fetch_tool:
                response = await web_fetch_tool.fetch_url("https://example.com")
            
            assert response.success is False
            assert "Request timeout" in response.error_message

    @pytest.mark.asyncio
    async def test_fetch_url_content_too_large(self, web_fetch_tool):
        """Test fetch_url with content too large."""
        # Create config with very small max size
        small_config = WebFetchConfig(max_content_size=10)
        small_tool = WebFetchTool(small_config)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Mock response with large content-length
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {"content-length": "1000000"}  # 1MB
            mock_response.url = "https://example.com"
            
            # Setup request method - create a proper async context manager mock
            mock_request_context = Mock()
            mock_request_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_request_context.__aexit__ = AsyncMock()
            mock_session.request = Mock(return_value=mock_request_context)
            
            async with small_tool:
                response = await small_tool.fetch_url("https://example.com")
            
            assert response.success is False
            assert "Content too large" in response.error_message

    @pytest.mark.asyncio
    async def test_fetch_json_success(self, web_fetch_tool):
        """Test successful JSON fetch."""
        test_data = {"key": "value", "number": 42}
        
        with patch.object(web_fetch_tool, 'fetch_url') as mock_fetch:
            mock_fetch.return_value = WebResponse(
                status_code=200,
                content=json.dumps(test_data),
                headers={"content-type": "application/json"},
                success=True,
                url="https://example.com/api",
                error_message=None,
                response_time_ms=100.0
            )
            
            async with web_fetch_tool:
                result = await web_fetch_tool.fetch_json("https://example.com/api")
            
            assert result == test_data

    @pytest.mark.asyncio
    async def test_fetch_json_invalid_json(self, web_fetch_tool):
        """Test fetch_json with invalid JSON."""
        with patch.object(web_fetch_tool, 'fetch_url') as mock_fetch:
            mock_fetch.return_value = WebResponse(
                status_code=200,
                content="invalid json",
                headers={"content-type": "application/json"},
                success=True,
                url="https://example.com/api",
                error_message=None,
                response_time_ms=100.0
            )
            
            async with web_fetch_tool:
                with pytest.raises(Exception, match="Invalid JSON response"):
                    await web_fetch_tool.fetch_json("https://example.com/api")

    @pytest.mark.asyncio
    async def test_fetch_json_request_failure(self, web_fetch_tool):
        """Test fetch_json with request failure."""
        with patch.object(web_fetch_tool, 'fetch_url') as mock_fetch:
            mock_fetch.return_value = WebResponse(
                status_code=404,
                content="",
                headers={},
                success=False,
                url="https://example.com/api",
                error_message="HTTP 404",
                response_time_ms=100.0
            )
            
            async with web_fetch_tool:
                with pytest.raises(Exception, match="Failed to fetch URL"):
                    await web_fetch_tool.fetch_json("https://example.com/api")

    @pytest.mark.asyncio
    async def test_fetch_text_success(self, web_fetch_tool):
        """Test successful text fetch."""
        test_text = "Hello, world!"
        
        with patch.object(web_fetch_tool, 'fetch_url') as mock_fetch:
            mock_fetch.return_value = WebResponse(
                status_code=200,
                content=test_text,
                headers={"content-type": "text/plain"},
                success=True,
                url="https://example.com/text",
                error_message=None,
                response_time_ms=100.0
            )
            
            async with web_fetch_tool:
                result = await web_fetch_tool.fetch_text("https://example.com/text")
            
            assert result == test_text

    @pytest.mark.asyncio
    async def test_post_data_success(self, web_fetch_tool):
        """Test successful POST data."""
        test_data = {"name": "test", "value": 123}
        
        with patch.object(web_fetch_tool, 'fetch_url') as mock_fetch:
            mock_fetch.return_value = WebResponse(
                status_code=201,
                content='{"id": 1, "status": "created"}',
                headers={"content-type": "application/json"},
                success=True,
                url="https://example.com/api",
                error_message=None,
                response_time_ms=200.0
            )
            
            async with web_fetch_tool:
                response = await web_fetch_tool.post_data("https://example.com/api", test_data)
            
            assert response.success is True
            assert response.status_code == 201
            
            # Verify fetch_url was called with correct parameters
            mock_fetch.assert_called_once()
            call_args = mock_fetch.call_args
            assert call_args[0][0] == "https://example.com/api"  # URL
            assert call_args[1]['method'] == "POST"
            assert call_args[1]['headers']['Content-Type'] == 'application/json'
            assert json.loads(call_args[1]['data']) == test_data

    def test_configuration_defaults(self):
        """Test default configuration values."""
        config = WebFetchConfig()
        
        assert config.timeout == 30.0
        assert config.max_redirects == 10
        assert config.max_content_size == 10 * 1024 * 1024
        assert config.rate_limit_requests == 60
        assert config.rate_limit_window == 60
        assert config.verify_ssl is True
        assert "localhost" in config.blocked_domains
        assert "127.0.0.1" in config.blocked_domains

    def test_web_response_model(self):
        """Test WebResponse pydantic model."""
        response = WebResponse(
            status_code=200,
            content="test content",
            headers={"content-type": "text/html"},
            success=True,
            url="https://example.com",
            error_message=None,
            response_time_ms=150.0
        )
        
        assert response.status_code == 200
        assert response.content == "test content"
        assert response.headers["content-type"] == "text/html"
        assert response.success is True
        assert response.url == "https://example.com"
        assert response.error_message is None
        assert response.response_time_ms == 150.0

    def test_get_tools_method(self, web_fetch_tool):
        """Test get_tools method for pydantic-ai integration."""
        tools = web_fetch_tool.get_tools()
        
        assert isinstance(tools, dict)
        assert 'fetch_url' in tools
        assert 'fetch_json' in tools
        assert 'fetch_text' in tools
        assert 'post_data' in tools
        assert tools['fetch_url'] is web_fetch_tool

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, web_fetch_tool):
        """Test rate limiting integration in fetch_url."""
        # Create tool with very low rate limit
        low_limit_config = WebFetchConfig(rate_limit_requests=1, rate_limit_window=60)
        low_limit_tool = WebFetchTool(low_limit_config)
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Mock successful response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.url = "https://example.com"
            mock_content = Mock()
            
            # Create async iterator for iter_chunked
            async def mock_iter_chunked(chunk_size):
                yield b"content"
            
            mock_content.iter_chunked = mock_iter_chunked
            mock_response.content = mock_content
            
            # Setup request method - create a proper async context manager mock
            mock_request_context = Mock()
            mock_request_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_request_context.__aexit__ = AsyncMock()
            mock_session.request = Mock(return_value=mock_request_context)
            
            async with low_limit_tool:
                # First request should succeed immediately
                response1 = await low_limit_tool.fetch_url("https://example.com")
                assert response1.success is True
                
                # Second request should be rate limited and take longer
                import time
                start_time = time.time()
                response2 = await low_limit_tool.fetch_url("https://example.com")
                elapsed = time.time() - start_time
                
                # Should have been delayed by rate limiter
                assert elapsed > 0.05  # At least some delay
                assert response2.success is True

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, web_fetch_tool):
        """Test concurrent request handling."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Mock response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.url = "https://example.com"
            mock_content = Mock()
            
            # Create async iterator for iter_chunked
            async def mock_iter_chunked(chunk_size):
                yield b"content"
            
            mock_content.iter_chunked = mock_iter_chunked
            mock_response.content = mock_content
            
            # Setup request method - create a proper async context manager mock
            mock_request_context = Mock()
            mock_request_context.__aenter__ = AsyncMock(return_value=mock_response)
            mock_request_context.__aexit__ = AsyncMock()
            mock_session.request = Mock(return_value=mock_request_context)
            
            async with web_fetch_tool:
                # Make multiple concurrent requests
                tasks = [
                    web_fetch_tool.fetch_url(f"https://example{i}.com")
                    for i in range(3)
                ]
                responses = await asyncio.gather(*tasks)
                
                # All should succeed
                for response in responses:
                    assert response.success is True
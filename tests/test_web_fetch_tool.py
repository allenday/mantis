"""
Tests for WebFetchTool functionality.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

import httpx

from mantis.tools.web_fetch import WebFetchTool, WebFetchConfig, WebResponse, RateLimiter


class TestRateLimiter:
    """Test the rate limiter component."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_allow_initial_requests(self):
        """Test that initial requests within limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # First 5 requests should be allowed
        for _ in range(5):
            allowed = await limiter.acquire()
            assert allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_block_excess_requests(self):
        """Test that requests exceeding limit are blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # First 2 requests should be allowed
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        
        # Third request should be blocked
        assert await limiter.acquire() is False
    
    @pytest.mark.asyncio
    async def test_rate_limit_window_reset(self):
        """Test that rate limit resets after window expires."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        
        # First request allowed
        assert await limiter.acquire() is True
        
        # Second request blocked
        assert await limiter.acquire() is False
        
        # Wait for window to reset
        await asyncio.sleep(1.1)
        
        # Request should be allowed again
        assert await limiter.acquire() is True


class TestWebFetchConfig:
    """Test WebFetchConfig model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = WebFetchConfig()
        
        assert config.timeout == 30.0
        assert config.max_content_size == 10 * 1024 * 1024
        assert config.user_agent == "Mantis-Agent/1.0 (Web Fetch Tool)"
        assert config.follow_redirects is True
        assert config.verify_ssl is True
        assert config.allowed_schemes == ["http", "https"]
        assert config.blocked_domains == []
        assert config.allowed_domains is None
        assert config.rate_limit_requests == 60
        assert config.rate_limit_window == 60
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = WebFetchConfig(
            timeout=10.0,
            max_content_size=1024,
            blocked_domains=["evil.com"],
            allowed_domains=["safe.com"]
        )
        
        assert config.timeout == 10.0
        assert config.max_content_size == 1024
        assert config.blocked_domains == ["evil.com"]
        assert config.allowed_domains == ["safe.com"]


class TestWebFetchTool:
    """Test WebFetchTool functionality."""
    
    @pytest.fixture
    def web_tool(self):
        """Create WebFetchTool instance for testing."""
        config = WebFetchConfig(
            rate_limit_requests=100,  # High limit for testing
            timeout=5.0
        )
        return WebFetchTool(config)
    
    @pytest.fixture
    def mock_response(self):
        """Create mock HTTP response."""
        response = Mock()
        response.status_code = 200
        response.is_success = True
        response.reason_phrase = "OK"
        response.headers = {"content-type": "text/html"}
        response.text = "<html><body>Test content</body></html>"
        response.content = b"<html><body>Test content</body></html>"
        response.url = "https://example.com"
        return response
    
    def test_url_validation_allowed(self):
        """Test URL validation for allowed URLs."""
        tool = WebFetchTool()
        
        assert tool._validate_url("https://example.com") is True
        assert tool._validate_url("http://test.org") is True
    
    def test_url_validation_blocked_scheme(self):
        """Test URL validation blocks disallowed schemes."""
        config = WebFetchConfig(allowed_schemes=["https"])
        tool = WebFetchTool(config)
        
        assert tool._validate_url("https://example.com") is True
        assert tool._validate_url("http://example.com") is False
        assert tool._validate_url("ftp://example.com") is False
    
    def test_url_validation_blocked_domain(self):
        """Test URL validation blocks forbidden domains."""
        config = WebFetchConfig(blocked_domains=["evil.com", "malware.org"])
        tool = WebFetchTool(config)
        
        assert tool._validate_url("https://example.com") is True
        assert tool._validate_url("https://evil.com") is False
        assert tool._validate_url("https://sub.malware.org") is False
    
    def test_url_validation_allowed_domain_only(self):
        """Test URL validation with allowed domains list."""
        config = WebFetchConfig(allowed_domains=["safe.com", "trusted.org"])
        tool = WebFetchTool(config)
        
        assert tool._validate_url("https://safe.com") is True
        assert tool._validate_url("https://sub.trusted.org") is True
        assert tool._validate_url("https://example.com") is False
    
    def test_content_parsing_json(self):
        """Test JSON content parsing."""
        tool = WebFetchTool()
        json_data = '{"key": "value", "number": 42}'
        
        parsed = tool._parse_content(json_data, "application/json")
        expected = json.dumps({"key": "value", "number": 42}, indent=2, ensure_ascii=False)
        
        assert parsed == expected
    
    def test_content_parsing_xml(self):
        """Test XML content parsing."""
        tool = WebFetchTool()
        xml_data = "<root><item>value</item></root>"
        
        parsed = tool._parse_content(xml_data, "text/xml")
        assert "<root>" in parsed
        assert "<item>value</item>" in parsed
    
    def test_content_parsing_invalid_json(self):
        """Test that invalid JSON returns original content."""
        tool = WebFetchTool()
        invalid_json = '{"key": invalid}'
        
        parsed = tool._parse_content(invalid_json, "application/json")
        assert parsed == invalid_json
    
    @pytest.mark.asyncio
    async def test_fetch_url_success(self, web_tool, mock_response):
        """Test successful URL fetch."""
        with patch.object(web_tool, '_ensure_client') as mock_ensure:
            web_tool._client = AsyncMock()
            web_tool._client.request.return_value = mock_response
            
            response = await web_tool.fetch_url("https://example.com")
            
            assert response.success is True
            assert response.status_code == 200
            assert response.url == "https://example.com"
            assert response.content_type == "text/html"
            assert "Test content" in response.content
            assert response.error_message is None
    
    @pytest.mark.asyncio
    async def test_fetch_url_invalid_url(self, web_tool):
        """Test fetch with invalid URL."""
        response = await web_tool.fetch_url("invalid://bad-url")
        
        assert response.success is False
        assert response.status_code == 400
        assert "URL validation failed" in response.error_message
    
    @pytest.mark.asyncio
    async def test_fetch_url_timeout(self, web_tool):
        """Test fetch with timeout."""
        with patch.object(web_tool, '_ensure_client'):
            web_tool._client = AsyncMock()
            web_tool._client.request.side_effect = httpx.TimeoutException("Timeout")
            
            response = await web_tool.fetch_url("https://example.com")
            
            assert response.success is False
            assert response.status_code == 408
            assert response.error_message == "Request timeout"
    
    @pytest.mark.asyncio
    async def test_fetch_url_network_error(self, web_tool):
        """Test fetch with network error."""
        with patch.object(web_tool, '_ensure_client'):
            web_tool._client = AsyncMock()
            web_tool._client.request.side_effect = httpx.NetworkError("Connection failed")
            
            response = await web_tool.fetch_url("https://example.com")
            
            assert response.success is False
            assert response.status_code == 0
            assert "Network error" in response.error_message
    
    @pytest.mark.asyncio
    async def test_fetch_url_content_too_large(self, web_tool):
        """Test fetch with content exceeding size limit."""
        # Configure small content limit
        web_tool.config.max_content_size = 10
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "This content is too long for the limit"
        mock_response.content = b"This content is too long for the limit"
        mock_response.url = "https://example.com"
        
        with patch.object(web_tool, '_ensure_client'):
            web_tool._client = AsyncMock()
            web_tool._client.request.return_value = mock_response
            
            response = await web_tool.fetch_url("https://example.com")
            
            assert response.success is False
            assert response.status_code == 413
            assert "Content too large" in response.error_message
    
    @pytest.mark.asyncio
    async def test_fetch_json_success(self, web_tool):
        """Test successful JSON fetch."""
        json_data = {"message": "Hello, World!", "status": "success"}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = json.dumps(json_data)
        mock_response.content = json.dumps(json_data).encode()
        mock_response.url = "https://api.example.com/data"
        
        with patch.object(web_tool, '_ensure_client'):
            web_tool._client = AsyncMock()
            web_tool._client.request.return_value = mock_response
            
            result = await web_tool.fetch_json("https://api.example.com/data")
            
            assert result == json_data
    
    @pytest.mark.asyncio
    async def test_fetch_json_invalid_json(self, web_tool):
        """Test JSON fetch with invalid JSON response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "not valid json"
        mock_response.content = b"not valid json"
        mock_response.url = "https://api.example.com/data"
        
        with patch.object(web_tool, '_ensure_client'):
            web_tool._client = AsyncMock()
            web_tool._client.request.return_value = mock_response
            
            with pytest.raises(ValueError, match="Invalid JSON response"):
                await web_tool.fetch_json("https://api.example.com/data")
    
    @pytest.mark.asyncio
    async def test_fetch_json_request_failed(self, web_tool):
        """Test JSON fetch with failed request."""
        with patch.object(web_tool, 'fetch_url') as mock_fetch:
            mock_fetch.return_value = WebResponse(
                url="https://api.example.com/data",
                status_code=404,
                content_type="text/plain",
                content="Not Found",
                response_time_ms=100,
                success=False,
                error_message="HTTP 404: Not Found"
            )
            
            with pytest.raises(ValueError, match="Failed to fetch URL"):
                await web_tool.fetch_json("https://api.example.com/data")
    
    @pytest.mark.asyncio
    async def test_fetch_text_success(self, web_tool):
        """Test successful text fetch."""
        text_content = "This is plain text content"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = text_content
        mock_response.content = text_content.encode()
        mock_response.url = "https://example.com/text"
        
        with patch.object(web_tool, '_ensure_client'):
            web_tool._client = AsyncMock()
            web_tool._client.request.return_value = mock_response
            
            result = await web_tool.fetch_text("https://example.com/text")
            
            assert result == text_content
    
    @pytest.mark.asyncio
    async def test_post_data_success(self, web_tool):
        """Test successful POST request."""
        post_data = {"key": "value", "number": 42}
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.is_success = True
        mock_response.reason_phrase = "Created"
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"id": 123, "created": true}'
        mock_response.content = b'{"id": 123, "created": true}'
        mock_response.url = "https://api.example.com/create"
        
        with patch.object(web_tool, '_ensure_client'):
            web_tool._client = AsyncMock()
            web_tool._client.request.return_value = mock_response
            
            response = await web_tool.post_data("https://api.example.com/create", post_data)
            
            assert response.success is True
            assert response.status_code == 201
            assert "created" in response.content
            
            # Verify the request was called with correct parameters
            web_tool._client.request.assert_called_once()
            call_args = web_tool._client.request.call_args
            assert call_args[1]["method"] == "POST"
            assert call_args[1]["url"] == "https://api.example.com/create"
            assert json.loads(call_args[1]["content"]) == post_data
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting functionality."""
        config = WebFetchConfig(rate_limit_requests=2, rate_limit_window=60)
        tool = WebFetchTool(config)
        
        # Mock both URL validation and HTTP client to test rate limiting
        with patch.object(tool, '_validate_url', return_value=True), \
             patch.object(tool, '_ensure_client'), \
             patch.object(tool, '_client', new=AsyncMock()) as mock_client:
            
            # Mock successful responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.headers = {"content-type": "text/plain"}
            mock_response.text = "success"
            mock_response.content = b"success"
            mock_response.url = "https://example.com"
            mock_client.request.return_value = mock_response
             
            # First two requests should succeed
            response1 = await tool.fetch_url("https://example.com")
            response2 = await tool.fetch_url("https://example.com")
            response3 = await tool.fetch_url("https://example.com")
            
            # First two should succeed
            assert response1.success is True
            assert response2.success is True
            
            # Third should fail due to rate limit
            assert response3.status_code == 429
            assert "Rate limit exceeded" in response3.error_message
    
    @pytest.mark.asyncio
    async def test_context_manager(self, web_tool):
        """Test WebFetchTool as async context manager."""
        async with web_tool as tool:
            assert tool._client is not None
        
        # Client should be closed after context exit
        assert web_tool._client is None
    
    def test_get_tools(self, web_tool):
        """Test tools dictionary for pydantic-ai integration."""
        tools = web_tool.get_tools()
        
        expected_tools = ['fetch_url', 'fetch_json', 'fetch_text', 'post_data']
        assert all(tool_name in tools for tool_name in expected_tools)
        assert all(tools[tool_name] == web_tool for tool_name in expected_tools)


@pytest.mark.asyncio
async def test_integration_with_httpbin():
    """Integration test with httpbin.org (if available)."""
    try:
        tool = WebFetchTool()
        
        # Test basic GET request
        async with tool:
            response = await tool.fetch_url("https://httpbin.org/get")
            
            if response.success:
                assert response.status_code == 200
                assert "httpbin.org" in response.content
            else:
                # Skip if httpbin is not available
                pytest.skip("httpbin.org not available for integration test")
                
    except Exception:
        # Skip integration test if network issues
        pytest.skip("Network not available for integration test")
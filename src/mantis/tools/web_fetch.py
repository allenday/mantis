"""
Web fetch tool for HTTP requests and content retrieval.

This tool enables agents to fetch content from web URLs, supporting various
content types and response handling with robust error management and security.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

import httpx
from pydantic import BaseModel, Field, ConfigDict


class WebResponse(BaseModel):
    """Response model for web fetch operations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: str = Field(..., description="The requested URL")
    status_code: int = Field(..., description="HTTP status code")
    content_type: str = Field(..., description="Response content type")
    content: str = Field(..., description="Response content as string")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    success: bool = Field(..., description="Whether the request was successful")
    error_message: Optional[str] = Field(None, description="Error message if request failed")


class WebFetchConfig(BaseModel):
    """Configuration for web fetch operations."""

    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_content_size: int = Field(10 * 1024 * 1024, description="Maximum content size in bytes (10MB)")
    user_agent: str = Field("Mantis-Agent/1.0 (Web Fetch Tool)", description="User agent string")
    follow_redirects: bool = Field(True, description="Whether to follow redirects")
    verify_ssl: bool = Field(True, description="Whether to verify SSL certificates")
    allowed_schemes: List[str] = Field(default_factory=lambda: ["http", "https"], description="Allowed URL schemes")
    blocked_domains: List[str] = Field(default_factory=list, description="Blocked domain patterns")
    allowed_domains: Optional[List[str]] = Field(
        None, description="Allowed domain patterns (if set, only these are allowed)"
    )
    rate_limit_requests: int = Field(60, description="Max requests per minute")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")


class RateLimiter:
    """Simple rate limiter for web requests."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[datetime] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Check if request is allowed under rate limit."""
        async with self._lock:
            now = datetime.now()
            # Remove old requests outside the window
            self.requests = [
                req_time for req_time in self.requests if now - req_time < timedelta(seconds=self.window_seconds)
            ]

            if len(self.requests) >= self.max_requests:
                return False

            self.requests.append(now)
            return True


class WebFetchTool:
    """Web fetch tool for HTTP requests and content retrieval."""

    def __init__(self, config: Optional[WebFetchConfig] = None):
        self.config = config or WebFetchConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit_requests, self.config.rate_limit_window)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self):
        """Ensure HTTP client is initialized."""
        if not self._client:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=self.config.follow_redirects,
                verify=self.config.verify_ssl,
                headers={"User-Agent": self.config.user_agent},
            )

    def _validate_url(self, url: str) -> bool:
        """Validate URL against security policies."""
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in self.config.allowed_schemes:
                return False

            # Check domain restrictions
            hostname = parsed.hostname
            if not hostname:
                return False

            # Check blocked domains
            for blocked in self.config.blocked_domains:
                if blocked.lower() in hostname.lower():
                    return False

            # Check allowed domains (if specified)
            if self.config.allowed_domains:
                allowed = False
                for allowed_domain in self.config.allowed_domains:
                    if allowed_domain.lower() in hostname.lower():
                        allowed = True
                        break
                if not allowed:
                    return False

            return True

        except Exception:
            return False

    def _parse_content(self, content: str, content_type: str) -> str:
        """Parse and process content based on content type."""
        try:
            if "application/json" in content_type:
                # Pretty print JSON
                data = json.loads(content)
                return json.dumps(data, indent=2, ensure_ascii=False)

            elif "text/xml" in content_type or "application/xml" in content_type:
                # Pretty print XML
                root = ET.fromstring(content)
                return ET.tostring(root, encoding="unicode", method="xml")

            elif "text/html" in content_type:
                # For HTML, return as-is but could add parsing/cleaning
                return content

            else:
                # Plain text or other formats
                return content

        except Exception:
            # If parsing fails, return original content
            return content

    async def fetch_url(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
    ) -> WebResponse:
        """
        Fetch content from a URL with specified HTTP method.

        Args:
            url: The URL to fetch
            method: HTTP method (GET, POST, PUT, etc.)
            headers: Optional additional headers
            data: Optional request data for POST/PUT requests

        Returns:
            WebResponse with the fetched content and metadata
        """
        start_time = time.time()

        # Validate URL
        if not self._validate_url(url):
            return WebResponse(
                url=url,
                status_code=400,
                content_type="text/plain",
                content="",
                response_time_ms=0,
                success=False,
                error_message="URL validation failed: blocked or invalid URL",
            )

        # Check rate limit
        if not await self.rate_limiter.acquire():
            return WebResponse(
                url=url,
                status_code=429,
                content_type="text/plain",
                content="",
                response_time_ms=0,
                success=False,
                error_message="Rate limit exceeded",
            )

        try:
            await self._ensure_client()

            # Prepare request
            request_headers = headers or {}
            request_data = None

            if data:
                if isinstance(data, dict):
                    if method.upper() in ["POST", "PUT", "PATCH"]:
                        request_data = json.dumps(data)
                        request_headers["Content-Type"] = "application/json"
                else:
                    request_data = str(data)

            # Make request
            response = await self._client.request(
                method=method.upper(), url=url, headers=request_headers, content=request_data
            )

            response_time = (time.time() - start_time) * 1000
            content_type = response.headers.get("content-type", "text/plain")

            # Check content size
            content_length = len(response.content)
            if content_length > self.config.max_content_size:
                return WebResponse(
                    url=url,
                    status_code=413,
                    content_type=content_type,
                    content="",
                    headers=dict(response.headers),
                    response_time_ms=response_time,
                    success=False,
                    error_message=f"Content too large: {content_length} bytes exceeds limit of {self.config.max_content_size}",
                )

            # Get content as text
            content = response.text

            # Parse content based on type
            parsed_content = self._parse_content(content, content_type)

            return WebResponse(
                url=str(response.url),
                status_code=response.status_code,
                content_type=content_type,
                content=parsed_content,
                headers=dict(response.headers),
                response_time_ms=response_time,
                success=response.is_success,
                error_message=None if response.is_success else f"HTTP {response.status_code}: {response.reason_phrase}",
            )

        except httpx.TimeoutException:
            return WebResponse(
                url=url,
                status_code=408,
                content_type="text/plain",
                content="",
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message="Request timeout",
            )

        except httpx.NetworkError as e:
            return WebResponse(
                url=url,
                status_code=0,
                content_type="text/plain",
                content="",
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=f"Network error: {str(e)}",
            )

        except Exception as e:
            return WebResponse(
                url=url,
                status_code=500,
                content_type="text/plain",
                content="",
                response_time_ms=(time.time() - start_time) * 1000,
                success=False,
                error_message=f"Unexpected error: {str(e)}",
            )

    async def fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Fetch JSON content from a URL.

        Args:
            url: The URL to fetch JSON from
            headers: Optional additional headers

        Returns:
            Parsed JSON data as dictionary

        Raises:
            ValueError: If response is not valid JSON or request fails
        """
        response = await self.fetch_url(url, headers=headers)

        if not response.success:
            raise ValueError(f"Failed to fetch URL: {response.error_message}")

        try:
            return json.loads(response.content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")

    async def fetch_text(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """
        Fetch text content from a URL.

        Args:
            url: The URL to fetch text from
            headers: Optional additional headers

        Returns:
            Response content as string

        Raises:
            ValueError: If request fails
        """
        response = await self.fetch_url(url, headers=headers)

        if not response.success:
            raise ValueError(f"Failed to fetch URL: {response.error_message}")

        return response.content

    async def post_data(self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> WebResponse:
        """
        POST data to a URL.

        Args:
            url: The URL to POST to
            data: Data to send in request body
            headers: Optional additional headers

        Returns:
            WebResponse with the server's response
        """
        return await self.fetch_url(url, method="POST", headers=headers, data=data)

    def get_tools(self) -> Dict[str, Any]:
        """Return dictionary of available tools for pydantic-ai integration."""
        return {
            "fetch_url": self,
            "fetch_json": self,
            "fetch_text": self,
            "post_data": self,
        }

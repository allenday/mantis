"""
Web fetch tool for HTTP requests with security features and rate limiting.

This tool enables agents to make secure HTTP requests with built-in
rate limiting, URL validation, and comprehensive error handling.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel, Field, ConfigDict


class WebResponse(BaseModel):
    """Response model for web fetch operations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    status_code: int = Field(..., description="HTTP status code")
    content: str = Field(..., description="Response content as text")
    headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    success: bool = Field(..., description="Whether the request was successful")
    url: str = Field(..., description="Final URL after redirects")
    error_message: Optional[str] = Field(None, description="Error message if request failed")
    response_time_ms: float = Field(..., description="Response time in milliseconds")


class WebFetchConfig(BaseModel):
    """Configuration for web fetch operations."""

    timeout: float = Field(30.0, description="Request timeout in seconds")
    user_agent: str = Field("Mantis-Agent/1.0 (Web Fetch Tool)", description="User agent string for requests")
    max_redirects: int = Field(10, description="Maximum number of redirects to follow")
    max_content_size: int = Field(10 * 1024 * 1024, description="Maximum content size in bytes")
    rate_limit_requests: int = Field(60, description="Max requests per window")
    rate_limit_window: int = Field(60, description="Rate limit window in seconds")
    verify_ssl: bool = Field(True, description="Whether to verify SSL certificates")
    allowed_domains: Optional[List[str]] = Field(None, description="Allowed domains for requests")
    blocked_domains: List[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0"], description="Blocked domains for security"
    )


class RateLimiter:
    """Rate limiter for HTTP requests."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Acquire permission to make a request."""
        async with self._lock:
            now = time.time()
            # Remove old requests outside the window
            self.requests = [req_time for req_time in self.requests if now - req_time < self.window_seconds]

            if len(self.requests) >= self.max_requests:
                return False

            self.requests.append(now)
            return True

    async def wait_for_slot(self) -> None:
        """Wait until a request slot is available."""
        while not await self.acquire():
            await asyncio.sleep(0.1)


class WebFetchTool:
    """Web fetch tool with security features and rate limiting."""

    def __init__(self, config: Optional[WebFetchConfig] = None):
        self.config = config or WebFetchConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit_requests, self.config.rate_limit_window)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry."""
        connector = aiohttp.TCPConnector(ssl=self.config.verify_ssl, limit=100, limit_per_host=30)

        timeout = aiohttp.ClientTimeout(total=self.config.timeout)

        self._session = aiohttp.ClientSession(
            connector=connector, timeout=timeout, headers={"User-Agent": self.config.user_agent}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    def _validate_url(self, url: str) -> bool:
        """Validate URL for security."""
        try:
            parsed = urlparse(url)

            # Check scheme
            if parsed.scheme not in ["http", "https"]:
                return False

            # Check for blocked domains
            if any(blocked in parsed.netloc.lower() for blocked in self.config.blocked_domains):
                return False

            # Check allowed domains if specified
            if self.config.allowed_domains:
                if not any(allowed in parsed.netloc.lower() for allowed in self.config.allowed_domains):
                    return False

            # Check for private IP ranges
            hostname = parsed.hostname
            if hostname:
                # Basic check for private IPs
                if hostname.startswith("10.") or hostname.startswith("192.168.") or hostname.startswith("172."):
                    return False

            return True

        except Exception:
            return False

    async def fetch_url(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
    ) -> WebResponse:
        """
        Fetch content from a URL.

        Args:
            url: URL to fetch
            method: HTTP method (GET, POST, etc.)
            headers: Optional headers to include
            data: Optional data to send with request

        Returns:
            WebResponse with content and metadata
        """
        start_time = time.time()

        # Validate URL
        if not self._validate_url(url):
            return WebResponse(
                status_code=0,
                content="",
                headers={},
                success=False,
                url=url,
                error_message="URL validation failed - blocked or invalid URL",
                response_time_ms=0,
            )

        # Rate limiting
        await self.rate_limiter.wait_for_slot()

        if not self._session:
            return WebResponse(
                status_code=0,
                content="",
                headers={},
                success=False,
                url=url,
                error_message="Session not initialized - use as async context manager",
                response_time_ms=0,
            )

        try:
            # Prepare request
            request_headers = headers or {}

            # Make request
            async with self._session.request(
                method=method.upper(),
                url=url,
                headers=request_headers,
                data=data,
                max_redirects=self.config.max_redirects,
            ) as response:
                # Check content size
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.config.max_content_size:
                    return WebResponse(
                        status_code=response.status,
                        content="",
                        headers=dict(response.headers),
                        success=False,
                        url=str(response.url),
                        error_message=f"Content too large: {content_length} bytes",
                        response_time_ms=(time.time() - start_time) * 1000,
                    )

                # Read content with size limit
                content = ""
                bytes_read = 0
                async for chunk in response.content.iter_chunked(8192):
                    bytes_read += len(chunk)
                    if bytes_read > self.config.max_content_size:
                        return WebResponse(
                            status_code=response.status,
                            content="",
                            headers=dict(response.headers),
                            success=False,
                            url=str(response.url),
                            error_message=f"Content too large: exceeded {self.config.max_content_size} bytes",
                            response_time_ms=(time.time() - start_time) * 1000,
                        )
                    content += chunk.decode("utf-8", errors="ignore")

                response_time = (time.time() - start_time) * 1000

                return WebResponse(
                    status_code=response.status,
                    content=content,
                    headers=dict(response.headers),
                    success=200 <= response.status < 300,
                    url=str(response.url),
                    error_message=None if 200 <= response.status < 300 else f"HTTP {response.status}",
                    response_time_ms=response_time,
                )

        except asyncio.TimeoutError:
            return WebResponse(
                status_code=0,
                content="",
                headers={},
                success=False,
                url=url,
                error_message="Request timeout",
                response_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return WebResponse(
                status_code=0,
                content="",
                headers={},
                success=False,
                url=url,
                error_message=f"Request failed: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def fetch_json(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Fetch JSON data from a URL.

        Args:
            url: URL to fetch
            headers: Optional headers to include

        Returns:
            Parsed JSON data

        Raises:
            Exception: If request fails or response is not valid JSON
        """
        response = await self.fetch_url(url, headers=headers)

        if not response.success:
            raise Exception(f"Failed to fetch URL: {response.error_message}")

        try:
            import json

            return json.loads(response.content)
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {str(e)}")

    async def fetch_text(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """
        Fetch text content from a URL.

        Args:
            url: URL to fetch
            headers: Optional headers to include

        Returns:
            Text content

        Raises:
            Exception: If request fails
        """
        response = await self.fetch_url(url, headers=headers)

        if not response.success:
            raise Exception(f"Failed to fetch URL: {response.error_message}")

        return response.content

    async def post_data(self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> WebResponse:
        """
        POST data to a URL.

        Args:
            url: URL to post to
            data: Data to post
            headers: Optional headers to include

        Returns:
            WebResponse with result
        """
        import json

        post_headers = headers or {}
        post_headers["Content-Type"] = "application/json"

        return await self.fetch_url(url, method="POST", headers=post_headers, data=json.dumps(data))

    def get_tools(self) -> Dict[str, Any]:
        """Return dictionary of available tools for pydantic-ai integration."""
        return {
            "fetch_url": self,
            "fetch_json": self,
            "fetch_text": self,
            "post_data": self,
        }

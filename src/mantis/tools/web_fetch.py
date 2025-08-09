"""
Native pydantic-ai web fetch tool.
Simplified to only support pydantic-ai integration.
"""

import logging
import aiohttp
from .base import log_tool_invocation, log_tool_result

logger = logging.getLogger(__name__)


async def web_fetch_url(url: str) -> str:
    """Fetch content from a web URL.

    This tool fetches content from web pages and returns information about
    the fetch operation, including success status and content length.

    Args:
        url: URL to fetch content from

    Returns:
        Success message with content length or error message
    """
    log_tool_invocation("web_fetch", "web_fetch_url", {"url": url})

    try:
        # Create secure session with proper settings
        timeout = aiohttp.ClientTimeout(total=30.0)
        headers = {"User-Agent": "Mantis-WebFetch/1.0"}

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, ssl=True) as response:
                # Read content with size limit
                content = await response.read()
                max_size = 10 * 1024 * 1024  # 10MB limit

                if len(content) > max_size:
                    content = content[:max_size]

                content_text = content.decode("utf-8", errors="ignore")

                if response.status == 200:
                    log_tool_result("web_fetch", "web_fetch_url", {
                        "url": url, 
                        "status_code": response.status, 
                        "content_length": len(content_text),
                        "success": True
                    })
                    return content_text  # Return actual content for LLM/testing
                else:
                    error_msg = f"Failed to fetch URL {url}: HTTP {response.status}"
                    log_tool_result("web_fetch", "web_fetch_url", {
                        "url": url, 
                        "status_code": response.status, 
                        "success": False
                    })
                    return error_msg

    except Exception as e:
        error_msg = f"Error fetching URL {url}: {str(e)}"
        return error_msg

"""
Native pydantic-ai web fetch tool.
Simplified to only support pydantic-ai integration.
"""

import logging
import aiohttp

# Observability imports
try:
    from ..observability import get_structured_logger

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("web_fetch")
else:
    obs_logger = None  # type: ignore


async def web_fetch_url(url: str) -> str:
    """Fetch content from a web URL.

    This tool fetches content from web pages and returns information about
    the fetch operation, including success status and content length.

    Args:
        url: URL to fetch content from

    Returns:
        Success message with content length or error message
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: web_fetch_url for {url}")

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
                    result_msg = (
                        f"Successfully fetched {len(content_text)} characters from {url} (status: {response.status})"
                    )
                    if OBSERVABILITY_AVAILABLE and obs_logger:
                        obs_logger.info(f"Web fetch successful: {len(content_text)} chars")
                    return result_msg
                else:
                    error_msg = f"Failed to fetch URL {url}: HTTP {response.status}"
                    if OBSERVABILITY_AVAILABLE and obs_logger:
                        obs_logger.error(f"Web fetch failed: HTTP {response.status}")
                    return error_msg

    except Exception as e:
        error_msg = f"Error fetching URL {url}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Web fetch exception: {e}")
        return error_msg

"""
Native pydantic-ai web search tool using DuckDuckGo.
Simplified to only support pydantic-ai integration.
"""

import logging
from duckduckgo_search import DDGS

# Observability imports
try:
    from ..observability import get_structured_logger

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("web_search")
else:
    obs_logger = None  # type: ignore


async def web_search(query: str, max_results: int = 10) -> str:
    """Search the web using DuckDuckGo for information.

    This tool performs web searches and returns formatted results with
    titles, URLs, and snippets from relevant web pages.

    Args:
        query: Search query to look for
        max_results: Maximum number of search results to return (default: 10)

    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: web_search for '{query}', max_results: {max_results}")

    try:
        # Use DuckDuckGo search
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return f"No results found for query: '{query}'"

            # Format results for LLM
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(f"{i}. **{result['title']}**\n   {result['href']}\n   {result['body']}")

            result_text = f"Found {len(results)} results for '{query}':\n\n" + "\n\n".join(formatted_results)

            if OBSERVABILITY_AVAILABLE and obs_logger:
                obs_logger.info(f"Web search returned {len(results)} results")

            return result_text

    except Exception as e:
        error_msg = f"Error searching for '{query}': {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Web search exception: {e}")
        return error_msg

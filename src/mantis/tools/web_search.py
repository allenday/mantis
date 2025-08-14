"""
Native pydantic-ai web search tool using DuckDuckGo.
Simplified to only support pydantic-ai integration.
"""

import logging

try:
    from duckduckgo_search import DDGS  # type: ignore[assignment,import-untyped]
except ImportError:
    from ddgs import DDGS  # type: ignore[assignment,import-untyped,import-not-found,no-redef]
from .base import log_tool_invocation, log_tool_result

logger = logging.getLogger(__name__)


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
    log_tool_invocation("web_search", "web_search", {"query": query, "max_results": max_results})

    try:
        # Use DuckDuckGo search
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

            if not results:
                log_tool_result("web_search", "web_search", {"results_count": 0, "query": query})
                return f"No results found for query: '{query}'"

            # Format results for LLM
            formatted_results = []
            for i, result in enumerate(results, 1):
                formatted_results.append(f"{i}. **{result['title']}**\n   {result['href']}\n   {result['body']}")

            result_text = f"Found {len(results)} results for '{query}':\n\n" + "\n\n".join(formatted_results)

            log_tool_result("web_search", "web_search", {"results_count": len(results), "query": query})

            return result_text

    except Exception as e:
        error_msg = f"Error searching for '{query}': {str(e)}"
        return error_msg

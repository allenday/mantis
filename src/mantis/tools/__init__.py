"""
Tools package for Mantis agents.

This package contains various tools that agents can use for external operations
like web fetching, searching, and other integrations.
"""

from .web_fetch import WebFetchTool, WebFetchConfig, WebResponse
from .web_search import WebSearchTool, WebSearchConfig, SearchResult, SearchResponse, SearchFilters

__all__ = [
    "WebFetchTool",
    "WebFetchConfig",
    "WebResponse",
    "WebSearchTool",
    "WebSearchConfig",
    "SearchResult",
    "SearchResponse",
    "SearchFilters",
]

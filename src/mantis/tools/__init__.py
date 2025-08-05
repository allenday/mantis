"""
Tools package for Mantis agents.

This package contains various tools that agents can use for external operations
like web fetching, searching, git operations, and other integrations.
"""

from .web_fetch import WebFetchTool, WebFetchConfig, WebResponse
from .web_search import WebSearchTool, WebSearchConfig, SearchResult, SearchResponse, SearchFilters
from .git_operations import GitOperationsTool, GitOperationsConfig, RepositoryInfo, CommitInfo, CodeMatch

__all__ = [
    "WebFetchTool",
    "WebFetchConfig",
    "WebResponse",
    "WebSearchTool",
    "WebSearchConfig",
    "SearchResult",
    "SearchResponse",
    "SearchFilters",
    "GitOperationsTool",
    "GitOperationsConfig",
    "RepositoryInfo",
    "CommitInfo",
    "CodeMatch",
]

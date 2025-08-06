"""
Tools package for Mantis agents.

This package contains various tools that agents can use for external operations
like web fetching, searching, git operations, registry access, and other integrations.
"""

from .web_fetch import WebFetchTool, WebFetchConfig, WebResponse
from .web_search import WebSearchTool, WebSearchConfig, SearchResult, SearchResponse, SearchFilters
from .git_operations import GitOperationsTool, GitOperationsConfig, RepositoryInfo, CommitInfo, CodeMatch
from .registry_access import (
    RegistryTool,
    RegistryConfig,
    AgentCard,
    AgentSpec,
    SearchFilters as RegistrySearchFilters,
    RegistryError,
)

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
    "RegistryTool",
    "RegistryConfig",
    "AgentCard",
    "AgentSpec",
    "RegistrySearchFilters",
    "RegistryError",
]
"""
Native pydantic-ai tools for Mantis agents.
Simplified to only export the direct pydantic-ai functions.
"""

# Import native pydantic-ai tool functions
from .agent_registry import registry_search_agents, registry_get_agent_details
from .web_fetch import web_fetch_url
from .web_search import web_search
from .git_operations import git_analyze_repository

__all__ = [
    "registry_search_agents",
    "registry_get_agent_details", 
    "web_fetch_url",
    "web_search",
    "git_analyze_repository",
]
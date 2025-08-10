"""
Native pydantic-ai tools for Mantis agents.
Simplified to only export the direct pydantic-ai functions.
"""

# Import native pydantic-ai tool functions
from .agent_registry import registry_search_agents, registry_get_agent_details
from .web_fetch import web_fetch_url
from .web_search import web_search
from .git_operations import git_analyze_repository
from .gitlab_integration import gitlab_list_projects, gitlab_list_issues, gitlab_create_issue, gitlab_get_issue
from .jira_integration import jira_list_projects, jira_list_issues, jira_create_issue, jira_get_issue
from .divination import get_random_number, draw_tarot_card, cast_i_ching_trigram, draw_multiple_tarot_cards, flip_coin

__all__ = [
    "registry_search_agents",
    "registry_get_agent_details",
    "web_fetch_url",
    "web_search",
    "git_analyze_repository",
    "gitlab_list_projects",
    "gitlab_list_issues",
    "gitlab_create_issue",
    "gitlab_get_issue",
    "jira_list_projects",
    "jira_list_issues",
    "jira_create_issue",
    "jira_get_issue",
    "get_random_number",
    "draw_tarot_card",
    "cast_i_ching_trigram",
    "draw_multiple_tarot_cards",
    "flip_coin",
]

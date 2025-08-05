"""
Tools package for Mantis agents.

This package contains various tools that agents can use for external operations
like GitLab integration, web operations, and other API integrations.
"""

from .gitlab_integration import GitLabTool, GitLabConfig, GitLabProject, GitLabIssue, GitLabMergeRequest, GitLabPipeline, MCPError

__all__ = [
    "GitLabTool",
    "GitLabConfig", 
    "GitLabProject",
    "GitLabIssue",
    "GitLabMergeRequest",
    "GitLabPipeline",
    "MCPError",
]
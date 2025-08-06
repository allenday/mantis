"""
GitLab integration tool using MCP server.

This tool provides GitLab operations by integrating with the gitlab-mcp
server (https://github.com/zereight/gitlab-mcp), enabling agents to
interact with GitLab APIs for project management, issue tracking, and more.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class GitLabConfig(BaseModel):
    """Configuration for GitLab MCP integration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Authentication
    personal_access_token: str = Field(..., description="GitLab personal access token")
    api_url: str = Field(default="https://gitlab.com/api/v4", description="GitLab API URL")

    # MCP Server Configuration
    read_only_mode: bool = Field(default=False, description="Restrict to read-only operations")

    # Feature toggles
    enable_wiki_api: bool = Field(default=True, description="Enable wiki operations")
    enable_milestone_api: bool = Field(default=True, description="Enable milestone operations")
    enable_pipeline_api: bool = Field(default=True, description="Enable pipeline operations")

    # Transport and connection settings
    transport_mode: str = Field(default="stdio", description="MCP transport mode (stdio, sse, streamable-http)")
    host: str = Field(default="127.0.0.1", description="Server host")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")

    # Proxy settings
    http_proxy: Optional[str] = Field(default=None, description="HTTP proxy URL")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS proxy URL")
    no_proxy: str = Field(default="localhost,127.0.0.1", description="Proxy exclusions")


class GitLabProject(BaseModel):
    """GitLab project information."""

    id: int = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    path: str = Field(..., description="Project path")
    namespace: str = Field(..., description="Project namespace")
    description: Optional[str] = Field(None, description="Project description")
    web_url: str = Field(..., description="Project web URL")
    ssh_url_to_repo: Optional[str] = Field(None, description="SSH clone URL")
    http_url_to_repo: Optional[str] = Field(None, description="HTTP clone URL")
    visibility: str = Field(..., description="Project visibility (private, internal, public)")
    default_branch: Optional[str] = Field(None, description="Default branch name")


class GitLabIssue(BaseModel):
    """GitLab issue information."""

    id: int = Field(..., description="Issue ID")
    iid: int = Field(..., description="Issue IID (project-scoped)")
    title: str = Field(..., description="Issue title")
    description: Optional[str] = Field(None, description="Issue description")
    state: str = Field(..., description="Issue state (opened, closed)")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    author: Dict[str, Any] = Field(..., description="Issue author information")
    assignee: Optional[Dict[str, Any]] = Field(None, description="Issue assignee information")
    web_url: str = Field(..., description="Issue web URL")
    labels: List[str] = Field(default_factory=list, description="Issue labels")


class GitLabMergeRequest(BaseModel):
    """GitLab merge request information."""

    id: int = Field(..., description="Merge request ID")
    iid: int = Field(..., description="Merge request IID (project-scoped)")
    title: str = Field(..., description="Merge request title")
    description: Optional[str] = Field(None, description="Merge request description")
    state: str = Field(..., description="Merge request state (opened, closed, merged)")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    author: Dict[str, Any] = Field(..., description="Merge request author")
    assignee: Optional[Dict[str, Any]] = Field(None, description="Merge request assignee")
    source_branch: str = Field(..., description="Source branch name")
    target_branch: str = Field(..., description="Target branch name")
    web_url: str = Field(..., description="Merge request web URL")
    merge_status: str = Field(..., description="Merge status")


class GitLabPipeline(BaseModel):
    """GitLab pipeline information."""

    id: int = Field(..., description="Pipeline ID")
    status: str = Field(..., description="Pipeline status")
    ref: str = Field(..., description="Git reference")
    sha: str = Field(..., description="Commit SHA")
    web_url: str = Field(..., description="Pipeline web URL")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class MCPError(Exception):
    """Exception raised when MCP server communication fails."""

    pass


class GitLabTool:
    """GitLab integration tool using MCP server communication."""

    def __init__(self, config: Optional[GitLabConfig] = None):
        self.config = config or GitLabConfig(personal_access_token="")
        self._validate_config()

    def _validate_config(self):
        """Validate the configuration."""
        # Allow empty token for initialization purposes (read-only mode)
        if not self.config.personal_access_token and not self.config.read_only_mode:
            raise ValueError("GitLab personal access token is required for non-read-only mode")

        if not self.config.api_url:
            raise ValueError("GitLab API URL is required")

    async def _call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the GitLab MCP server.

        This method handles the MCP communication protocol to invoke
        tools on the gitlab-mcp server.

        Args:
            tool_name: Name of the MCP tool to call
            parameters: Parameters to pass to the tool

        Returns:
            Dictionary containing the tool response

        Raises:
            MCPError: If MCP communication fails
        """
        # Check if we have a valid configuration for MCP calls
        if not self.config.personal_access_token:
            raise MCPError("GitLab personal access token is required for MCP operations")

        # TODO: Implement actual MCP client communication
        # For now, this is a placeholder that simulates the MCP protocol

        logger.debug(f"Calling MCP tool: {tool_name} with parameters: {parameters}")

        # This would be replaced with actual MCP client implementation
        # using the Model Context Protocol to communicate with the gitlab-mcp server

        # Simulate MCP request/response for development
        mcp_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": parameters},
            "id": 1,
        }

        logger.info(f"MCP Request: {json.dumps(mcp_request, indent=2)}")

        # In a real implementation, this would:
        # 1. Connect to the MCP server (stdio, sse, or streamable-http)
        # 2. Send the JSON-RPC request
        # 3. Receive and parse the response
        # 4. Handle errors appropriately

        # For now, return a placeholder response
        raise MCPError(f"MCP server communication not yet implemented for tool: {tool_name}")

    async def list_projects(self, search: Optional[str] = None, limit: int = 20) -> List[GitLabProject]:
        """
        List GitLab projects accessible to the authenticated user.

        Args:
            search: Optional search string to filter projects
            limit: Maximum number of projects to return

        Returns:
            List of GitLabProject objects
        """
        parameters: Dict[str, Any] = {"per_page": limit}

        if search:
            parameters["search"] = search

        try:
            response = await self._call_mcp_tool("list_projects", parameters)
            projects = []

            for project_data in response.get("projects", []):
                project = GitLabProject(
                    id=project_data["id"],
                    name=project_data["name"],
                    path=project_data["path"],
                    namespace=project_data["namespace"]["full_path"],
                    description=project_data.get("description"),
                    web_url=project_data["web_url"],
                    ssh_url_to_repo=project_data.get("ssh_url_to_repo"),
                    http_url_to_repo=project_data.get("http_url_to_repo"),
                    visibility=project_data["visibility"],
                    default_branch=project_data.get("default_branch"),
                )
                projects.append(project)

            return projects

        except Exception as e:
            raise MCPError(f"Failed to list projects: {str(e)}")

    async def get_project(self, project_id: Union[int, str]) -> GitLabProject:
        """
        Get details of a specific GitLab project.

        Args:
            project_id: Project ID or path

        Returns:
            GitLabProject object with project details
        """
        parameters = {"project_id": str(project_id)}

        try:
            response = await self._call_mcp_tool("get_project", parameters)
            project_data = response["project"]

            return GitLabProject(
                id=project_data["id"],
                name=project_data["name"],
                path=project_data["path"],
                namespace=project_data["namespace"]["full_path"],
                description=project_data.get("description"),
                web_url=project_data["web_url"],
                ssh_url_to_repo=project_data.get("ssh_url_to_repo"),
                http_url_to_repo=project_data.get("http_url_to_repo"),
                visibility=project_data["visibility"],
                default_branch=project_data.get("default_branch"),
            )

        except Exception as e:
            raise MCPError(f"Failed to get project {project_id}: {str(e)}")

    async def list_issues(
        self, project_id: Union[int, str], state: str = "opened", labels: Optional[List[str]] = None, limit: int = 20
    ) -> List[GitLabIssue]:
        """
        List issues for a specific GitLab project.

        Args:
            project_id: Project ID or path
            state: Issue state filter (opened, closed, all)
            labels: Optional list of labels to filter by
            limit: Maximum number of issues to return

        Returns:
            List of GitLabIssue objects
        """
        parameters = {"project_id": str(project_id), "state": state, "per_page": limit}

        if labels:
            parameters["labels"] = ",".join(labels)

        try:
            response = await self._call_mcp_tool("list_issues", parameters)
            issues = []

            for issue_data in response.get("issues", []):
                issue = GitLabIssue(
                    id=issue_data["id"],
                    iid=issue_data["iid"],
                    title=issue_data["title"],
                    description=issue_data.get("description"),
                    state=issue_data["state"],
                    created_at=issue_data["created_at"],
                    updated_at=issue_data["updated_at"],
                    author=issue_data["author"],
                    assignee=issue_data.get("assignee"),
                    web_url=issue_data["web_url"],
                    labels=issue_data.get("labels", []),
                )
                issues.append(issue)

            return issues

        except Exception as e:
            raise MCPError(f"Failed to list issues for project {project_id}: {str(e)}")

    async def create_issue(
        self,
        project_id: Union[int, str],
        title: str,
        description: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignee_id: Optional[int] = None,
    ) -> GitLabIssue:
        """
        Create a new issue in a GitLab project.

        Args:
            project_id: Project ID or path
            title: Issue title
            description: Optional issue description
            labels: Optional list of labels to apply
            assignee_id: Optional user ID to assign the issue to

        Returns:
            GitLabIssue object representing the created issue
        """
        if self.config.read_only_mode:
            raise MCPError("Cannot create issue: read-only mode is enabled")

        parameters: Dict[str, Any] = {"project_id": str(project_id), "title": title}

        if description:
            parameters["description"] = description
        if labels:
            parameters["labels"] = ",".join(labels)
        if assignee_id:
            parameters["assignee_ids"] = [assignee_id]

        try:
            response = await self._call_mcp_tool("create_issue", parameters)
            issue_data = response["issue"]

            return GitLabIssue(
                id=issue_data["id"],
                iid=issue_data["iid"],
                title=issue_data["title"],
                description=issue_data.get("description"),
                state=issue_data["state"],
                created_at=issue_data["created_at"],
                updated_at=issue_data["updated_at"],
                author=issue_data["author"],
                assignee=issue_data.get("assignee"),
                web_url=issue_data["web_url"],
                labels=issue_data.get("labels", []),
            )

        except Exception as e:
            raise MCPError(f"Failed to create issue in project {project_id}: {str(e)}")

    async def list_merge_requests(
        self, project_id: Union[int, str], state: str = "opened", target_branch: Optional[str] = None, limit: int = 20
    ) -> List[GitLabMergeRequest]:
        """
        List merge requests for a specific GitLab project.

        Args:
            project_id: Project ID or path
            state: Merge request state filter (opened, closed, merged, all)
            target_branch: Optional target branch filter
            limit: Maximum number of merge requests to return

        Returns:
            List of GitLabMergeRequest objects
        """
        parameters = {"project_id": str(project_id), "state": state, "per_page": limit}

        if target_branch:
            parameters["target_branch"] = target_branch

        try:
            response = await self._call_mcp_tool("list_merge_requests", parameters)
            merge_requests = []

            for mr_data in response.get("merge_requests", []):
                mr = GitLabMergeRequest(
                    id=mr_data["id"],
                    iid=mr_data["iid"],
                    title=mr_data["title"],
                    description=mr_data.get("description"),
                    state=mr_data["state"],
                    created_at=mr_data["created_at"],
                    updated_at=mr_data["updated_at"],
                    author=mr_data["author"],
                    assignee=mr_data.get("assignee"),
                    source_branch=mr_data["source_branch"],
                    target_branch=mr_data["target_branch"],
                    web_url=mr_data["web_url"],
                    merge_status=mr_data.get("merge_status", "unchecked"),
                )
                merge_requests.append(mr)

            return merge_requests

        except Exception as e:
            raise MCPError(f"Failed to list merge requests for project {project_id}: {str(e)}")

    async def create_merge_request(
        self,
        project_id: Union[int, str],
        title: str,
        source_branch: str,
        target_branch: str,
        description: Optional[str] = None,
        assignee_id: Optional[int] = None,
    ) -> GitLabMergeRequest:
        """
        Create a new merge request in a GitLab project.

        Args:
            project_id: Project ID or path
            title: Merge request title
            source_branch: Source branch name
            target_branch: Target branch name
            description: Optional merge request description
            assignee_id: Optional user ID to assign the merge request to

        Returns:
            GitLabMergeRequest object representing the created merge request
        """
        if self.config.read_only_mode:
            raise MCPError("Cannot create merge request: read-only mode is enabled")

        parameters = {
            "project_id": str(project_id),
            "title": title,
            "source_branch": source_branch,
            "target_branch": target_branch,
        }

        if description:
            parameters["description"] = description
        if assignee_id:
            parameters["assignee_id"] = str(assignee_id)

        try:
            response = await self._call_mcp_tool("create_merge_request", parameters)
            mr_data = response["merge_request"]

            return GitLabMergeRequest(
                id=mr_data["id"],
                iid=mr_data["iid"],
                title=mr_data["title"],
                description=mr_data.get("description"),
                state=mr_data["state"],
                created_at=mr_data["created_at"],
                updated_at=mr_data["updated_at"],
                author=mr_data["author"],
                assignee=mr_data.get("assignee"),
                source_branch=mr_data["source_branch"],
                target_branch=mr_data["target_branch"],
                web_url=mr_data["web_url"],
                merge_status=mr_data.get("merge_status", "unchecked"),
            )

        except Exception as e:
            raise MCPError(f"Failed to create merge request in project {project_id}: {str(e)}")

    async def list_pipelines(
        self, project_id: Union[int, str], ref: Optional[str] = None, status: Optional[str] = None, limit: int = 20
    ) -> List[GitLabPipeline]:
        """
        List pipelines for a specific GitLab project.

        Args:
            project_id: Project ID or path
            ref: Optional git reference filter
            status: Optional pipeline status filter
            limit: Maximum number of pipelines to return

        Returns:
            List of GitLabPipeline objects
        """
        if not self.config.enable_pipeline_api:
            raise MCPError("Pipeline API is disabled")

        parameters = {"project_id": str(project_id), "per_page": limit}

        if ref:
            parameters["ref"] = ref
        if status:
            parameters["status"] = status

        try:
            response = await self._call_mcp_tool("list_pipelines", parameters)
            pipelines = []

            for pipeline_data in response.get("pipelines", []):
                pipeline = GitLabPipeline(
                    id=pipeline_data["id"],
                    status=pipeline_data["status"],
                    ref=pipeline_data["ref"],
                    sha=pipeline_data["sha"],
                    web_url=pipeline_data["web_url"],
                    created_at=pipeline_data["created_at"],
                    updated_at=pipeline_data["updated_at"],
                )
                pipelines.append(pipeline)

            return pipelines

        except Exception as e:
            raise MCPError(f"Failed to list pipelines for project {project_id}: {str(e)}")

    async def get_file_contents(self, project_id: Union[int, str], file_path: str, ref: str = "main") -> str:
        """
        Get the contents of a file from a GitLab repository.

        Args:
            project_id: Project ID or path
            file_path: Path to the file in the repository
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            File contents as string
        """
        parameters = {"project_id": str(project_id), "file_path": file_path, "ref": ref}

        try:
            response = await self._call_mcp_tool("get_file_contents", parameters)
            return response.get("content", "")

        except Exception as e:
            raise MCPError(f"Failed to get file contents from {project_id}:{file_path}: {str(e)}")

    async def search_repositories(self, query: str, limit: int = 20) -> List[GitLabProject]:
        """
        Search GitLab repositories.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of GitLabProject objects matching the search
        """
        parameters = {"search": query, "per_page": limit}

        try:
            response = await self._call_mcp_tool("search_repositories", parameters)
            projects = []

            for project_data in response.get("projects", []):
                project = GitLabProject(
                    id=project_data["id"],
                    name=project_data["name"],
                    path=project_data["path"],
                    namespace=project_data["namespace"]["full_path"],
                    description=project_data.get("description"),
                    web_url=project_data["web_url"],
                    ssh_url_to_repo=project_data.get("ssh_url_to_repo"),
                    http_url_to_repo=project_data.get("http_url_to_repo"),
                    visibility=project_data["visibility"],
                    default_branch=project_data.get("default_branch"),
                )
                projects.append(project)

            return projects

        except Exception as e:
            raise MCPError(f"Failed to search repositories: {str(e)}")

    def get_tools(self) -> Dict[str, Any]:
        """Return dictionary of available tools for pydantic-ai integration."""
        return {
            "gitlab_list_projects": self,
            "gitlab_get_project": self,
            "gitlab_list_issues": self,
            "gitlab_create_issue": self,
            "gitlab_list_merge_requests": self,
            "gitlab_create_merge_request": self,
            "gitlab_list_pipelines": self,
            "gitlab_get_file_contents": self,
            "gitlab_search_repositories": self,
        }

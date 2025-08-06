"""
Jira integration tool using MCP server.

This tool provides Jira operations by integrating with the mcp-atlassian
server (https://github.com/sooperset/mcp-atlassian), enabling agents to
interact with Jira APIs for issue tracking, project management, and more.
"""

import json
import logging
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class JiraConfig(BaseModel):
    """Configuration for Jira MCP integration."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Authentication
    api_token: str = Field(..., description="Jira API token")
    email: str = Field(..., description="Jira user email")
    server_url: str = Field(..., description="Jira server URL")

    # MCP Server Configuration
    read_only_mode: bool = Field(default=False, description="Restrict to read-only operations")

    # Feature toggles
    enable_issue_transitions: bool = Field(default=True, description="Enable issue state transitions")
    enable_comments: bool = Field(default=True, description="Enable comment operations")
    enable_attachments: bool = Field(default=True, description="Enable attachment operations")

    # Transport and connection settings
    transport_mode: str = Field(default="stdio", description="MCP transport mode (stdio, sse, streamable-http)")
    host: str = Field(default="127.0.0.1", description="Server host")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")

    # Filtering and limits
    max_search_results: int = Field(default=50, description="Maximum search results")
    default_project_filter: Optional[str] = Field(default=None, description="Default project filter")

    # Proxy settings
    http_proxy: Optional[str] = Field(default=None, description="HTTP proxy URL")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS proxy URL")
    no_proxy: str = Field(default="localhost,127.0.0.1", description="Proxy exclusions")


class JiraIssue(BaseModel):
    """Jira issue information."""

    key: str = Field(..., description="Issue key (e.g., PROJ-123)")
    id: str = Field(..., description="Issue ID")
    summary: str = Field(..., description="Issue summary")
    description: Optional[str] = Field(None, description="Issue description")
    status: str = Field(..., description="Issue status")
    priority: str = Field(..., description="Issue priority")
    assignee: Optional[Dict[str, Any]] = Field(None, description="Assignee information")
    reporter: Dict[str, Any] = Field(..., description="Reporter information")
    created: str = Field(..., description="Creation timestamp")
    updated: str = Field(..., description="Last update timestamp")
    project: Dict[str, Any] = Field(..., description="Project information")
    issue_type: Dict[str, Any] = Field(..., description="Issue type information")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    components: List[Dict[str, Any]] = Field(default_factory=list, description="Issue components")
    fix_versions: List[Dict[str, Any]] = Field(default_factory=list, description="Fix versions")


class JiraProject(BaseModel):
    """Jira project information."""

    key: str = Field(..., description="Project key")
    id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    project_type: str = Field(..., description="Project type")
    lead: Dict[str, Any] = Field(..., description="Project lead information")
    url: str = Field(..., description="Project URL")
    avatar_urls: Dict[str, str] = Field(..., description="Avatar URLs")


class JiraBoard(BaseModel):
    """Jira board information."""

    id: int = Field(..., description="Board ID")
    name: str = Field(..., description="Board name")
    type: str = Field(..., description="Board type (scrum, kanban)")
    location: Dict[str, Any] = Field(..., description="Board location information")


class JiraComment(BaseModel):
    """Jira comment information."""

    id: str = Field(..., description="Comment ID")
    body: str = Field(..., description="Comment body")
    author: Dict[str, Any] = Field(..., description="Comment author")
    created: str = Field(..., description="Creation timestamp")
    updated: str = Field(..., description="Last update timestamp")


class MCPError(Exception):
    """Exception raised when MCP server communication fails."""

    pass


class JiraTool:
    """Jira integration tool using MCP server communication."""

    def __init__(self, config: Optional[JiraConfig] = None):
        self.config = config or JiraConfig(api_token="", email="", server_url="")
        self._validate_config()

    def _validate_config(self):
        """Validate the configuration."""
        # Allow empty credentials for initialization purposes (read-only mode)
        if not self.config.api_token and not self.config.read_only_mode:
            raise ValueError("Jira API token is required for non-read-only mode")

        if not self.config.email and not self.config.read_only_mode:
            raise ValueError("Jira user email is required for non-read-only mode")

        if not self.config.server_url:
            raise ValueError("Jira server URL is required")

    async def _call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on the mcp-atlassian server.

        This method handles the MCP communication protocol to invoke
        tools on the mcp-atlassian server.

        Args:
            tool_name: Name of the MCP tool to call
            parameters: Parameters to pass to the tool

        Returns:
            Dictionary containing the tool response

        Raises:
            MCPError: If MCP communication fails
        """
        # Check if we have valid configuration for MCP calls
        if not self.config.api_token:
            raise MCPError("Jira API token is required for MCP operations")

        # TODO: Implement actual MCP client communication
        # For now, this is a placeholder that simulates the MCP protocol

        logger.debug(f"Calling MCP tool: {tool_name} with parameters: {parameters}")

        # This would be replaced with actual MCP client implementation
        # using the Model Context Protocol to communicate with the mcp-atlassian server

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

    async def get_issue(self, issue_key: str) -> JiraIssue:
        """
        Get details of a specific Jira issue.

        Args:
            issue_key: Issue key (e.g., PROJ-123)

        Returns:
            JiraIssue object with issue details
        """
        parameters = {"issue_key": issue_key}

        try:
            response = await self._call_mcp_tool("get_issue", parameters)
            issue_data = response["issue"]

            return JiraIssue(
                key=issue_data["key"],
                id=issue_data["id"],
                summary=issue_data["fields"]["summary"],
                description=issue_data["fields"].get("description"),
                status=issue_data["fields"]["status"]["name"],
                priority=issue_data["fields"]["priority"]["name"],
                assignee=issue_data["fields"].get("assignee"),
                reporter=issue_data["fields"]["reporter"],
                created=issue_data["fields"]["created"],
                updated=issue_data["fields"]["updated"],
                project=issue_data["fields"]["project"],
                issue_type=issue_data["fields"]["issuetype"],
                labels=issue_data["fields"].get("labels", []),
                components=issue_data["fields"].get("components", []),
                fix_versions=issue_data["fields"].get("fixVersions", []),
            )

        except Exception as e:
            raise MCPError(f"Failed to get issue {issue_key}: {str(e)}")

    async def search_issues(
        self,
        jql: str,
        max_results: Optional[int] = None,
        start_at: int = 0,
        expand: Optional[List[str]] = None,
    ) -> List[JiraIssue]:
        """
        Search for Jira issues using JQL (Jira Query Language).

        Args:
            jql: JQL query string
            max_results: Maximum number of results to return
            start_at: Starting index for pagination
            expand: List of fields to expand

        Returns:
            List of JiraIssue objects matching the search
        """
        parameters = {
            "jql": jql,
            "start_at": start_at,
            "max_results": max_results or self.config.max_search_results,
        }

        if expand:
            parameters["expand"] = expand

        try:
            response = await self._call_mcp_tool("search_issues", parameters)
            issues = []

            for issue_data in response.get("issues", []):
                issue = JiraIssue(
                    key=issue_data["key"],
                    id=issue_data["id"],
                    summary=issue_data["fields"]["summary"],
                    description=issue_data["fields"].get("description"),
                    status=issue_data["fields"]["status"]["name"],
                    priority=issue_data["fields"]["priority"]["name"],
                    assignee=issue_data["fields"].get("assignee"),
                    reporter=issue_data["fields"]["reporter"],
                    created=issue_data["fields"]["created"],
                    updated=issue_data["fields"]["updated"],
                    project=issue_data["fields"]["project"],
                    issue_type=issue_data["fields"]["issuetype"],
                    labels=issue_data["fields"].get("labels", []),
                    components=issue_data["fields"].get("components", []),
                    fix_versions=issue_data["fields"].get("fixVersions", []),
                )
                issues.append(issue)

            return issues

        except Exception as e:
            raise MCPError(f"Failed to search issues with JQL '{jql}': {str(e)}")

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        components: Optional[List[str]] = None,
    ) -> JiraIssue:
        """
        Create a new Jira issue.

        Args:
            project_key: Project key where to create the issue
            summary: Issue summary
            issue_type: Issue type (e.g., Task, Bug, Story)
            description: Optional issue description
            assignee: Optional assignee username or account ID
            priority: Optional priority name
            labels: Optional list of labels
            components: Optional list of component names

        Returns:
            JiraIssue object representing the created issue
        """
        if self.config.read_only_mode:
            raise MCPError("Cannot create issue: read-only mode is enabled")

        parameters = {
            "project_key": project_key,
            "summary": summary,
            "issue_type": issue_type,
        }

        if description:
            parameters["description"] = description
        if assignee:
            parameters["assignee"] = assignee
        if priority:
            parameters["priority"] = priority
        if labels:
            parameters["labels"] = ",".join(labels)
        if components:
            parameters["components"] = ",".join(components)

        try:
            response = await self._call_mcp_tool("create_issue", parameters)
            issue_data = response["issue"]

            return JiraIssue(
                key=issue_data["key"],
                id=issue_data["id"],
                summary=issue_data["fields"]["summary"],
                description=issue_data["fields"].get("description"),
                status=issue_data["fields"]["status"]["name"],
                priority=issue_data["fields"]["priority"]["name"],
                assignee=issue_data["fields"].get("assignee"),
                reporter=issue_data["fields"]["reporter"],
                created=issue_data["fields"]["created"],
                updated=issue_data["fields"]["updated"],
                project=issue_data["fields"]["project"],
                issue_type=issue_data["fields"]["issuetype"],
                labels=issue_data["fields"].get("labels", []),
                components=issue_data["fields"].get("components", []),
                fix_versions=issue_data["fields"].get("fixVersions", []),
            )

        except Exception as e:
            raise MCPError(f"Failed to create issue in project {project_key}: {str(e)}")

    async def update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> JiraIssue:
        """
        Update an existing Jira issue.

        Args:
            issue_key: Issue key to update
            summary: Optional new summary
            description: Optional new description
            assignee: Optional new assignee
            priority: Optional new priority
            labels: Optional new labels

        Returns:
            Updated JiraIssue object
        """
        if self.config.read_only_mode:
            raise MCPError("Cannot update issue: read-only mode is enabled")

        parameters = {"issue_key": issue_key}

        if summary is not None:
            parameters["summary"] = summary
        if description is not None:
            parameters["description"] = description
        if assignee is not None:
            parameters["assignee"] = assignee
        if priority is not None:
            parameters["priority"] = priority
        if labels is not None:
            parameters["labels"] = ",".join(labels)

        try:
            await self._call_mcp_tool("update_issue", parameters)
            # Return the updated issue
            return await self.get_issue(issue_key)

        except Exception as e:
            raise MCPError(f"Failed to update issue {issue_key}: {str(e)}")

    async def transition_issue(self, issue_key: str, transition_id: str) -> JiraIssue:
        """
        Transition a Jira issue to a new status.

        Args:
            issue_key: Issue key to transition
            transition_id: Transition ID or name

        Returns:
            Updated JiraIssue object after transition
        """
        if self.config.read_only_mode:
            raise MCPError("Cannot transition issue: read-only mode is enabled")

        if not self.config.enable_issue_transitions:
            raise MCPError("Issue transitions are disabled")

        parameters = {"issue_key": issue_key, "transition_id": transition_id}

        try:
            await self._call_mcp_tool("transition_issue", parameters)
            # Return the updated issue
            return await self.get_issue(issue_key)

        except Exception as e:
            raise MCPError(f"Failed to transition issue {issue_key}: {str(e)}")

    async def add_comment(self, issue_key: str, body: str) -> JiraComment:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Issue key to comment on
            body: Comment text

        Returns:
            JiraComment object representing the created comment
        """
        if self.config.read_only_mode:
            raise MCPError("Cannot add comment: read-only mode is enabled")

        if not self.config.enable_comments:
            raise MCPError("Comments are disabled")

        parameters = {"issue_key": issue_key, "body": body}

        try:
            response = await self._call_mcp_tool("add_comment", parameters)
            comment_data = response["comment"]

            return JiraComment(
                id=comment_data["id"],
                body=comment_data["body"],
                author=comment_data["author"],
                created=comment_data["created"],
                updated=comment_data["updated"],
            )

        except Exception as e:
            raise MCPError(f"Failed to add comment to issue {issue_key}: {str(e)}")

    async def get_projects(self, expand: Optional[List[str]] = None) -> List[JiraProject]:
        """
        Get list of Jira projects accessible to the authenticated user.

        Args:
            expand: Optional list of fields to expand

        Returns:
            List of JiraProject objects
        """
        parameters = {}
        if expand:
            parameters["expand"] = expand

        try:
            response = await self._call_mcp_tool("get_projects", parameters)
            projects = []

            for project_data in response.get("projects", []):
                project = JiraProject(
                    key=project_data["key"],
                    id=project_data["id"],
                    name=project_data["name"],
                    description=project_data.get("description"),
                    project_type=project_data["projectTypeKey"],
                    lead=project_data["lead"],
                    url=project_data["self"],
                    avatar_urls=project_data["avatarUrls"],
                )
                projects.append(project)

            return projects

        except Exception as e:
            raise MCPError(f"Failed to get projects: {str(e)}")

    async def get_boards(self, project_key: Optional[str] = None) -> List[JiraBoard]:
        """
        Get list of Jira boards.

        Args:
            project_key: Optional project key to filter boards

        Returns:
            List of JiraBoard objects
        """
        parameters = {}
        if project_key:
            parameters["project_key"] = project_key

        try:
            response = await self._call_mcp_tool("get_boards", parameters)
            boards = []

            for board_data in response.get("boards", []):
                board = JiraBoard(
                    id=board_data["id"],
                    name=board_data["name"],
                    type=board_data["type"],
                    location=board_data["location"],
                )
                boards.append(board)

            return boards

        except Exception as e:
            raise MCPError(f"Failed to get boards: {str(e)}")

    def get_tools(self) -> Dict[str, Any]:
        """Return dictionary of available tools for pydantic-ai integration."""
        return {
            "jira_get_issue": self,
            "jira_search_issues": self,
            "jira_create_issue": self,
            "jira_update_issue": self,
            "jira_transition_issue": self,
            "jira_add_comment": self,
            "jira_get_projects": self,
            "jira_get_boards": self,
        }

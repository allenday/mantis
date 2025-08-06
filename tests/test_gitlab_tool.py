"""
Tests for GitLabTool integration.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from mantis.tools import GitLabTool, GitLabConfig, GitLabProject, GitLabIssue, GitLabMergeRequest, GitLabPipeline, GitLabMCPError


class TestGitLabConfig:
    """Test cases for GitLabConfig."""

    def test_gitlab_config_creation(self):
        """Test GitLabConfig creation with required fields."""
        config = GitLabConfig(personal_access_token="test_token")
        
        assert config.personal_access_token == "test_token"
        assert config.api_url == "https://gitlab.com/api/v4"
        assert config.read_only_mode == False
        assert config.enable_wiki_api == True
        assert config.enable_milestone_api == True
        assert config.enable_pipeline_api == True
        assert config.transport_mode == "stdio"
        assert config.host == "127.0.0.1"
        assert config.timeout == 30.0

    def test_gitlab_config_custom_values(self):
        """Test GitLabConfig with custom values."""
        config = GitLabConfig(
            personal_access_token="custom_token",
            api_url="https://gitlab.example.com/api/v4",
            read_only_mode=True,
            enable_wiki_api=False,
            transport_mode="sse",
            timeout=60.0
        )
        
        assert config.personal_access_token == "custom_token"
        assert config.api_url == "https://gitlab.example.com/api/v4"
        assert config.read_only_mode == True
        assert config.enable_wiki_api == False
        assert config.transport_mode == "sse"
        assert config.timeout == 60.0


class TestGitLabModels:
    """Test cases for GitLab data models."""

    def test_gitlab_project_model(self):
        """Test GitLabProject model validation."""
        project = GitLabProject(
            id=123,
            name="test-project",
            path="test-project",
            namespace="user/test-project",
            web_url="https://gitlab.com/user/test-project",
            visibility="private"
        )
        
        assert project.id == 123
        assert project.name == "test-project"
        assert project.path == "test-project"
        assert project.namespace == "user/test-project"
        assert project.web_url == "https://gitlab.com/user/test-project"
        assert project.visibility == "private"

    def test_gitlab_issue_model(self):
        """Test GitLabIssue model validation."""
        issue = GitLabIssue(
            id=456,
            iid=1,
            title="Test Issue",
            state="opened",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            author={"name": "Test User", "username": "testuser"},
            web_url="https://gitlab.com/user/project/-/issues/1"
        )
        
        assert issue.id == 456
        assert issue.iid == 1
        assert issue.title == "Test Issue"
        assert issue.state == "opened"
        assert issue.author["username"] == "testuser"

    def test_gitlab_merge_request_model(self):
        """Test GitLabMergeRequest model validation."""
        mr = GitLabMergeRequest(
            id=789,
            iid=2,
            title="Test MR",
            state="opened",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z",
            author={"name": "Test User", "username": "testuser"},
            source_branch="feature-branch",
            target_branch="main",
            web_url="https://gitlab.com/user/project/-/merge_requests/2",
            merge_status="can_be_merged"
        )
        
        assert mr.id == 789
        assert mr.iid == 2
        assert mr.title == "Test MR"
        assert mr.source_branch == "feature-branch"
        assert mr.target_branch == "main"
        assert mr.merge_status == "can_be_merged"

    def test_gitlab_pipeline_model(self):
        """Test GitLabPipeline model validation."""
        pipeline = GitLabPipeline(
            id=101112,
            status="success",
            ref="main",
            sha="abc123def456",
            web_url="https://gitlab.com/user/project/-/pipelines/101112",
            created_at="2023-01-01T00:00:00Z",
            updated_at="2023-01-01T00:00:00Z"
        )
        
        assert pipeline.id == 101112
        assert pipeline.status == "success"
        assert pipeline.ref == "main"
        assert pipeline.sha == "abc123def456"


class TestGitLabTool:
    """Test cases for GitLabTool."""

    def test_gitlab_tool_initialization(self):
        """Test GitLabTool initialization."""
        config = GitLabConfig(personal_access_token="test_token")
        tool = GitLabTool(config)
        
        assert tool.config.personal_access_token == "test_token"

    def test_gitlab_tool_initialization_without_config(self):
        """Test GitLabTool initialization without config should fail."""
        with pytest.raises(ValueError, match="GitLab personal access token is required"):
            GitLabTool()

    def test_gitlab_tool_validation_empty_token(self):
        """Test GitLabTool validation with empty token."""
        config = GitLabConfig(personal_access_token="")
        with pytest.raises(ValueError, match="GitLab personal access token is required"):
            GitLabTool(config)

    def test_gitlab_tool_validation_empty_api_url(self):
        """Test GitLabTool validation with empty API URL."""
        config = GitLabConfig(personal_access_token="test_token", api_url="")
        with pytest.raises(ValueError, match="GitLab API URL is required"):
            GitLabTool(config)

    def test_get_tools_method(self):
        """Test get_tools method returns expected tools."""
        config = GitLabConfig(personal_access_token="test_token")
        tool = GitLabTool(config)
        
        tools = tool.get_tools()
        
        expected_tools = [
            "gitlab_list_projects", "gitlab_get_project", "gitlab_list_issues", "gitlab_create_issue",
            "gitlab_list_merge_requests", "gitlab_create_merge_request", "gitlab_list_pipelines",
            "gitlab_get_file_contents", "gitlab_search_repositories"
        ]
        
        assert set(tools.keys()) == set(expected_tools)
        # All tools should point to the GitLabTool instance
        for tool_name in expected_tools:
            assert tools[tool_name] == tool

    @pytest.mark.asyncio
    async def test_mcp_tool_call_placeholder(self):
        """Test _call_mcp_tool method raises GitLabMCPError (placeholder implementation)."""
        config = GitLabConfig(personal_access_token="test_token")
        tool = GitLabTool(config)
        
        with pytest.raises(GitLabMCPError, match="MCP server communication not yet implemented"):
            await tool._call_mcp_tool("test_tool", {"param": "value"})

    @pytest.mark.asyncio
    async def test_list_projects_mcp_error(self):
        """Test list_projects handles MCP communication error."""
        config = GitLabConfig(personal_access_token="test_token")
        tool = GitLabTool(config)
        
        with pytest.raises(GitLabMCPError, match="MCP server communication not yet implemented"):
            await tool.list_projects()

    @pytest.mark.asyncio
    async def test_create_issue_read_only_mode(self):
        """Test create_issue fails in read-only mode."""
        config = GitLabConfig(personal_access_token="test_token", read_only_mode=True)
        tool = GitLabTool(config)
        
        with pytest.raises(GitLabMCPError, match="Cannot create issue: read-only mode is enabled"):
            await tool.create_issue("project", "Test Issue")

    @pytest.mark.asyncio
    async def test_create_merge_request_read_only_mode(self):
        """Test create_merge_request fails in read-only mode."""
        config = GitLabConfig(personal_access_token="test_token", read_only_mode=True)
        tool = GitLabTool(config)
        
        with pytest.raises(GitLabMCPError, match="Cannot create merge request: read-only mode is enabled"):
            await tool.create_merge_request("project", "Test MR", "feature", "main")

    @pytest.mark.asyncio
    async def test_list_pipelines_disabled_api(self):
        """Test list_pipelines fails when pipeline API is disabled."""
        config = GitLabConfig(personal_access_token="test_token", enable_pipeline_api=False)
        tool = GitLabTool(config)
        
        with pytest.raises(GitLabMCPError, match="Pipeline API is disabled"):
            await tool.list_pipelines("project")

    @pytest.mark.asyncio
    @patch('mantis.tools.gitlab_integration.GitLabTool._call_mcp_tool')
    async def test_list_projects_success(self, mock_mcp_call):
        """Test successful list_projects call."""
        config = GitLabConfig(personal_access_token="test_token")
        tool = GitLabTool(config)
        
        # Mock successful MCP response
        mock_mcp_call.return_value = {
            "projects": [
                {
                    "id": 123,
                    "name": "test-project",
                    "path": "test-project",
                    "namespace": {"full_path": "user/test-project"},
                    "web_url": "https://gitlab.com/user/test-project",
                    "visibility": "private"
                }
            ]
        }
        
        projects = await tool.list_projects()
        
        assert len(projects) == 1
        assert projects[0].id == 123
        assert projects[0].name == "test-project"
        assert projects[0].namespace == "user/test-project"
        
        mock_mcp_call.assert_called_once_with("list_projects", {"per_page": 20})

    @pytest.mark.asyncio
    @patch('mantis.tools.gitlab_integration.GitLabTool._call_mcp_tool')
    async def test_list_projects_with_search(self, mock_mcp_call):
        """Test list_projects with search parameter."""
        config = GitLabConfig(personal_access_token="test_token")
        tool = GitLabTool(config)
        
        mock_mcp_call.return_value = {"projects": []}
        
        await tool.list_projects(search="test", limit=10)
        
        mock_mcp_call.assert_called_once_with("list_projects", {"per_page": 10, "search": "test"})

    @pytest.mark.asyncio
    @patch('mantis.tools.gitlab_integration.GitLabTool._call_mcp_tool')
    async def test_create_issue_success(self, mock_mcp_call):
        """Test successful create_issue call."""
        config = GitLabConfig(personal_access_token="test_token")
        tool = GitLabTool(config)
        
        # Mock successful MCP response
        mock_mcp_call.return_value = {
            "issue": {
                "id": 456,
                "iid": 1,
                "title": "Test Issue",
                "state": "opened",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z",
                "author": {"name": "Test User", "username": "testuser"},
                "web_url": "https://gitlab.com/user/project/-/issues/1",
                "labels": ["bug"]
            }
        }
        
        issue = await tool.create_issue(
            "project", 
            "Test Issue", 
            description="Test description",
            labels=["bug"],
            assignee_id=123
        )
        
        assert issue.id == 456
        assert issue.title == "Test Issue"
        assert issue.labels == ["bug"]
        
        expected_params = {
            "project_id": "project",
            "title": "Test Issue",
            "description": "Test description",
            "labels": "bug",
            "assignee_ids": [123]
        }
        mock_mcp_call.assert_called_once_with("create_issue", expected_params)


class TestDirectExecutorIntegration:
    """Test DirectExecutor integration with GitLabTool."""

    @patch('mantis.tools.GitLabConfig')
    @patch('mantis.tools.GitLabTool')
    def test_direct_executor_tool_initialization(self, mock_gitlab_tool, mock_gitlab_config):
        """Test DirectExecutor initializes GitLab tools."""
        from mantis.core.orchestrator import DirectExecutor
        
        # Mock GitLab tool to return expected tools
        mock_tool_instance = MagicMock()
        mock_tool_instance.get_tools.return_value = {
            "gitlab_list_projects": mock_tool_instance,
            "gitlab_get_project": mock_tool_instance,
            "gitlab_list_issues": mock_tool_instance,
            "gitlab_create_issue": mock_tool_instance,
            "gitlab_list_merge_requests": mock_tool_instance,
            "gitlab_create_merge_request": mock_tool_instance,
            "gitlab_list_pipelines": mock_tool_instance,
            "gitlab_get_file_contents": mock_tool_instance,
            "gitlab_search_repositories": mock_tool_instance,
        }
        mock_gitlab_tool.return_value = mock_tool_instance
        
        executor = DirectExecutor()
        tools = executor.get_available_tools()
        
        # Should have GitLab tools available
        expected_gitlab_tools = [
            "gitlab_list_projects", "gitlab_get_project", "gitlab_list_issues", "gitlab_create_issue",
            "gitlab_list_merge_requests", "gitlab_create_merge_request", "gitlab_list_pipelines",
            "gitlab_get_file_contents", "gitlab_search_repositories"
        ]
        
        for tool_name in expected_gitlab_tools:
            assert tool_name in tools

    def test_direct_executor_tool_initialization_failure(self):
        """Test DirectExecutor handles GitLab tool initialization failure gracefully."""
        from mantis.core.orchestrator import DirectExecutor
        from unittest.mock import patch
        
        # Mock GitLabTool at the point of import
        with patch('mantis.tools.gitlab_integration.GitLabTool') as mock_tool:
            # Make GitLabTool raise an exception during initialization
            mock_tool.side_effect = Exception("GitLab initialization failed")
            
            # Should not raise exception, just log warning
            executor = DirectExecutor()
            tools = executor.get_available_tools()
            
            # Should have other tools but no GitLab tools
            gitlab_tool_names = [
                "gitlab_list_projects", "gitlab_get_project", "gitlab_list_issues", "gitlab_create_issue",
                "gitlab_list_merge_requests", "gitlab_create_merge_request", "gitlab_list_pipelines",
                "gitlab_get_file_contents", "gitlab_search_repositories"
            ]
            
            # Verify no GitLab tools are registered
            for tool_name in gitlab_tool_names:
                assert tool_name not in tools
            
            # Should still have other tools (web_fetch, web_search, git_operations)
            assert len(tools) > 0
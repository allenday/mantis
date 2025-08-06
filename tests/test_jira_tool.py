"""
Tests for JiraTool integration.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from mantis.tools import JiraTool, JiraConfig, JiraIssue, JiraProject, JiraBoard, JiraComment, MCPError


class TestJiraConfig:
    """Test cases for JiraConfig."""

    def test_jira_config_creation(self):
        """Test JiraConfig creation with required fields."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        
        assert config.api_token == "test_token"
        assert config.email == "test@example.com"
        assert config.server_url == "https://test.atlassian.net"
        assert config.read_only_mode == False
        assert config.enable_issue_transitions == True
        assert config.enable_comments == True
        assert config.enable_attachments == True
        assert config.transport_mode == "stdio"
        assert config.host == "127.0.0.1"
        assert config.timeout == 30.0
        assert config.max_search_results == 50

    def test_jira_config_custom_values(self):
        """Test JiraConfig with custom values."""
        config = JiraConfig(
            api_token="custom_token",
            email="custom@example.com",
            server_url="https://custom.atlassian.net",
            read_only_mode=True,
            enable_comments=False,
            transport_mode="sse",
            timeout=60.0,
            max_search_results=100
        )
        
        assert config.api_token == "custom_token"
        assert config.email == "custom@example.com"
        assert config.server_url == "https://custom.atlassian.net"
        assert config.read_only_mode == True
        assert config.enable_comments == False
        assert config.transport_mode == "sse"
        assert config.timeout == 60.0
        assert config.max_search_results == 100


class TestJiraModels:
    """Test cases for Jira data models."""

    def test_jira_issue_model(self):
        """Test JiraIssue model validation."""
        issue = JiraIssue(
            key="TEST-123",
            id="10001",
            summary="Test Issue",
            status="Open",
            priority="High",
            reporter={"name": "Test User", "accountId": "123"},
            created="2023-01-01T00:00:00Z",
            updated="2023-01-01T00:00:00Z",
            project={"key": "TEST", "name": "Test Project"},
            issue_type={"name": "Task", "id": "1"}
        )
        
        assert issue.key == "TEST-123"
        assert issue.id == "10001"
        assert issue.summary == "Test Issue"
        assert issue.status == "Open"
        assert issue.priority == "High"
        assert issue.reporter["accountId"] == "123"

    def test_jira_project_model(self):
        """Test JiraProject model validation."""
        project = JiraProject(
            key="TEST",
            id="10000",
            name="Test Project",
            project_type="software",
            lead={"name": "Project Lead", "accountId": "123"},
            url="https://test.atlassian.net/projects/TEST",
            avatar_urls={"48x48": "https://test.atlassian.net/avatar.png"}
        )
        
        assert project.key == "TEST"
        assert project.id == "10000"
        assert project.name == "Test Project"
        assert project.project_type == "software"
        assert project.lead["accountId"] == "123"

    def test_jira_board_model(self):
        """Test JiraBoard model validation."""
        board = JiraBoard(
            id=1,
            name="Test Board",
            type="scrum",
            location={"projectKey": "TEST", "projectName": "Test Project"}
        )
        
        assert board.id == 1
        assert board.name == "Test Board"
        assert board.type == "scrum"
        assert board.location["projectKey"] == "TEST"

    def test_jira_comment_model(self):
        """Test JiraComment model validation."""
        comment = JiraComment(
            id="10001",
            body="This is a test comment",
            author={"name": "Test User", "accountId": "123"},
            created="2023-01-01T00:00:00Z",
            updated="2023-01-01T00:00:00Z"
        )
        
        assert comment.id == "10001"
        assert comment.body == "This is a test comment"
        assert comment.author["accountId"] == "123"


class TestJiraTool:
    """Test cases for JiraTool."""

    def test_jira_tool_initialization(self):
        """Test JiraTool initialization."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        tool = JiraTool(config)
        
        assert tool.config.api_token == "test_token"
        assert tool.config.email == "test@example.com"

    def test_jira_tool_initialization_without_config(self):
        """Test JiraTool initialization without config should fail."""
        with pytest.raises(ValueError, match="Jira API token is required"):
            JiraTool()

    def test_jira_tool_validation_empty_token(self):
        """Test JiraTool validation with empty token."""
        config = JiraConfig(
            api_token="",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        with pytest.raises(ValueError, match="Jira API token is required"):
            JiraTool(config)

    def test_jira_tool_validation_empty_email(self):
        """Test JiraTool validation with empty email."""
        config = JiraConfig(
            api_token="test_token",
            email="",
            server_url="https://test.atlassian.net"
        )
        with pytest.raises(ValueError, match="Jira user email is required"):
            JiraTool(config)

    def test_jira_tool_validation_empty_server_url(self):
        """Test JiraTool validation with empty server URL."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url=""
        )
        with pytest.raises(ValueError, match="Jira server URL is required"):
            JiraTool(config)

    def test_jira_tool_read_only_mode_validation(self):
        """Test JiraTool allows empty credentials in read-only mode."""
        config = JiraConfig(
            api_token="",
            email="",
            server_url="https://test.atlassian.net",
            read_only_mode=True
        )
        tool = JiraTool(config)  # Should not raise an error
        assert tool.config.read_only_mode == True

    def test_get_tools_method(self):
        """Test get_tools method returns expected tools."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        tool = JiraTool(config)
        
        tools = tool.get_tools()
        
        expected_tools = [
            "get_issue", "search_issues", "create_issue", "update_issue",
            "transition_issue", "add_comment", "get_projects", "get_boards"
        ]
        
        assert set(tools.keys()) == set(expected_tools)
        # All tools should point to the JiraTool instance
        for tool_name in expected_tools:
            assert tools[tool_name] == tool

    @pytest.mark.asyncio
    async def test_mcp_tool_call_placeholder(self):
        """Test _call_mcp_tool method raises MCPError (placeholder implementation)."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        tool = JiraTool(config)
        
        with pytest.raises(MCPError, match="MCP server communication not yet implemented"):
            await tool._call_mcp_tool("test_tool", {"param": "value"})

    @pytest.mark.asyncio
    async def test_get_issue_mcp_error(self):
        """Test get_issue handles MCP communication error."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        tool = JiraTool(config)
        
        with pytest.raises(MCPError, match="MCP server communication not yet implemented"):
            await tool.get_issue("TEST-123")

    @pytest.mark.asyncio
    async def test_create_issue_read_only_mode(self):
        """Test create_issue fails in read-only mode."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net",
            read_only_mode=True
        )
        tool = JiraTool(config)
        
        with pytest.raises(MCPError, match="Cannot create issue: read-only mode is enabled"):
            await tool.create_issue("TEST", "Test Issue")

    @pytest.mark.asyncio
    async def test_update_issue_read_only_mode(self):
        """Test update_issue fails in read-only mode."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net",
            read_only_mode=True
        )
        tool = JiraTool(config)
        
        with pytest.raises(MCPError, match="Cannot update issue: read-only mode is enabled"):
            await tool.update_issue("TEST-123", summary="Updated Summary")

    @pytest.mark.asyncio
    async def test_transition_issue_disabled(self):
        """Test transition_issue fails when transitions are disabled."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net",
            enable_issue_transitions=False
        )
        tool = JiraTool(config)
        
        with pytest.raises(MCPError, match="Issue transitions are disabled"):
            await tool.transition_issue("TEST-123", "Done")

    @pytest.mark.asyncio
    async def test_add_comment_disabled(self):
        """Test add_comment fails when comments are disabled."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net",
            enable_comments=False
        )
        tool = JiraTool(config)
        
        with pytest.raises(MCPError, match="Comments are disabled"):
            await tool.add_comment("TEST-123", "Test comment")

    @pytest.mark.asyncio
    @patch('mantis.tools.jira_integration.JiraTool._call_mcp_tool')
    async def test_get_issue_success(self, mock_mcp_call):
        """Test successful get_issue call."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        tool = JiraTool(config)
        
        # Mock successful MCP response
        mock_mcp_call.return_value = {
            "issue": {
                "key": "TEST-123",
                "id": "10001",
                "fields": {
                    "summary": "Test Issue",
                    "description": "Test description",
                    "status": {"name": "Open"},
                    "priority": {"name": "High"},
                    "assignee": {"name": "Test Assignee", "accountId": "456"},
                    "reporter": {"name": "Test Reporter", "accountId": "123"},
                    "created": "2023-01-01T00:00:00Z",
                    "updated": "2023-01-01T00:00:00Z",
                    "project": {"key": "TEST", "name": "Test Project"},
                    "issuetype": {"name": "Task", "id": "1"},
                    "labels": ["bug", "urgent"],
                    "components": [{"name": "Frontend"}],
                    "fixVersions": [{"name": "1.0.0"}]
                }
            }
        }
        
        issue = await tool.get_issue("TEST-123")
        
        assert issue.key == "TEST-123"
        assert issue.summary == "Test Issue"
        assert issue.description == "Test description"
        assert issue.status == "Open"
        assert issue.priority == "High"
        assert issue.labels == ["bug", "urgent"]
        
        mock_mcp_call.assert_called_once_with("get_issue", {"issue_key": "TEST-123"})

    @pytest.mark.asyncio
    @patch('mantis.tools.jira_integration.JiraTool._call_mcp_tool')
    async def test_search_issues_success(self, mock_mcp_call):
        """Test successful search_issues call."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        tool = JiraTool(config)
        
        # Mock successful MCP response
        mock_mcp_call.return_value = {
            "issues": [
                {
                    "key": "TEST-123",
                    "id": "10001",
                    "fields": {
                        "summary": "Test Issue",
                        "status": {"name": "Open"},
                        "priority": {"name": "High"},
                        "reporter": {"name": "Test Reporter", "accountId": "123"},
                        "created": "2023-01-01T00:00:00Z",
                        "updated": "2023-01-01T00:00:00Z",
                        "project": {"key": "TEST", "name": "Test Project"},
                        "issuetype": {"name": "Task", "id": "1"}
                    }
                }
            ]
        }
        
        issues = await tool.search_issues("project = TEST")
        
        assert len(issues) == 1
        assert issues[0].key == "TEST-123"
        assert issues[0].summary == "Test Issue"
        
        mock_mcp_call.assert_called_once_with("search_issues", {
            "jql": "project = TEST",
            "start_at": 0,
            "max_results": 50
        })

    @pytest.mark.asyncio
    @patch('mantis.tools.jira_integration.JiraTool._call_mcp_tool')
    async def test_create_issue_success(self, mock_mcp_call):
        """Test successful create_issue call."""
        config = JiraConfig(
            api_token="test_token",
            email="test@example.com",
            server_url="https://test.atlassian.net"
        )
        tool = JiraTool(config)
        
        # Mock successful MCP response
        mock_mcp_call.return_value = {
            "issue": {
                "key": "TEST-124",
                "id": "10002",
                "fields": {
                    "summary": "New Test Issue",
                    "description": "Test description",
                    "status": {"name": "Open"},
                    "priority": {"name": "Medium"},
                    "reporter": {"name": "Test Reporter", "accountId": "123"},
                    "created": "2023-01-01T00:00:00Z",
                    "updated": "2023-01-01T00:00:00Z",
                    "project": {"key": "TEST", "name": "Test Project"},
                    "issuetype": {"name": "Task", "id": "1"},
                    "labels": ["new"]
                }
            }
        }
        
        issue = await tool.create_issue(
            "TEST",
            "New Test Issue",
            description="Test description",
            priority="Medium",
            labels=["new"]
        )
        
        assert issue.key == "TEST-124"
        assert issue.summary == "New Test Issue"
        assert issue.description == "Test description"
        assert issue.labels == ["new"]
        
        expected_params = {
            "project_key": "TEST",
            "summary": "New Test Issue",
            "issue_type": "Task",
            "description": "Test description",
            "priority": "Medium",
            "labels": "new"
        }
        mock_mcp_call.assert_called_once_with("create_issue", expected_params)


class TestDirectExecutorIntegration:
    """Test DirectExecutor integration with JiraTool."""

    @patch('mantis.tools.JiraConfig')
    @patch('mantis.tools.JiraTool')
    def test_direct_executor_tool_initialization(self, mock_jira_tool, mock_jira_config):
        """Test DirectExecutor initializes Jira tools."""
        from mantis.core.orchestrator import DirectExecutor
        
        # Mock Jira tool to return expected tools
        mock_tool_instance = MagicMock()
        mock_tool_instance.get_tools.return_value = {
            "get_issue": mock_tool_instance,
            "search_issues": mock_tool_instance,
            "create_issue": mock_tool_instance,
            "update_issue": mock_tool_instance,
            "transition_issue": mock_tool_instance,
            "add_comment": mock_tool_instance,
            "get_projects": mock_tool_instance,
            "get_boards": mock_tool_instance,
        }
        mock_jira_tool.return_value = mock_tool_instance
        
        executor = DirectExecutor()
        tools = executor.get_available_tools()
        
        # Should have Jira tools available
        expected_jira_tools = [
            "get_issue", "search_issues", "create_issue", "update_issue",
            "transition_issue", "add_comment", "get_projects", "get_boards"
        ]
        
        for tool_name in expected_jira_tools:
            assert tool_name in tools

    def test_direct_executor_tool_initialization_failure(self):
        """Test DirectExecutor handles Jira tool initialization failure gracefully."""
        from mantis.core.orchestrator import DirectExecutor
        from unittest.mock import patch
        
        # Mock JiraTool at the point of import
        with patch('mantis.tools.jira_integration.JiraTool') as mock_tool:
            # Make JiraTool raise an exception during initialization
            mock_tool.side_effect = Exception("Jira initialization failed")
            
            # Should not raise exception, just log warning
            executor = DirectExecutor()
            tools = executor.get_available_tools()
            
            # Should have other tools but no Jira tools
            jira_tool_names = [
                "get_issue", "search_issues", "create_issue", "update_issue",
                "transition_issue", "add_comment", "get_projects", "get_boards"
            ]
            
            # Verify no Jira tools are registered
            for tool_name in jira_tool_names:
                assert tool_name not in tools
            
            # Should still have other tools (web_fetch, web_search, git_operations)
            assert len(tools) > 0
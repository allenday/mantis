"""
Tests for GitOperationsTool.

These tests verify the functionality, security controls, and integration
of the GitOperationsTool with git2md library.
"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from mantis.tools.git_operations import (
    GitOperationsTool,
    GitOperationsConfig,
    RepositoryInfo,
    CommitInfo,
    CodeMatch,
)


class TestGitOperationsConfig:
    """Test GitOperationsConfig model validation."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GitOperationsConfig()
        
        assert config.max_repo_size_mb == 100.0
        assert config.max_files == 1000
        assert config.allowed_schemes == ["https"]
        assert "localhost" in config.blocked_domains
        assert config.clone_timeout == 300.0
        assert config.temp_cleanup is True
        assert config.max_search_results == 50

    def test_custom_config(self):
        """Test custom configuration values."""
        config = GitOperationsConfig(
            max_repo_size_mb=50.0,
            max_files=500,
            allowed_schemes=["https", "ssh"],
            blocked_domains=["evil.com"],
            clone_timeout=120.0,
            temp_cleanup=False,
            max_search_results=25,
        )
        
        assert config.max_repo_size_mb == 50.0
        assert config.max_files == 500
        assert config.allowed_schemes == ["https", "ssh"]
        assert config.blocked_domains == ["evil.com"]
        assert config.clone_timeout == 120.0
        assert config.temp_cleanup is False
        assert config.max_search_results == 25


class TestGitOperationsTool:
    """Test GitOperationsTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create GitOperationsTool instance for testing."""
        config = GitOperationsConfig(
            max_repo_size_mb=10.0,  # Small for testing
            max_files=100,
            clone_timeout=30.0,
        )
        return GitOperationsTool(config)

    def test_initialization(self, tool):
        """Test tool initialization."""
        assert tool.config.max_repo_size_mb == 10.0
        assert tool.config.max_files == 100
        assert tool._temp_dirs == []

    def test_validate_repository_url_valid(self, tool):
        """Test URL validation with valid URLs."""
        valid_urls = [
            "https://github.com/user/repo.git",
            "https://gitlab.com/user/repo",
            "https://bitbucket.org/user/repo.git",
        ]
        
        for url in valid_urls:
            assert tool._validate_repository_url(url) is True

    def test_validate_repository_url_invalid_scheme(self, tool):
        """Test URL validation with invalid schemes."""
        invalid_urls = [
            "http://github.com/user/repo.git",  # HTTP not allowed
            "ftp://example.com/repo.git",
            "ssh://git@github.com/user/repo.git",  # SSH not in default allowed
        ]
        
        for url in invalid_urls:
            assert tool._validate_repository_url(url) is False

    def test_validate_repository_url_blocked_domains(self, tool):
        """Test URL validation with blocked domains."""
        blocked_urls = [
            "https://localhost/repo.git",
            "https://127.0.0.1/repo.git",
            "https://192.168.1.1/repo.git",
            "https://10.0.0.1/repo.git",
        ]
        
        for url in blocked_urls:
            assert tool._validate_repository_url(url) is False

    def test_validate_repository_url_malformed(self, tool):
        """Test URL validation with malformed URLs."""
        malformed_urls = [
            "not-a-url",
            "https://",
            "",
            "https://github.com",  # No path
        ]
        
        for url in malformed_urls:
            assert tool._validate_repository_url(url) is False

    def test_get_repo_name(self, tool):
        """Test repository name extraction."""
        test_cases = [
            ("https://github.com/user/repo.git", "repo"),
            ("https://gitlab.com/group/project", "project"),
            ("https://bitbucket.org/user/my-repo.git", "my-repo"),
            ("https://example.com/path/to/repository", "repository"),
        ]
        
        for url, expected_name in test_cases:
            assert tool._get_repo_name(url) == expected_name

    def test_get_repo_name_fallback(self, tool):
        """Test repository name extraction fallback."""
        # Test with invalid URL - the function returns the invalid URL as fallback
        assert tool._get_repo_name("invalid-url") == "invalid-url"

    @pytest.mark.asyncio
    @patch('mantis.tools.git_operations.asyncio.create_subprocess_exec')
    async def test_run_git_command_success(self, mock_subprocess, tool):
        """Test successful git command execution."""
        # Mock successful process
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"output", b""))
        mock_subprocess.return_value = mock_process
        
        result = await tool._run_git_command(["git", "status"])
        
        assert result == "output"
        mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    @patch('mantis.tools.git_operations.asyncio.create_subprocess_exec')
    async def test_run_git_command_failure(self, mock_subprocess, tool):
        """Test git command execution failure."""
        # Mock failed process
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"error message"))
        mock_subprocess.return_value = mock_process
        
        with pytest.raises(Exception, match="Git command failed"):
            await tool._run_git_command(["git", "invalid-command"])

    @pytest.mark.asyncio
    @patch('mantis.tools.git_operations.asyncio.create_subprocess_exec')
    async def test_run_git_command_timeout(self, mock_subprocess, tool):
        """Test git command timeout."""
        # Mock process that times out
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_subprocess.return_value = mock_process
        
        with pytest.raises(Exception, match="Git command timed out"):
            await tool._run_git_command(["git", "clone"], timeout=0.1)

    def test_get_directory_size(self, tool):
        """Test directory size calculation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            (temp_path / "file1.txt").write_text("hello world")  # 11 bytes
            (temp_path / "file2.txt").write_text("test")  # 4 bytes
            
            size_mb = tool._get_directory_size(temp_path)
            expected_size = 15 / (1024 * 1024)  # Convert to MB
            
            assert abs(size_mb - expected_size) < 0.001

    def test_count_files(self, tool):
        """Test file counting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files and directories
            (temp_path / "file1.txt").write_text("content")
            (temp_path / "file2.py").write_text("print('hello')")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file3.js").write_text("console.log('test')")
            
            count = tool._count_files(temp_path)
            assert count == 3

    def test_detect_languages(self, tool):
        """Test programming language detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create files with different extensions
            (temp_path / "script.py").write_text("print('python')")
            (temp_path / "app.js").write_text("console.log('js')")
            (temp_path / "style.css").write_text("body { margin: 0; }")
            (temp_path / "README.md").write_text("# Project")
            
            languages = tool._detect_languages(temp_path)
            
            assert "Python" in languages
            assert "JavaScript" in languages
            assert "CSS" in languages
            assert len(languages) == 3  # README.md doesn't have a mapped language

    @pytest.mark.asyncio
    @patch.object(GitOperationsTool, '_run_git_command')
    @patch('mantis.tools.git_operations.tempfile.mkdtemp')
    async def test_analyze_repository_success(self, mock_mkdtemp, mock_git_cmd, tool):
        """Test successful repository analysis."""
        # Setup mocks
        temp_dir = "/tmp/test_repo"
        mock_mkdtemp.return_value = temp_dir
        
        # Mock git command responses
        mock_git_cmd.side_effect = [
            None,  # git clone (no output expected)
            "main",  # git branch --show-current
            "abc123|Initial commit",  # git log
        ]
        
        # Mock file system operations
        with patch.object(tool, '_get_directory_size', return_value=5.0), \
             patch.object(tool, '_count_files', return_value=10), \
             patch.object(tool, '_detect_languages', return_value=["Python", "JavaScript"]):
            
            result = await tool.analyze_repository("https://github.com/user/repo.git")
            
            assert isinstance(result, RepositoryInfo)
            assert result.url == "https://github.com/user/repo.git"
            assert result.name == "repo"
            assert result.branch == "main"
            assert result.commit_hash == "abc123"
            assert result.commit_message == "Initial commit"
            assert result.file_count == 10
            assert result.size_mb == 5.0
            assert result.languages == ["Python", "JavaScript"]

    @pytest.mark.asyncio
    async def test_analyze_repository_invalid_url(self, tool):
        """Test repository analysis with invalid URL."""
        with pytest.raises(Exception, match="Invalid or blocked repository URL"):
            await tool.analyze_repository("http://localhost/repo.git")

    def test_cleanup_temp_dirs(self, tool):
        """Test temporary directory cleanup."""
        # Create a real temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        tool._temp_dirs.append(temp_dir)
        
        # Verify directory exists
        assert temp_dir.exists()
        
        # Cleanup
        tool._cleanup_temp_dirs()
        
        # Verify directory is removed and list is cleared
        assert not temp_dir.exists()
        assert tool._temp_dirs == []

    def test_get_tools(self, tool):
        """Test get_tools method returns correct tool mapping."""
        tools = tool.get_tools()
        
        expected_tools = [
            "analyze_repository",
            "extract_file_content", 
            "get_commit_history",
            "generate_documentation",
            "search_code",
        ]
        
        assert list(tools.keys()) == expected_tools
        
        # All values should be the tool instance
        for tool_func in tools.values():
            assert tool_func is tool


class TestRepositoryInfo:
    """Test RepositoryInfo model."""

    def test_repository_info_creation(self):
        """Test RepositoryInfo model creation."""
        repo_info = RepositoryInfo(
            url="https://github.com/user/repo.git",
            name="repo",
            branch="main",
            commit_hash="abc123",
            commit_message="Initial commit",
            file_count=100,
            size_mb=25.5,
            languages=["Python", "JavaScript"],
        )
        
        assert repo_info.url == "https://github.com/user/repo.git"
        assert repo_info.name == "repo"
        assert repo_info.branch == "main"
        assert repo_info.commit_hash == "abc123"
        assert repo_info.commit_message == "Initial commit"
        assert repo_info.file_count == 100
        assert repo_info.size_mb == 25.5
        assert repo_info.languages == ["Python", "JavaScript"]


class TestCommitInfo:
    """Test CommitInfo model."""

    def test_commit_info_creation(self):
        """Test CommitInfo model creation."""
        commit_info = CommitInfo(
            hash="abc123def456",
            author="John Doe",
            date="2024-01-15T10:30:00Z",
            message="Add new feature",
            files_changed=5,
        )
        
        assert commit_info.hash == "abc123def456"
        assert commit_info.author == "John Doe"
        assert commit_info.date == "2024-01-15T10:30:00Z"
        assert commit_info.message == "Add new feature"
        assert commit_info.files_changed == 5


class TestCodeMatch:
    """Test CodeMatch model."""

    def test_code_match_creation(self):
        """Test CodeMatch model creation."""
        code_match = CodeMatch(
            file_path="src/main.py",
            line_number=42,
            line_content="def analyze_repository(self, repo_url: str):",
            context_before=["    async def _run_git_command(self):", "        pass"],
            context_after=["        if not self._validate_repository_url(repo_url):"],
        )
        
        assert code_match.file_path == "src/main.py"
        assert code_match.line_number == 42
        assert code_match.line_content == "def analyze_repository(self, repo_url: str):"
        assert len(code_match.context_before) == 2
        assert len(code_match.context_after) == 1


class TestIntegration:
    """Integration tests for GitOperationsTool."""

    @pytest.fixture
    def tool(self):
        """Create tool for integration testing."""
        return GitOperationsTool()

    def test_tool_import_integration(self):
        """Test that tool can be imported and used in DirectExecutor."""
        from mantis.core.orchestrator import DirectExecutor
        
        executor = DirectExecutor()
        tools = executor.get_available_tools()
        
        assert "git_operations" in tools
        assert isinstance(tools["git_operations"], GitOperationsTool)

    def test_config_validation_integration(self):
        """Test configuration validation in realistic scenarios."""
        # Test production-like config
        prod_config = GitOperationsConfig(
            max_repo_size_mb=500.0,
            max_files=5000,
            allowed_schemes=["https"],
            blocked_domains=[
                "localhost", "127.0.0.1", "0.0.0.0",
                "192.168.", "10.", "172.",
                "internal.company.com",
            ],
            clone_timeout=600.0,
            temp_cleanup=True,
            max_search_results=100,
        )
        
        tool = GitOperationsTool(prod_config)
        
        # Test that production config is properly applied
        assert tool.config.max_repo_size_mb == 500.0
        assert tool.config.max_files == 5000
        assert "internal.company.com" in tool.config.blocked_domains
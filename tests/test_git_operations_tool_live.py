"""
Live integration tests for GitOperationsTool.
Tests against real repositories - fail fast if they don't work.
"""

import pytest
import tempfile
from pathlib import Path

from mantis.tools.git_operations import (
    GitOperationsTool,
    GitOperationsConfig,
)


class TestGitOperationsToolLive:
    """Live integration tests for GitOperationsTool."""

    @pytest.fixture
    def config(self):
        """Create secure test configuration."""
        return GitOperationsConfig(
            max_repo_size_mb=50.0,  # Smaller for tests
            max_files=500,
            allowed_schemes=["https"],
            blocked_domains=["localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10.", "172."],
            clone_timeout=30.0,
            temp_cleanup=True,
        )

    @pytest.mark.asyncio
    async def test_analyze_small_public_repo_live(self, config):
        """Test analyzing a small public repository - live data."""
        tool = GitOperationsTool(config)
        
        # Use a small, stable public repo for testing
        repo_url = "https://github.com/octocat/Hello-World.git"
        
        try:
            repo_info = await tool.analyze_repository(repo_url)
            
            assert repo_info.name == "Hello-World"
            assert repo_info.url == repo_url
            assert repo_info.branch is not None
            assert repo_info.size_mb > 0
            assert repo_info.file_count > 0
            assert repo_info.commit_hash is not None
            assert len(repo_info.commit_hash) >= 7  # At least short hash
            
        finally:
            # Cleanup is handled by temp_cleanup=True
            pass

    @pytest.mark.asyncio 
    async def test_analyze_nonexistent_repo_fails_fast(self, config):
        """Test that nonexistent repos fail fast."""
        tool = GitOperationsTool(config)
        
        with pytest.raises(Exception):  # Should raise an exception
            await tool.analyze_repository("https://github.com/this-repo-should-not-exist-12345/test.git")

    @pytest.mark.asyncio
    async def test_security_blocked_domains(self, config):
        """Test that blocked domains are rejected."""
        tool = GitOperationsTool(config)
        
        with pytest.raises(Exception):  # Should raise security exception
            await tool.analyze_repository("https://localhost/malicious-repo.git")

    @pytest.mark.asyncio
    async def test_security_non_https_blocked(self, config):
        """Test that non-HTTPS schemes are blocked."""
        tool = GitOperationsTool(config)
        
        with pytest.raises(Exception):  # Should raise security exception
            await tool.analyze_repository("git://github.com/octocat/Hello-World.git")

    @pytest.mark.asyncio
    async def test_large_repo_size_limit(self, config):
        """Test that large repos are rejected based on size limit."""
        # Set very small size limit for test
        config.max_repo_size_mb = 0.001  # 1KB limit
        
        tool = GitOperationsTool(config)
        
        with pytest.raises(Exception):  # Should raise size limit exception
            await tool.analyze_repository("https://github.com/octocat/Hello-World.git")
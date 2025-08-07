"""
Live integration tests for GitOperationsTool.
Tests against real repositories - fail fast if they don't work.
"""

import pytest
import os

from mantis.tools.git_operations import git_analyze_repository


class TestGitOperationsToolLive:
    """Live integration tests for git_analyze_repository function."""

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio
    async def test_analyze_small_public_repo_live(self):
        """Test analyzing a small public repository - live data."""
        # Use a small, stable public repo for testing
        repo_url = "https://github.com/octocat/Hello-World.git"
        
        result = await git_analyze_repository(repo_url)
        
        assert "error" not in result.lower()
        assert "failed" not in result.lower()
        assert "hello-world" in result.lower()
        assert len(result) > 50  # Should have substantial analysis

    @pytest.mark.skipif(not os.getenv('ANTHROPIC_API_KEY'), reason="ANTHROPIC_API_KEY not set")
    @pytest.mark.asyncio 
    async def test_analyze_nonexistent_repo_fails_fast(self):
        """Test that nonexistent repos fail fast."""
        result = await git_analyze_repository("https://github.com/this-repo-should-not-exist-12345/test.git")
        
        # Should return error message
        assert ("error" in result.lower() or "failed" in result.lower() or "not found" in result.lower())
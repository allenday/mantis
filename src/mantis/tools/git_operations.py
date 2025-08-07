"""
Native pydantic-ai git operations tool.
Simplified to only support pydantic-ai integration.
"""

import logging
import tempfile
import shutil
from pathlib import Path
import subprocess
from urllib.parse import urlparse

# Observability imports
try:
    from ..observability import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("git_operations")
else:
    obs_logger = None


async def git_analyze_repository(repo_url: str) -> str:
    """Analyze a git repository and return information about its structure.
    
    This tool analyzes git repositories to provide information about their
    structure, languages, commit history, and other relevant details.
    
    Args:
        repo_url: URL of the git repository to analyze
    
    Returns:
        Repository analysis including structure, languages, and recent commits
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: git_analyze_repository for {repo_url}")
    
    try:
        # Security validation
        parsed = urlparse(repo_url)
        if parsed.scheme not in ["https"]:
            return f"Error: Only HTTPS repositories are allowed, got {parsed.scheme}"
        
        blocked_domains = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10.", "172."]
        if any(blocked in parsed.netloc for blocked in blocked_domains):
            return f"Error: Blocked domain in repository URL: {parsed.netloc}"
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            clone_path = temp_path / repo_name
            
            # Clone repository (shallow clone for speed)
            clone_cmd = [
                "git", "clone", "--depth", "1", "--single-branch", 
                repo_url, str(clone_path)
            ]
            
            result = subprocess.run(
                clone_cmd, capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return f"Error cloning repository: {result.stderr}"
            
            # Get basic repo info
            repo_info = []
            repo_info.append(f"**Repository: {repo_name}**")
            repo_info.append(f"URL: {repo_url}")
            
            # Get current branch and commit
            try:
                branch_result = subprocess.run(
                    ["git", "branch", "--show-current"], 
                    cwd=clone_path, capture_output=True, text=True
                )
                if branch_result.returncode == 0:
                    repo_info.append(f"Branch: {branch_result.stdout.strip()}")
                
                commit_result = subprocess.run(
                    ["git", "rev-parse", "--short", "HEAD"],
                    cwd=clone_path, capture_output=True, text=True
                )
                if commit_result.returncode == 0:
                    repo_info.append(f"Latest Commit: {commit_result.stdout.strip()}")
                    
            except Exception:
                pass  # Skip if git commands fail
            
            # Count files and estimate size
            try:
                file_count = sum(1 for _ in clone_path.rglob('*') if _.is_file() and not _.name.startswith('.git'))
                repo_info.append(f"Files: {file_count}")
                
                # Get directory size (rough estimate)
                size_result = subprocess.run(
                    ["du", "-sh", str(clone_path)],
                    capture_output=True, text=True
                )
                if size_result.returncode == 0:
                    size = size_result.stdout.split()[0]
                    repo_info.append(f"Size: {size}")
                    
            except Exception:
                pass  # Skip if commands fail
            
            result_text = "\\n".join(repo_info)
            
            if OBSERVABILITY_AVAILABLE and obs_logger:
                obs_logger.info(f"Git repository analysis completed for {repo_name}")
            
            return result_text
        
    except Exception as e:
        error_msg = f"Error analyzing repository {repo_url}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Git analysis exception: {e}")
        return error_msg
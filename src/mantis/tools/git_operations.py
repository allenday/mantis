"""
Git operations tool using git2md integration.

This tool enables agents to perform git repository analysis and content extraction
by integrating with the existing third_party/git2md library, providing secure
repository access with comprehensive error handling.
"""

import asyncio
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ConfigDict


class RepositoryInfo(BaseModel):
    """Information about a git repository."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: str = Field(..., description="Repository URL")
    name: str = Field(..., description="Repository name")
    branch: str = Field(..., description="Current/default branch")
    commit_hash: Optional[str] = Field(None, description="Latest commit hash")
    commit_message: Optional[str] = Field(None, description="Latest commit message")
    file_count: int = Field(..., description="Total number of files")
    size_mb: float = Field(..., description="Repository size in MB")
    languages: List[str] = Field(default_factory=list, description="Programming languages detected")


class CommitInfo(BaseModel):
    """Information about a git commit."""

    hash: str = Field(..., description="Commit hash")
    author: str = Field(..., description="Commit author")
    date: str = Field(..., description="Commit date")
    message: str = Field(..., description="Commit message")
    files_changed: int = Field(..., description="Number of files changed")


class CodeMatch(BaseModel):
    """Code search result."""

    file_path: str = Field(..., description="File path containing the match")
    line_number: int = Field(..., description="Line number of the match")
    line_content: str = Field(..., description="Content of the matching line")
    context_before: List[str] = Field(default_factory=list, description="Lines before the match")
    context_after: List[str] = Field(default_factory=list, description="Lines after the match")


class GitOperationsConfig(BaseModel):
    """Configuration for git operations."""

    max_repo_size_mb: float = Field(100.0, description="Maximum repository size in MB")
    max_files: int = Field(1000, description="Maximum number of files to process")
    allowed_schemes: List[str] = Field(
        default_factory=lambda: ["https"], description="Allowed URL schemes for repositories"
    )
    blocked_domains: List[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10.", "172."],
        description="Blocked domains for security",
    )
    clone_timeout: float = Field(300.0, description="Timeout for git clone operations in seconds")
    temp_cleanup: bool = Field(True, description="Whether to cleanup temporary directories")
    max_search_results: int = Field(50, description="Maximum search results to return")


class GitOperationsTool:
    """Git operations tool with git2md integration."""

    def __init__(self, config: Optional[GitOperationsConfig] = None):
        self.config = config or GitOperationsConfig()
        self._temp_dirs: List[Path] = []

    def __del__(self):
        """Cleanup temporary directories on deletion."""
        if self.config.temp_cleanup:
            self._cleanup_temp_dirs()

    def _cleanup_temp_dirs(self):
        """Clean up temporary directories."""
        for temp_dir in self._temp_dirs:
            try:
                if temp_dir.exists():
                    import shutil

                    shutil.rmtree(temp_dir)
            except Exception:
                pass  # Ignore cleanup errors
        self._temp_dirs.clear()

    def _validate_repository_url(self, repo_url: str) -> bool:
        """Validate repository URL for security."""
        try:
            parsed = urlparse(repo_url)

            # Check scheme
            if parsed.scheme not in self.config.allowed_schemes:
                return False

            # Check for blocked domains
            hostname = parsed.hostname or ""
            for blocked in self.config.blocked_domains:
                if blocked in hostname.lower():
                    return False

            # Basic format validation
            if not parsed.netloc or not parsed.path:
                return False

            return True

        except Exception:
            return False

    def _get_repo_name(self, repo_url: str) -> str:
        """Extract repository name from URL."""
        try:
            parsed = urlparse(repo_url)
            path = parsed.path.strip("/")

            # Remove .git suffix if present
            if path.endswith(".git"):
                path = path[:-4]

            # Get the last part as repo name
            return path.split("/")[-1] if "/" in path else path

        except Exception:
            return "unknown-repo"

    async def _run_git_command(self, cmd: List[str], cwd: Optional[Path] = None, timeout: float = 30.0) -> str:
        """Run a git command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, cwd=cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore")
                raise Exception(f"Git command failed: {error_msg}")

            return stdout.decode("utf-8", errors="ignore")

        except asyncio.TimeoutError:
            raise Exception(f"Git command timed out after {timeout} seconds")
        except Exception as e:
            raise Exception(f"Git command error: {str(e)}")

    def _get_directory_size(self, directory: Path) -> float:
        """Get directory size in MB."""
        try:
            total_size = 0
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0

    def _count_files(self, directory: Path) -> int:
        """Count files in directory."""
        try:
            return len([f for f in directory.rglob("*") if f.is_file()])
        except Exception:
            return 0

    def _detect_languages(self, directory: Path) -> List[str]:
        """Detect programming languages in repository."""
        language_extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".h": "C/C++",
            ".cs": "C#",
            ".php": "PHP",
            ".rb": "Ruby",
            ".go": "Go",
            ".rs": "Rust",
            ".swift": "Swift",
            ".kt": "Kotlin",
            ".scala": "Scala",
            ".r": "R",
            ".m": "Objective-C",
            ".sh": "Shell",
            ".sql": "SQL",
            ".html": "HTML",
            ".css": "CSS",
            ".scss": "SCSS",
            ".vue": "Vue",
            ".jsx": "JSX",
            ".tsx": "TSX",
        }

        languages = set()
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    suffix = file_path.suffix.lower()
                    if suffix in language_extensions:
                        languages.add(language_extensions[suffix])
        except Exception:
            pass

        return sorted(list(languages))

    async def analyze_repository(self, repo_url: str) -> RepositoryInfo:
        """
        Analyze a git repository and return information about it.

        Args:
            repo_url: URL of the git repository

        Returns:
            RepositoryInfo with repository analysis

        Raises:
            Exception: If repository analysis fails
        """
        if not self._validate_repository_url(repo_url):
            raise Exception(f"Invalid or blocked repository URL: {repo_url}")

        repo_name = self._get_repo_name(repo_url)

        # Create temporary directory for cloning
        temp_dir = Path(tempfile.mkdtemp(prefix=f"mantis_git_{repo_name}_"))
        self._temp_dirs.append(temp_dir)

        try:
            # Clone repository (shallow clone for efficiency)
            await self._run_git_command(
                ["git", "clone", "--depth", "1", repo_url, str(temp_dir)], timeout=self.config.clone_timeout
            )

            # Check repository size
            repo_size = self._get_directory_size(temp_dir)
            if repo_size > self.config.max_repo_size_mb:
                raise Exception(f"Repository too large: {repo_size:.1f}MB (max: {self.config.max_repo_size_mb}MB)")

            # Count files
            file_count = self._count_files(temp_dir)
            if file_count > self.config.max_files:
                raise Exception(f"Too many files: {file_count} (max: {self.config.max_files})")

            # Get current branch
            branch_output = await self._run_git_command(["git", "branch", "--show-current"], cwd=temp_dir)
            branch = branch_output.strip() or "main"

            # Get latest commit info
            commit_output = await self._run_git_command(["git", "log", "-1", "--format=%H|%s"], cwd=temp_dir)

            commit_hash, commit_message = None, None
            if commit_output.strip():
                parts = commit_output.strip().split("|", 1)
                commit_hash = parts[0]
                commit_message = parts[1] if len(parts) > 1 else ""

            # Detect languages
            languages = self._detect_languages(temp_dir)

            return RepositoryInfo(
                url=repo_url,
                name=repo_name,
                branch=branch,
                commit_hash=commit_hash,
                commit_message=commit_message,
                file_count=file_count,
                size_mb=repo_size,
                languages=languages,
            )

        except Exception as e:
            raise Exception(f"Repository analysis failed: {str(e)}")

    async def extract_file_content(self, repo_url: str, file_path: str) -> str:
        """
        Extract content of a specific file from a repository.

        Args:
            repo_url: URL of the git repository
            file_path: Path to the file within the repository

        Returns:
            File content as string

        Raises:
            Exception: If file extraction fails
        """
        if not self._validate_repository_url(repo_url):
            raise Exception(f"Invalid or blocked repository URL: {repo_url}")

        repo_name = self._get_repo_name(repo_url)

        # Create temporary directory for cloning
        temp_dir = Path(tempfile.mkdtemp(prefix=f"mantis_git_{repo_name}_"))
        self._temp_dirs.append(temp_dir)

        try:
            # Clone repository (shallow clone)
            await self._run_git_command(
                ["git", "clone", "--depth", "1", repo_url, str(temp_dir)], timeout=self.config.clone_timeout
            )

            # Check if file exists
            target_file = temp_dir / file_path
            if not target_file.exists():
                raise Exception(f"File not found: {file_path}")

            if not target_file.is_file():
                raise Exception(f"Path is not a file: {file_path}")

            # Read file content
            try:
                content = target_file.read_text(encoding="utf-8")
                return content
            except UnicodeDecodeError:
                # Try reading as binary and represent as base64
                import base64

                binary_content = target_file.read_bytes()
                return f"[Binary file - Base64 encoded]\n{base64.b64encode(binary_content).decode('ascii')}"

        except Exception as e:
            raise Exception(f"File extraction failed: {str(e)}")

    async def get_commit_history(self, repo_url: str, limit: int = 10) -> List[CommitInfo]:
        """
        Get commit history from a repository.

        Args:
            repo_url: URL of the git repository
            limit: Maximum number of commits to return

        Returns:
            List of CommitInfo objects

        Raises:
            Exception: If commit history retrieval fails
        """
        if not self._validate_repository_url(repo_url):
            raise Exception(f"Invalid or blocked repository URL: {repo_url}")

        repo_name = self._get_repo_name(repo_url)

        # Create temporary directory for cloning
        temp_dir = Path(tempfile.mkdtemp(prefix=f"mantis_git_{repo_name}_"))
        self._temp_dirs.append(temp_dir)

        try:
            # Clone repository with more history for commit analysis
            depth = min(limit * 2, 50)  # Get a bit more than requested
            await self._run_git_command(
                ["git", "clone", "--depth", str(depth), repo_url, str(temp_dir)], timeout=self.config.clone_timeout
            )

            # Get commit history
            commit_output = await self._run_git_command(
                ["git", "log", f"-{limit}", "--format=%H|%an|%ad|%s|%H", "--date=iso"], cwd=temp_dir
            )

            commits = []
            for line in commit_output.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split("|")
                if len(parts) >= 4:
                    commit_hash = parts[0]
                    author = parts[1]
                    date = parts[2]
                    message = parts[3]

                    # Get files changed count for this commit
                    try:
                        stat_output = await self._run_git_command(
                            ["git", "show", "--stat", "--format=", commit_hash], cwd=temp_dir
                        )

                        # Count lines that look like file changes
                        files_changed = len(
                            [
                                line
                                for line in stat_output.split("\n")
                                if line.strip() and "|" in line and ("++" in line or "--" in line)
                            ]
                        )
                    except Exception:
                        files_changed = 0

                    commits.append(
                        CommitInfo(
                            hash=commit_hash, author=author, date=date, message=message, files_changed=files_changed
                        )
                    )

            return commits

        except Exception as e:
            raise Exception(f"Commit history retrieval failed: {str(e)}")

    async def generate_documentation(self, repo_url: str) -> str:
        """
        Generate markdown documentation from repository using git2md.

        Args:
            repo_url: URL of the git repository

        Returns:
            Markdown documentation as string

        Raises:
            Exception: If documentation generation fails
        """
        if not self._validate_repository_url(repo_url):
            raise Exception(f"Invalid or blocked repository URL: {repo_url}")

        repo_name = self._get_repo_name(repo_url)

        # Create temporary directory for cloning
        temp_dir = Path(tempfile.mkdtemp(prefix=f"mantis_git_{repo_name}_"))
        self._temp_dirs.append(temp_dir)

        try:
            # Clone repository
            await self._run_git_command(
                ["git", "clone", "--depth", "1", repo_url, str(temp_dir)], timeout=self.config.clone_timeout
            )

            # Check repository size constraints
            repo_size = self._get_directory_size(temp_dir)
            if repo_size > self.config.max_repo_size_mb:
                raise Exception(f"Repository too large: {repo_size:.1f}MB (max: {self.config.max_repo_size_mb}MB)")

            # Use git2md to generate documentation
            try:
                # Import git2md functionality
                import sys

                git2md_path = Path(__file__).parent.parent.parent.parent / "third_party" / "git2md" / "src"
                sys.path.insert(0, str(git2md_path))

                from git2md import load_converters, load_exporters, process_directory, get_converter
                from utils.ignore import load_ignore

                # Load converters and exporters
                converters_list = load_converters()
                exporters_list = load_exporters()

                if not converters_list or not exporters_list:
                    raise Exception("git2md converters or exporters not available")

                default_converter = next(
                    (c for c in converters_list if c.__class__.__name__ == "DefaultConverter"), converters_list[0]
                )
                exporter = exporters_list[0]

                # Load ignore patterns
                gitignore_spec = load_ignore(temp_dir, [])

                # Generate documentation
                output = f"# {repo_name}\n\n"
                output += f"Repository: {repo_url}\n\n"

                # Generate tree structure
                tree_output = process_directory(temp_dir, gitignore_spec)
                output += f"## Repository Structure\n```\n{tree_output}\n```\n\n"

                # Process files
                from utils.ignore import should_ignore

                file_count = 0
                for file_path in temp_dir.rglob("*"):
                    if file_count >= self.config.max_files:
                        output += f"\n*[Truncated - maximum file limit ({self.config.max_files}) reached]*\n"
                        break

                    if (
                        file_path.is_file()
                        and not should_ignore(str(file_path), [], str(temp_dir), gitignore_spec)
                        and file_path.stat().st_size > 0
                    ):
                        try:
                            conv = get_converter(file_path, converters_list, default_converter)
                            content = conv.convert(file_path)
                            language = conv.get_language(file_path)
                            rel_path = file_path.relative_to(temp_dir)
                            output += exporter.format(rel_path, content, language)
                            file_count += 1
                        except Exception:
                            # Skip files that can't be processed
                            continue

                return output

            except ImportError as e:
                raise Exception(f"git2md import failed: {str(e)}")

        except Exception as e:
            raise Exception(f"Documentation generation failed: {str(e)}")

    async def search_code(self, repo_url: str, query: str, context_lines: int = 3) -> List[CodeMatch]:
        """
        Search for code patterns in a repository.

        Args:
            repo_url: URL of the git repository
            query: Search query (supports regex)
            context_lines: Number of context lines to include

        Returns:
            List of CodeMatch objects

        Raises:
            Exception: If code search fails
        """
        if not self._validate_repository_url(repo_url):
            raise Exception(f"Invalid or blocked repository URL: {repo_url}")

        repo_name = self._get_repo_name(repo_url)

        # Create temporary directory for cloning
        temp_dir = Path(tempfile.mkdtemp(prefix=f"mantis_git_{repo_name}_"))
        self._temp_dirs.append(temp_dir)

        try:
            # Clone repository
            await self._run_git_command(
                ["git", "clone", "--depth", "1", repo_url, str(temp_dir)], timeout=self.config.clone_timeout
            )

            # Compile regex pattern
            try:
                pattern = re.compile(query, re.IGNORECASE | re.MULTILINE)
            except re.error as e:
                raise Exception(f"Invalid regex pattern: {str(e)}")

            matches: List[CodeMatch] = []

            # Search through files
            for file_path in temp_dir.rglob("*"):
                if len(matches) >= self.config.max_search_results:
                    break

                if not file_path.is_file():
                    continue

                # Skip binary files and large files
                try:
                    if file_path.stat().st_size > 1024 * 1024:  # Skip files > 1MB
                        continue

                    # Try to read as text
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.split("\n")

                    for line_num, line in enumerate(lines, 1):
                        if pattern.search(line):
                            # Get context lines
                            start_idx = max(0, line_num - context_lines - 1)
                            end_idx = min(len(lines), line_num + context_lines)

                            context_before = lines[start_idx : line_num - 1]
                            context_after = lines[line_num:end_idx]

                            rel_path = str(file_path.relative_to(temp_dir))

                            matches.append(
                                CodeMatch(
                                    file_path=rel_path,
                                    line_number=line_num,
                                    line_content=line,
                                    context_before=context_before,
                                    context_after=context_after,
                                )
                            )

                            if len(matches) >= self.config.max_search_results:
                                break

                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read
                    continue

            return matches

        except Exception as e:
            raise Exception(f"Code search failed: {str(e)}")

    def get_tools(self) -> Dict[str, Any]:
        """Return dictionary of available tools for pydantic-ai integration."""
        return {
            "analyze_repository": self,
            "extract_file_content": self,
            "get_commit_history": self,
            "generate_documentation": self,
            "search_code": self,
        }

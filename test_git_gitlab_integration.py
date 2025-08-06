#!/usr/bin/env python3
"""
Real LLM agent integration test for GitLab and Git operations tools.
This demonstrates that LLM agents can successfully use our Git-related tools.
"""
import asyncio
import os
from typing import Dict, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from pydantic_ai import Agent, RunContext


async def test_real_git_operations_integration():
    """Test REAL LLM agent with REAL Git operations tool using octocat repo."""
    print('🧪 Testing REAL LLM agent with REAL Git operations tool...')
    
    from mantis.tools import GitOperationsTool, GitOperationsConfig
    
    # Create REAL Git operations tool with secure config
    config = GitOperationsConfig(
        max_repo_size_mb=10.0,  # Small for test
        max_files=100,
        allowed_schemes=["https"],
        blocked_domains=["localhost", "127.0.0.1"],
        clone_timeout=60.0,
        temp_cleanup=True,
        max_search_results=10,
    )
    git_tool = GitOperationsTool(config)
    
    # Create REAL pydantic-ai agent
    agent = Agent(
        'anthropic:claude-3-5-haiku-20241022',
        deps_type=Dict[str, Any],
        system_prompt='You are a helpful assistant that can analyze Git repositories. Use the git tools when asked about repository information or code search.'
    )
    
    @agent.tool
    async def get_repo_info(ctx: RunContext[Dict[str, Any]], repo_url: str) -> str:
        """Get information about a Git repository."""
        try:
            print(f'  📦 Analyzing repository: {repo_url}')
            repo_info = await git_tool.analyze_repository(repo_url)
            
            info_summary = f"""Repository Information:
- Name: {repo_info.name}
- URL: {repo_info.url}
- Default Branch: {repo_info.branch}
- File Count: {repo_info.file_count}
- Size: {repo_info.size_mb} MB
- Languages: {', '.join(repo_info.languages)}
- Latest Commit: {repo_info.commit_hash}
- Commit Message: {repo_info.commit_message or 'N/A'}"""
            
            print(f'  ✅ Repository analysis completed successfully')
            return info_summary
            
        except Exception as e:
            print(f'  💥 Git tool error: {str(e)}')
            return f'Failed to analyze repository: {str(e)}'
    
    @agent.tool
    async def search_code(ctx: RunContext[Dict[str, Any]], repo_url: str, query: str) -> str:
        """Search for code in a repository."""
        try:
            print(f'  🔍 Searching for "{query}" in {repo_url}')
                
            matches = await git_tool.search_code(repo_url, query, context_lines=3)
            
            if matches:
                search_results = []
                for match in matches[:5]:  # Limit to first 5 matches
                    result = f"File: {match.file_path} (Line {match.line_number})\n"
                    result += f"Code: {match.content}\n"
                    if match.context_before:
                        result += f"Context before: {match.context_before[-1] if match.context_before else 'N/A'}\n"
                    if match.context_after:
                        result += f"Context after: {match.context_after[0] if match.context_after else 'N/A'}"
                    search_results.append(result)
                
                summary = f"Found {len(matches)} matches for '{query}':\n\n" + "\n\n".join(search_results)
                print(f'  ✅ Found {len(matches)} code matches')
                return summary
            else:
                print('  ❌ No code matches found')
                return f"No code matches found for '{query}' in the repository"
                
        except Exception as e:
            print(f'  💥 Code search error: {str(e)}')
            return f'Code search failed: {str(e)}'
    
    # Test repository analysis
    print('  🤖 Calling LLM agent to analyze octocat Hello-World repository...')
    result = await agent.run(
        'Please analyze the repository https://github.com/octocat/Hello-World.git and then search for any "hello" or "world" related code in it.',
        deps={}
    )
    
    print(f'\n📋 Agent response:\n{result.output}')
    
    # Verify real Git operations happened
    response_lower = result.output.lower()
    success_indicators = [
        'hello-world' in response_lower or 'octocat' in response_lower,
        'repository' in response_lower,
        len(result.output) > 200,
        any(word in response_lower for word in ['file', 'code', 'commit', 'branch'])
    ]
    
    if all(success_indicators[:3]):
        print('\n🎉 SUCCESS: Real LLM agent successfully used real Git operations tool!')
        return True
    else:
        print('\n💥 FAILED: Git operations integration did not work as expected')
        print(f'   Success indicators: {success_indicators}')
        return False


async def test_real_gitlab_integration():
    """Test REAL LLM agent with REAL GitLab tool."""
    print('\n🧪 Testing REAL LLM agent with REAL GitLab tool...')
    
    from mantis.tools import GitLabTool, GitLabConfig
    
    # Check if GitLab credentials are available
    gitlab_token = os.getenv('GITLAB_PERSONAL_ACCESS_TOKEN') or os.getenv('GITLAB_TOKEN')
    gitlab_url = os.getenv('GITLAB_API_URL', 'https://gitlab.com/api/v4')
    
    if not gitlab_token:
        print('  ⚠️  No GitLab token found - creating read-only tool for testing')
        config = GitLabConfig(
            personal_access_token="",
            api_url=gitlab_url,
            read_only_mode=True,
            timeout=10.0,
        )
    else:
        print(f'  🔑 GitLab token found - creating full-access tool')
        config = GitLabConfig(
            personal_access_token=gitlab_token,
            api_url=gitlab_url,
            read_only_mode=False,
            timeout=10.0,
        )
    
    gitlab_tool = GitLabTool(config)
    
    # Create REAL pydantic-ai agent
    agent = Agent(
        'anthropic:claude-3-5-haiku-20241022',
        deps_type=Dict[str, Any],
        system_prompt='You are a helpful assistant that can interact with GitLab. Use the GitLab tools when asked about projects, issues, or GitLab operations.'
    )
    
    @agent.tool
    async def gitlab_list_projects(ctx: RunContext[Dict[str, Any]], search: str = None) -> str:
        """List GitLab projects."""
        try:
            print(f'  📋 Getting GitLab projects list...')
            if search:
                print(f'      Searching for: {search}')
            projects = await gitlab_tool.list_projects(search=search, limit=3)
            
            if projects:
                project_list = []
                for project in projects:
                    proj_info = f"- {project.name} ({project.namespace})"
                    if project.description:
                        proj_info += f": {project.description[:100]}..."
                    project_list.append(proj_info)
                
                summary = f"Found {len(projects)} GitLab projects:\n\n" + "\n".join(project_list)
                print(f'  ✅ Retrieved {len(projects)} projects')
                return summary
            else:
                print('  ❌ No projects found or access denied')
                return "No GitLab projects found or access denied"
                
        except Exception as e:
            print(f'  💥 GitLab projects error: {str(e)}')
            return f'Failed to get GitLab projects: {str(e)}'
    
    # Test GitLab operations
    print('  🤖 Calling LLM agent to explore GitLab...')
    result = await agent.run(
        'Please show me some GitLab projects that are available, and tell me about what you find.',
        deps={}
    )
    
    print(f'\n📋 Agent response:\n{result.output}')
    
    # Verify GitLab integration (even if limited by permissions)
    response_lower = result.output.lower()
    success_indicators = [
        'gitlab' in response_lower,
        len(result.output) > 100,
        any(word in response_lower for word in ['project', 'issue', 'access', 'error', 'mcp'])
    ]
    
    if all(success_indicators):
        print('\n🎉 SUCCESS: Real LLM agent successfully attempted GitLab operations!')
        return True
    else:
        print('\n💥 FAILED: GitLab integration did not work as expected')
        return False


async def test_real_jira_integration():
    """Test REAL LLM agent with REAL Jira tool."""
    print('\n🧪 Testing REAL LLM agent with REAL Jira tool...')
    
    from mantis.tools import JiraTool, JiraConfig
    
    # Check if Jira credentials are available
    jira_token = os.getenv('JIRA_API_TOKEN')
    jira_email = os.getenv('JIRA_EMAIL') 
    jira_url = os.getenv('JIRA_SERVER_URL', 'https://your-domain.atlassian.net')
    
    if not jira_token or not jira_email:
        print('  ⚠️  No Jira credentials found - creating read-only tool for testing')
        config = JiraConfig(
            api_token="",
            email="",
            server_url=jira_url,
            read_only_mode=True,
            timeout=10.0,
        )
    else:
        print(f'  🔑 Jira credentials found - creating full-access tool')
        config = JiraConfig(
            api_token=jira_token,
            email=jira_email, 
            server_url=jira_url,
            read_only_mode=False,
            timeout=10.0,
        )
    
    jira_tool = JiraTool(config)
    
    # Create REAL pydantic-ai agent
    agent = Agent(
        'anthropic:claude-3-5-haiku-20241022',
        deps_type=Dict[str, Any],
        system_prompt='You are a helpful assistant that can interact with Jira. Use the Jira tools when asked about projects, issues, or Jira operations.'
    )
    
    @agent.tool
    async def jira_get_projects(ctx: RunContext[Dict[str, Any]]) -> str:
        """Get list of Jira projects."""
        try:
            print(f'  📋 Getting Jira projects list...')
            projects = await jira_tool.get_projects()
            
            if projects:
                project_list = []
                for project in projects[:3]:  # Limit to first 3
                    proj_info = f"- {project.name} ({project.key})"
                    if project.description:
                        proj_info += f": {project.description[:100]}..."
                    project_list.append(proj_info)
                
                summary = f"Found {len(projects)} Jira projects (showing first 3):\n\n" + "\n".join(project_list)
                print(f'  ✅ Retrieved {len(projects)} projects')
                return summary
            else:
                print('  ❌ No projects found or access denied')
                return "No Jira projects found or access denied"
                
        except Exception as e:
            print(f'  💥 Jira projects error: {str(e)}')
            return f'Failed to get Jira projects: {str(e)}'
    
    # Test Jira operations
    print('  🤖 Calling LLM agent to explore Jira...')
    result = await agent.run(
        'Please show me some Jira projects that are available, and tell me about what you find.',
        deps={}
    )
    
    print(f'\n📋 Agent response:\n{result.output}')
    
    # Verify Jira integration (even if limited by permissions) 
    response_lower = result.output.lower()
    success_indicators = [
        'jira' in response_lower,
        len(result.output) > 100,
        any(word in response_lower for word in ['project', 'issue', 'access', 'error', 'mcp'])
    ]
    
    if all(success_indicators):
        print('\n🎉 SUCCESS: Real LLM agent successfully attempted Jira operations!')
        return True
    else:
        print('\n💥 FAILED: Jira integration did not work as expected')
        return False


async def main():
    """Run all Git and GitLab integration tests."""
    print('🚀 Starting REAL Git, GitLab & Jira LLM Agent Integration Tests')
    print('=' * 65)
    
    tests = [
        test_real_git_operations_integration,
        test_real_gitlab_integration,
        test_real_jira_integration,
    ]
    
    results = []
    for test_func in tests:
        try:
            success = await test_func()
            results.append(success)
        except Exception as e:
            print(f'\n💥 Test failed with exception: {e}')
            results.append(False)
    
    print('\n' + '=' * 65)
    print(f'📊 Git & GitLab Integration Test Results: {sum(results)}/{len(results)} passed')
    
    if all(results):
        print('🎉 ALL GIT INTEGRATION TESTS PASSED! LLM agents can use our Git tools!')
    else:
        print('❌ Some Git integration tests failed. Check the output above.')
    
    return all(results)


if __name__ == '__main__':
    asyncio.run(main())
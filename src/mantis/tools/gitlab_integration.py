"""
Native pydantic-ai GitLab integration tool.
Simplified to only support pydantic-ai integration.
"""

import logging
import aiohttp
from typing import Optional

# Observability imports
try:
    from ..observability import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("gitlab_integration")
else:
    obs_logger = None  # type: ignore


async def gitlab_list_projects(gitlab_url: str, access_token: str, search: Optional[str] = None) -> str:
    """List GitLab projects accessible to the authenticated user.
    
    Args:
        gitlab_url: GitLab instance URL (e.g., https://gitlab.com)
        access_token: GitLab personal access token
        search: Optional search string to filter projects
        
    Returns:
        Formatted list of projects with names, descriptions, and URLs
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: gitlab_list_projects for {gitlab_url}")
    
    try:
        api_url = f"{gitlab_url.rstrip('/')}/api/v4/projects"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"per_page": "20", "membership": "true"}
        
        if search:
            params["search"] = search
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, params=params) as response:
                if response.status != 200:
                    return f"Failed to fetch GitLab projects: HTTP {response.status}"
                
                projects = await response.json()
                
                if not projects:
                    search_info = f" matching '{search}'" if search else ""
                    return f"No GitLab projects found{search_info}"
                
                # Format results for LLM
                formatted_results = []
                for project in projects:
                    name = project.get("name", "Unknown")
                    description = project.get("description", "No description")
                    web_url = project.get("web_url", "")
                    namespace = project.get("namespace", {}).get("full_path", "")
                    
                    formatted_results.append(
                        f"- **{name}** ({namespace}): {description}\n  URL: {web_url}"
                    )
                
                result_text = f"Found {len(projects)} GitLab projects:\n\n" + "\n\n".join(formatted_results)
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"GitLab projects listed: {len(projects)} results")
                
                return result_text
                
    except Exception as e:
        error_msg = f"Error listing GitLab projects: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"GitLab projects list failed: {e}")
        return error_msg


async def gitlab_list_issues(gitlab_url: str, access_token: str, project_id: str, state: str = "opened") -> str:
    """List issues for a specific GitLab project.
    
    Args:
        gitlab_url: GitLab instance URL (e.g., https://gitlab.com)
        access_token: GitLab personal access token
        project_id: Project ID or path (e.g., "123" or "group/project")
        state: Issue state filter (opened, closed, all)
        
    Returns:
        Formatted list of issues with titles, states, and URLs
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: gitlab_list_issues for project {project_id}")
    
    try:
        # URL encode the project_id in case it contains special characters
        from urllib.parse import quote_plus
        encoded_project_id = quote_plus(project_id)
        
        api_url = f"{gitlab_url.rstrip('/')}/api/v4/projects/{encoded_project_id}/issues"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"per_page": "20", "state": state}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, params=params) as response:
                if response.status != 200:
                    return f"Failed to fetch GitLab issues: HTTP {response.status}"
                
                issues = await response.json()
                
                if not issues:
                    return f"No {state} issues found in GitLab project {project_id}"
                
                # Format results for LLM
                formatted_results = []
                for issue in issues:
                    title = issue.get("title", "Untitled")
                    iid = issue.get("iid", "?")
                    state = issue.get("state", "unknown")
                    web_url = issue.get("web_url", "")
                    author = issue.get("author", {}).get("name", "Unknown")
                    created = issue.get("created_at", "").split("T")[0] if issue.get("created_at") else ""
                    
                    formatted_results.append(
                        f"- **#{iid}: {title}** [{state}]\n  Author: {author}, Created: {created}\n  URL: {web_url}"
                    )
                
                result_text = f"Found {len(issues)} {state} issues in project {project_id}:\n\n" + "\n\n".join(formatted_results)
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"GitLab issues listed: {len(issues)} results")
                
                return result_text
                
    except Exception as e:
        error_msg = f"Error listing GitLab issues for {project_id}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"GitLab issues list failed: {e}")
        return error_msg


async def gitlab_create_issue(gitlab_url: str, access_token: str, project_id: str, title: str, description: Optional[str] = None) -> str:
    """Create a new issue in a GitLab project.
    
    Args:
        gitlab_url: GitLab instance URL (e.g., https://gitlab.com)
        access_token: GitLab personal access token
        project_id: Project ID or path (e.g., "123" or "group/project") 
        title: Issue title
        description: Optional issue description
        
    Returns:
        Confirmation message with issue details and URL
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: gitlab_create_issue in project {project_id}")
    
    try:
        # URL encode the project_id in case it contains special characters
        from urllib.parse import quote_plus
        encoded_project_id = quote_plus(project_id)
        
        api_url = f"{gitlab_url.rstrip('/')}/api/v4/projects/{encoded_project_id}/issues"
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {"title": title}
        
        if description:
            data["description"] = description
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, data=data) as response:
                if response.status not in [200, 201]:
                    return f"Failed to create GitLab issue: HTTP {response.status}"
                
                issue = await response.json()
                
                title = issue.get("title", "Untitled")
                iid = issue.get("iid", "?")
                web_url = issue.get("web_url", "")
                
                result_msg = f"Successfully created GitLab issue #{iid}: {title}\nURL: {web_url}"
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"GitLab issue created: #{iid}")
                
                return result_msg
                
    except Exception as e:
        error_msg = f"Error creating GitLab issue in {project_id}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"GitLab issue creation failed: {e}")
        return error_msg


async def gitlab_get_issue(gitlab_url: str, access_token: str, project_id: str, issue_iid: str) -> str:
    """Get detailed information about a specific GitLab issue.
    
    Args:
        gitlab_url: GitLab instance URL (e.g., https://gitlab.com)
        access_token: GitLab personal access token
        project_id: Project ID or path (e.g., "123" or "group/project")
        issue_iid: Issue internal ID (e.g., "42")
        
    Returns:
        Detailed issue information including description, comments, and metadata
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: gitlab_get_issue for issue #{issue_iid} in project {project_id}")
    
    try:
        # URL encode the project_id in case it contains special characters
        from urllib.parse import quote_plus
        encoded_project_id = quote_plus(project_id)
        
        api_url = f"{gitlab_url.rstrip('/')}/api/v4/projects/{encoded_project_id}/issues/{issue_iid}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as response:
                if response.status == 404:
                    return f"GitLab issue #{issue_iid} not found in project {project_id}"
                elif response.status != 200:
                    return f"Failed to fetch GitLab issue: HTTP {response.status}"
                
                issue = await response.json()
                
                # Format detailed issue information
                title = issue.get("title", "Untitled")
                iid = issue.get("iid", "?")
                state = issue.get("state", "unknown")
                description = issue.get("description", "No description")
                web_url = issue.get("web_url", "")
                author = issue.get("author", {}).get("name", "Unknown")
                assignee = issue.get("assignee")
                assignee_name = assignee.get("name", "Unassigned") if assignee else "Unassigned"
                created = issue.get("created_at", "").split("T")[0] if issue.get("created_at") else ""
                updated = issue.get("updated_at", "").split("T")[0] if issue.get("updated_at") else ""
                labels = issue.get("labels", [])
                milestone = issue.get("milestone")
                milestone_title = milestone.get("title", "No milestone") if milestone else "No milestone"
                
                # Get issue notes/comments
                notes_url = f"{gitlab_url.rstrip('/')}/api/v4/projects/{encoded_project_id}/issues/{issue_iid}/notes"
                notes_text = ""
                try:
                    async with session.get(notes_url, headers=headers) as notes_response:
                        if notes_response.status == 200:
                            notes = await notes_response.json()
                            if notes:
                                notes_text = f"\n\n**Comments ({len(notes)}):**\n"
                                for note in notes[:5]:  # Limit to 5 most recent comments
                                    note_author = note.get("author", {}).get("name", "Unknown")
                                    note_body = note.get("body", "")
                                    note_created = note.get("created_at", "").split("T")[0] if note.get("created_at") else ""
                                    notes_text += f"\n- **{note_author}** ({note_created}): {note_body[:200]}{'...' if len(note_body) > 200 else ''}"
                except Exception:
                    pass  # Skip comments if they fail to load
                
                result_text = f"""**GitLab Issue #{iid}: {title}** [{state}]

**Project:** {project_id}
**Author:** {author}
**Assignee:** {assignee_name}
**Created:** {created}
**Updated:** {updated}
**Milestone:** {milestone_title}
**Labels:** {', '.join(labels) if labels else 'None'}
**URL:** {web_url}

**Description:**
{description}
{notes_text}"""
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"GitLab issue #{iid} retrieved successfully")
                
                return result_text
                
    except Exception as e:
        error_msg = f"Error getting GitLab issue #{issue_iid} in {project_id}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"GitLab get issue failed: {e}")
        return error_msg
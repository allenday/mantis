"""
Native pydantic-ai Jira integration tool.
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
    obs_logger = get_structured_logger("jira_integration")
else:
    obs_logger = None  # type: ignore


async def jira_list_projects(jira_url: str, username: str, api_token: str, project_key: Optional[str] = None) -> str:
    """List Jira projects accessible to the authenticated user.
    
    Args:
        jira_url: Jira instance URL (e.g., https://company.atlassian.net)
        username: Jira username/email
        api_token: Jira API token
        project_key: Optional specific project key to filter by
        
    Returns:
        Formatted list of projects with keys, names, and descriptions
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: jira_list_projects for {jira_url}")
    
    try:
        api_url = f"{jira_url.rstrip('/')}/rest/api/2/project"
        
        # Use HTTP Basic Auth with username and API token
        auth = aiohttp.BasicAuth(username, api_token)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, auth=auth) as response:
                if response.status != 200:
                    return f"Failed to fetch Jira projects: HTTP {response.status}"
                
                projects = await response.json()
                
                # Filter by project key if specified
                if project_key:
                    projects = [p for p in projects if p.get("key", "").upper() == project_key.upper()]
                
                if not projects:
                    filter_info = f" with key '{project_key}'" if project_key else ""
                    return f"No Jira projects found{filter_info}"
                
                # Format results for LLM
                formatted_results = []
                for project in projects[:20]:  # Limit to 20 results
                    key = project.get("key", "Unknown")
                    name = project.get("name", "Unknown")
                    description = project.get("description", "No description")
                    project_url = project.get("self", "")
                    
                    formatted_results.append(
                        f"- **{key}: {name}**: {description}\n  URL: {project_url}"
                    )
                
                result_text = f"Found {len(projects)} Jira projects:\n\n" + "\n\n".join(formatted_results)
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Jira projects listed: {len(projects)} results")
                
                return result_text
                
    except Exception as e:
        error_msg = f"Error listing Jira projects: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Jira projects list failed: {e}")
        return error_msg


async def jira_list_issues(jira_url: str, username: str, api_token: str, project_key: str, status: str = "open") -> str:
    """List issues for a specific Jira project.
    
    Args:
        jira_url: Jira instance URL (e.g., https://company.atlassian.net)
        username: Jira username/email
        api_token: Jira API token
        project_key: Project key (e.g., "PROJ", "DEV")
        status: Issue status filter (open, closed, all)
        
    Returns:
        Formatted list of issues with summaries, statuses, and URLs
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: jira_list_issues for project {project_key}")
    
    try:
        # Build JQL query based on status filter
        if status.lower() == "open":
            jql = f'project = "{project_key}" AND resolution = Unresolved'
        elif status.lower() == "closed":
            jql = f'project = "{project_key}" AND resolution != Unresolved'
        else:  # all
            jql = f'project = "{project_key}"'
        
        api_url = f"{jira_url.rstrip('/')}/rest/api/2/search"
        params = {
            "jql": jql,
            "maxResults": "20",
            "fields": "key,summary,status,assignee,created,priority"
        }
        
        # Use HTTP Basic Auth with username and API token
        auth = aiohttp.BasicAuth(username, api_token)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, auth=auth) as response:
                if response.status != 200:
                    return f"Failed to fetch Jira issues: HTTP {response.status}"
                
                data = await response.json()
                issues = data.get("issues", [])
                
                if not issues:
                    return f"No {status} issues found in Jira project {project_key}"
                
                # Format results for LLM
                formatted_results = []
                for issue in issues:
                    key = issue.get("key", "?")
                    summary = issue["fields"].get("summary", "No summary")
                    status_name = issue["fields"].get("status", {}).get("name", "Unknown")
                    assignee = issue["fields"].get("assignee")
                    assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
                    created = issue["fields"].get("created", "").split("T")[0] if issue["fields"].get("created") else ""
                    priority = issue["fields"].get("priority", {}).get("name", "Unknown") if issue["fields"].get("priority") else "Unknown"
                    
                    issue_url = f"{jira_url.rstrip('/')}/browse/{key}"
                    
                    formatted_results.append(
                        f"- **{key}: {summary}** [{status_name}]\n  Assignee: {assignee_name}, Priority: {priority}, Created: {created}\n  URL: {issue_url}"
                    )
                
                result_text = f"Found {len(issues)} {status} issues in project {project_key}:\n\n" + "\n\n".join(formatted_results)
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Jira issues listed: {len(issues)} results")
                
                return result_text
                
    except Exception as e:
        error_msg = f"Error listing Jira issues for {project_key}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Jira issues list failed: {e}")
        return error_msg


async def jira_create_issue(jira_url: str, username: str, api_token: str, project_key: str, summary: str, 
                          description: Optional[str] = None, issue_type: str = "Task") -> str:
    """Create a new issue in a Jira project.
    
    Args:
        jira_url: Jira instance URL (e.g., https://company.atlassian.net)
        username: Jira username/email
        api_token: Jira API token
        project_key: Project key (e.g., "PROJ", "DEV")
        summary: Issue summary/title
        description: Optional issue description
        issue_type: Issue type (Task, Bug, Story, etc.)
        
    Returns:
        Confirmation message with issue details and URL
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: jira_create_issue in project {project_key}")
    
    try:
        api_url = f"{jira_url.rstrip('/')}/rest/api/2/issue"
        
        # Build issue data
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type}
            }
        }
        
        if description:
            issue_data["fields"]["description"] = description
        
        # Use HTTP Basic Auth with username and API token
        auth = aiohttp.BasicAuth(username, api_token)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=issue_data, auth=auth) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    return f"Failed to create Jira issue: HTTP {response.status} - {error_text}"
                
                result = await response.json()
                
                issue_key = result.get("key", "Unknown")
                issue_url = f"{jira_url.rstrip('/')}/browse/{issue_key}"
                
                result_msg = f"Successfully created Jira issue {issue_key}: {summary}\nURL: {issue_url}"
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Jira issue created: {issue_key}")
                
                return result_msg
                
    except Exception as e:
        error_msg = f"Error creating Jira issue in {project_key}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Jira issue creation failed: {e}")
        return error_msg


async def jira_get_issue(jira_url: str, username: str, api_token: str, issue_key: str) -> str:
    """Get detailed information about a specific Jira issue.
    
    Args:
        jira_url: Jira instance URL (e.g., https://company.atlassian.net)
        username: Jira username/email
        api_token: Jira API token
        issue_key: Issue key (e.g., "PROJ-123")
        
    Returns:
        Detailed issue information including description, comments, and metadata
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: jira_get_issue for issue {issue_key}")
    
    try:
        api_url = f"{jira_url.rstrip('/')}/rest/api/2/issue/{issue_key}"
        params = {
            "expand": "comments,changelog",
            "fields": "summary,description,status,assignee,reporter,created,updated,priority,labels,components,fixVersions,resolution,resolutiondate"
        }
        
        # Use HTTP Basic Auth with username and API token
        auth = aiohttp.BasicAuth(username, api_token)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, params=params, auth=auth) as response:
                if response.status == 404:
                    return f"Jira issue {issue_key} not found"
                elif response.status != 200:
                    return f"Failed to fetch Jira issue: HTTP {response.status}"
                
                issue = await response.json()
                fields = issue.get("fields", {})
                
                # Format detailed issue information
                key = issue.get("key", "Unknown")
                summary = fields.get("summary", "No summary")
                description = fields.get("description", "No description")
                status = fields.get("status", {}).get("name", "Unknown")
                assignee = fields.get("assignee")
                assignee_name = assignee.get("displayName", "Unassigned") if assignee else "Unassigned"
                reporter = fields.get("reporter", {}).get("displayName", "Unknown")
                created = fields.get("created", "").split("T")[0] if fields.get("created") else ""
                updated = fields.get("updated", "").split("T")[0] if fields.get("updated") else ""
                priority = fields.get("priority", {}).get("name", "Unknown") if fields.get("priority") else "Unknown"
                labels = fields.get("labels", [])
                components = [comp.get("name", "") for comp in fields.get("components", [])]
                fix_versions = [ver.get("name", "") for ver in fields.get("fixVersions", [])]
                resolution = fields.get("resolution")
                resolution_name = resolution.get("name", "Unresolved") if resolution else "Unresolved"
                resolution_date = fields.get("resolutiondate", "").split("T")[0] if fields.get("resolutiondate") else ""
                
                issue_url = f"{jira_url.rstrip('/')}/browse/{key}"
                
                # Get comments
                comments_text = ""
                comments = issue.get("fields", {}).get("comment", {}).get("comments", [])
                if comments:
                    comments_text = f"\n\n**Comments ({len(comments)}):**\n"
                    for comment in comments[-5:]:  # Last 5 comments
                        comment_author = comment.get("author", {}).get("displayName", "Unknown")
                        comment_body = comment.get("body", "")
                        comment_created = comment.get("created", "").split("T")[0] if comment.get("created") else ""
                        comments_text += f"\n- **{comment_author}** ({comment_created}): {comment_body[:200]}{'...' if len(comment_body) > 200 else ''}"
                
                result_text = f"""**Jira Issue {key}: {summary}** [{status}]

**Reporter:** {reporter}
**Assignee:** {assignee_name}
**Priority:** {priority}
**Created:** {created}
**Updated:** {updated}
**Resolution:** {resolution_name}
{f"**Resolution Date:** {resolution_date}" if resolution_date else ""}
**Labels:** {', '.join(labels) if labels else 'None'}
**Components:** {', '.join(components) if components else 'None'}
**Fix Versions:** {', '.join(fix_versions) if fix_versions else 'None'}
**URL:** {issue_url}

**Description:**
{description}
{comments_text}"""
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Jira issue {key} retrieved successfully")
                
                return result_text
                
    except Exception as e:
        error_msg = f"Error getting Jira issue {issue_key}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Jira get issue failed: {e}")
        return error_msg
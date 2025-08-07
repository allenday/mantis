"""
Native pydantic-ai registry access tool.
Simplified to only support pydantic-ai integration.
"""

import logging
import aiohttp
from typing import List

# Observability imports
try:
    from ..observability import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("registry_access")
else:
    obs_logger = None


async def registry_search_agents(query: str, limit: int = 20) -> str:
    """Search for agents in the registry using natural language queries.
    
    Args:
        query: Search query describing the type of agent you're looking for
        limit: Maximum number of results to return (default: 20)
    
    Returns:
        Formatted list of matching agents with names, descriptions, and URLs
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: registry_search_agents with query: '{query}', limit: {limit}")
    
    try:
        from ..config import DEFAULT_REGISTRY
        
        # Simple HTTP search request
        search_url = f"{DEFAULT_REGISTRY}/search"
        async with aiohttp.ClientSession() as session:
            async with session.post(search_url, json={"query": query, "limit": limit}) as response:
                if response.status != 200:
                    return f"Registry search failed: HTTP {response.status}"
                
                data = await response.json()
                agents = data.get("agents", [])
                
                if not agents:
                    return f"No agents found matching query: '{query}'"
                
                # Format results for LLM
                formatted_results = []
                for agent in agents:
                    name = agent.get("name", "Unknown")
                    description = agent.get("description", "No description")
                    url = agent.get("url", "No URL")
                    similarity = agent.get("similarity_score", 0)
                    
                    sim_info = f" (similarity: {similarity:.3f})" if similarity else ""
                    formatted_results.append(f"- **{name}**{sim_info}: {description}\\n  URL: {url}")
                
                result_text = f"Found {len(agents)} agents matching '{query}':\\n\\n" + "\\n\\n".join(formatted_results)
                
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Registry search returned {len(agents)} results")
                
                return result_text
                
    except Exception as e:
        error_msg = f"Error searching agents: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Registry search failed: {e}")
        return error_msg


async def registry_get_agent_details(agent_url: str) -> str:
    """Get detailed information about a specific agent.
    
    Args:
        agent_url: URL of the agent to get details for
    
    Returns:
        Agent details formatted for LLM
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: registry_get_agent_details for {agent_url}")
    
    try:
        from ..agent.card import format_mantis_card_for_llm
        
        # Simple HTTP request to get agent details
        async with aiohttp.ClientSession() as session:
            async with session.get(agent_url) as response:
                if response.status != 200:
                    return f"Failed to fetch agent details: HTTP {response.status}"
                
                # Parse the MantisAgentCard from response
                data = await response.json()
                
                # Use existing card formatting functionality
                from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
                mantis_card = MantisAgentCard()
                # Simple conversion from JSON to protobuf (simplified)
                mantis_card.agent_card.name = data.get("name", "Unknown")
                mantis_card.agent_card.description = data.get("description", "No description")
                
                return format_mantis_card_for_llm(mantis_card)
                
    except Exception as e:
        error_msg = f"Error getting agent details for {agent_url}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Get agent details failed: {e}")
        return error_msg
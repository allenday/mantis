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

from ..config import DEFAULT_REGISTRY
from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
from ..agent.card import load_agent_card_from_json

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("registry_access")
else:
    obs_logger = None  # type: ignore


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
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
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
        # from ..agent.card import format_mantis_card_for_llm  # TODO: Implement this function

        # Simple HTTP request to get agent details
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
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

                # return format_mantis_card_for_llm(mantis_card)  # TODO: Implement this function
                return f"Agent Details: {mantis_card.agent_card.name} - {mantis_card.agent_card.description}"

    except Exception as e:
        error_msg = f"Error getting agent details for {agent_url}: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Get agent details failed: {e}")
        return error_msg


async def list_all_agents(page_size: int = 200, include_inactive: bool = False) -> List[MantisAgentCard]:
    """
    List all agents from the registry using JSONRPC transport.

    Args:
        page_size: Number of agents to fetch per page (default: 200)
        include_inactive: Whether to include inactive agents (default: False)

    Returns:
        List of MantisAgentCard objects
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: list_all_agents (page_size: {page_size})")

    try:
        # JSONRPC request to registry
        jsonrpc_request = {"jsonrpc": "2.0", "method": "list_agents", "params": {}, "id": 1}

        # Use same SSL fix as registration to avoid aiohttp issues
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{DEFAULT_REGISTRY}/jsonrpc", json=jsonrpc_request, headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")

                data = await response.json()

                if "error" in data:
                    raise Exception(f"JSONRPC Error: {data['error']}")

                result = data.get("result", {})
                registry_agent_cards = result.get("agents", [])

                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Retrieved {len(registry_agent_cards)} agents from registry")

                # Convert registry agent cards to MantisAgentCard objects
                mantis_cards = []
                for registry_card in registry_agent_cards:
                    try:
                        # The registry returns FastA2A format directly, not wrapped in agent_card
                        # Convert to MantisAgentCard using the existing loader
                        mantis_card = load_agent_card_from_json(registry_card)
                        mantis_cards.append(mantis_card)

                    except Exception as e:
                        logger.warning(f"Failed to parse agent card: {e}")
                        continue

                return mantis_cards

    except Exception as e:
        error_msg = f"Error listing agents from registry: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"List all agents failed: {e}")
        raise Exception(error_msg)


async def get_agent_by_name(agent_name: str) -> MantisAgentCard:
    """Get a specific agent by name from the registry.

    Args:
        agent_name: Name of the agent to retrieve

    Returns:
        MantisAgentCard for the requested agent

    Raises:
        ValueError: If agent not found
        Exception: If registry access fails
    """
    if OBSERVABILITY_AVAILABLE and obs_logger:
        obs_logger.info(f"🎯 TOOL_INVOKED: get_agent_by_name with name: '{agent_name}'")

    try:
        all_agents = await list_all_agents()

        # Search by name or ID
        from ..agent import AgentInterface

        for agent_card in all_agents:
            agent_interface = AgentInterface(agent_card)
            if agent_interface.name == agent_name or agent_interface.agent_id == agent_name:
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Found agent '{agent_name}' in registry")
                return agent_card

        # No fallbacks - fail fast if agent not found in registry

        # Agent not found
        available_names = []
        for agent_card in all_agents:
            agent_interface = AgentInterface(agent_card)
            available_names.append(agent_interface.name)

        available_str = ", ".join(available_names[:10])
        if len(available_names) > 10:
            available_str += "..."

        raise ValueError(f"Agent '{agent_name}' not found in registry. Available: {available_str}")

    except ValueError:
        raise  # Re-raise agent not found errors
    except Exception as e:
        error_msg = f"Error getting agent '{agent_name}' from registry: {str(e)}"
        if OBSERVABILITY_AVAILABLE and obs_logger:
            obs_logger.error(f"Get agent by name failed: {e}")
        raise Exception(error_msg)

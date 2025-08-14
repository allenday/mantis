"""
Team formation tools for Chief of Staff coordination.

Provides tools for assembling teams from the agent registry.
"""

from typing import List, Dict, Any

from .base import log_tool_invocation, log_tool_result
from ..tools.agent_registry import list_all_agents
from ..agent import AgentInterface
from ..observability.logger import get_structured_logger

logger = get_structured_logger(__name__)


async def get_random_agents_from_registry(count: int = 3) -> List[Dict[str, Any]]:
    """
    Get a random selection of agents from the registry for team formation.

    Retrieves agents from the A2A registry and randomly selects the requested number
    of agents for team assembly. Fails fast if the registry is unavailable or empty.

    Args:
        count: Number of random agents to select (1-10, default: 3)

    Returns:
        List of dictionaries representing selected agents (ADK-compatible format)

    Raises:
        ValueError: If count is not between 1 and 10
        RuntimeError: If registry is unavailable or returns no agents
    """
    log_tool_invocation("team_formation", "get_random_agents_from_registry", {"count": count})

    if count < 1 or count > 10:
        raise ValueError("Agent count must be between 1 and 10")

    # Fetch agents from registry - fail fast if registry is unavailable
    try:
        all_agents = await list_all_agents()
        if not all_agents:
            raise RuntimeError("Agent registry returned empty list - no agents available for team formation")

        logger.info(
            "Retrieved agents from registry",
            structured_data={"total_available": len(all_agents), "requested_count": count},
        )

    except Exception as e:
        # Fail fast - no fallbacks, no graceful degradation
        error_msg = f"Failed to retrieve agents from registry: {str(e)}"
        logger.error(
            "Team formation failed - registry unavailable",
            structured_data={"error": error_msg, "requested_count": count},
        )
        raise RuntimeError(error_msg) from e

    # Ensure we have enough agents
    if len(all_agents) < count:
        available_count = len(all_agents)
        logger.warning(
            "Insufficient agents in registry", structured_data={"requested": count, "available": available_count}
        )
        count = available_count

    # Select random subset using proper random selection
    import random

    selected_agent_cards = random.sample(all_agents, count)

    # Convert agent cards to AgentInterface protobuf objects
    selected_agents = []
    for agent_card in selected_agent_cards:
        # Create AgentInterface to access rich information
        agent_interface_wrapper = AgentInterface(agent_card)

        # Create serializable dictionary instead of protobuf (for ADK compatibility)
        agent_data = {
            "agent_id": agent_interface_wrapper.agent_id,
            "name": agent_interface_wrapper.name,
            "description": agent_interface_wrapper.description,
            "capabilities_summary": ", ".join(agent_interface_wrapper.primary_domains),
            "persona_summary": f"{agent_interface_wrapper.name}: {agent_interface_wrapper.communication_style}",
            "role_preference": agent_interface_wrapper.role_preference,
            "available": True,
        }

        selected_agents.append(agent_data)

    log_tool_result(
        "team_formation",
        "get_random_agents_from_registry",
        {"selected_count": len(selected_agents), "agent_names": [a["name"] for a in selected_agents]},
    )

    return selected_agents

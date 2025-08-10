"""
Team formation tools for Chief of Staff coordination.

Provides tools for assembling teams from the agent registry.
"""

from .base import log_tool_invocation, log_tool_result
from ..tools.agent_registry import list_all_agents
from ..agent import AgentInterface
from ..observability.logger import get_structured_logger
from ..proto.mantis.v1 import mantis_persona_pb2
from typing import List

logger = get_structured_logger(__name__)


def _get_mock_agents() -> List[mantis_persona_pb2.MantisAgentCard]:
    """Create mock agents for testing when registry is unavailable."""
    mock_agents = []

    # Mock Philosopher Agent
    philosopher = mantis_persona_pb2.MantisAgentCard()
    philosopher.agent_card.agent_id = "mock-philosopher"
    philosopher.agent_card.name = "Dr. Sofia Wisdom"
    philosopher.agent_card.description = "A wise philosopher specializing in ethics and virtue theory"
    philosopher.agent_card.role_preference = "advisor"
    philosopher.agent_card.primary_domains.extend(["philosophy", "ethics", "critical thinking"])
    philosopher.agent_card.communication_style = "thoughtful and reflective with careful reasoning"
    mock_agents.append(philosopher)

    # Mock Psychologist Agent
    psychologist = mantis_persona_pb2.MantisAgentCard()
    psychologist.agent_card.agent_id = "mock-psychologist"
    psychologist.agent_card.name = "Dr. Maya Insight"
    psychologist.agent_card.description = "A clinical psychologist focused on human behavior and well-being"
    psychologist.agent_card.role_preference = "analyst"
    psychologist.agent_card.primary_domains.extend(["psychology", "mental health", "human behavior"])
    psychologist.agent_card.communication_style = "empathetic and evidence-based with practical insights"
    mock_agents.append(psychologist)

    # Mock Life Coach Agent
    coach = mantis_persona_pb2.MantisAgentCard()
    coach.agent_card.agent_id = "mock-coach"
    coach.agent_card.name = "Alex Motivator"
    coach.agent_card.description = "A life coach focused on personal development and goal achievement"
    coach.agent_card.role_preference = "mentor"
    coach.agent_card.primary_domains.extend(["life coaching", "personal development", "motivation"])
    coach.agent_card.communication_style = "energetic and supportive with actionable advice"
    mock_agents.append(coach)

    return mock_agents


async def get_random_agents_from_registry(count: int = 3) -> str:
    """
    Get a random selection of agents from the registry for team formation.

    This tool is designed for Chief of Staff coordination - allowing them
    to assemble teams dynamically from available agents.

    Args:
        count: Number of random agents to select (default: 3, max: 10)

    Returns:
        Formatted list of selected agents with their names and brief descriptions
    """
    log_tool_invocation("team_formation", "get_random_agents_from_registry", {"count": count})

    if count < 1 or count > 10:
        return "Error: Agent count must be between 1 and 10"

    try:
        # Get all available agents
        try:
            all_agents = await list_all_agents()
            if not all_agents:
                logger.warning("Registry returned no agents, using local mock agents")
                all_agents = _get_mock_agents()
        except Exception as registry_error:
            logger.warning(f"Registry access failed: {registry_error}, using local mock agents")
            all_agents = _get_mock_agents()

        if not all_agents:
            return "Error: No agents available from registry or local fallback"

        if len(all_agents) < count:
            count = len(all_agents)

        # Select random agents
        import random

        selected_agent_cards = random.sample(all_agents, count)

        # Format the response with agent information
        result_lines = [f"🎯 **Selected {count} Random Agents for Team Assembly**\n"]

        selected_agents = []
        for i, agent_card in enumerate(selected_agent_cards, 1):
            # Create AgentInterface to access rich information
            agent_interface = AgentInterface(agent_card)

            result_lines.append(f"**{i}. {agent_interface.name}**")
            result_lines.append(f"   Role: {agent_interface.description[:100]}...")
            result_lines.append(f"   Expertise: {', '.join(agent_interface.primary_domains[:3])}")
            result_lines.append(f"   Communication Style: {agent_interface.communication_style[:80]}...")
            result_lines.append("")

            selected_agents.append(
                {
                    "name": agent_interface.name,
                    "role_preference": agent_interface.role_preference,
                    "primary_domains": agent_interface.primary_domains[:3],
                }
            )

        result_lines.append(f"✅ **Team Assembly Complete**: {count} agents ready for coordination")

        log_tool_result(
            "team_formation",
            "get_random_agents_from_registry",
            {
                "selected_count": count,
                "total_available": len(all_agents),
                "selected_agents": [agent["name"] for agent in selected_agents],
            },
        )

        return "\n".join(result_lines)

    except Exception as e:
        error_msg = f"Error selecting random agents: {str(e)}"
        logger.error(f"Team formation failed: {e}")
        return error_msg

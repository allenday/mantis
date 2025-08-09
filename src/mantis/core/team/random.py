"""
Random team formation strategy using agent registry.
"""

import random
from typing import List
import aiohttp

from .base import BaseTeam
from ...proto.mantis.v1 import mantis_core_pb2
from ...proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
from ...agent import AgentInterface
from ...observability.logger import get_structured_logger
from ...config import get_default_base_agent, DEFAULT_REGISTRY
from ...agent.card import load_agent_card_from_json


class RandomTeam(BaseTeam):
    """
    Random team formation strategy (TEAM_FORMATION_STRATEGY_RANDOM).

    Implements PRD requirement for random agent selection from registry
    ensuring diversity and avoiding duplicate selections.
    """

    async def select_team_members(
        self, simulation_input: mantis_core_pb2.SimulationInput, team_size: int = 3
    ) -> List[AgentInterface]:
        """Randomly select team members from agent registry."""
        logger = get_structured_logger(__name__)

        logger.info(
            "Selecting random team members from registry",
            structured_data={
                "team_size": team_size,
                "context_id": simulation_input.context_id,
                "registry_url": DEFAULT_REGISTRY,
            },
        )

        # Get all agents from registry
        try:
            available_agents = await self._list_all_agents_from_registry()
        except Exception as e:
            logger.warning(
                "Failed to list agents from registry, using default agent", structured_data={"error": str(e)}
            )
            # Fallback to default agent if registry fails
            default_agent = get_default_base_agent()
            if default_agent:
                available_agents = [default_agent] * team_size
            else:
                raise ValueError("No agents available and no default agent configured")

        if len(available_agents) < team_size:
            logger.warning(
                "Not enough available agents, using available ones",
                structured_data={"available": len(available_agents), "requested": team_size},
            )
            team_size = min(team_size, len(available_agents))

        # Random selection without replacement
        selected_agents = random.sample(available_agents, team_size) if available_agents else []

        # TODO: AgentSpec is underspecified in the protobuf schema. It currently only has
        # count, model_spec, and current_depth fields, but team formation needs to work
        # with actual agent information. For now, we'll use AgentInterface directly.
        # This should be revisited when AgentSpec is properly defined with agent_card fields.

        # Convert MantisAgentCard to AgentInterface instances
        members = []
        for mantis_agent in selected_agents:
            agent_interface = AgentInterface(mantis_agent)
            members.append(agent_interface)

        logger.info(
            "Random team selection completed",
            structured_data={"selected_agents": [member.name for member in members], "final_team_size": len(members)},
        )

        return members

    async def assign_member_contexts(
        self, members: List[AgentInterface], simulation_input: mantis_core_pb2.SimulationInput
    ) -> List[AgentInterface]:
        """Assign contexts using modular prompt system with MantisAgentCard persona data."""
        # Context assignment will be handled by modular prompt system
        # using rich persona data from MantisAgentCard via AgentInterface
        return members

    async def _list_all_agents_from_registry(self) -> List[MantisAgentCard]:
        """Get all available agents from the agent registry using list_agents method."""
        logger = get_structured_logger(__name__)

        jsonrpc_url = f"{DEFAULT_REGISTRY}/jsonrpc"
        list_payload = {"jsonrpc": "2.0", "method": "list_agents", "params": {}, "id": 1}

        logger.debug("Calling list_agents on registry", structured_data={"registry_url": DEFAULT_REGISTRY})

        async with aiohttp.ClientSession() as session:
            async with session.post(jsonrpc_url, json=list_payload) as response:
                if response.status != 200:
                    raise RuntimeError(f"Registry request failed with status {response.status}")

                data = await response.json()

                if "error" in data:
                    raise RuntimeError(f"Registry error: {data['error']['message']}")

                all_agents_json = data.get("result", {}).get("agents", [])

                # Convert JSON agent data to MantisAgentCard protobuf objects
                mantis_agents = []
                for agent_json in all_agents_json:
                    try:
                        mantis_card = load_agent_card_from_json(agent_json)
                        mantis_agents.append(mantis_card)
                    except Exception as e:
                        logger.warning(
                            "Failed to convert agent from registry",
                            structured_data={"agent_name": agent_json.get("name", "unknown"), "error": str(e)},
                        )
                        continue

                logger.info(
                    "Successfully loaded agents from registry",
                    structured_data={"total_agents": len(mantis_agents), "registry_url": DEFAULT_REGISTRY},
                )

                return mantis_agents

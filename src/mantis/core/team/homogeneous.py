"""
Homogeneous team formation strategy using agent registry.
"""

import random
from typing import List
import aiohttp

from .base import BaseTeam
from ...proto.mantis.v1 import mantis_core_pb2
from ...proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard, RolePreference
from ...agent import AgentInterface
from ...observability.logger import get_structured_logger
from ...config import get_default_base_agent, DEFAULT_REGISTRY
from ...agent.card import load_agent_card_from_json
from google.protobuf import struct_pb2


class HomogeneousTeam(BaseTeam):
    """
    Homogeneous team formation strategy (TEAM_FORMATION_STRATEGY_HOMOGENEOUS).
    
    Implements PRD requirement for selecting a single agent from registry
    and replicating that choice N times for specialized, focused collaboration.
    """
    
    async def select_team_members(self, 
                                  simulation_input: mantis_core_pb2.SimulationInput,
                                  team_size: int = 3) -> List[AgentInterface]:
        """Select a single agent from registry and replicate N times for homogeneous team."""
        logger = get_structured_logger(__name__)
        
        logger.info(
            "Selecting homogeneous team members from registry",
            structured_data={
                "team_size": team_size,
                "context_id": simulation_input.context_id,
                "registry_url": DEFAULT_REGISTRY
            }
        )
        
        # Get all agents from registry
        try:
            available_agents = await self._list_all_agents_from_registry()
        except Exception as e:
            logger.warning(
                "Failed to list agents from registry, using default agent",
                structured_data={"error": str(e)}
            )
            # Fallback to default agent if registry fails
            default_agent = get_default_base_agent()
            if default_agent:
                available_agents = [default_agent]
            else:
                raise ValueError("No agents available and no default agent configured")
        
        if not available_agents:
            raise ValueError("No agents available from registry")
        
        # Select a single agent randomly, then replicate it N times
        selected_agent = random.choice(available_agents)
        
        logger.info(
            "Selected agent for homogeneous team replication",
            structured_data={
                "selected_agent": selected_agent.agent_card.name,
                "team_size": team_size
            }
        )
        
        # TODO: Same AgentSpec issue as RandomTeam - using AgentInterface directly for now
        
        # Convert to AgentInterface instances - replicate the same agent
        members = []
        for i in range(team_size):
            agent_interface = AgentInterface(selected_agent)
            members.append(agent_interface)
        
        logger.info(
            "Homogeneous team selection completed",
            structured_data={
                "base_agent": selected_agent.agent_card.name,
                "team_members": [member.name for member in members],
                "final_team_size": len(members)
            }
        )
        
        return members
    
    async def assign_member_contexts(self, 
                                     members: List[AgentInterface],
                                     simulation_input: mantis_core_pb2.SimulationInput) -> List[AgentInterface]:
        """Assign contexts using modular prompt system with MantisAgentCard persona data."""
        # Context assignment will be handled by modular prompt system
        # using rich persona data from MantisAgentCard via AgentInterface
        return members
    
    async def _list_all_agents_from_registry(self) -> List[MantisAgentCard]:
        """Get all available agents from the agent registry using list_agents method."""
        logger = get_structured_logger(__name__)
        
        jsonrpc_url = f"{DEFAULT_REGISTRY}/jsonrpc"
        list_payload = {
            "jsonrpc": "2.0",
            "method": "list_agents",
            "params": {},
            "id": 1
        }
        
        logger.debug(
            "Calling list_agents on registry",
            structured_data={"registry_url": DEFAULT_REGISTRY}
        )
        
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
                            structured_data={
                                "agent_name": agent_json.get("name", "unknown"),
                                "error": str(e)
                            }
                        )
                        continue
                
                logger.info(
                    "Successfully loaded agents from registry",
                    structured_data={
                        "total_agents": len(mantis_agents),
                        "registry_url": DEFAULT_REGISTRY
                    }
                )
                
                return mantis_agents
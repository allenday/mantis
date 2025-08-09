"""
Tarot-based team formation strategy using divination tools and agent registry.
"""

from typing import List
import aiohttp

from .base import BaseTeam
from ...proto.mantis.v1 import mantis_core_pb2
from ...proto.mantis.v1.mantis_persona_pb2 import RolePreference
from ...config import DEFAULT_REGISTRY
from ...agent.card import load_agent_card_from_json
from google.protobuf import struct_pb2


class TarotTeam(BaseTeam):
    """
    Concrete implementation for tarot card team formation.
    Uses divination tools to select cards and registry lookup for agents.
    """
    
    async def select_team_members(self, 
                                  simulation_input: mantis_core_pb2.SimulationInput,
                                  team_size: int = 3) -> List[mantis_core_pb2.AgentSpec]:
        """Select tarot card agents using divination tools."""
        from ...tools.divination import get_drawn_tarot_cards_with_orientations
        
        # Draw random tarot cards
        drawn_cards = get_drawn_tarot_cards_with_orientations(team_size)
        
        # Find agents in registry
        jsonrpc_url = f"{DEFAULT_REGISTRY}/jsonrpc"
        list_payload = {
            "jsonrpc": "2.0",
            "method": "list_agents",
            "params": {},
            "id": 1
        }
        
        members = []
        async with aiohttp.ClientSession() as session:
            async with session.post(jsonrpc_url, json=list_payload) as response:
                if response.status == 200:
                    data = await response.json()
                    all_agents = data.get("result", {}).get("agents", [])
                    
                    for card_info in drawn_cards:
                        display_name = card_info['display_name']
                        
                        # Find agent by name
                        agent_data = None
                        for agent in all_agents:
                            if agent.get("name") == display_name:
                                agent_data = agent
                                break
                        
                        if agent_data:
                            try:
                                # Convert to MantisAgentCard
                                mantis_card = load_agent_card_from_json(agent_data)
                                
                                # Create TeamMemberSpec protobuf message
                                member = mantis_core_pb2.AgentSpec()
                                member.agent_name = display_name
                                member.agent_card.CopyFrom(mantis_card.agent_card)
                                member.role = RolePreference.ROLE_PREFERENCE_FOLLOWER
                                
                                # Add metadata
                                metadata = struct_pb2.Struct()
                                metadata["card_name"] = card_info['name']
                                metadata["inverted"] = card_info['inverted'] #needs to be set randomly, not part fo agent card
                                member.metadata.CopyFrom(metadata)
                                
                                members.append(member)
                                
                            except Exception:
                                # Skip failed conversions
                                continue
        
        return members

    async def assign_member_contexts(self, 
                                     members: List[mantis_core_pb2.AgentSpec],
                                     simulation_input: mantis_core_pb2.SimulationInput) -> List[mantis_core_pb2.AgentSpec]:
        """Assign contexts using modular prompt system with MantisAgentCard persona data."""
        # Context assignment will be handled by modular prompt system
        # using rich persona data from MantisAgentCard via AgentInterface
        # Tarot-specific metadata (card positions, orientations) are preserved in member.metadata
        return members
"""
Abstract team formation base class and factory.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List

from ...proto.mantis.v1 import mantis_core_pb2
from ...proto.mantis.v1.mantis_persona_pb2 import RolePreference, MantisAgentCard
from ...agent import AgentInterface
from google.protobuf import struct_pb2


class AbstractTeam(ABC):
    """
    Abstract base class for team formation patterns.
    
    Handles dynamic agent selection, context assignment, and parallel execution
    of team members with support for both DIRECT and A2A execution strategies.
    """

    def __init__(self, execution_strategy: mantis_core_pb2.ExecutionStrategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT):
        self._executor = None
        self.execution_strategy = execution_strategy
        
    def _get_executor(self):
        """Get executor based on execution strategy."""
        if self._executor is None:
            if self.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_DIRECT:
                from ..executor import DirectExecutor
                self._executor = DirectExecutor()
            elif self.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_A2A:
                from ..executor import A2AExecutor
                self._executor = A2AExecutor()
            else:
                raise ValueError(f"Unsupported execution strategy: {self.execution_strategy}")
        return self._executor

    @abstractmethod
    async def select_team_members(self, 
                                  simulation_input: mantis_core_pb2.SimulationInput,
                                  team_size: int = 3) -> List[AgentInterface]:
        """
        Select team members based on the simulation context and strategy.
        
        Args:
            simulation_input: The simulation request context
            team_size: Number of team members to select
            
        Returns:
            List of AgentInterface instances with agent details and contexts
        """
        pass

    @abstractmethod
    async def assign_member_contexts(self, 
                                     members: List[AgentInterface],
                                     simulation_input: mantis_core_pb2.SimulationInput) -> List[AgentInterface]:
        """
        Assign specific contexts to each team member.
        
        Args:
            members: Selected team members
            simulation_input: Base simulation context
            
        Returns:
            Team members with assigned contexts
        """
        pass

    async def execute_team_member(self,
                                  member: AgentInterface,
                                  simulation_input: mantis_core_pb2.SimulationInput,
                                  agent_spec: mantis_core_pb2.AgentSpec,
                                  agent_index: int) -> mantis_core_pb2.AgentResponse:
        """
        Execute a single team member with follower role.
        
        Args:
            member: Team member specification
            simulation_input: Simulation context
            agent_spec: Agent execution specification
            agent_index: Index of agent in team
            
        Returns:
            Agent response from team member
        """
        from ...prompt import PromptCompositionEngine, CompositionStrategy
        from ...prompt.variables import create_composition_context
        from ...llm.structured_extractor import StructuredExtractor
        from ...config import DEFAULT_MODEL

        executor = self._get_executor()
        
        # Create execution context for team member
        execution_context = {
            "current_depth": 1,  # Team members are depth 1
            "max_depth": simulation_input.max_depth,
            "team_size": len(simulation_input.agents) if simulation_input.agents else 1,
            "assigned_role": RolePreference.Name(member.role) if member.role != RolePreference.ROLE_PREFERENCE_UNSPECIFIED else "follower",
            "agent_index": agent_index
        }
        
        # Add team context to simulation input
        member_simulation = mantis_core_pb2.SimulationInput()
        member_simulation.CopyFrom(simulation_input)
        member_simulation.query = member.member_context
        
        # Convert A2A AgentCard to MantisAgentCard if needed
        if hasattr(member.agent_card, 'name'):  # It's an A2A AgentCard
            # For now, create a minimal MantisAgentCard wrapper
            # In a full implementation, this would be a proper conversion
            mantis_card = MantisAgentCard()
            mantis_card.agent_card.CopyFrom(member.agent_card)
        else:
            mantis_card = member.agent_card
        
        # Compose prompt using the specific team member agent
        composition_engine = PromptCompositionEngine()
        context = create_composition_context(
            mantis_card=mantis_card,
            simulation_input=member_simulation,
            agent_spec=agent_spec,
            execution_context=execution_context,
        )
        
        composed_prompt = await composition_engine.compose_prompt(
            context=context, strategy=CompositionStrategy.BLENDED
        )
        
        # Execute with minimal tools for team members
        extractor = StructuredExtractor()
        model = DEFAULT_MODEL
        
        result = await extractor.extract_text_response(
            prompt=composed_prompt.final_prompt,
            query=member_simulation.query,
            model=model
        )
        
        # Create response
        response = mantis_core_pb2.AgentResponse()
        response.text_response = result
        response.output_modes.append("text/markdown")
        
        return response

    async def execute_team(self,
                          simulation_input: mantis_core_pb2.SimulationInput,
                          team_size: int = 3) -> mantis_core_pb2.TeamExecutionResult:
        """
        Execute complete team formation and execution workflow.
        
        Args:
            simulation_input: Base simulation context
            team_size: Number of team members
            
        Returns:
            TeamExecutionResult protobuf message with all responses and metadata
        """
        # Step 1: Select team members
        members = await self.select_team_members(simulation_input, team_size)
        
        # Step 2: Assign contexts
        members = await self.assign_member_contexts(members, simulation_input)
        
        # Step 3: Execute team members in parallel
        agent_spec = mantis_core_pb2.AgentSpec()
        agent_spec.count = 1
        
        tasks = []
        for i, member in enumerate(members):
            task = self.execute_team_member(member, simulation_input, agent_spec, i)
            tasks.append(task)
        
        # Execute all team members concurrently
        responses = await asyncio.gather(*tasks)
        
        # Create execution metadata as protobuf Struct
        execution_metadata = struct_pb2.Struct()
        execution_metadata["team_size"] = len(members)
        execution_metadata["execution_strategy"] = "concurrent"
        execution_metadata["roles"] = [RolePreference.Name(member.role) for member in members]
        
        # Create and return TeamExecutionResult protobuf message
        result = mantis_core_pb2.TeamExecutionResult()
        result.member_responses.extend(responses)
        result.member_specs.extend(members)
        result.execution_metadata.CopyFrom(execution_metadata)
        result.execution_strategy = self.execution_strategy
        result.total_team_time = 0.0  # TODO: Add timing
        
        # Set successful execution result
        result.team_execution_result.status = mantis_core_pb2.EXECUTION_STATUS_SUCCESS
        
        return result


class BaseTeam(AbstractTeam):
    """
    Base team implementation that leverages MantisAgentCard persona data.
    
    Provides common functionality for using agent card original_content,
    communication_style, decision_framework, and other persona characteristics
    instead of creating custom member_context strings.
    """

    def _create_team_member_context(
        self,
        member: AgentInterface,
        simulation_input: mantis_core_pb2.SimulationInput,
        team_members: List[AgentInterface],
        member_index: int,
        specialized_role: str = ""
    ) -> str:
        """
        Create member context using MantisAgentCard persona data instead of custom strings.
        
        Will be implemented when modular prompt system is built.
        """
        raise NotImplementedError("Modular prompt system not yet implemented")
    
    def _get_agent_interface(self, member: AgentInterface) -> AgentInterface:
        """
        Extract MantisAgentCard from team member, handling conversion if needed.
        
        Args:
            member: Team member specification
            
        Returns:
            MantisAgentCard if available, None otherwise
        """
        # This would need to be implemented based on how the agent card is stored
        # For now, assume the agent_card field contains the necessary data
        # In a full implementation, this might require registry lookup or card conversion
        
        # If the member already has a MantisAgentCard reference, use it
        if hasattr(member, 'mantis_agent_card'):
            return member.mantis_agent_card
        
        # Otherwise, try to convert from the base agent_card
        # This would typically involve calling ensure_mantis_agent_card()
        try:
            from ...agent.card import ensure_mantis_agent_card
            from ...proto.a2a_pb2 import AgentCard
            
            # Create AgentCard from member.agent_card and convert
            temp_card = AgentCard()
            temp_card.CopyFrom(member.agent_card)
            return ensure_mantis_agent_card(temp_card)
            
        except Exception:
            return None
    
    def _create_team_coordination_context(
        self,
        member: AgentInterface,
        team_members: List[AgentInterface],
        member_index: int,
        specialized_role: str = ""
    ) -> str:
        """
        Create team coordination context that complements the persona data.
        
        Will be implemented when modular prompt system is built.
        """
        raise NotImplementedError("Modular prompt system not yet implemented")


class TeamFactory:
    """Factory for creating team instances based on strategy."""
    
    @staticmethod
    def create_team(
        strategy: mantis_core_pb2.TeamFormationStrategy,
        execution_strategy: mantis_core_pb2.ExecutionStrategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
    ) -> AbstractTeam:
        """Create team instance based on formation strategy."""
        
        if strategy == mantis_core_pb2.TEAM_FORMATION_STRATEGY_RANDOM:
            from .random import RandomTeam
            return RandomTeam(execution_strategy)
        elif strategy == mantis_core_pb2.TEAM_FORMATION_STRATEGY_HOMOGENEOUS:
            from .homogeneous import HomogeneousTeam
            return HomogeneousTeam(execution_strategy)
        elif strategy == mantis_core_pb2.TEAM_FORMATION_STRATEGY_TAROT:
            from .tarot import TarotTeam
            return TarotTeam(execution_strategy)
        else:
            raise ValueError(f"Unsupported team formation strategy: {strategy}")
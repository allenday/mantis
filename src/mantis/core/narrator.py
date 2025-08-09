"""
Abstract narrator patterns for multi-agent response synthesis.
"""

from abc import ABC, abstractmethod

from ..proto.mantis.v1 import mantis_core_pb2
from ..proto.mantis.v1.mantis_core_pb2 import ContextualExecution as ProtoExecutionContext
from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard, RolePreference
from .team_formation import AbstractTeamFormation, TarotTeamFormation


class AbstractNarrator(ABC):
    """
    Abstract base class for narrator patterns.
    
    Handles response aggregation and synthesis from multiple agents
    with support for both DIRECT and A2A execution strategies.
    """

    def __init__(self, execution_strategy: mantis_core_pb2.ExecutionStrategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT):
        self._executor = None
        self.execution_strategy = execution_strategy
        
    def _get_executor(self):
        """Get executor based on execution strategy."""
        if self._executor is None:
            if self.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_DIRECT:
                from .executor import DirectExecutor
                self._executor = DirectExecutor()
            elif self.execution_strategy == mantis_core_pb2.EXECUTION_STRATEGY_A2A:
                from .executor import A2AExecutor
                self._executor = A2AExecutor()
            else:
                raise ValueError(f"Unsupported execution strategy: {self.execution_strategy}")
        return self._executor

    @abstractmethod
    async def get_narrator_agent(self) -> MantisAgentCard:
        """
        Get the narrator agent for synthesis.
        
        Returns:
            MantisAgentCard for the narrator agent
        """
        pass

    @abstractmethod
    async def aggregate_responses(self, 
                                  team_result: mantis_core_pb2.TeamExecutionResult) -> str:
        """
        Aggregate multiple agent responses into concatenated format.
        
        Args:
            team_result: Result from team execution
            
        Returns:
            Concatenated responses string for narrator input
        """
        pass

    @abstractmethod
    async def create_narrative_context(self,
                                       simulation_input: mantis_core_pb2.SimulationInput,
                                       team_result: mantis_core_pb2.TeamExecutionResult,
                                       aggregated_responses: str) -> str:
        """
        Create narrative context for the narrator agent.
        
        Args:
            simulation_input: Original simulation context
            team_result: Team execution results
            aggregated_responses: Concatenated team responses
            
        Returns:
            Narrative context string for narrator
        """
        pass

    async def synthesize_narrative(self,
                                   simulation_input: mantis_core_pb2.SimulationInput,
                                   team_result: mantis_core_pb2.TeamExecutionResult) -> mantis_core_pb2.AgentResponse:
        """
        Synthesize team responses into coherent narrative using narrator agent.
        
        Args:
            simulation_input: Original simulation context
            team_result: Results from team execution
            
        Returns:
            Final narrative response from narrator
        """
        from ..prompt import PromptCompositionEngine, CompositionStrategy
        from ..prompt.variables import create_composition_context
        from ..llm.structured_extractor import StructuredExtractor
        from ..config import DEFAULT_MODEL

        # Get narrator agent
        narrator_card = await self.get_narrator_agent()
        
        # Aggregate team responses
        aggregated_responses = await self.aggregate_responses(team_result)
        
        # Create narrative context
        narrative_context = await self.create_narrative_context(
            simulation_input, team_result, aggregated_responses
        )
        
        # Create execution context for narrator
        execution_context = ProtoExecutionContext()
        execution_context.current_depth = 1  # Narrator synthesizes at depth 1
        execution_context.max_depth = simulation_input.max_depth
        execution_context.team_size = 1  # Narrator is single agent
        execution_context.assigned_role = RolePreference.Name(RolePreference.ROLE_PREFERENCE_NARRATOR)  # Key role for synthesis
        execution_context.agent_index = 0
        
        # Create simulation input for narrator
        narrator_simulation = mantis_core_pb2.SimulationInput()
        narrator_simulation.CopyFrom(simulation_input)
        narrator_simulation.query = narrative_context
        narrator_simulation.max_depth = 1  # No further recursion
        
        # Create agent spec
        agent_spec = mantis_core_pb2.AgentSpec()
        agent_spec.count = 1
        
        # Compose prompt using narrator agent
        composition_engine = PromptCompositionEngine()
        context = create_composition_context(
            mantis_card=narrator_card,
            simulation_input=narrator_simulation,
            agent_spec=agent_spec,
            execution_context=execution_context,
        )
        
        composed_prompt = await composition_engine.compose_prompt(
            context=context, strategy=CompositionStrategy.BLENDED
        )
        
        # Execute narrator
        extractor = StructuredExtractor()
        model = DEFAULT_MODEL
        
        result = await extractor.extract_text_response(
            prompt=composed_prompt.final_prompt,
            query=narrator_simulation.query,
            model=model
        )
        
        # Create final response
        response = mantis_core_pb2.AgentResponse()
        response.text_response = result
        response.output_modes.append("text/markdown")
        
        return response


class TarotNarrator(AbstractNarrator):
    """
    Concrete implementation for tarot reading narrative synthesis.
    Uses Tarot Reader agent to synthesize individual card responses.
    """
    
    async def get_narrator_agent(self) -> MantisAgentCard:
        """Get the Tarot Reader agent for narrative synthesis."""
        from ..agent.card import load_agent_card_from_json
        from ..config import DEFAULT_REGISTRY
        import aiohttp
        
        # Find Tarot Reader in registry
        jsonrpc_url = f"{DEFAULT_REGISTRY}/jsonrpc"
        list_payload = {
            "jsonrpc": "2.0",
            "method": "list_agents",
            "params": {},
            "id": 1
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(jsonrpc_url, json=list_payload) as response:
                if response.status == 200:
                    data = await response.json()
                    all_agents = data.get("result", {}).get("agents", [])
                    
                    # Find Tarot Reader agent
                    for agent in all_agents:
                        if agent.get("name") == "Tarot Reader":
                            return load_agent_card_from_json(agent)
        
        # Fallback to minimal agent card if not found
        raise RuntimeError("Tarot Reader agent not found in registry")

    async def aggregate_responses(self, 
                                  team_result: mantis_core_pb2.TeamExecutionResult) -> str:
        """Aggregate tarot card responses with position information."""
        concatenated_responses = []
        
        for i, (member, response) in enumerate(zip(team_result.member_specs, team_result.member_responses)):
            position = member.position or f"Position {i+1}"
            inverted = member.metadata.get("inverted", False) if "inverted" in member.metadata else False
            orientation = " (Inverted)" if inverted else ""
            card_name = f"{member.agent_name}{orientation}"
            
            section = f"### {position}: {card_name}\n{response.text_response}"
            concatenated_responses.append(section)
        
        return "\n\n".join(concatenated_responses)

    async def create_narrative_context(self,
                                       simulation_input: mantis_core_pb2.SimulationInput,
                                       team_result: mantis_core_pb2.TeamExecutionResult,
                                       aggregated_responses: str) -> str:
        """Create narrative context for Tarot Reader synthesis."""
        
        # Create card descriptions for context
        card_descriptions = []
        for member in team_result.member_specs:
            inverted = member.metadata.get("inverted", False) if "inverted" in member.metadata else False
            orientation = " (Inverted)" if inverted else ""
            card_descriptions.append(f"{member.agent_name}{orientation}")
        
        narrative_context = f"""
You are the Master Tarot Reader conducting this reading.

Cards drawn: {', '.join(card_descriptions)}

The individual cards have spoken. Here are their complete responses:

{aggregated_responses}

---

As the Master Tarot Reader, provide your final interpretation that:
- Weaves together the messages from all three cards
- Shows how they form a coherent narrative about the situation
- Identifies patterns, tensions, and connections between the cards
- Offers synthesis and deeper insight that emerges from their combination
- Provides strategic guidance based on the complete reading

Draw upon your mastery of tarot to reveal the deeper story these cards tell together.
"""
        
        return narrative_context


class MultiAgentOrchestrator:
    """
    Orchestrator that combines team formation and narrator patterns.
    
    This class demonstrates how the abstract patterns work together
    for complete multi-agent scenarios.
    """
    
    def __init__(self, 
                 team_formation: AbstractTeamFormation,
                 narrator: AbstractNarrator):
        self.team_formation = team_formation
        self.narrator = narrator
    
    async def execute_multi_agent_scenario(self,
                                          simulation_input: mantis_core_pb2.SimulationInput,
                                          team_size: int = 3) -> mantis_core_pb2.AgentResponse:
        """
        Execute complete multi-agent scenario with team formation and narrative synthesis.
        
        Args:
            simulation_input: Base simulation context
            team_size: Number of team members
            
        Returns:
            Final synthesized response from narrator
        """
        # Step 1: Execute team formation and get individual responses
        team_result = await self.team_formation.execute_team(simulation_input, team_size)
        
        # Step 2: Synthesize narrative from team responses
        final_response = await self.narrator.synthesize_narrative(simulation_input, team_result)
        
        return final_response


# Factory function for easy tarot scenario creation
def create_tarot_orchestrator(execution_strategy: mantis_core_pb2.ExecutionStrategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT) -> MultiAgentOrchestrator:
    """Create orchestrator with tarot team formation and narrator."""
    return MultiAgentOrchestrator(
        team_formation=TarotTeamFormation(execution_strategy),
        narrator=TarotNarrator(execution_strategy)
    )
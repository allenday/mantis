"""
Integration layer for connecting the prompt composition system with the orchestrator.

This module provides the bridge between the modular prompt system and the
existing execution infrastructure, handling prompt generation during agent execution.
"""

from typing import Optional, Dict, Any, List
import logging

from .composition_engine import PromptCompositionEngine, CompositionContext, CompositionStrategy
from .variables import VariableSystem
from ..agent.card import ensure_mantis_agent_card
from ..proto.mantis.v1.mantis_core_pb2 import SimulationInput, AgentSpec
from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard, RolePreference

logger = logging.getLogger(__name__)


class PromptIntegrationService:
    """
    Service that integrates prompt composition with agent execution.

    This service is used by execution strategies to generate context-appropriate
    prompts for agents during simulation execution.
    """

    def __init__(self):
        self._composition_engine = PromptCompositionEngine()
        self._variable_system = VariableSystem()

    def generate_agent_prompt(
        self,
        agent_card: MantisAgentCard,
        simulation_input: SimulationInput,
        agent_spec: AgentSpec,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a complete prompt for an agent based on context.

        Args:
            agent_card: The MantisAgentCard with persona and capability data
            simulation_input: The simulation input with query and context
            agent_spec: The agent specification with role and constraints
            execution_context: Additional execution context (depth, team info, etc.)

        Returns:
            Generated prompt string ready for LLM execution
        """
        try:
            # Ensure we have a MantisAgentCard
            mantis_card = ensure_mantis_agent_card(agent_card)

            # Create composition context
            composition_context = self._create_composition_context(
                mantis_card, simulation_input, agent_spec, execution_context or {}
            )

            # Generate prompt using composition engine
            prompt = self._composition_engine.compose_prompt(
                composition_context,
                strategy=CompositionStrategy.LAYERED,  # Default strategy
            )

            logger.debug(f"Generated prompt for agent {mantis_card.persona_title or mantis_card.agent_card.name}")
            return prompt

        except Exception as e:
            logger.error(f"Failed to generate agent prompt: {e}")
            # Return fallback prompt
            return self._create_fallback_prompt(agent_card, simulation_input)

    def _create_composition_context(
        self,
        agent_card: MantisAgentCard,
        simulation_input: SimulationInput,
        agent_spec: AgentSpec,
        execution_context: Dict[str, Any],
    ) -> CompositionContext:
        """Create a CompositionContext from the available information."""

        # Extract context parameters with defaults
        current_depth = execution_context.get("current_depth", 0)
        max_depth = simulation_input.max_depth if simulation_input.HasField("max_depth") else 3
        team_size = execution_context.get("team_size", 1)
        Agent_index = execution_context.get("agent_index", 0)

        # Determine roles based on agent characteristics and context
        role_assignment = self._determine_role_assignment(agent_card, execution_context)

        # Extract team composition if available
        team_composition = execution_context.get("team_composition", [])

        # Determine delegation and coordination needs
        requires_delegation = self._assess_delegation_needs(
            agent_card, simulation_input, current_depth, max_depth, team_size
        )
        requires_coordination = team_size > 1

        # Create context
        context = CompositionContext(
            agent_card=agent_card,
            simulation_input=simulation_input,
            agent_spec=agent_spec,
            current_depth=current_depth,
            max_depth=max_depth,
            team_size=team_size,
            agent_index=Agent_index,
            is_leader=role_assignment["is_leader"],
            is_follower=role_assignment["is_follower"],
            is_narrator=role_assignment["is_narrator"],
            team_composition=team_composition,
            requires_delegation=requires_delegation,
            requires_coordination=requires_coordination,
            execution_context=execution_context,
        )

        return context

    def _determine_role_assignment(
        self, agent_card: MantisAgentCard, execution_context: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Determine role assignment for the agent in current context."""

        # Check for explicit role assignment in execution context
        explicit_role = execution_context.get("assigned_role")
        if explicit_role:
            return {
                "is_leader": explicit_role == "leader",
                "is_follower": explicit_role == "follower",
                "is_narrator": explicit_role == "narrator",
            }

        # Determine based on agent capabilities and preferences
        if agent_card.HasField("competency_scores") and agent_card.competency_scores.HasField("role_adaptation"):
            role_adaptation = agent_card.competency_scores.role_adaptation

            # Use explicit preference if set
            if role_adaptation.preferred_role == RolePreference.ROLE_PREFERENCE_LEADER:
                return {"is_leader": True, "is_follower": False, "is_narrator": False}
            elif role_adaptation.preferred_role == RolePreference.ROLE_PREFERENCE_FOLLOWER:
                return {"is_leader": False, "is_follower": True, "is_narrator": False}
            elif role_adaptation.preferred_role == RolePreference.ROLE_PREFERENCE_NARRATOR:
                return {"is_leader": False, "is_follower": False, "is_narrator": True}

            # Use capability scores if no explicit preference
            scores = {
                "leader": role_adaptation.leader_score,
                "follower": role_adaptation.follower_score,
                "narrator": role_adaptation.narrator_score,
            }
            best_role = max(scores, key=scores.get)

            return {
                "is_leader": best_role == "leader",
                "is_follower": best_role == "follower",
                "is_narrator": best_role == "narrator",
            }

        # Default to independent/follower role
        return {"is_leader": False, "is_follower": True, "is_narrator": False}

    def _assess_delegation_needs(
        self,
        agent_card: MantisAgentCard,
        simulation_input: SimulationInput,
        current_depth: int,
        max_depth: int,
        team_size: int,
    ) -> bool:
        """Assess whether the agent should focus on delegation."""

        # Can't delegate if at max depth
        if current_depth >= max_depth - 1:
            return False

        # Single agent scenarios with depth capacity suggest delegation potential
        if team_size == 1 and current_depth < max_depth - 1:
            return True

        # Check if agent has leadership capabilities that suggest delegation
        if agent_card.HasField("competency_scores"):
            competencies = agent_card.competency_scores

            if competencies.HasField("role_adaptation"):
                leader_score = competencies.role_adaptation.leader_score
                if leader_score >= 0.7:  # Strong leader
                    return True

            # Check for strategic or coordination competencies
            if competencies.competency_scores:
                strategic_score = competencies.competency_scores.get("strategic planning and long-term vision", 0.0)
                leadership_score = competencies.competency_scores.get("team leadership and inspiring others", 0.0)

                if strategic_score >= 0.7 or leadership_score >= 0.7:
                    return True

        return False

    def _create_fallback_prompt(self, agent_card, simulation_input: SimulationInput) -> str:
        """Create a basic fallback prompt when composition fails."""
        if hasattr(agent_card, "persona_title"):
            agent_name = agent_card.persona_title or agent_card.agent_card.name
        else:
            agent_name = getattr(agent_card, "name", "AI Agent")

        return f"""You are {agent_name}. Please address the following request:

{simulation_input.query}

Provide a helpful and accurate response based on your capabilities and expertise."""

    def analyze_prompt_composition(
        self,
        agent_card: MantisAgentCard,
        simulation_input: SimulationInput,
        agent_spec: AgentSpec,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze what prompt modules would be applied without generating the full prompt.
        Useful for debugging and understanding prompt composition decisions.
        """
        try:
            mantis_card = ensure_mantis_agent_card(agent_card)
            composition_context = self._create_composition_context(
                mantis_card, simulation_input, agent_spec, execution_context or {}
            )

            return self._composition_engine.analyze_composition(composition_context)

        except Exception as e:
            logger.error(f"Failed to analyze prompt composition: {e}")
            return {"error": str(e)}

    def get_composition_engine(self) -> PromptCompositionEngine:
        """Get the underlying composition engine for advanced usage."""
        return self._composition_engine


# Global service instance
_prompt_integration_service: Optional[PromptIntegrationService] = None


def get_prompt_integration_service() -> PromptIntegrationService:
    """Get or create the global prompt integration service."""
    global _prompt_integration_service

    if _prompt_integration_service is None:
        _prompt_integration_service = PromptIntegrationService()

    return _prompt_integration_service


def integrate_with_executor(executor_class):
    """
    Decorator to integrate prompt composition with an executor class.

    This decorator modifies the execute_agent method to use the prompt
    composition system for generating agent prompts.
    """
    original_execute_agent = executor_class.execute_agent

    async def enhanced_execute_agent(self, simulation_input, agent_spec, agent_index):
        """Enhanced execute_agent that uses prompt composition."""
        # Get the agent card (this would need to be provided by the specific executor)
        # For now, this is a placeholder - actual integration would require
        # executor-specific logic to retrieve the agent card

        # This is where we'd integrate with the agent registry or card storage
        # agent_card = get_agent_card_for_spec(agent_spec)

        # For demonstration, return original behavior
        return await original_execute_agent(self, simulation_input, agent_spec, agent_index)

    executor_class.execute_agent = enhanced_execute_agent
    return executor_class


def create_execution_context(
    current_depth: int = 0,
    team_size: int = 1,
    agent_index: int = 0,
    assigned_role: Optional[str] = None,
    team_composition: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Helper function to create execution context for prompt generation.

    Args:
        current_depth: Current recursion depth
        team_size: Size of the current team
        agent_index: Index of this agent in the team
        assigned_role: Explicitly assigned role ('leader', 'follower', 'narrator')
        team_composition: List of other team member names/roles
        **kwargs: Additional context parameters

    Returns:
        Execution context dictionary
    """
    context = {
        "current_depth": current_depth,
        "team_size": team_size,
        "agent_index": agent_index,
        "team_composition": team_composition or [],
    }

    if assigned_role:
        context["assigned_role"] = assigned_role

    context.update(kwargs)
    return context

"""
Agent module for Mantis.

Provides AgentInterface class that encapsulates all agent card complexity
and exposes a clean, simple interface for working with agents.
"""

from typing import Optional, List, Dict, Any
from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard, RolePreference
from ..proto.a2a_pb2 import AgentCard
from ..observability.logger import get_structured_logger


class AgentInterface:
    """
    Clean interface that encapsulates all the complexity from mantis/agent/card.py.

    Provides simple access to rich persona data from MantisAgentCard without
    exposing the underlying protobuf complexity to team formation and execution.
    """

    def __init__(self, mantis_agent_card: MantisAgentCard):
        """Initialize AgentInterface with a MantisAgentCard."""
        self._mantis_card = mantis_agent_card
        self._logger = get_structured_logger(__name__)

    @classmethod
    def from_agent_card(cls, agent_card: AgentCard) -> "AgentInterface":
        """Create AgentInterface from base AgentCard, converting to MantisAgentCard."""
        from .card import ensure_mantis_agent_card

        mantis_card = ensure_mantis_agent_card(agent_card)
        return cls(mantis_card)

    @classmethod
    def from_json(cls, agent_data: Dict[str, Any]) -> "AgentInterface":
        """Create AgentInterface from JSON agent data."""
        from .card import load_agent_card_from_json

        mantis_card = load_agent_card_from_json(agent_data)
        return cls(mantis_card)

    # Simple identification properties
    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        # Handle case where agent_card might not have id field
        agent_card = self._mantis_card.agent_card
        if hasattr(agent_card, "id") and agent_card.id:
            return agent_card.id
        else:
            return agent_card.name

    @property
    def name(self) -> str:
        """Get agent name."""
        return self._mantis_card.agent_card.name

    @property
    def description(self) -> str:
        """Get agent description."""
        return self._mantis_card.agent_card.description

    # Rich persona data access
    @property
    def persona_content(self) -> str:
        """Get the full original persona content."""
        return self._mantis_card.persona_characteristics.original_content or ""

    @property
    def communication_style(self) -> str:
        """Get the agent's communication style."""
        return self._mantis_card.persona_characteristics.communication_style or ""

    @property
    def decision_framework(self) -> str:
        """Get the agent's decision-making framework."""
        return self._mantis_card.persona_characteristics.decision_framework or ""

    @property
    def core_principles(self) -> List[str]:
        """Get the agent's core principles."""
        return list(self._mantis_card.persona_characteristics.core_principles)

    @property
    def thinking_patterns(self) -> List[str]:
        """Get the agent's thinking patterns."""
        return list(self._mantis_card.persona_characteristics.thinking_patterns)

    @property
    def characteristic_phrases(self) -> List[str]:
        """Get the agent's characteristic phrases."""
        return list(self._mantis_card.persona_characteristics.characteristic_phrases)

    @property
    def behavioral_tendencies(self) -> List[str]:
        """Get the agent's behavioral tendencies."""
        return list(self._mantis_card.persona_characteristics.behavioral_tendencies)

    # Capabilities and skills
    @property
    def capabilities_summary(self) -> str:
        """Get a summary of agent capabilities."""
        if self._mantis_card.skills_summary.skill_overview:
            return self._mantis_card.skills_summary.skill_overview

        # Fallback to primary domains
        primary_domains = list(self._mantis_card.domain_expertise.primary_domains)
        if primary_domains:
            return f"Expert in: {', '.join(primary_domains[:3])}"

        return self._mantis_card.agent_card.description

    @property
    def persona_summary(self) -> str:
        """Get a brief persona summary."""
        if self._mantis_card.persona_characteristics.communication_style:
            style = self._mantis_card.persona_characteristics.communication_style
            return f"Communication: {style[:100]}..." if len(style) > 100 else f"Communication: {style}"

        # Fallback to core principles
        principles = list(self._mantis_card.persona_characteristics.core_principles)
        if principles:
            return f"Guided by: {', '.join(principles[:2])}"

        return "Persona data available in full content"

    @property
    def role_preference(self) -> str:
        """Get preferred role as string."""
        pref = self._mantis_card.competency_scores.role_adaptation.preferred_role
        if pref == RolePreference.ROLE_PREFERENCE_LEADER:
            return "LEADER"
        elif pref == RolePreference.ROLE_PREFERENCE_FOLLOWER:
            return "FOLLOWER"
        elif pref == RolePreference.ROLE_PREFERENCE_NARRATOR:
            return "NARRATOR"
        else:
            return "UNSPECIFIED"

    @property
    def primary_skill_tags(self) -> List[str]:
        """Get primary skill tags for categorization."""
        return list(self._mantis_card.skills_summary.primary_skill_tags)

    @property
    def signature_abilities(self) -> List[str]:
        """Get signature abilities that distinguish this agent."""
        return list(self._mantis_card.skills_summary.signature_abilities)

    # Domain expertise
    @property
    def primary_domains(self) -> List[str]:
        """Get primary expertise domains."""
        return list(self._mantis_card.domain_expertise.primary_domains)

    @property
    def methodologies(self) -> List[str]:
        """Get preferred methodologies and frameworks."""
        return list(self._mantis_card.domain_expertise.methodologies)

    # Competency scores
    def get_competency_score(self, competency: str) -> Optional[float]:
        """Get score for a specific competency (0.0-1.0)."""
        return self._mantis_card.competency_scores.competency_scores.get(competency)

    @property
    def leader_score(self) -> float:
        """Get leadership capability score (0.0-1.0)."""
        return self._mantis_card.competency_scores.role_adaptation.leader_score

    @property
    def follower_score(self) -> float:
        """Get follower capability score (0.0-1.0)."""
        return self._mantis_card.competency_scores.role_adaptation.follower_score

    @property
    def narrator_score(self) -> float:
        """Get narrator capability score (0.0-1.0)."""
        return self._mantis_card.competency_scores.role_adaptation.narrator_score

    # Availability and status
    @property
    def available(self) -> bool:
        """Check if agent is available for execution."""
        # For now, assume all agents are available
        # In the future, this could check registry status
        return True

    # Access to underlying protobuf objects when needed
    @property
    def mantis_agent_card(self) -> MantisAgentCard:
        """Get the underlying MantisAgentCard (use sparingly)."""
        return self._mantis_card

    @property
    def agent_card(self) -> AgentCard:
        """Get the underlying A2A AgentCard (use sparingly)."""
        return self._mantis_card.agent_card

    # Context generation for prompts
    def get_persona_context(self, include_team_info: bool = False) -> str:
        """
        Generate context string for prompts using rich persona data.

        Args:
            include_team_info: Whether to include placeholder for team coordination info

        Returns:
            Rich context string suitable for prompt assembly
        """
        context_parts = []

        # Start with full persona content if available
        if self.persona_content:
            context_parts.append(self.persona_content)
        else:
            # Fallback: construct from available components
            context_parts.append(f"You are {self.name}.")
            if self.description:
                context_parts.append(self.description)

        # Add communication style guidance
        if self.communication_style:
            context_parts.append(f"\n## Communication Style\n{self.communication_style}")

        # Add decision framework
        if self.decision_framework:
            context_parts.append(f"\n## Decision Framework\n{self.decision_framework}")

        # Add core principles
        if self.core_principles:
            principles_text = "\n".join([f"- {principle}" for principle in self.core_principles])
            context_parts.append(f"\n## Core Principles\n{principles_text}")

        # Add characteristic phrases
        if self.characteristic_phrases:
            phrases_text = ", ".join(self.characteristic_phrases[:3])  # Limit to 3
            context_parts.append(f"\n## Characteristic Expressions\nTypical phrases: {phrases_text}")

        # Placeholder for team coordination info
        if include_team_info:
            context_parts.append("\n## Team Context\n[Team coordination context will be inserted here]")

        return "\n".join(context_parts)

    def get_capabilities_context(self) -> str:
        """Generate capabilities context for prompts."""
        context_parts = []

        if self.signature_abilities:
            abilities_text = "\n".join([f"- {ability}" for ability in self.signature_abilities])
            context_parts.append(f"## Your Signature Abilities\n{abilities_text}")

        if self.primary_domains:
            domains_text = ", ".join(self.primary_domains[:3])  # Limit to 3
            context_parts.append(f"\n## Your Expertise Domains\n{domains_text}")

        if self.methodologies:
            methods_text = ", ".join(self.methodologies[:3])  # Limit to 3
            context_parts.append(f"\n## Your Preferred Methodologies\n{methods_text}")

        return "\n".join(context_parts)

    def __str__(self) -> str:
        """String representation."""
        return f"AgentInterface({self.name})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return f"AgentInterface(name='{self.name}', id='{self.agent_id}', available={self.available})"

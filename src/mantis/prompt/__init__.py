"""
Prompt system for Mantis.

Provides modular prompt composition with AgentInterface integration
and template-based assembly for contextual orchestration.
"""

from .contextual import ContextualPrompt, ContextualPromptBuilder
from .factory import create_simulation_prompt, create_simulation_prompt_with_interface, create_a2a_message_from_prompt
from .composition_engine import PromptCompositionEngine, CompositionStrategy, ComposedPrompt
from .variables import CompositionContext, create_composition_context
from .templates import (
    SIMULATION_BASE_PREFIX,
    SIMULATION_BASE_SUFFIX,
    PERSONA_ADHERENCE_SUFFIX,
    TEAM_COORDINATION_PREFIX,
    TEAM_COLLABORATION_SUFFIX,
    CURRENT_TASK_HEADER,
    TEAM_CONTEXT_HEADER,
    AGENT_CONTEXT_HEADER,
    LEADER_ROLE_CONTEXT,
    FOLLOWER_ROLE_CONTEXT,
    NARRATOR_ROLE_CONTEXT,
    RANDOM_TEAM_CONTEXT,
    HOMOGENEOUS_TEAM_CONTEXT,
    TAROT_TEAM_CONTEXT,
    FALLBACK_AGENT_CONTEXT,
    CAPABILITY_CONTEXT_HEADER,
    EXPERTISE_CONTEXT_HEADER,
    TEAM_COLLABORATION_GUIDELINES,
    AGENT_COORDINATION_CONSTRAINTS,
)

__all__ = [
    "ContextualPrompt",
    "ContextualPromptBuilder",
    "create_simulation_prompt",
    "create_simulation_prompt_with_interface",
    "create_a2a_message_from_prompt",
    "PromptCompositionEngine",
    "CompositionStrategy",
    "ComposedPrompt",
    "CompositionContext",
    "create_composition_context",
    # Template constants
    "SIMULATION_BASE_PREFIX",
    "SIMULATION_BASE_SUFFIX",
    "PERSONA_ADHERENCE_SUFFIX",
    "TEAM_COORDINATION_PREFIX",
    "TEAM_COLLABORATION_SUFFIX",
    "CURRENT_TASK_HEADER",
    "TEAM_CONTEXT_HEADER",
    "AGENT_CONTEXT_HEADER",
    "LEADER_ROLE_CONTEXT",
    "FOLLOWER_ROLE_CONTEXT",
    "NARRATOR_ROLE_CONTEXT",
    "RANDOM_TEAM_CONTEXT",
    "HOMOGENEOUS_TEAM_CONTEXT",
    "TAROT_TEAM_CONTEXT",
    "FALLBACK_AGENT_CONTEXT",
    "CAPABILITY_CONTEXT_HEADER",
    "EXPERTISE_CONTEXT_HEADER",
    "TEAM_COLLABORATION_GUIDELINES",
    "AGENT_COORDINATION_CONSTRAINTS",
]

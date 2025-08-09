"""
Prompt system for Mantis.

Provides modular prompt composition with AgentInterface integration
and template-based assembly for contextual orchestration.
"""

from .contextual import ContextualPrompt, ContextualPromptBuilder
from .factory import (
    create_simulation_prompt,
    create_simulation_prompt_with_interface,
    create_a2a_message_from_prompt
)
from .templates import *

__all__ = [
    "ContextualPrompt",
    "ContextualPromptBuilder",
    "create_simulation_prompt",
    "create_simulation_prompt_with_interface", 
    "create_a2a_message_from_prompt",
    # Template constants will be exported from templates module
]
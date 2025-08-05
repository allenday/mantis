"""
Modular prompt composition system for Mantis agents.

This module provides a flexible framework for composing prompts by combining:
- Base persona characteristics from MantisAgentCard
- Role-specific instructions (leader/follower/narrator)
- Context-aware adaptations based on recursion depth and team composition
- Capability modules for specialized functionality
"""

from .composition_engine import PromptCompositionEngine, CompositionStrategy, ComposedPrompt
from .variables import CompositionContext, create_composition_context

__all__ = [
    "PromptCompositionEngine",
    "CompositionStrategy",
    "ComposedPrompt",
    "CompositionContext",
    "create_composition_context",
]

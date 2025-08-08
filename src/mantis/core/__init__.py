"""
Core Mantis functionality - ContextualPrompt template assembly and orchestration.
"""

from .contextual_prompt import ContextualPromptBuilder, ContextualPrompt, create_simulation_prompt
from .orchestrator import SimpleOrchestrator as SimulationOrchestrator

__all__ = [
    "ContextualPromptBuilder", 
    "ContextualPrompt", 
    "create_simulation_prompt", 
    "SimulationOrchestrator"
]

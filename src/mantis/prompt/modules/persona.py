"""
Persona module - establishes authentic agent identity and characteristics.
"""

from .base import BasePromptModule
from ..variables import CompositionContext


class PersonaModule(BasePromptModule):
    """Module that establishes the agent's authentic persona foundation."""

    def get_module_name(self) -> str:
        return "persona"

    def get_priority(self) -> int:
        return 1000  # Highest priority - establishes foundation

    async def generate_content(self, context: CompositionContext) -> str:
        """Generate persona-based prompt content."""

        # Use original_content as the primary persona source
        original_content = context.get_variable("persona.original_content", "")

        if original_content:
            return str(original_content)  # Return as-is, it's already formatted

        # Fallback to agent name and basic info
        agent_name = context.get_variable("agent.name", "Unknown Agent")
        agent_description = context.get_variable("agent.description", "")

        if agent_description:
            return f"{agent_description}\n\nApply your authentic characteristics and expertise to this task."
        else:
            return f"You are {agent_name}. Apply your authentic characteristics and expertise to this task."

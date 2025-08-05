"""
Core prompt composition engine that orchestrates module selection and prompt assembly.
"""

import logging
from pydantic import BaseModel, ConfigDict
from enum import Enum
from typing import List, Dict, Any

from .variables import CompositionContext
from .modules.base import BasePromptModule
from .modules.persona import PersonaModule
from .modules.role import RoleModule
from .modules.leader import LeaderModule
from .modules.context import ContextModule
from .modules.capability import CapabilityModule

logger = logging.getLogger(__name__)


class CompositionStrategy(Enum):
    """Different strategies for combining prompt modules."""

    LAYERED = "layered"  # Clear sections with separators (debugging)
    BLENDED = "blended"  # Seamless integration (production)
    CONDITIONAL = "conditional"  # Rule-based combinations


class ComposedPrompt(BaseModel):
    """Result of prompt composition containing final prompt and metadata."""

    final_prompt: str
    modules_used: List[BasePromptModule]
    variables_resolved: Dict[str, Any]
    strategy: CompositionStrategy
    metadata: Dict[str, Any]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PromptCompositionEngine:
    """
    Central orchestrator for modular prompt composition.

    Combines persona characteristics, role instructions, and context-aware
    adaptations to generate coherent, authentic prompts for agent execution.
    """

    def __init__(self):
        self.modules: List[BasePromptModule] = []
        self._register_core_modules()

    def _register_core_modules(self):
        """Register the core prompt modules."""
        self.modules = [PersonaModule(), RoleModule(), LeaderModule(), ContextModule(), CapabilityModule()]
        logger.info(f"Registered {len(self.modules)} core prompt modules")

    async def compose_prompt(
        self, context: CompositionContext, strategy: CompositionStrategy = CompositionStrategy.BLENDED
    ) -> ComposedPrompt:
        """
        Compose a prompt using selected modules and specified strategy.

        Args:
            context: Composition context with agent card and execution details
            strategy: How to combine modules (layered, blended, conditional)

        Returns:
            ComposedPrompt with final prompt text and metadata
        """
        logger.info(f"Composing prompt with {strategy.value} strategy")

        # Select applicable modules
        applicable_modules = self._select_modules(context)
        logger.debug(f"Selected {len(applicable_modules)} applicable modules")

        # Generate content from each module
        module_contents = []
        variables_resolved = {}

        for module in applicable_modules:
            try:
                content = await module.generate_content(context)
                if content.strip():  # Only include non-empty content
                    module_contents.append((module, content))

                # Collect resolved variables
                module_vars = getattr(module, "_resolved_variables", {})
                variables_resolved.update(module_vars)

            except Exception as e:
                logger.error(f"Error generating content for {module.get_module_name()}: {e}")
                continue

        # Combine content using selected strategy
        final_prompt = self._combine_content(module_contents, strategy)

        return ComposedPrompt(
            final_prompt=final_prompt,
            modules_used=[m for m, _ in module_contents],
            variables_resolved=variables_resolved,
            strategy=strategy,
            metadata={
                "total_modules": len(applicable_modules),
                "active_modules": len(module_contents),
                "prompt_length": len(final_prompt),
            },
        )

    def _select_modules(self, context: CompositionContext) -> List[BasePromptModule]:
        """Select modules applicable to the current context."""
        applicable = []

        for module in self.modules:
            if module.is_applicable(context):
                applicable.append(module)
                logger.debug(f"Module {module.get_module_name()} is applicable")
            else:
                logger.debug(f"Module {module.get_module_name()} not applicable")

        # Sort by priority (higher priority first)
        applicable.sort(key=lambda m: m.get_priority(), reverse=True)
        return applicable

    def _combine_content(
        self, module_contents: List[tuple[BasePromptModule, str]], strategy: CompositionStrategy
    ) -> str:
        """Combine module content using the specified strategy."""

        if not module_contents:
            return "# No applicable modules found for this context."

        if strategy == CompositionStrategy.LAYERED:
            return self._layered_combination(module_contents)
        elif strategy == CompositionStrategy.BLENDED:
            return self._blended_combination(module_contents)
        elif strategy == CompositionStrategy.CONDITIONAL:
            return self._conditional_combination(module_contents)
        else:
            raise ValueError(f"Unknown composition strategy: {strategy}")

    def _layered_combination(self, module_contents: List[tuple[BasePromptModule, str]]) -> str:
        """Combine modules in clear, separated sections."""
        sections = []

        for module, content in module_contents:
            section = f"# {module.get_module_name()}\n{content.strip()}"
            sections.append(section)

        return "\n\n---\n\n".join(sections)

    def _blended_combination(self, module_contents: List[tuple[BasePromptModule, str]]) -> str:
        """Seamlessly blend module content for production use."""
        # Find persona module (should be first/highest priority)
        persona_content = ""
        other_contents = []

        for module, content in module_contents:
            if module.get_module_name() == "persona":
                persona_content = content.strip()
            else:
                other_contents.append(content.strip())

        # Start with persona foundation
        combined = persona_content

        # Blend in other modules
        if other_contents:
            combined += "\n\n" + "\n\n".join(other_contents)

        return combined

    def _conditional_combination(self, module_contents: List[tuple[BasePromptModule, str]]) -> str:
        """Rule-based combination for complex scenarios."""
        # For now, fall back to blended - can be enhanced with specific rules
        return self._blended_combination(module_contents)

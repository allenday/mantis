"""
Core prompt composition engine that orchestrates module selection and prompt assembly.
"""

import logging
from typing import List

from ..proto.mantis.v1 import mantis_core_pb2
from .variables import CompositionContext
from .modules.base import BasePromptModule
from .modules.persona import PersonaModule
from .modules.role import RoleModule
from .modules.leader import LeaderModule
from .modules.context import ContextModule
from .modules.capability import CapabilityModule

logger = logging.getLogger(__name__)


# Now using protobuf CompositionStrategy and ComposedPrompt instead of Pydantic models


class PromptCompositionEngine:
    """
    Central orchestrator for modular prompt composition.

    Combines persona characteristics, role instructions, and context-aware
    adaptations to generate coherent, authentic prompts for agent execution.
    """

    def __init__(self) -> None:
        self.modules: List[BasePromptModule] = []
        self._register_core_modules()

    def _register_core_modules(self) -> None:
        """Register the core prompt modules."""
        self.modules = [PersonaModule(), RoleModule(), LeaderModule(), ContextModule(), CapabilityModule()]
        logger.info(f"Registered {len(self.modules)} core prompt modules")

    async def compose_prompt(
        self, context: CompositionContext, strategy: mantis_core_pb2.CompositionStrategy = mantis_core_pb2.COMPOSITION_STRATEGY_BLENDED
    ) -> mantis_core_pb2.ComposedPrompt:
        """
        Compose a prompt using selected modules and specified strategy.

        Args:
            context: Composition context with agent card and execution details
            strategy: How to combine modules (layered, blended, conditional)

        Returns:
            ComposedPrompt protobuf message with final prompt text and metadata
        """
        strategy_name = mantis_core_pb2.CompositionStrategy.Name(strategy)
        logger.info(f"Composing prompt with {strategy_name} strategy")

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

        # Create protobuf ComposedPrompt
        composed_prompt = mantis_core_pb2.ComposedPrompt()
        composed_prompt.final_prompt = final_prompt
        composed_prompt.modules_used.extend([m.get_module_name() for m, _ in module_contents])
        composed_prompt.strategy = strategy
        
        # Convert variables_resolved dict to protobuf Struct
        if variables_resolved:
            composed_prompt.variables_resolved.update(variables_resolved)
        
        # Add metadata as protobuf Struct
        metadata = {
            "total_modules": len(applicable_modules),
            "active_modules": len(module_contents), 
            "prompt_length": len(final_prompt),
        }
        composed_prompt.metadata.update(metadata)

        return composed_prompt

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
        self, module_contents: List[tuple[BasePromptModule, str]], strategy: mantis_core_pb2.CompositionStrategy
    ) -> str:
        """Combine module content using the specified strategy."""

        if not module_contents:
            return "# No applicable modules found for this context."

        if strategy == mantis_core_pb2.COMPOSITION_STRATEGY_LAYERED:
            return self._layered_combination(module_contents)
        elif strategy == mantis_core_pb2.COMPOSITION_STRATEGY_BLENDED:
            return self._blended_combination(module_contents)
        elif strategy == mantis_core_pb2.COMPOSITION_STRATEGY_CONDITIONAL:
            return self._conditional_combination(module_contents)
        else:
            strategy_name = mantis_core_pb2.CompositionStrategy.Name(strategy)
            raise ValueError(f"Unknown composition strategy: {strategy_name}")

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

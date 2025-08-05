"""
Capability module - highlights relevant domain expertise and competencies.
"""

from .base import BasePromptModule
from ..variables import CompositionContext


class CapabilityModule(BasePromptModule):
    """Module that highlights relevant capabilities and domain expertise."""

    def get_module_name(self) -> str:
        return "capability"

    def get_priority(self) -> int:
        return 500  # Medium priority

    async def generate_content(self, context: CompositionContext) -> str:
        """Generate capability-focused content."""

        primary_domains = context.get_variable("domain.primary", [])
        methodologies = context.get_variable("domain.methodologies", [])

        if not primary_domains and not methodologies:
            return ""  # Skip if no domain expertise

        template = """## Your Capabilities & Expertise
**Primary Domains:** ${domain.primary}
**Key Methodologies:** ${domain.methodologies}

Apply your expertise strategically to deliver exceptional results in these areas."""

        return self.substitute_template(template, context)

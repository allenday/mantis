"""
Base class for prompt modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any

from ..variables import CompositionContext, substitute_variables


class BasePromptModule(ABC):
    """Base class for all prompt modules."""
    
    def __init__(self):
        self._resolved_variables: Dict[str, Any] = {}
    
    @abstractmethod
    def get_module_name(self) -> str:
        """Return the module name for identification."""
        pass
    
    def get_priority(self) -> int:
        """Return module priority (higher = applied first)."""
        return 100
    
    def is_applicable(self, context: CompositionContext) -> bool:
        """Check if this module applies to the given context."""
        return True
    
    @abstractmethod
    async def generate_content(self, context: CompositionContext) -> str:
        """Generate prompt content for this module."""
        pass
    
    def substitute_template(self, template: str, context: CompositionContext) -> str:
        """Substitute variables in template and track resolved variables."""
        result = substitute_variables(template, context.variables)
        self._resolved_variables = context.variables.copy()
        return result
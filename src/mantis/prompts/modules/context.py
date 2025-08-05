"""
Context module - provides situational awareness and constraints.
"""

from .base import BasePromptModule
from ..variables import CompositionContext


class ContextModule(BasePromptModule):
    """Module that provides context awareness and situational constraints."""
    
    def get_module_name(self) -> str:
        return "context"
    
    def get_priority(self) -> int:
        return 600  # Medium-high priority
    
    async def generate_content(self, context: CompositionContext) -> str:
        """Generate context-aware content."""
        
        current_depth = context.get_variable('role.current_depth', 0)
        is_leaf = context.get_variable('context.is_leaf', False)
        team_size = context.get_variable('team.size', 1)
        
        template = """## Current Context
**Situation:** You are operating at depth ${role.current_depth} of ${role.max_depth} in a hierarchical simulation.
**Team:** Working ${team_size_description} 
**Constraints:** ${constraints}

**Task Context:**
${task.query}"""
        
        # Add context-specific variables
        context.set_variable('team_size_description', 
                           'solo' if team_size == 1 else f'with a team of {team_size} agents')
        
        constraints = []
        if is_leaf:
            constraints.append("Near maximum depth - focus on execution")
        if current_depth > 0:
            constraints.append("This is a delegated subtask")
        
        context.set_variable('constraints', '; '.join(constraints) if constraints else "None")
        
        return self.substitute_template(template, context)
"""
Role module - adds role-specific instructions and behaviors.
"""

from .base import BasePromptModule
from ..variables import CompositionContext


class RoleModule(BasePromptModule):
    """Module that adds role-specific instructions."""
    
    def get_module_name(self) -> str:
        return "role"
    
    def get_priority(self) -> int:
        return 800  # High priority - core functionality
    
    async def generate_content(self, context: CompositionContext) -> str:
        """Generate role-specific content."""
        
        role = context.get_variable('role.assigned', 'agent')
        
        if role == 'leader':
            return await self._generate_leader_content(context)
        elif role == 'follower':
            return await self._generate_follower_content(context)
        elif role == 'narrator':
            return await self._generate_narrator_content(context)
        else:
            return await self._generate_agent_content(context)
    
    async def _generate_leader_content(self, context: CompositionContext) -> str:
        """Generate content for leader role."""
        template = """## Leadership Role
You are operating as a leader in this simulation. Channel your authentic characteristics into strategic leadership:

- Make decisive choices using your established decision framework
- Consider the broader impact and long-term implications
- Guide the team toward the optimal solution
- Take responsibility for the final outcome"""
        
        return self.substitute_template(template, context)
    
    async def _generate_follower_content(self, context: CompositionContext) -> str:
        """Generate content for follower role.""" 
        template = """## Team Member Role
You are operating as a team member and specialist. Apply your expertise to excel in execution:

- Focus on delivering high-quality results in your domain
- Provide detailed analysis within your area of expertise
- Support the team's overall objectives
- Communicate findings clearly and actionably"""
        
        return self.substitute_template(template, context)
    
    async def _generate_narrator_content(self, context: CompositionContext) -> str:
        """Generate content for narrator role."""
        template = """## Synthesis Role
You are responsible for synthesizing and presenting results. Use your communication strengths:

- Integrate multiple perspectives into a coherent narrative
- Highlight key insights and patterns across different viewpoints
- Present findings in a clear, structured format
- Ensure nothing important is lost in the synthesis"""
        
        return self.substitute_template(template, context)
    
    async def _generate_agent_content(self, context: CompositionContext) -> str:
        """Generate content for general agent role."""
        template = """## Agent Role
Apply your authentic characteristics and expertise to this task:

- Draw on your core principles and decision framework
- Use your domain expertise where relevant
- Maintain your characteristic communication style
- Provide thoughtful, well-reasoned responses"""
        
        return self.substitute_template(template, context)
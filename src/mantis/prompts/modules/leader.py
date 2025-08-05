"""
Leader module - specialized team building and delegation capabilities.
"""

from .base import BasePromptModule
from ..variables import CompositionContext


class LeaderModule(BasePromptModule):
    """Module that adds leader-specific team building and delegation capabilities."""
    
    def get_module_name(self) -> str:
        return "leader"
    
    def get_priority(self) -> int:
        return 700  # High priority for leaders
    
    def is_applicable(self, context: CompositionContext) -> bool:
        """Only applicable when agent is assigned leader role."""
        return context.get_variable('role.is_leader', False)
    
    async def generate_content(self, context: CompositionContext) -> str:
        """Generate leader-specific content based on depth and context."""
        
        current_depth = context.get_variable('role.current_depth', 0)
        max_depth = context.get_variable('role.max_depth', 3)
        can_delegate = context.get_variable('team.can_delegate', False)
        
        if current_depth == 0:
            return await self._generate_strategic_leader_content(context)
        elif can_delegate and current_depth <= max_depth - 2:
            return await self._generate_team_builder_content(context)
        else:
            return await self._generate_execution_leader_content(context)
    
    async def _generate_strategic_leader_content(self, context: CompositionContext) -> str:
        """Generate content for strategic leadership at top level."""
        template = """## Strategic Leadership
You are leading at the highest level. Focus on strategic vision and high-level decision making:

**Strategic Approach:**
- Break down complex problems into manageable components
- Identify key decision points and success criteria
- Consider multiple approaches and their trade-offs
- Plan the overall execution strategy

**Current Context:**
- Task: ${task.query}
- Maximum delegation depth: ${role.max_depth}
- Team building available: ${team.can_delegate}"""
        
        return self.substitute_template(template, context)
    
    async def _generate_team_builder_content(self, context: CompositionContext) -> str:
        """Generate team building content for mid-level leaders."""
        template = """## Team Building & Delegation
You can build a team to tackle this challenge. Use your leadership skills to assemble and coordinate the right specialists:

**Team Building Strategy:**
- Analyze the task requirements to identify needed competencies
- Consider which aspects require specialist expertise vs generalist skills
- Think about team composition: leaders, specialists, and communicators
- Plan the delegation strategy and coordination approach

**Available Resources:**
- Recursion budget remaining: ${context.recursion_remaining}
- Available agents for recruitment: ${team.available_agents}
- Current team size: ${team.size}

**Delegation Decision Framework:**
1. **When to delegate:** Complex tasks benefit from specialist expertise, multiple perspectives needed, or task can be parallelized
2. **What to delegate:** Specific sub-problems that align with agent expertise, analysis tasks requiring domain knowledge
3. **How to coordinate:** Clear task definition, success criteria, and integration plan for results

Consider whether this task would benefit from team collaboration or if you should handle it directly."""
        
        return self.substitute_template(template, context)
    
    async def _generate_execution_leader_content(self, context: CompositionContext) -> str:
        """Generate content for execution-focused leadership near max depth."""
        template = """## Execution Leadership
You are leading near the maximum recursion depth. Focus on direct execution and coordination:

**Execution Focus:**
- Apply your expertise directly to solve the problem
- Coordinate any existing team members effectively
- Synthesize insights and make final decisions
- Ensure deliverable quality and completeness

**Context:**
- Current depth: ${role.current_depth}/${role.max_depth}
- Recursion remaining: ${context.recursion_remaining}
- Team coordination required: ${team.size} members"""
        
        return self.substitute_template(template, context)
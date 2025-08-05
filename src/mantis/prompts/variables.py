"""
Context and variable management for prompt composition.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompositionContext:
    """Context information needed for prompt composition."""
    mantis_card: Any  # MantisAgentCard
    simulation_input: Any  # SimulationInput
    agent_spec: Any  # AgentSpec
    execution_context: Union[Dict[str, Any], Any] = field(default_factory=dict)  # Can be dict or proto ExecutionContext
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable value with fallback to default."""
        return self.variables.get(key, default)
    
    def set_variable(self, key: str, value: Any):
        """Set a variable value."""
        self.variables[key] = value


def create_composition_context(
    mantis_card: Any,
    simulation_input: Any, 
    agent_spec: Any,
    execution_context: Optional[Any] = None
) -> CompositionContext:
    """
    Create a composition context with resolved variables.
    
    Args:
        mantis_card: MantisAgentCard with persona and competency data
        simulation_input: SimulationInput with query and constraints
        agent_spec: AgentSpec with role preferences and configuration
        execution_context: Current execution state (depth, team size, etc.)
        
    Returns:
        CompositionContext with resolved template variables
    """
    if execution_context is None:
        execution_context = {}
    
    context = CompositionContext(
        mantis_card=mantis_card,
        simulation_input=simulation_input,
        agent_spec=agent_spec,
        execution_context=execution_context
    )
    
    # Resolve template variables
    variables = _resolve_template_variables(context)
    context.variables = variables
    
    logger.debug(f"Created composition context with {len(variables)} variables")
    return context


def _resolve_template_variables(context: CompositionContext) -> Dict[str, Any]:
    """Resolve all template variables from context."""
    variables = {}
    
    # Agent identity variables - handle both dict and protobuf structures
    if hasattr(context.mantis_card, 'agent_card'):
        variables['agent.name'] = context.mantis_card.agent_card.name
        variables['agent.description'] = context.mantis_card.agent_card.description
    elif isinstance(context.mantis_card, dict):
        agent_card = context.mantis_card.get('agent_card', {})
        variables['agent.name'] = agent_card.get('name', 'Unknown Agent')
        variables['agent.description'] = agent_card.get('description', '')
    
    # Persona variables - handle both dict and protobuf structures
    original_content = ""
    if hasattr(context.mantis_card, 'persona_characteristics'):
        persona = context.mantis_card.persona_characteristics
        variables['persona.core_principles'] = getattr(persona, 'core_principles', [])
        variables['persona.communication_style'] = getattr(persona, 'communication_style', '')
        variables['persona.decision_framework'] = getattr(persona, 'decision_framework', '')
        variables['persona.thinking_patterns'] = getattr(persona, 'thinking_patterns', [])
        variables['persona.characteristic_phrases'] = getattr(persona, 'characteristic_phrases', [])
        original_content = getattr(persona, 'original_content', '')
    
    # Try to get original_content from extension params if not found above
    if not original_content and isinstance(context.mantis_card, dict):
        try:
            extensions = context.mantis_card.get('agent_card', {}).get('capabilities', {}).get('extensions', [])
            for ext in extensions:
                if 'persona-characteristics' in ext.get('uri', ''):
                    original_content = ext.get('params', {}).get('original_content', '')
                    break
        except (AttributeError, KeyError):
            pass
    
    variables['persona.original_content'] = original_content
    
    # Role context variables - handle both dict and proto ExecutionContext
    exec_ctx = context.execution_context
    if isinstance(exec_ctx, dict):
        # Dict version (legacy)
        variables['role.assigned'] = exec_ctx.get('assigned_role', 'agent')
        variables['role.current_depth'] = exec_ctx.get('current_depth', 0)
        variables['role.max_depth'] = exec_ctx.get('max_depth', 3)
        variables['role.is_leader'] = exec_ctx.get('assigned_role') == 'leader'
        variables['role.is_follower'] = exec_ctx.get('assigned_role') == 'follower'
        variables['role.is_narrator'] = exec_ctx.get('assigned_role') == 'narrator'
        variables['task.parent_task'] = exec_ctx.get('parent_task', '')
        variables['team.size'] = exec_ctx.get('team_size', 1)
        variables['team.available_agents'] = exec_ctx.get('available_agents', [])
    else:
        # Proto ExecutionContext version
        variables['role.assigned'] = getattr(exec_ctx, 'assigned_role', 'agent')
        variables['role.current_depth'] = getattr(exec_ctx, 'current_depth', 0)
        variables['role.max_depth'] = getattr(exec_ctx, 'max_depth', 3)
        variables['role.is_leader'] = getattr(exec_ctx, 'assigned_role', '') == 'leader'
        variables['role.is_follower'] = getattr(exec_ctx, 'assigned_role', '') == 'follower'  
        variables['role.is_narrator'] = getattr(exec_ctx, 'assigned_role', '') == 'narrator'
        variables['task.parent_task'] = getattr(exec_ctx, 'parent_task', '')
        variables['team.size'] = getattr(exec_ctx, 'team_size', 1)
        variables['team.available_agents'] = list(getattr(exec_ctx, 'available_agents', []))
    
    # Task context variables
    if hasattr(context.simulation_input, 'query'):
        variables['task.query'] = context.simulation_input.query
    
    # Team context variables (derived)
    variables['team.can_delegate'] = variables['role.current_depth'] < variables['role.max_depth'] - 1
    
    # Competency variables
    if hasattr(context.mantis_card, 'competency_scores'):
        comp_scores = context.mantis_card.competency_scores
        if hasattr(comp_scores, 'competency_scores'):
            variables['competencies.scores'] = dict(comp_scores.competency_scores)
        
        if hasattr(comp_scores, 'role_adaptation'):
            role_adapt = comp_scores.role_adaptation
            variables['competencies.leader_score'] = getattr(role_adapt, 'leader_score', 0.0)
            variables['competencies.follower_score'] = getattr(role_adapt, 'follower_score', 0.0)
            variables['competencies.narrator_score'] = getattr(role_adapt, 'narrator_score', 0.0)
    
    # Domain expertise variables
    if hasattr(context.mantis_card, 'domain_expertise'):
        domain = context.mantis_card.domain_expertise
        variables['domain.primary'] = getattr(domain, 'primary_domains', [])
        variables['domain.secondary'] = getattr(domain, 'secondary_domains', [])
        variables['domain.methodologies'] = getattr(domain, 'methodologies', [])
        variables['domain.tools'] = getattr(domain, 'tools_and_frameworks', [])
    
    # Context-specific variables
    variables['context.recursion_remaining'] = variables['role.max_depth'] - variables['role.current_depth']
    variables['context.is_leaf'] = variables['context.recursion_remaining'] <= 1
    variables['context.depth_percentage'] = variables['role.current_depth'] / max(variables['role.max_depth'], 1)
    
    return variables


def substitute_variables(template: str, variables: Dict[str, Any]) -> str:
    """
    Substitute variables in template using ${variable.name} syntax.
    
    Args:
        template: Template string with ${var} placeholders
        variables: Dictionary of variable values
        
    Returns:
        Template with variables substituted
    """
    result = template
    
    for key, value in variables.items():
        placeholder = f"${{{key}}}"
        
        # Convert value to string representation
        if isinstance(value, list):
            if value:  # Non-empty list
                if len(value) == 1:
                    str_value = str(value[0])
                else:
                    str_value = ", ".join(str(v) for v in value)
            else:
                str_value = "None"
        elif isinstance(value, bool):
            str_value = "yes" if value else "no"
        elif value is None:
            str_value = "None"
        else:
            str_value = str(value)
        
        result = result.replace(placeholder, str_value)
    
    return result
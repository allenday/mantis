# Modular Prompt Composition System

## Overview

The Mantis modular prompt composition system enables flexible, context-aware prompt generation that preserves persona authenticity while adding sophisticated capabilities like team building and delegation. The system combines rich persona data with functional modules to create coherent, effective prompts for AI agents in various roles and contexts.

## Architecture

### Core Components

1. **PromptCompositionEngine**: Central orchestrator that combines modules
2. **PromptModule**: Base abstraction for reusable prompt components  
3. **CompositionContext**: Rich context carrying agent and situation data
4. **VariableSystem**: Template variable substitution and management
5. **Integration Layer**: Bridge to existing orchestrator infrastructure

### Module Types

- **PersonaModule**: Core identity and authentic voice
- **RoleModule**: Role-specific behavior adaptation
- **LeaderModule**: Team building and delegation capabilities
- **ContextModule**: Situational awareness and environment adaptation
- **CapabilityModule**: Skills highlighting and limitation awareness

## Key Design Principles

### 1. Persona Authenticity First

The system maintains authentic persona characteristics as the foundation, with other modules adapting to enhance rather than override the core identity.

```python
# Persona always provides the foundation
PersonaModule(priority=FOUNDATION)  # Executes first
RoleModule(priority=ROLE_ADAPTATION)  # Adapts persona to role
```

### 2. Context-Aware Adaptation

Modules dynamically adapt based on context factors:
- Recursion depth (0 = strategic, max = execution-focused)
- Team size (1 = independent, >1 = coordination-focused)  
- Role assignment (leader/follower/narrator)
- Task complexity and requirements

### 3. Modular Composition Strategies

Three composition strategies for different needs:

- **Layered**: Clear sections with separators (debugging/analysis)
- **Blended**: Seamless integration (production use)
- **Conditional**: Complex rule-based combinations (advanced scenarios)

## Leader Module Deep Dive

The LeaderModule is the most sophisticated component, providing team-building capabilities:

### Team Building Process

1. **Task Analysis**: Break down requirements into competency needs
2. **Registry Queries**: Search for agents with complementary skills
3. **Team Formation**: Balance roles and communication styles
4. **Delegation Framework**: Match tasks to agent strengths

### Leadership Context Adaptation

- **Top-Level (depth 0)**: Strategic oversight and team architecture
- **Mid-Level (depth 1-2)**: Active team building and coordination
- **Near-Max (depth 2+)**: Direct execution with minimal delegation

### Registry Query Framework

The system provides structured guidance for leaders to query the agent registry:

```python
# Example registry query guidance
"""
When searching for team members, structure your queries to identify:

1. Core Competencies: Match required skills to agent expertise scores
2. Role Preferences: Balance leaders, followers, and facilitators  
3. Domain Knowledge: Ensure coverage of all relevant subject areas
4. Communication Compatibility: Consider interaction styles
5. Workload Capacity: Assess current depth and delegation availability
"""
```

## Variable System

### Available Variables

The system provides rich template variables for dynamic content:

#### Agent Identity
- `${agent_name}`, `${agent_title}`, `${agent_description}`
- `${persona_voice}`, `${core_principles}`, `${decision_framework}`

#### Role & Team Context  
- `${current_role}`, `${role_description}`, `${team_size}`
- `${team_composition}`, `${hierarchy_level}`

#### Task Context
- `${task_query}`, `${task_type}`, `${task_context}`
- `${current_depth}`, `${max_depth}`

#### Capabilities
- `${top_competencies}`, `${leadership_score}`, `${expertise_domains}`

#### Team Building (Leaders)
- `${registry_query_guidance}`, `${delegation_framework}`
- `${team_building_context}`

### Variable Substitution

Variables use `${variable_name}` syntax with automatic substitution:

```python
template = "You are ${agent_title} with expertise in ${expertise_domains}"
# Becomes: "You are Strategic Transformation Leader with expertise in 
#          • Strategic Planning\n• Organizational Transformation"
```

## Composition Examples

### Example 1: Strategic Leader Team Building

**Context**: Top-level leader (depth 0), solo start, complex transformation task

**Generated Prompt Structure**:
```
# Core Persona & Identity
[Authentic persona characteristics and voice]

# Role Adaptation: Team Leader  
[Leadership responsibilities and approach]

# Leadership & Team Building
[Registry query guidance and delegation framework]

# Context & Situational Awareness
[Task understanding and operational constraints]

# Capabilities & Skills
[Competency scores and expertise areas]
```

### Example 2: Technical Specialist Execution

**Context**: Data scientist as team member (depth 1), follower role

**Generated Prompt Structure**:
```
# Core Persona & Identity
[Technical specialist characteristics]

# Role Adaptation: Team Member & Specialist
[Collaboration style and expertise application]

# Capabilities & Skills  
[Technical competencies and domain knowledge]

# Context & Situational Awareness
[Team coordination and task specifics]
```

## Integration with Orchestrator

### PromptIntegrationService

The `PromptIntegrationService` bridges the composition system with execution:

```python
service = get_prompt_integration_service()
prompt = service.generate_agent_prompt(
    agent_card=mantis_agent_card,
    simulation_input=simulation_input,
    agent_spec=agent_spec,
    execution_context={
        'current_depth': 1,
        'team_size': 3,
        'assigned_role': 'leader'
    }
)
```

### Role Determination

The system automatically determines roles based on:
1. Explicit role assignments in execution context
2. Agent role preferences (from `RoleAdaptation`)
3. Competency scores and capabilities
4. Context requirements (team size, task complexity)

## Advanced Features

### Conditional Module Application

Modules can have complex applicability conditions:

```python
def check_conditions(self, context) -> bool:
    # Leader module applies when:
    return (context.is_leader or                              # Explicit role
            context.agent_card.leadership_score >= 0.7 or    # High capability  
            (context.team_size > 1 and context.depth < 2))   # Team context
```

### Module Dependencies and Conflicts

Modules can specify dependencies and conflicts:

```python
def get_dependencies(self) -> List[str]:
    return ["core_persona"]  # Requires persona module first

def get_conflicts(self) -> List[str]:  
    return ["independent_worker"]  # Can't be used with this module
```

### Dynamic Template Selection

Modules can select different templates based on context:

```python
def generate_content(self, context) -> str:
    if context.current_depth == 0:
        return self._get_strategic_template()
    elif context.requires_delegation:
        return self._get_team_building_template()
    else:
        return self._get_coordination_template()
```

## Usage Patterns

### Basic Usage

```python
# Create composition engine
engine = PromptCompositionEngine()

# Create context
context = CompositionContext(
    agent_card=mantis_agent_card,
    simulation_input=simulation_input,
    agent_spec=agent_spec,
    current_depth=0,
    is_leader=True
)

# Generate prompt
prompt = engine.compose_prompt(context)
```

### Advanced Usage

```python
# Custom module selection
prompt = engine.compose_prompt(
    context,
    strategy=CompositionStrategy.BLENDED,
    required_modules={'leader_team_building'},
    excluded_modules={'capability_awareness'}
)

# Composition analysis
analysis = engine.analyze_composition(context)
print(f"Would apply {analysis['applicable_modules']} modules")
```

### Integration with Execution

```python
# In an execution strategy
async def execute_agent(self, simulation_input, agent_spec, agent_index):
    # Get agent card from registry/storage
    agent_card = await self.get_agent_card(agent_spec)
    
    # Generate contextual prompt
    service = get_prompt_integration_service()
    prompt = service.generate_agent_prompt(
        agent_card, simulation_input, agent_spec,
        execution_context={
            'current_depth': self.current_depth,
            'team_size': len(self.current_team),
            'agent_index': agent_index
        }
    )
    
    # Execute with generated prompt
    return await self.llm_execute(prompt, agent_card)
```

## Benefits

### For Agent Quality
- **Authentic Voice**: Persona characteristics preserved across contexts
- **Role Appropriateness**: Behavior adapts to leadership/specialist roles
- **Context Awareness**: Agents understand their situation and constraints

### For Team Building
- **Systematic Approach**: Structured framework for team composition
- **Registry Integration**: Clear guidance for finding suitable team members  
- **Delegation Excellence**: Match tasks to agent strengths and preferences

### For System Scalability
- **Modular Design**: Easy to extend with new capabilities
- **Reusable Components**: Modules work across different agent personas
- **Flexible Composition**: Multiple strategies for different use cases

### For Development
- **Clear Separation**: Persona vs functional concerns cleanly separated
- **Easy Testing**: Individual modules can be tested in isolation
- **Rich Debugging**: Composition analysis shows decision reasoning

## Future Extensions

### Planned Enhancements
- **Dynamic Module Loading**: Runtime module registration
- **Learning Integration**: Modules adapt based on outcome feedback
- **Advanced Templates**: Conditional sections within templates
- **Multi-Modal Support**: Visual and audio prompt components

### Integration Opportunities  
- **Registry Deep Integration**: Direct agent card resolution
- **Performance Optimization**: Caching and pre-compilation
- **Analytics Integration**: Prompt effectiveness tracking
- **A2A Protocol**: Enhanced agent-to-agent communication prompts

## Conclusion

The modular prompt composition system provides a sophisticated yet flexible foundation for creating context-aware, persona-authentic prompts that enable effective team building and delegation while maintaining individual agent identity. The system's modular design allows for easy extension and customization while providing powerful capabilities out of the box.
"""
Template strings for prompt composition.

Contains reusable template constants for different types of prompts
and contexts in the Mantis orchestration system.
"""

# Base simulation templates
SIMULATION_BASE_PREFIX = (
    "You are participating in a multi-agent simulation designed to explore complex scenarios "
    "through coordinated interaction between specialized agents."
)

SIMULATION_BASE_SUFFIX = (
    "Please provide a thoughtful response that leverages your specific expertise "
    "and contributes meaningfully to the overall simulation."
)

PERSONA_ADHERENCE_SUFFIX = "Stay true to your persona characteristics and communication style as you respond."

# Team coordination templates
TEAM_COORDINATION_PREFIX = "You are working as part of a multi-agent team to address this challenge."

TEAM_COLLABORATION_SUFFIX = (
    "Collaborate effectively with your team members while bringing your unique perspective to bear."
)

# Task-specific templates
CURRENT_TASK_HEADER = "## Current Task"

TEAM_CONTEXT_HEADER = "## Team Context"

AGENT_CONTEXT_HEADER = "## Agent Context"

# Role-specific templates
LEADER_ROLE_CONTEXT = (
    "As the team leader, you are responsible for guiding the overall direction, "
    "making key decisions, and synthesizing input from team members."
)

FOLLOWER_ROLE_CONTEXT = (
    "As a team member, focus on your specialized expertise while supporting "
    "the overall team objectives and collaborating effectively with others."
)

NARRATOR_ROLE_CONTEXT = (
    "As the narrator, your role is to synthesize different perspectives, "
    "facilitate communication, and help weave together the various contributions "
    "into a coherent narrative."
)

# Strategy-specific templates
RANDOM_TEAM_CONTEXT = (
    "You have been randomly selected for this diverse team. "
    "Bring your unique capabilities to complement the varied perspectives of your teammates."
)

HOMOGENEOUS_TEAM_CONTEXT = (
    "You are part of a specialized team where all members share similar expertise. "
    "Leverage your shared knowledge while providing your own specialized focus within the domain."
)

TAROT_TEAM_CONTEXT = (
    "You are drawn as part of a tarot reading to provide archetypal wisdom and insight. "
    "Respond in character as your archetype, offering the unique perspective and energy you represent."
)

# Error and fallback templates
FALLBACK_AGENT_CONTEXT = "You are an AI agent with your own expertise and perspective."

CAPABILITY_CONTEXT_HEADER = "## Your Capabilities"

EXPERTISE_CONTEXT_HEADER = "## Your Expertise"

# Coordination guidelines
TEAM_COLLABORATION_GUIDELINES = """## Team Collaboration Guidelines

- Stay true to your persona characteristics and communication style
- Leverage your unique expertise while collaborating effectively  
- Build on and complement your teammates' contributions
- Provide insights that demonstrate your specialized knowledge
- Maintain your authentic voice and decision-making approach"""

# Agent coordination constraints
AGENT_COORDINATION_CONSTRAINTS = """## Agent Coordination Protocol

**IMPORTANT**: When coordinating with other agents, you must:

1. **Use Registry Discovery First**: Always use `get_random_agents_from_registry` to discover available agents before any coordination
2. **Only Invoke Registry Agents**: ONLY invoke agents whose names were explicitly returned by registry tools - never assume agents exist
3. **No Fictional Agents**: Never invoke philosophical figures (e.g., "Aristotle", "Socrates") or historical figures as agents unless they appear in the registry
4. **Exact Name Matching**: Use the exact agent names returned by registry tools, not variations or similar names

If agent validation fails, return to registry discovery - do not guess or create agent names."""

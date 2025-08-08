"""
ContextualPrompt template assembly for flexible orchestration.

Implements simple template-based prompt composition using native A2A Message types
instead of complex protobuf schemas. This provides the foundation for rich
contextual orchestration without heavyweight proto dependencies.
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from ..proto import a2a_pb2
from ..proto.mantis.v1 import mantis_persona_pb2


@dataclass
class ContextualPrompt:
    """Simple contextual prompt with template assembly."""
    
    # Core template components
    prefixes: List[str]
    core_content: str
    suffixes: List[str]
    
    # Context data
    agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None
    task_context: Optional[Dict[str, Any]] = None
    
    def assemble(self) -> str:
        """Assemble the final prompt from all components."""
        parts = []
        
        # Add prefixes
        parts.extend(self.prefixes)
        
        # Add agent persona context if available
        if self.agent_card:
            persona_context = self._extract_persona_context()
            if persona_context:
                parts.append(persona_context)
        
        # Add core content
        parts.append(self.core_content)
        
        # Add task context
        if self.task_context:
            task_section = self._format_task_context()
            if task_section:
                parts.append(task_section)
        
        # Add suffixes
        parts.extend(self.suffixes)
        
        return "\n\n".join(filter(None, parts))
    
    def _extract_persona_context(self) -> str:
        """Extract persona information into prompt context."""
        if not self.agent_card:
            return ""
            
        parts = []
        
        # Basic agent info
        if self.agent_card.agent_card:
            parts.append(f"Agent: {self.agent_card.agent_card.name}")
            if self.agent_card.agent_card.description:
                parts.append(f"Role: {self.agent_card.agent_card.description}")
        
        # Persona characteristics
        if self.agent_card.persona_characteristics:
            char = self.agent_card.persona_characteristics
            if char.core_principles:
                parts.append(f"Core Principles: {', '.join(char.core_principles)}")
            if char.decision_framework:
                parts.append(f"Decision Framework: {char.decision_framework}")
            if char.communication_style:
                parts.append(f"Communication Style: {char.communication_style}")
        
        # Domain expertise
        if self.agent_card.domain_expertise:
            exp = self.agent_card.domain_expertise
            if exp.primary_domains:
                parts.append(f"Primary Domains: {', '.join(exp.primary_domains)}")
            if exp.methodologies:
                parts.append(f"Methodologies: {', '.join(exp.methodologies)}")
        
        # Skills summary
        if self.agent_card.skills_summary:
            skills = self.agent_card.skills_summary
            if skills.skill_overview:
                parts.append(f"Skills: {skills.skill_overview}")
            if skills.signature_abilities:
                parts.append(f"Signature Abilities: {', '.join(skills.signature_abilities)}")
        
        if parts:
            return "## Agent Context\n" + "\n".join(parts)
        return ""
    
    def _format_task_context(self) -> str:
        """Format task context information."""
        if not self.task_context:
            return ""
            
        parts = ["## Task Context"]
        
        for key, value in self.task_context.items():
            if value is not None:
                parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(parts)


class ContextualPromptBuilder:
    """Builder for creating ContextualPrompt instances."""
    
    def __init__(self):
        self.prefixes: List[str] = []
        self.core_content: str = ""
        self.suffixes: List[str] = []
        self.agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None
        self.task_context: Dict[str, Any] = {}
    
    def add_prefix(self, prefix: str) -> 'ContextualPromptBuilder':
        """Add a prefix section."""
        self.prefixes.append(prefix)
        return self
    
    def set_core_content(self, content: str) -> 'ContextualPromptBuilder':
        """Set the main prompt content."""
        self.core_content = content
        return self
    
    def add_suffix(self, suffix: str) -> 'ContextualPromptBuilder':
        """Add a suffix section."""
        self.suffixes.append(suffix)
        return self
    
    def with_agent(self, agent_card: mantis_persona_pb2.MantisAgentCard) -> 'ContextualPromptBuilder':
        """Add agent persona context."""
        self.agent_card = agent_card
        return self
    
    def with_task_context(self, **context) -> 'ContextualPromptBuilder':
        """Add task context variables."""
        self.task_context.update(context)
        return self
    
    def build(self) -> ContextualPrompt:
        """Build the final ContextualPrompt."""
        return ContextualPrompt(
            prefixes=self.prefixes.copy(),
            core_content=self.core_content,
            suffixes=self.suffixes.copy(),
            agent_card=self.agent_card,
            task_context=self.task_context.copy()
        )


def create_simulation_prompt(
    query: str,
    agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None,
    context_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> ContextualPrompt:
    """Create a simulation prompt with standard template assembly."""
    
    builder = ContextualPromptBuilder()
    
    # Standard prefix for simulation context
    builder.add_prefix(
        "You are participating in a multi-agent simulation designed to explore complex scenarios "
        "through coordinated interaction between specialized agents."
    )
    
    # Core query content
    builder.set_core_content(f"## Query\n{query}")
    
    # Add agent if provided
    if agent_card:
        builder.with_agent(agent_card)
    
    # Add context information
    if context_id or task_id:
        builder.with_task_context(
            context_id=context_id,
            task_id=task_id
        )
    
    # Standard suffix for response formatting
    builder.add_suffix(
        "Please provide a thoughtful response that leverages your specific expertise "
        "and contributes meaningfully to the overall simulation."
    )
    
    return builder.build()


def create_a2a_message_from_prompt(
    prompt: ContextualPrompt,
    context_id: Optional[str] = None,
    task_id: Optional[str] = None
) -> a2a_pb2.Message:
    """Convert a ContextualPrompt to an A2A Message for protocol compatibility."""
    
    message = a2a_pb2.Message()
    message.role = a2a_pb2.USER  # Set as user role
    
    # Create text part with assembled prompt
    text_part = a2a_pb2.Part()
    text_part.text = prompt.assemble()
    message.content.append(text_part)
    
    # Set context/task IDs if provided
    if context_id:
        message.context_id = context_id
    if task_id:
        message.task_id = task_id
    
    return message
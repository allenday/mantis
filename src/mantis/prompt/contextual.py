"""
ContextualPrompt template assembly for flexible orchestration.

Implements simple template-based prompt composition using native A2A Message types
and AgentInterface integration for rich persona-based context generation.
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
import uuid
from ..proto import a2a_pb2
from ..proto.mantis.v1 import mantis_persona_pb2
from ..observability.logger import get_structured_logger

if TYPE_CHECKING:
    from ..agent import AgentInterface

logger = get_structured_logger(__name__)


class ContextualPrompt:
    """
    Simple contextual prompt with direct A2A Message template generation.
    
    Implements PRD requirement for ContextualPrompt that creates ready-to-use
    A2A Messages through simple template assembly (prefix + base + suffix).
    
    Enhanced with AgentInterface support for rich persona context generation.
    """
    
    def __init__(
        self,
        agent_name: str = "",
        context_content: str = "",
        priority: int = 0,
        prefixes: Optional[List[str]] = None,
        core_content: str = "",
        suffixes: Optional[List[str]] = None,
        agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None,
        agent_interface: Optional["AgentInterface"] = None,
        task_context: Optional[Dict[str, Any]] = None
    ):
        # PRD-specified fields
        self.agent_name = agent_name or (agent_interface.name if agent_interface else "")
        self.context_content = context_content
        self.priority = priority
        
        # Template assembly components
        self.prefixes = prefixes or []
        self.core_content = core_content
        self.suffixes = suffixes or []
        
        # Context data - prefer AgentInterface over raw MantisAgentCard
        self.agent_interface = agent_interface
        self.agent_card = agent_card
        self.task_context = task_context or {}
    
    def assemble(self) -> str:
        """Assemble the final prompt from all components."""
        parts = []
        
        # Add prefixes
        parts.extend(self.prefixes)
        
        # Add agent persona context if available (prefer AgentInterface)
        persona_context = ""
        if self.agent_interface:
            persona_context = self._extract_persona_context_from_interface()
        elif self.agent_card:
            persona_context = self._extract_persona_context()
        
        if persona_context:
            parts.append(persona_context)
        
        # Add core content
        if self.core_content:
            parts.append(self.core_content)
        
        # Add task context
        if self.task_context:
            task_section = self._format_task_context()
            if task_section:
                parts.append(task_section)
        
        # Add suffixes
        parts.extend(self.suffixes)
        
        return "\n\n".join(filter(None, parts))
    
    def create_message_template(
        self,
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        role: int = a2a_pb2.ROLE_USER
    ) -> a2a_pb2.Message:
        """
        Create ready-to-use A2A Message from contextual prompt template.
        
        This implements the PRD requirement for ContextualPrompt.message_template
        that generates A2A Messages without intermediate processing.
        """
        message = a2a_pb2.Message()
        message.message_id = f"ctx-{uuid.uuid4().hex[:12]}"
        message.role = role  # type: ignore[assignment]
        
        # Set context/task IDs if provided
        if context_id:
            message.context_id = context_id
        if task_id:
            message.task_id = task_id
        
        # Create text part with assembled prompt content
        text_part = a2a_pb2.Part()
        
        # Use context_content if specified (PRD field), otherwise fall back to template assembly
        if self.context_content:
            text_part.text = self.context_content
        else:
            # Assemble from template components
            text_part.text = self.assemble()
        
        message.content.append(text_part)
        
        logger.debug(
            "Created A2A Message template",
            structured_data={
                "message_id": message.message_id,
                "agent_name": self.agent_name,
                "context_id": context_id,
                "task_id": task_id,
                "content_length": len(text_part.text),
                "priority": self.priority
            }
        )
        
        return message
    
    def _extract_persona_context_from_interface(self) -> str:
        """Extract persona information from AgentInterface into prompt context."""
        if not self.agent_interface:
            return ""
        
        # Use the rich persona context generation from AgentInterface
        return self.agent_interface.get_persona_context(include_team_info=False)
    
    def _extract_persona_context(self) -> str:
        """Extract persona information from MantisAgentCard into prompt context (legacy)."""
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
    """Builder for creating ContextualPrompt instances with enhanced PRD compliance."""
    
    def __init__(self):
        self.agent_name: str = ""
        self.context_content: str = ""
        self.priority: int = 0
        self.prefixes: List[str] = []
        self.core_content: str = ""
        self.suffixes: List[str] = []
        self.agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None
        self.agent_interface: Optional["AgentInterface"] = None
        self.task_context: Dict[str, Any] = {}
    
    def set_agent_name(self, agent_name: str) -> 'ContextualPromptBuilder':
        """Set target agent identification (PRD field)."""
        self.agent_name = agent_name
        return self
    
    def set_context_content(self, context_content: str) -> 'ContextualPromptBuilder':
        """Set context for customization (PRD field)."""
        self.context_content = context_content
        return self
    
    def set_priority(self, priority: int) -> 'ContextualPromptBuilder':
        """Set ordering priority within groups (PRD field)."""
        self.priority = priority
        return self
    
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
        """Add agent persona context using MantisAgentCard."""
        self.agent_card = agent_card
        # Auto-extract agent name if not set
        if not self.agent_name and agent_card.agent_card:
            self.agent_name = agent_card.agent_card.name
        return self
    
    def with_agent_interface(self, agent_interface: "AgentInterface") -> 'ContextualPromptBuilder':
        """Add agent persona context using AgentInterface (preferred)."""
        self.agent_interface = agent_interface
        # Auto-extract agent name if not set
        if not self.agent_name:
            self.agent_name = agent_interface.name
        return self
    
    def with_task_context(self, **context) -> 'ContextualPromptBuilder':
        """Add task context variables."""
        self.task_context.update(context)
        return self
    
    def build(self) -> ContextualPrompt:
        """Build the final ContextualPrompt with PRD compliance."""
        return ContextualPrompt(
            agent_name=self.agent_name,
            context_content=self.context_content,
            priority=self.priority,
            prefixes=self.prefixes.copy(),
            core_content=self.core_content,
            suffixes=self.suffixes.copy(),
            agent_card=self.agent_card,
            agent_interface=self.agent_interface,
            task_context=self.task_context.copy()
        )
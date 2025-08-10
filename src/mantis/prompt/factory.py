"""
Factory functions for creating ContextualPrompt instances.

Provides convenient functions for creating prompts for different scenarios
using templates and AgentInterface integration.
"""

from typing import Optional, TYPE_CHECKING
from ..proto import a2a_pb2
from ..proto.mantis.v1 import mantis_persona_pb2
from .contextual import ContextualPrompt
from .templates import (
    SIMULATION_BASE_PREFIX,
    SIMULATION_BASE_SUFFIX,
    PERSONA_ADHERENCE_SUFFIX,
    CURRENT_TASK_HEADER,
    AGENT_COORDINATION_CONSTRAINTS,
    CHIEF_OF_STAFF_TEAM_FORMATION,
)
from ..observability.logger import get_structured_logger

if TYPE_CHECKING:
    from ..agent import AgentInterface

logger = get_structured_logger(__name__)


def create_simulation_prompt(
    query: str,
    agent_card: Optional[mantis_persona_pb2.MantisAgentCard] = None,
    context_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> ContextualPrompt:
    """Create a simulation prompt with standard template assembly."""

    # Determine agent name from card
    agent_name = ""
    if agent_card and agent_card.agent_card:
        agent_name = agent_card.agent_card.name

    # Create ContextualPrompt with standard template structure
    return ContextualPrompt(
        agent_name=agent_name,
        context_content="",  # Will use template assembly
        priority=0,
        prefixes=[SIMULATION_BASE_PREFIX],
        core_content=f"## Query\n{query}",
        suffixes=[SIMULATION_BASE_SUFFIX],
        agent_card=agent_card,
        task_context={"context_id": context_id, "task_id": task_id},
    )


def create_simulation_prompt_with_interface(
    query: str, agent_interface: "AgentInterface", context_id: Optional[str] = None, task_id: Optional[str] = None
) -> ContextualPrompt:
    """Create a simulation prompt using AgentInterface (preferred method)."""

    # FIXME: This is a terrible hardcoded hack - agent roles should be determined by
    # agent capabilities, competency scores, or explicit role assignments in the protobuf,
    # not by string matching on agent names. Need proper role detection system.
    agent_name_lower = agent_interface.name.lower()
    is_coordinator = "chief" in agent_name_lower and "staff" in agent_name_lower
    
    # Only apply coordination constraints to coordinator agents
    if is_coordinator:
        # Coordinator gets both team formation guidance and coordination constraints
        suffixes = [CHIEF_OF_STAFF_TEAM_FORMATION, AGENT_COORDINATION_CONSTRAINTS, SIMULATION_BASE_SUFFIX, PERSONA_ADHERENCE_SUFFIX]
        logger.info(f"Added Chief of Staff team formation guidance and coordination constraints for agent: {agent_interface.name}")
    else:
        # Regular team members get standard suffixes without coordination constraints
        suffixes = [SIMULATION_BASE_SUFFIX, PERSONA_ADHERENCE_SUFFIX]
        logger.info(f"Created prompt for team member agent (no coordination constraints): {agent_interface.name}")

    # Create ContextualPrompt with AgentInterface
    return ContextualPrompt(
        agent_name=agent_interface.name,
        context_content="",  # Will use template assembly
        priority=0,
        prefixes=[SIMULATION_BASE_PREFIX],
        core_content=f"{CURRENT_TASK_HEADER}\n{query}",
        suffixes=suffixes,
        agent_interface=agent_interface,
        task_context={"context_id": context_id, "task_id": task_id},
    )


def create_a2a_message_from_prompt(
    prompt: ContextualPrompt, context_id: Optional[str] = None, task_id: Optional[str] = None
) -> a2a_pb2.Message:
    """
    Convert a ContextualPrompt to an A2A Message for protocol compatibility.

    Uses the direct message_template creation method as per PRD requirements.
    """
    logger.info(
        "Creating A2A Message from ContextualPrompt",
        structured_data={
            "agent_name": prompt.agent_name,
            "context_id": context_id,
            "task_id": task_id,
            "priority": prompt.priority,
        },
    )

    # Use the create_message_template method (PRD requirement)
    return prompt.create_message_template(context_id=context_id, task_id=task_id, role=a2a_pb2.ROLE_USER)

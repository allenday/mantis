"""
FastA2A-compatible ADK adapters for Chief of Staff integration.

This module provides bridges between the FastA2A framework and ADK-powered
agents, allowing ADK agents to be served as regular A2A agents alongside
other FastA2A agents in the agent-server deployment.
"""

import uuid
from typing import Any, Dict, Optional

from ..observability.logger import get_structured_logger
from ..proto.mantis.v1 import mantis_core_pb2
from ..proto import a2a_pb2

logger = get_structured_logger(__name__)


class ADKFastA2ABridge:
    """
    Bridge between FastA2A and ADK for Chief of Staff agent.
    
    This adapter allows ADK-powered Chief of Staff to be served as a regular
    FastA2A agent, maintaining compatibility with the A2A protocol while
    providing enhanced orchestration capabilities internally.
    """

    def __init__(self, tools: Optional[Dict[str, Any]] = None) -> None:
        """Initialize ADK-FastA2A bridge."""
        self.tools = tools or {}
        self._initialize_adk_router()
        logger.info("ADK-FastA2A bridge initialized", 
                   structured_data={"tools_count": len(self.tools)})

    def _initialize_adk_router(self) -> None:
        """Initialize the ADK router with tools."""
        from .router import ChiefOfStaffRouter
        
        self.adk_router = ChiefOfStaffRouter(tools=self.tools)
        logger.info("ADK router initialized for FastA2A bridge")

    async def handle_skill_request(self, skill_name: str, request: str, context: Optional[str] = None) -> str:
        """
        Handle FastA2A skill request using ADK orchestration.
        
        This method bridges FastA2A skill requests to ADK routing, allowing
        the Chief of Staff to use advanced orchestration capabilities while
        maintaining FastA2A compatibility.
        
        Args:
            skill_name: The skill being requested (from FastA2A)
            request: The user request/query
            context: Optional context information
            
        Returns:
            Response string compatible with FastA2A expectations
        """
        logger.info(
            "Processing FastA2A skill request via ADK",
            structured_data={
                "skill_name": skill_name,
                "request_length": len(request),
                "has_context": context is not None
            }
        )

        try:
            # Create SimulationInput for ADK routing
            simulation_input = mantis_core_pb2.SimulationInput()
            simulation_input.context_id = f"fasta2a-{uuid.uuid4().hex[:8]}"
            simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
            simulation_input.max_depth = 2  # Enable tools for Chief of Staff coordination
            
            # Build comprehensive query including skill context
            if context:
                simulation_input.query = f"""As Chief of Staff, you are being asked to handle a '{skill_name}' request.

Context: {context}

Request: {request}

Use your coordination and orchestration capabilities to provide a comprehensive response. If this requires multiple perspectives or specialized knowledge, coordinate with appropriate agents to ensure a thorough and strategic response."""
            else:
                simulation_input.query = f"""As Chief of Staff, you are being asked to handle a '{skill_name}' request.

Request: {request}

Use your strategic thinking and coordination capabilities to provide a comprehensive response. If this requires specialized knowledge or multiple perspectives, coordinate with appropriate agents as needed."""

            # Route through ADK
            simulation_output = await self.adk_router.route_simulation(simulation_input)
            
            # Extract response for FastA2A
            if simulation_output.response_message and simulation_output.response_message.content:
                response_text = simulation_output.response_message.content[0].text
                logger.info(
                    "ADK skill request completed successfully",
                    structured_data={
                        "context_id": simulation_output.context_id,
                        "response_length": len(response_text),
                        "final_state": simulation_output.final_state
                    }
                )
                return response_text
            else:
                # Fallback to artifacts if no response message
                if simulation_output.response_artifacts:
                    artifact_texts = []
                    for artifact in simulation_output.response_artifacts:
                        for part in artifact.parts:
                            if part.text:
                                artifact_texts.append(part.text)
                    
                    if artifact_texts:
                        response_text = "\n\n".join(artifact_texts)
                        logger.info("Using artifact content as response")
                        return response_text
                
                # Final fallback
                logger.warning("No response content found in simulation output")
                return f"I apologize, but I was unable to process your {skill_name} request at this time. Please try again."

        except Exception as e:
            logger.error(
                "ADK skill request failed",
                structured_data={
                    "skill_name": skill_name,
                    "error": str(e)
                }
            )
            return f"I encountered an error while processing your {skill_name} request: {str(e)}. Please try again."


class ADKSkillHandler:
    """
    FastA2A skill handler that uses ADK for processing.
    
    This class implements the FastA2A skill handler interface while
    internally using ADK orchestration for enhanced capabilities.
    """

    def __init__(self, skill_name: str, description: str, tools: Optional[Dict[str, Any]] = None) -> None:
        """Initialize ADK skill handler."""
        self.skill_name = skill_name
        self.description = description
        self.bridge = ADKFastA2ABridge(tools=tools)
        logger.info(f"ADK skill handler initialized for '{skill_name}'")

    async def __call__(self, request: str, context: Optional[str] = None) -> str:
        """
        Handle skill request (FastA2A interface).
        
        This method is called by FastA2A when a skill request is made.
        """
        return await self.bridge.handle_skill_request(self.skill_name, request, context)


def create_adk_enhanced_skills(base_skills: list, tools: Optional[Dict[str, Any]] = None) -> list:
    """
    Create ADK-enhanced FastA2A skills from base agent skills.
    
    This function converts regular agent skills to ADK-enhanced skills that
    use the ChiefOfStaffRouter for orchestration while maintaining FastA2A
    compatibility.
    
    Args:
        base_skills: List of base agent skills from AgentCard
        tools: Optional tools dictionary for ADK router
        
    Returns:
        List of ADK-enhanced FastA2A skills
    """
    from fasta2a import Skill
    
    enhanced_skills = []
    
    for base_skill in base_skills:
        # Create ADK skill handler
        skill_handler = ADKSkillHandler(
            skill_name=base_skill.name,
            description=base_skill.description,
            tools=tools
        )
        
        # Create FastA2A skill with ADK handler
        enhanced_skill = Skill(
            name=base_skill.name.lower().replace(" ", "_"),
            description=f"ADK-Enhanced: {base_skill.description}",
            # Use the ADK skill handler instead of regular LLM
            handler=skill_handler,
            # No need for system_prompt or model since we're using custom handler
        )
        
        enhanced_skills.append(enhanced_skill)
        logger.info(f"Created ADK-enhanced skill: {base_skill.name}")
    
    return enhanced_skills
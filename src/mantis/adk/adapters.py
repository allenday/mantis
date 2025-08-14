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
        logger.info("ADK-FastA2A bridge initialized", structured_data={"tools_count": len(self.tools)})

    def _initialize_adk_router(self) -> None:
        """Initialize the ADK router with tools."""
        from .router import AgentRouter

        self.adk_router = AgentRouter(tools=self.tools)
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
                "has_context": context is not None,
            },
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
                response_text = str(simulation_output.response_message.content[0].text)
                logger.info(
                    "ADK skill request completed successfully",
                    structured_data={
                        "context_id": simulation_output.context_id,
                        "response_length": len(response_text),
                        "final_state": simulation_output.final_state,
                    },
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
            logger.error("ADK skill request failed", structured_data={"skill_name": skill_name, "error": str(e)})
            return f"I encountered an error while processing your {skill_name} request: {str(e)}. Please try again."


class ADKSkillHandler:
    """
    FastA2A skill handler that uses ADK for processing.

    This class implements the FastA2A skill handler interface while
    internally using ADK orchestration for enhanced capabilities.

    NOTE: This handler integrates with FastA2A's async task system to avoid
    blocking the A2A message/send endpoint while ADK processing happens.
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
        For ADK integration, we need to ensure this doesn't block the A2A protocol.

        The key insight is that FastA2A will manage the async task lifecycle,
        so this handler should complete efficiently while still providing the
        full ADK orchestration capability.
        """
        try:
            import asyncio

            logger.info(
                f"ADK skill handler called for '{self.skill_name}'",
                structured_data={
                    "skill_name": self.skill_name,
                    "request_length": len(request),
                    "has_context": context is not None,
                },
            )

            # Add timeout protection to prevent hanging A2A requests
            # This ensures the A2A message/send endpoint can return promptly
            timeout_seconds = 25  # Slightly less than ADK router timeout

            result = await asyncio.wait_for(
                self.bridge.handle_skill_request(self.skill_name, request, context), timeout=timeout_seconds
            )

            logger.info(
                f"ADK skill request completed for '{self.skill_name}'",
                structured_data={"skill_name": self.skill_name, "response_length": len(result), "success": True},
            )
            return result

        except asyncio.TimeoutError:
            error_msg = f"ADK processing for {self.skill_name} timed out after {timeout_seconds} seconds. This may indicate an API connectivity issue or complex request requiring more time."
            logger.error(
                f"ADK skill handler timeout for '{self.skill_name}'",
                structured_data={
                    "skill_name": self.skill_name,
                    "timeout_seconds": timeout_seconds,
                    "error_type": "timeout",
                },
            )
            return error_msg

        except Exception as e:
            logger.error(
                f"ADK skill handler error for '{self.skill_name}'",
                structured_data={"skill_name": self.skill_name, "error": str(e), "error_type": type(e).__name__},
            )
            return (
                f"I encountered an error while processing your {self.skill_name} request: {str(e)}. Please try again."
            )


def create_adk_enhanced_skills(base_skills: list, tools: Optional[Dict[str, Any]] = None) -> list:
    """
    Create ADK-enhanced FastA2A skills from base agent skills.

    This function converts regular agent skills to ADK-enhanced skills that
    use the AgentRouter for orchestration while maintaining FastA2A
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
        skill_handler = ADKSkillHandler(skill_name=base_skill.name, description=base_skill.description, tools=tools)

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


def convert_protobuf_to_pydantic_dict(protobuf_obj: Any) -> Dict[str, Any]:
    """
    Convert protobuf object to Pydantic-compatible dictionary.

    This fixes the serialization issue when protobuf objects are passed
    to FastA2A which expects Pydantic-compatible data structures.

    Args:
        protobuf_obj: Protobuf object to convert

    Returns:
        Dictionary that can be serialized by Pydantic
    """
    try:
        from google.protobuf.json_format import MessageToDict

        # Convert protobuf to dictionary
        if hasattr(protobuf_obj, "DESCRIPTOR"):
            # This is a protobuf message
            result = MessageToDict(protobuf_obj, preserving_proto_field_name=True)
            return dict(result)
        else:
            # Handle non-protobuf objects
            if hasattr(protobuf_obj, "__dict__"):
                result = protobuf_obj.__dict__
                return dict(result)
            else:
                # Primitive types - wrap in dict
                return {"value": protobuf_obj}

    except Exception as e:
        logger.warning(f"Failed to convert protobuf object to dict: {e}")
        # Fallback: return basic dict representation
        return {"conversion_error": str(e), "type": str(type(protobuf_obj))}


def create_adk_compatible_agent_params(base_card: Any) -> Dict[str, Any]:
    """
    Create FastA2A-compatible parameters from protobuf AgentCard.

    This function converts protobuf objects to Pydantic-compatible
    structures to avoid serialization errors in FastA2A.

    Args:
        base_card: Protobuf AgentCard object

    Returns:
        Dictionary with FastA2A-compatible parameters
    """
    try:
        # Convert protobuf provider to dictionary
        provider_dict = None
        if hasattr(base_card, "provider") and base_card.provider:
            provider_dict = convert_protobuf_to_pydantic_dict(base_card.provider)

        # Create compatible parameters
        params = {
            "name": base_card.name if hasattr(base_card, "name") else "Unknown Agent",
            "url": base_card.url if hasattr(base_card, "url") else "http://localhost:9000",
            "version": base_card.version if hasattr(base_card, "version") else "1.0.0",
            "description": base_card.description if hasattr(base_card, "description") else "ADK-enhanced agent",
        }

        # Add provider as dictionary if available
        if provider_dict:
            params["provider"] = provider_dict

        logger.info(
            "Created ADK-compatible agent parameters", structured_data={"has_provider": provider_dict is not None}
        )

        return params

    except Exception as e:
        logger.error(f"Failed to create ADK-compatible parameters: {e}")
        # Fallback parameters
        return {
            "name": "ADK Chief of Staff",
            "url": "http://localhost:9053",
            "version": "1.0.0",
            "description": "ADK-enhanced Chief of Staff agent",
        }

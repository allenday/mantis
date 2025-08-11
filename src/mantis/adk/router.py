"""
ChiefOfStaffRouter - ADK-powered orchestration with A2A boundaries

This module implements the ChiefOfStaffRouter using Google ADK's SequentialAgent
for internal orchestration while preserving A2A as the external protocol boundary.
"""

import uuid
from typing import Dict, Any

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

from ..proto.mantis.v1 import mantis_core_pb2
from ..proto import a2a_pb2
from ..observability.logger import get_structured_logger
from ..config import DEFAULT_MODEL

logger = get_structured_logger(__name__)


class ChiefOfStaffRouter:
    """
    ADK-powered Chief of Staff agent router.
    
    Uses ADK SequentialAgent internally for orchestration while maintaining 
    A2A protobuf boundaries for external communication.
    
    Architecture:
    - Input: A2A SimulationInput protobuf
    - Internal: ADK SequentialAgent orchestration
    - Output: A2A SimulationOutput protobuf
    """

    def __init__(self) -> None:
        """Initialize the router with pydantic-ai."""
        self.app_name = "mantis-pydantic-ai-router"
        self._initialize_chief_of_staff_agent()
        logger.info("ChiefOfStaffRouter initialized with pydantic-ai backend")

    def _initialize_chief_of_staff_agent(self) -> None:
        """Initialize the Chief of Staff agent using pydantic-ai."""
        import os
        
        # Ensure API keys are loaded
        if not os.environ.get('ANTHROPIC_API_KEY'):
            from dotenv import load_dotenv
            load_dotenv()
        
        # Parse model from DEFAULT_MODEL (e.g., "anthropic:claude-3-5-haiku-20241022") 
        model_name = DEFAULT_MODEL.split(":", 1)[1] if ":" in DEFAULT_MODEL else DEFAULT_MODEL
        
        # Use pydantic-ai with Anthropic model
        self.anthropic_model = AnthropicModel(model_name)
        
        self.chief_of_staff_agent = Agent(
            model=self.anthropic_model,
            system_prompt="""You are the Chief of Staff, a senior coordinator and strategic advisor.
            
Your role is to:
1. Analyze incoming requests and determine the appropriate response approach
2. Break down complex tasks into manageable components
3. Provide strategic guidance and high-level coordination
4. Synthesize information from multiple sources when needed
5. Ensure clear, actionable communication

You have access to tools for web search, agent invocation, and analysis.
Always think strategically about the user's ultimate goal and provide 
comprehensive, well-structured responses."""
        )
        
        logger.info("Chief of Staff pydantic-ai agent initialized", 
                   structured_data={"model": model_name, "full_model_spec": DEFAULT_MODEL})

    async def route_simulation(
        self, simulation_input: mantis_core_pb2.SimulationInput
    ) -> mantis_core_pb2.SimulationOutput:
        """
        Route simulation through pydantic-ai orchestration.
        
        Args:
            simulation_input: A2A SimulationInput protobuf
            
        Returns:
            A2A SimulationOutput protobuf with pydantic-ai generated response
        """
        logger.info(
            "Routing simulation through pydantic-ai", 
            structured_data={
                "context_id": simulation_input.context_id,
                "query_length": len(simulation_input.query),
                "execution_strategy": simulation_input.execution_strategy,
            }
        )

        try:
            # Execute through pydantic-ai
            result = await self.chief_of_staff_agent.run(simulation_input.query)
            
            # Extract response text
            final_response_text = str(result.output) if result.output else ""

            # Convert back to A2A format
            return self._create_simulation_output(simulation_input, final_response_text)

        except Exception as e:
            logger.error(
                "pydantic-ai routing failed", 
                structured_data={
                    "context_id": simulation_input.context_id,
                    "error": str(e)
                }
            )
            return self._create_error_simulation_output(simulation_input, str(e))

    def _create_simulation_output(
        self, 
        simulation_input: mantis_core_pb2.SimulationInput, 
        response_text: str
    ) -> mantis_core_pb2.SimulationOutput:
        """Create successful A2A SimulationOutput from ADK response."""
        output = mantis_core_pb2.SimulationOutput()
        output.context_id = simulation_input.context_id
        output.final_state = a2a_pb2.TASK_STATE_COMPLETED
        output.execution_strategy = simulation_input.execution_strategy
        
        # Create A2A task
        task = a2a_pb2.Task()
        task.id = f"adk-task-{uuid.uuid4().hex[:12]}"
        task.context_id = simulation_input.context_id
        task.status.state = a2a_pb2.TASK_STATE_COMPLETED
        task.status.timestamp.GetCurrentTime()

        # Create A2A response message
        response_msg = a2a_pb2.Message()
        response_msg.message_id = f"adk-resp-{uuid.uuid4().hex[:12]}"
        response_msg.context_id = simulation_input.context_id
        response_msg.task_id = task.id
        response_msg.role = a2a_pb2.ROLE_AGENT

        # Add response content
        text_part = a2a_pb2.Part()
        text_part.text = response_text
        response_msg.content.append(text_part)

        # Create A2A artifact
        artifact = a2a_pb2.Artifact()
        artifact.artifact_id = f"adk-artifact-{uuid.uuid4().hex[:12]}"
        artifact.name = "chief_of_staff_response"
        artifact.description = "Response from ADK Chief of Staff agent"
        artifact.parts.append(text_part)

        # Assemble output
        task.history.append(response_msg)
        task.artifacts.append(artifact)
        output.simulation_task.CopyFrom(task)
        output.response_message.CopyFrom(response_msg)
        output.response_artifacts.append(artifact)

        logger.info(
            "ADK simulation output created",
            structured_data={
                "context_id": simulation_input.context_id,
                "response_length": len(response_text),
                "artifacts_count": len(output.response_artifacts)
            }
        )

        return output

    def _create_error_simulation_output(
        self, 
        simulation_input: mantis_core_pb2.SimulationInput, 
        error_message: str
    ) -> mantis_core_pb2.SimulationOutput:
        """Create error A2A SimulationOutput."""
        output = mantis_core_pb2.SimulationOutput()
        output.context_id = simulation_input.context_id
        output.final_state = a2a_pb2.TASK_STATE_FAILED
        output.execution_strategy = simulation_input.execution_strategy

        # Create error artifact
        error_artifact = a2a_pb2.Artifact()
        error_artifact.artifact_id = f"adk-error-{uuid.uuid4().hex[:12]}"
        error_artifact.name = "adk_routing_error"
        error_artifact.description = "ADK routing execution error"

        error_part = a2a_pb2.Part()
        error_part.text = f"ADK routing failed: {error_message}"
        error_artifact.parts.append(error_part)

        output.response_artifacts.append(error_artifact)

        return output

    async def health_check(self) -> Dict[str, Any]:
        """Health check for the pydantic-ai router."""
        try:
            # Parse model name for display
            model_name = DEFAULT_MODEL.split(":", 1)[1] if ":" in DEFAULT_MODEL else DEFAULT_MODEL
                
            return {
                "status": "healthy",
                "backend": "pydantic-ai",
                "model": model_name,
                "full_model_spec": DEFAULT_MODEL
            }
        except Exception as e:
            logger.error("pydantic-ai health check failed", structured_data={"error": str(e)})
            return {
                "status": "unhealthy", 
                "error": str(e)
            }
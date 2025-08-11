"""
ChiefOfStaffRouter - ADK-powered orchestration with A2A boundaries

This module implements the ChiefOfStaffRouter using Google ADK's SequentialAgent
for internal orchestration while preserving A2A as the external protocol boundary.
"""

import uuid
from typing import Dict, Any, Optional

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

    def __init__(self, tools: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the router with pydantic-ai and optional tools."""
        self.app_name = "mantis-pydantic-ai-router"
        self.tools = tools or {}
        self._initialize_chief_of_staff_agent()
        logger.info("ChiefOfStaffRouter initialized with pydantic-ai backend", 
                   structured_data={"tools_count": len(self.tools)})

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
        
        # Convert SimulationOrchestrator tools to pydantic-ai compatible format
        pydantic_tools = self._convert_tools_to_pydantic_format()
        
        # Build system prompt based on available tools
        tools_description = self._build_tools_description()
        
        self.chief_of_staff_agent = Agent(
            model=self.anthropic_model,
            system_prompt=f"""You are the Chief of Staff, a senior coordinator and strategic advisor.
            
Your role is to:
1. Analyze incoming requests and determine the appropriate response approach
2. Break down complex tasks into manageable components
3. Provide strategic guidance and high-level coordination
4. Coordinate team formation and delegate tasks to appropriate agents
5. Synthesize information from multiple sources when needed
6. Ensure clear, actionable communication

{tools_description}

Always think strategically about the user's ultimate goal and provide 
comprehensive, well-structured responses. When complex tasks require multiple 
perspectives or specialized knowledge, use your team formation tools to 
coordinate with appropriate agents.""",
            tools=pydantic_tools
        )
        
        logger.info("Chief of Staff pydantic-ai agent initialized", 
                   structured_data={
                       "model": model_name, 
                       "full_model_spec": DEFAULT_MODEL,
                       "pydantic_tools_count": len(pydantic_tools)
                   })

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

    def _convert_tools_to_pydantic_format(self) -> list:
        """Convert SimulationOrchestrator tools to pydantic-ai compatible format."""
        pydantic_tools = []
        
        if not self.tools:
            return pydantic_tools

        from pydantic_ai.tools import Tool
        
        # Helper function to create tool wrappers with proper closure capture
        def create_web_fetch_wrapper(func):
            async def web_fetch_wrapper(url: str) -> str:
                """Fetch content from a URL."""
                return await func(url)
            return Tool(web_fetch_wrapper, name="web_fetch_url")
        
        def create_web_search_wrapper(func):
            async def web_search_wrapper(query: str, num_results: int = 5) -> str:
                """Search the web for information."""
                return await func(query, num_results)
            return Tool(web_search_wrapper, name="web_search")
        
        def create_team_formation_wrapper(func):
            async def team_formation_wrapper(count: int = 3) -> str:
                """Get random agents from registry for team formation."""
                return await func(count)
            return Tool(team_formation_wrapper, name="get_random_agents_from_registry")
        
        def create_invoke_agent_wrapper(func):
            async def invoke_agent_wrapper(agent_name: str, query: str, context: str = "") -> str:
                """Invoke a specific agent by name with a query."""
                return await func(agent_name, query, context)
            return Tool(invoke_agent_wrapper, name="invoke_agent_by_name")
        
        def create_invoke_multiple_wrapper(func):
            async def invoke_multiple_wrapper(agent_names: str, query_template: str, contexts: str = "") -> Dict[str, str]:
                """Invoke multiple agents with a query template."""
                # Convert comma-separated string back to list
                agent_list = [name.strip() for name in agent_names.split(",")]
                context_list = [ctx.strip() for ctx in contexts.split(",") if ctx.strip()] if contexts else None
                return await func(agent_list, query_template, context_list)
            return Tool(invoke_multiple_wrapper, name="invoke_multiple_agents")
        
        def create_random_number_wrapper(func):
            def random_number_wrapper(min_val: int = 1, max_val: int = 100) -> int:
                """Generate a random number for divination purposes."""
                return func(min_val, max_val)
            return Tool(random_number_wrapper, name="get_random_number")
        
        def create_tarot_card_wrapper(func):
            def tarot_card_wrapper() -> str:
                """Draw a tarot card for divination purposes."""
                return func()
            return Tool(tarot_card_wrapper, name="draw_tarot_card")
        
        # Convert each tool to pydantic-ai format
        for tool_name, tool_func in self.tools.items():
            try:
                if tool_name == "web_fetch_url":
                    pydantic_tools.append(create_web_fetch_wrapper(tool_func))
                elif tool_name == "web_search":
                    pydantic_tools.append(create_web_search_wrapper(tool_func))
                elif tool_name == "get_random_agents_from_registry":
                    pydantic_tools.append(create_team_formation_wrapper(tool_func))
                elif tool_name == "invoke_agent_by_name":
                    pydantic_tools.append(create_invoke_agent_wrapper(tool_func))
                elif tool_name == "invoke_multiple_agents":
                    pydantic_tools.append(create_invoke_multiple_wrapper(tool_func))
                elif tool_name == "get_random_number":
                    pydantic_tools.append(create_random_number_wrapper(tool_func))
                elif tool_name == "draw_tarot_card":
                    pydantic_tools.append(create_tarot_card_wrapper(tool_func))
                    
            except Exception as e:
                logger.warning(f"Failed to convert tool {tool_name} to pydantic format: {e}")
                continue
        
        logger.info(f"Converted {len(pydantic_tools)} tools to pydantic-ai format")
        return pydantic_tools

    def _build_tools_description(self) -> str:
        """Build description of available tools for system prompt."""
        if not self.tools:
            return "No tools are currently available."
        
        descriptions = []
        
        if "web_fetch_url" in self.tools:
            descriptions.append("- Web content fetching: Retrieve content from URLs")
        if "web_search" in self.tools:
            descriptions.append("- Web search: Search the internet for information")
        if "get_random_agents_from_registry" in self.tools:
            descriptions.append("- Team formation: Discover and recruit agents with specific skills")
        if "invoke_agent_by_name" in self.tools:
            descriptions.append("- Agent coordination: Delegate tasks to specific agents")
        if "invoke_multiple_agents" in self.tools:
            descriptions.append("- Multi-agent coordination: Coordinate tasks across multiple agents")
        if "get_random_number" in self.tools or "draw_tarot_card" in self.tools:
            descriptions.append("- Divination tools: Random number generation and tarot card drawing")
        
        if descriptions:
            return f"Available tools:\n{chr(10).join(descriptions)}"
        else:
            return "No tools are currently available."
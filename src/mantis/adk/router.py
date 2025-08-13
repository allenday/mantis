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

    def __init__(self, tools: Optional[Dict[str, Any]] = None, orchestrator: Optional[Any] = None) -> None:
        """Initialize the router with pydantic-ai and optional tools."""
        self.app_name = "mantis-pydantic-ai-router"
        self.tools = tools or {}
        self.orchestrator = orchestrator  # Store orchestrator reference to access structured results
        self._initialize_chief_of_staff_agent()
        logger.info(
            "ChiefOfStaffRouter initialized with pydantic-ai backend", structured_data={"tools_count": len(self.tools)}
        )

    def _initialize_chief_of_staff_agent(self) -> None:
        """Initialize the Chief of Staff agent using pydantic-ai."""
        import os

        # Ensure API keys are loaded
        if not os.environ.get("ANTHROPIC_API_KEY"):
            from dotenv import load_dotenv

            load_dotenv()

        # Validate API key availability
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("ANTHROPIC_API_KEY not found - ADK router will fail")
            raise ValueError("ANTHROPIC_API_KEY environment variable is required for ADK integration")

        logger.info("ANTHROPIC_API_KEY found - ADK router can initialize")

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
            tools=pydantic_tools,
        )

        logger.info(
            "Chief of Staff pydantic-ai agent initialized",
            structured_data={
                "model": model_name,
                "full_model_spec": DEFAULT_MODEL,
                "pydantic_tools_count": len(pydantic_tools),
            },
        )

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
            },
        )

        try:
            import asyncio

            # CRITICAL FIX: Increase timeout for team coordination
            # Team coordination requires multiple sequential agent calls (60s each)
            timeout_seconds = 120  # Increased from 30s to support team coordination

            logger.info(
                "🎯 COORDINATION FLOW: Starting ADK processing",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "timeout_seconds": timeout_seconds,
                    "query_length": len(simulation_input.query),
                    "tools_available": len(self.tools),
                    "execution_strategy": simulation_input.execution_strategy,
                    "max_depth": simulation_input.max_depth,
                    "step": "1_adk_processing_start",
                },
            )

            # Execute through pydantic-ai with actual tool execution
            result = await asyncio.wait_for(
                self.chief_of_staff_agent.run(simulation_input.query), timeout=timeout_seconds
            )

            # Extract response text
            final_response_text = str(result.output) if result.output else ""

            logger.info(
                "🎯 COORDINATION FLOW: ADK processing completed successfully",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "response_length": len(final_response_text),
                    "execution_time": f"<{timeout_seconds}s",
                    "step": "2_adk_processing_complete",
                },
            )

            # Convert back to A2A format
            return self._create_simulation_output(simulation_input, final_response_text)

        except asyncio.TimeoutError:
            error_msg = f"ADK processing timed out after {timeout_seconds} seconds"
            logger.error(
                "🎯 COORDINATION FLOW: ADK routing timed out",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "timeout_seconds": timeout_seconds,
                    "step": "2_adk_timeout_error",
                    "likely_cause": "team_coordination_taking_too_long",
                },
            )
            return self._create_error_simulation_output(simulation_input, error_msg)

        except Exception as e:
            # FAIL HARD: Don't handle errors gracefully - let them propagate to expose root cause
            error_type = type(e).__name__
            error_msg = str(e)

            logger.error(
                "🔥 COORDINATION FLOW: ADK routing FAILED HARD - propagating error to expose root cause",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "error": error_msg,
                    "error_type": error_type,
                    "is_tool_error": "tool" in error_msg.lower(),
                    "is_connection_error": any(
                        term in error_msg.lower() for term in ["connection", "timeout", "unreachable"]
                    ),
                    "step": "2_adk_exception_FAIL_HARD",
                },
            )

            # FAIL HARD: Re-raise the exception instead of returning graceful error
            raise

    def _create_simulation_output(
        self, simulation_input: mantis_core_pb2.SimulationInput, response_text: str
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

        # CRITICAL FIX: Add collected structured results from recursive tool calls
        logger.info(
            "🎯 ADK ROUTER: Checking for structured results",
            structured_data={
                "context_id": simulation_input.context_id,
                "orchestrator_exists": self.orchestrator is not None,
                "orchestrator_id": id(self.orchestrator) if self.orchestrator else None,
                "has_structured_results_attr": (
                    hasattr(self.orchestrator, "current_structured_results") if self.orchestrator else False
                ),
                "structured_results_count": (
                    len(self.orchestrator.current_structured_results)
                    if self.orchestrator and hasattr(self.orchestrator, "current_structured_results")
                    else 0
                ),
            },
        )

        if self.orchestrator and hasattr(self.orchestrator, "current_structured_results"):
            logger.info(
                "🎯 ADK ROUTER: Found structured results, adding to output",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "follower_results_count": len(self.orchestrator.current_structured_results),
                    "orchestrator_id": id(self.orchestrator),
                },
            )

            for structured_result in self.orchestrator.current_structured_results:
                output.results.append(structured_result)

            logger.info(
                "Added structured follower results to ADK output",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "follower_results_count": len(self.orchestrator.current_structured_results),
                },
            )

            # Clear the structured results to prevent accumulation across invocations
            self.orchestrator.current_structured_results.clear()
        else:
            logger.warning(
                "🎯 ADK ROUTER: No orchestrator or structured results found",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "orchestrator_exists": self.orchestrator is not None,
                    "has_structured_results": (
                        hasattr(self.orchestrator, "current_structured_results") if self.orchestrator else False
                    ),
                },
            )

        logger.info(
            "ADK simulation output created",
            structured_data={
                "context_id": simulation_input.context_id,
                "response_length": len(response_text),
                "artifacts_count": len(output.response_artifacts),
                "structured_results_count": len(output.results),
            },
        )

        return output

    def _create_error_simulation_output(
        self, simulation_input: mantis_core_pb2.SimulationInput, error_message: str
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
                "full_model_spec": DEFAULT_MODEL,
            }
        except Exception as e:
            logger.error("pydantic-ai health check failed", structured_data={"error": str(e)})
            return {"status": "unhealthy", "error": str(e)}

    def _convert_tools_to_pydantic_format(self) -> list[Any]:
        """Convert SimulationOrchestrator tools to pydantic-ai compatible format."""
        pydantic_tools: list[Any] = []

        if not self.tools:
            return pydantic_tools

        # Helper function to create tool wrappers with proper closure capture
        def create_web_fetch_wrapper(func: Any) -> Any:
            async def web_fetch_wrapper(url: str) -> str:
                """Fetch content from a URL."""
                result = await func(url)
                return str(result)

            return web_fetch_wrapper

        def create_web_search_wrapper(func: Any) -> Any:
            async def web_search_wrapper(query: str, num_results: int = 5) -> str:
                """Search the web for information."""
                result = await func(query, num_results)
                return str(result)

            return web_search_wrapper

        def create_team_formation_wrapper(func: Any) -> Any:
            async def team_formation_wrapper(count: int = 3) -> str:
                """Get random agents from registry for team formation."""
                try:
                    # Get agent dictionaries from the tool function
                    agents_list = await func(count)

                    # Convert agent dictionaries to a formatted string for pydantic-ai compatibility
                    result_lines = [f"🎯 **Selected {len(agents_list)} Agents for Team Assembly**\n"]

                    for i, agent in enumerate(agents_list, 1):
                        result_lines.append(f"**{i}. {agent['name']}** (ID: {agent['agent_id']})")
                        result_lines.append(f"   Description: {agent['description']}")
                        result_lines.append(f"   Role Preference: {agent['role_preference']}")
                        result_lines.append(f"   Available: {'Yes' if agent['available'] else 'No'}")
                        result_lines.append("")

                    result_lines.append(
                        f"✅ **Team Assembly Complete**: {len(agents_list)} agents ready for coordination"
                    )

                    return "\n".join(result_lines)

                except Exception as e:
                    # FAIL HARD - team formation errors should be observable and re-raised
                    logger.error(
                        "🔥 FAIL HARD: Team formation wrapper - propagating raw error",
                        structured_data={"error": str(e), "requested_count": count},
                    )
                    # FAIL HARD: Re-raise original exception without wrapping
                    raise

            return team_formation_wrapper

        def create_invoke_agent_wrapper(func: Any) -> Any:
            async def invoke_agent_wrapper(agent_name: str, query: str, context: str = "") -> str:
                """Invoke a specific agent by name with a query."""
                result = await func(agent_name, query, context)
                return str(result)

            return invoke_agent_wrapper

        def create_invoke_agent_by_url_wrapper(func: Any) -> Any:
            async def invoke_agent_by_url_wrapper(
                agent_url: str, query: str, agent_name: Optional[str] = None, context: Optional[str] = None
            ) -> str:
                """Invoke an agent directly by URL, bypassing registry lookup."""
                try:
                    # Call the function and get result
                    result = await func(agent_url, query, agent_name or None, context or None)

                    # Handle both SimulationOutput protobuf objects and string responses
                    if isinstance(result, str):
                        # String response (likely error case)
                        return f"⚠️ **Direct Agent Response from {agent_name or agent_url}**:\n\n{result}"
                    elif (
                        hasattr(result, "response_message")
                        and result.response_message
                        and result.response_message.content
                    ):
                        # SimulationOutput protobuf object
                        response_text = result.response_message.content[0].text
                        return f"✅ **Direct Agent Response from {agent_name or agent_url}**:\n\n{response_text}"
                    else:
                        return f"⚠️ Agent at {agent_url} responded but generated no content."

                except Exception as e:
                    logger.error(
                        "🔥 FAIL HARD: Direct agent invocation wrapper - propagating raw error",
                        structured_data={"agent_url": agent_url, "error": str(e)},
                    )
                    # FAIL HARD: Re-raise original exception without wrapping
                    raise

            return invoke_agent_by_url_wrapper

        def create_invoke_multiple_wrapper(func: Any) -> Any:
            async def invoke_multiple_wrapper(
                agent_names: str, query_template: str, contexts: str = ""
            ) -> dict[str, str]:
                """Invoke multiple agents with a query template."""
                # Handle both JSON array strings and comma-separated strings
                try:
                    import json

                    # Try to parse as JSON array first
                    if agent_names.strip().startswith("[") and agent_names.strip().endswith("]"):
                        agent_list = json.loads(agent_names)
                    else:
                        # Fall back to comma-separated parsing
                        agent_list = [name.strip() for name in agent_names.split(",")]
                except (json.JSONDecodeError, ValueError):
                    # Fall back to comma-separated parsing if JSON fails
                    agent_list = [name.strip() for name in agent_names.split(",")]

                context_list = [ctx.strip() for ctx in contexts.split(",") if ctx.strip()] if contexts else None
                result = await func(agent_list, query_template, context_list)
                # Ensure result is a dict
                if isinstance(result, dict):
                    return result
                else:
                    return {"error": "Invalid result type", "result": str(result)}

            return invoke_multiple_wrapper

        def create_random_number_wrapper(func: Any) -> Any:
            def random_number_wrapper(min_val: int = 1, max_val: int = 100) -> int:
                """Generate a random number for divination purposes."""
                result = func(min_val, max_val)
                return int(result)

            return random_number_wrapper

        def create_tarot_card_wrapper(func: Any) -> Any:
            def tarot_card_wrapper() -> str:
                """Draw a tarot card for divination purposes."""
                result = func()
                return str(result)

            return tarot_card_wrapper

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
                elif tool_name == "invoke_agent_by_url":
                    pydantic_tools.append(create_invoke_agent_by_url_wrapper(tool_func))
                elif tool_name == "invoke_multiple_agents":
                    pydantic_tools.append(create_invoke_multiple_wrapper(tool_func))
                elif tool_name == "get_random_number":
                    pydantic_tools.append(create_random_number_wrapper(tool_func))
                elif tool_name == "draw_tarot_card":
                    pydantic_tools.append(create_tarot_card_wrapper(tool_func))
                else:
                    logger.warning("Unknown tool type ignored", structured_data={"tool_name": tool_name})

            except Exception as e:
                # Fail fast - tool conversion failure should be observable and fatal
                error_msg = f"Failed to convert tool '{tool_name}' to pydantic-ai format: {str(e)}"
                logger.error("Tool conversion failed", structured_data={"tool_name": tool_name, "error": str(e)})
                raise RuntimeError(error_msg) from e

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
        if "invoke_agent_by_url" in self.tools:
            descriptions.append("- Direct agent coordination: Invoke agents directly by URL (bypasses registry)")
        if "invoke_multiple_agents" in self.tools:
            descriptions.append("- Multi-agent coordination: Coordinate tasks across multiple agents")
        if "get_random_number" in self.tools or "draw_tarot_card" in self.tools:
            descriptions.append("- Divination tools: Random number generation and tarot card drawing")

        if descriptions:
            return f"Available tools:\n{chr(10).join(descriptions)}"
        else:
            return "No tools are currently available."

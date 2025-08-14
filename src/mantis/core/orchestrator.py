"""
Clean Orchestrator Implementation

Single orchestrator class using proper protobuf SimulationOutput with recursive structure.
Eliminates zombie SimpleOrchestrator and wrapper classes.
"""

from typing import Optional, Dict, Any, List
import uuid
import contextvars
from ..prompt import create_simulation_prompt_with_interface
from ..agent import AgentInterface
from ..proto.mantis.v1 import mantis_persona_pb2, mantis_core_pb2
from ..proto import a2a_pb2
from ..config import DEFAULT_MODEL
from ..observability.logger import get_structured_logger
from ..observability.tracing import get_tracer, trace_simulation

logger = get_structured_logger(__name__)
tracer = get_tracer("mantis.orchestrator")

# Context variable to pass agent information to tools
current_agent_context: contextvars.ContextVar[Dict[str, str]] = contextvars.ContextVar(
    "current_agent_context", default={}
)


class SimulationOrchestrator:
    """
    Clean orchestrator implementation using protobuf SimulationOutput for recursive structure.

    Handles both direct execution and nested recursive agent invocation with proper
    artifact aggregation through the protobuf SimulationOutput.results field.
    """

    def __init__(self) -> None:
        self.tools: Dict[str, Any] = {}
        self.active_tasks: Dict[str, a2a_pb2.Task] = {}
        # Track structured results from recursive tool calls for final aggregation
        self.current_structured_results: List[mantis_core_pb2.SimulationOutput] = []
        self._initialize_tools()
        logger.info("SimulationOrchestrator initialized", structured_data={"tools_count": len(self.tools)})

    def _initialize_tools(self) -> None:
        """Initialize tools without global state dependencies."""
        try:
            from ..tools.web_fetch import web_fetch_url
            from ..tools.web_search import web_search
            from ..tools.divination import get_random_number, draw_tarot_card
            from ..tools.team_formation import get_random_agents_from_registry

            # Import the clean recursive invocation tools that take orchestrator as parameter
            from ..tools.recursive_invocation import invoke_agent_by_name, invoke_multiple_agents, invoke_agent_by_url

            # Create bound methods for recursive invocation tools
            # CRITICAL: max_depth must be 0 to prevent infinite recursion
            async def bound_invoke_agent_by_name(
                agent_name: str, query: str, context: Optional[str] = None, max_depth: int = 1
            ) -> str:
                logger.info(
                    "🎯 ORCHESTRATOR: bound_invoke_agent_by_name called",
                    structured_data={
                        "agent_name": agent_name,
                        "query_preview": query[:100] + "..." if len(query) > 100 else query,
                        "orchestrator_id": id(self),
                        "current_results_count_before": len(self.current_structured_results),
                    },
                )

                # Get structured result
                simulation_output = await invoke_agent_by_name(agent_name, query, self, context, max_depth)

                # Store structured result for final aggregation
                self.current_structured_results.append(simulation_output)

                logger.info(
                    "🎯 ORCHESTRATOR: Stored structured result from recursive call",
                    structured_data={
                        "agent_name": agent_name,
                        "orchestrator_id": id(self),
                        "current_results_count_after": len(self.current_structured_results),
                        "simulation_output_context_id": simulation_output.context_id if simulation_output else "None",
                    },
                )

                # Extract text for LLM
                if simulation_output.response_message and simulation_output.response_message.content:
                    return str(simulation_output.response_message.content[0].text)
                return "No response generated"

            async def bound_invoke_multiple_agents(
                agent_names: list[str],
                query_template: str,
                individual_contexts: Optional[list[str]] = None,
                max_depth: int = 1,
            ) -> str:
                logger.info(
                    "🎯 ORCHESTRATOR: bound_invoke_multiple_agents called",
                    structured_data={
                        "agent_names": agent_names,
                        "agent_count": len(agent_names),
                        "query_template_preview": (
                            query_template[:100] + "..." if len(query_template) > 100 else query_template
                        ),
                        "orchestrator_id": id(self),
                        "current_results_count_before": len(self.current_structured_results),
                    },
                )

                # Get structured results
                results_dict = await invoke_multiple_agents(
                    agent_names, query_template, self, individual_contexts, max_depth
                )

                # Store all structured results for final aggregation
                for agent_name, sim_output in results_dict.items():
                    self.current_structured_results.append(sim_output)

                logger.info(
                    "🎯 ORCHESTRATOR: Stored structured results from multiple agents",
                    structured_data={
                        "agent_names": agent_names,
                        "orchestrator_id": id(self),
                        "current_results_count_after": len(self.current_structured_results),
                        "results_added": len(results_dict),
                    },
                )

                # Format results as text for LLM
                text_results = []
                for agent_name, sim_output in results_dict.items():
                    if sim_output.response_message and sim_output.response_message.content:
                        response_text = sim_output.response_message.content[0].text
                        text_results.append(f"**{agent_name}:** {response_text}")
                    else:
                        text_results.append(f"**{agent_name}:** No response generated")

                return "\n\n".join(text_results)

            async def bound_invoke_agent_by_url(
                agent_url: str, query: str, agent_name: str = "", context: str = ""
            ) -> str:
                logger.info(
                    "🎯 ORCHESTRATOR: bound_invoke_agent_by_url called",
                    structured_data={
                        "agent_url": agent_url,
                        "agent_name": agent_name,
                        "query_preview": query[:100] + "..." if len(query) > 100 else query,
                    },
                )

                # Call the direct URL invocation (no orchestrator needed for this one)
                simulation_output = await invoke_agent_by_url(agent_url, query, agent_name or None, context or None)

                # Store structured result for final aggregation
                self.current_structured_results.append(simulation_output)

                logger.info(
                    "🎯 ORCHESTRATOR: Stored structured result from URL invocation",
                    structured_data={
                        "agent_url": agent_url,
                        "agent_name": agent_name,
                        "orchestrator_id": id(self),
                        "current_results_count": len(self.current_structured_results),
                    },
                )

                # Extract text for LLM
                if simulation_output.response_message and simulation_output.response_message.content:
                    return str(simulation_output.response_message.content[0].text)
                return "No response generated"

            self.tools.update(
                {
                    "web_fetch_url": web_fetch_url,
                    "web_search": web_search,
                    "get_random_number": get_random_number,
                    "draw_tarot_card": draw_tarot_card,
                    "get_random_agents_from_registry": get_random_agents_from_registry,
                    "invoke_agent_by_name": bound_invoke_agent_by_name,
                    "invoke_agent_by_url": bound_invoke_agent_by_url,
                    "invoke_multiple_agents": bound_invoke_multiple_agents,
                }
            )

            logger.debug("Tools initialized", structured_data={"tools": list(self.tools.keys())})

        except Exception as e:
            logger.error("Failed to initialize tools", structured_data={"error": str(e)})
            raise

    @trace_simulation(context_id="", execution_strategy="direct")  # Will be updated dynamically
    async def execute_simulation(
        self, simulation_input: mantis_core_pb2.SimulationInput
    ) -> mantis_core_pb2.SimulationOutput:
        """
        Execute SimulationInput and return protobuf SimulationOutput with recursive results.

        Args:
            simulation_input: Protobuf SimulationInput with query and agent specs

        Returns:
            Protobuf SimulationOutput with nested results from recursive agent calls
        """
        logger.info(
            "Starting simulation execution",
            structured_data={
                "context_id": simulation_input.context_id,
                "query_length": len(simulation_input.query),
                "agent_specs": len(simulation_input.agents),
            },
        )

        # Add distributed tracing context
        with tracer.start_span(
            "simulation.execute",
            attributes={
                "simulation.context_id": simulation_input.context_id,
                "simulation.query_length": len(simulation_input.query),
                "simulation.agent_specs": len(simulation_input.agents),
                "simulation.execution_strategy": str(simulation_input.execution_strategy),
                "mantis.component": "orchestrator",
                "mantis.operation": "execute_simulation",
            },
        ):
            tracer.add_agent_context("orchestrator", "SimulationOrchestrator", simulation_input.context_id)

        try:
            # CRITICAL FIX: Use specified agent if provided, otherwise use Chief of Staff
            target_agent_card = None
            if simulation_input.agents and len(simulation_input.agents) > 0:
                agent_spec = simulation_input.agents[0]
                if agent_spec.HasField("agent") and agent_spec.agent:
                    # Load specific agent by name from registry using the agent info in the spec
                    from ..tools.agent_registry import get_agent_by_name

                    try:
                        # Get the full MantisAgentCard from registry using the agent name
                        target_agent_card = await get_agent_by_name(agent_spec.agent.name)

                        logger.info(
                            f"Using specified agent from registry: {agent_spec.agent.name}",
                            structured_data={
                                "agent_name": agent_spec.agent.name,
                                "agent_id": agent_spec.agent.agent_id,
                                "context_id": simulation_input.context_id,
                            },
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to load specified agent '{agent_spec.agent.name}' from registry: {e}, falling back to Chief of Staff",
                            structured_data={"context_id": simulation_input.context_id},
                        )
                        target_agent_card = None

            # Fallback to Chief of Staff for coordination if no specific agent provided
            if not target_agent_card:
                target_agent_card = await self._get_chief_of_staff_agent()
                logger.info(
                    "Using Chief of Staff agent (no specific agent provided or fallback)",
                    structured_data={"context_id": simulation_input.context_id},
                )

            # Execute the simulation
            disable_tools = simulation_input.max_depth <= 0
            logger.info(
                "Executing simulation with depth control",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "max_depth": simulation_input.max_depth,
                    "disable_tools": disable_tools,
                    "depth_logic": f"disable_tools = ({simulation_input.max_depth} <= 0) = {disable_tools}",
                },
            )

            # Check if we should route through ADK
            if self._should_use_adk_routing(target_agent_card, disable_tools):
                logger.info(
                    "Routing simulation through ADK",
                    structured_data={
                        "context_id": simulation_input.context_id,
                        "agent_name": target_agent_card.agent_card.name,
                    },
                )

                from ..adk.router import AgentRouter

                # Pass tools to ADK router (empty dict if tools disabled)
                adk_tools = {} if disable_tools else self.tools
                adk_router = AgentRouter(tools=adk_tools, orchestrator=self)

                return await adk_router.route_simulation(simulation_input)

            # Traditional execution path
            task = await self._execute_task_with_agent(
                query=simulation_input.query,
                agent_card=target_agent_card,
                context_id=simulation_input.context_id,
                max_depth=simulation_input.max_depth,
                disable_tools=disable_tools,
            )

            # Convert to protobuf SimulationOutput
            return await self._create_simulation_output(task, simulation_input)

        except Exception as e:
            logger.error(
                "Simulation execution failed",
                structured_data={"context_id": simulation_input.context_id, "error": str(e)},
            )
            # Create error response
            return self._create_error_simulation_output(simulation_input, str(e))

    async def _execute_task_with_agent(
        self,
        query: str,
        agent_card: mantis_persona_pb2.MantisAgentCard,
        context_id: str,
        max_depth: int = 3,
        disable_tools: bool = False,
    ) -> a2a_pb2.Task:
        """Execute a task with the specified agent."""

        task_id = f"sim-{context_id}"
        agent_interface = AgentInterface(agent_card)

        # Create and track task
        task = a2a_pb2.Task()
        task.id = task_id
        task.context_id = context_id
        task.status.state = a2a_pb2.TASK_STATE_WORKING
        task.status.timestamp.GetCurrentTime()

        self.active_tasks[task_id] = task

        # Set agent context for tools
        agent_context = {"agent_name": agent_interface.name, "task_id": task_id, "context_id": context_id}

        logger.info(
            f"Task execution starting with tools {'DISABLED' if disable_tools else 'ENABLED'}",
            structured_data={
                "context_id": context_id,
                "agent_name": agent_interface.name,
                "max_depth": max_depth,
                "disable_tools": disable_tools,
                "tools_available": len(self.tools) if not disable_tools else 0,
            },
        )

        # Execute with agent context
        try:
            from ..llm.structured_extractor import get_structured_extractor

            # Create prompt
            prompt = create_simulation_prompt_with_interface(
                query=query, agent_interface=agent_interface, context_id=context_id, task_id=task_id
            )

            # Create structured extractor
            extractor = get_structured_extractor(model_spec=DEFAULT_MODEL)

            # Prepare tools for LLM (only if not disabled)
            tools_for_llm = {} if disable_tools else self.tools

            # Run in agent context
            token = current_agent_context.set(agent_context)
            try:
                response_text = await extractor.extract_text_response_with_tools(
                    prompt=prompt.assemble(), query=query, model=DEFAULT_MODEL, tools=tools_for_llm
                )
            finally:
                current_agent_context.reset(token)

            # Create response message and artifact
            response_msg = a2a_pb2.Message()
            response_msg.message_id = f"resp-{uuid.uuid4().hex[:12]}"
            response_msg.context_id = context_id
            response_msg.task_id = task_id
            response_msg.role = a2a_pb2.ROLE_AGENT

            # Add response content
            text_part = a2a_pb2.Part()
            text_part.text = response_text
            response_msg.content.append(text_part)

            # Create artifact
            artifact = a2a_pb2.Artifact()
            artifact.artifact_id = f"artifact-{uuid.uuid4().hex[:12]}"
            artifact.name = f"{agent_interface.name}_response"
            artifact.description = f"Response from {agent_interface.name}"
            artifact.parts.append(text_part)

            # Add to task
            task.history.append(response_msg)
            task.artifacts.append(artifact)
            task.status.state = a2a_pb2.TASK_STATE_COMPLETED

            logger.info(
                "Task completed successfully",
                structured_data={
                    "task_id": task_id,
                    "agent_name": agent_interface.name,
                    "artifacts_count": len(task.artifacts),
                },
            )

            return task

        except Exception as e:
            task.status.state = a2a_pb2.TASK_STATE_FAILED
            logger.error("Task execution failed", structured_data={"task_id": task_id, "error": str(e)})
            raise

    async def _create_simulation_output(
        self, task: a2a_pb2.Task, simulation_input: mantis_core_pb2.SimulationInput
    ) -> mantis_core_pb2.SimulationOutput:
        """Create protobuf SimulationOutput from completed task."""

        output = mantis_core_pb2.SimulationOutput()
        output.context_id = task.context_id
        output.final_state = task.status.state
        output.simulation_task.CopyFrom(task)

        # Add response message
        if task.history:
            output.response_message.CopyFrom(task.history[-1])

        # Add artifacts
        for artifact in task.artifacts:
            output.response_artifacts.append(artifact)

        # Set execution details
        output.recursion_depth = simulation_input.max_depth
        output.execution_strategy = simulation_input.execution_strategy

        # Note: Nested results will be added by recursive invocation tools
        # through the add_nested_result method

        return output

    def add_nested_result(self, parent_task_id: str, nested_output: mantis_core_pb2.SimulationOutput) -> None:
        """Add nested SimulationOutput to parent task's artifacts and track for final output."""
        # This will be called by recursive invocation tools to aggregate nested results
        # For now, artifacts are added directly to parent task - proper nesting comes next
        pass

    def _create_error_simulation_output(
        self, simulation_input: mantis_core_pb2.SimulationInput, error_message: str
    ) -> mantis_core_pb2.SimulationOutput:
        """Create error SimulationOutput."""

        output = mantis_core_pb2.SimulationOutput()
        output.context_id = simulation_input.context_id
        output.final_state = a2a_pb2.TASK_STATE_FAILED

        # Create error artifact
        error_artifact = a2a_pb2.Artifact()
        error_artifact.artifact_id = f"error-{uuid.uuid4().hex[:12]}"
        error_artifact.name = "simulation_error"
        error_artifact.description = "Simulation execution error"

        error_part = a2a_pb2.Part()
        error_part.text = f"Simulation failed: {error_message}"
        error_artifact.parts.append(error_part)

        output.response_artifacts.append(error_artifact)

        return output

    async def _get_chief_of_staff_agent(self) -> mantis_persona_pb2.MantisAgentCard:
        """Get Chief of Staff agent card from registry - fail fast if unavailable."""
        from ..tools.agent_registry import list_all_agents

        logger.info("Loading Chief of Staff agent from registry")

        try:
            # Get all agents from registry - fail fast if unavailable
            all_agents = await list_all_agents()

            if not all_agents or len(all_agents) == 0:
                logger.error("Registry is empty - no agents available")
                raise ValueError("Registry is empty - no agents available")

        except Exception as registry_error:
            logger.error(
                "Registry access failed - system cannot operate without agent registry",
                structured_data={"error_type": type(registry_error).__name__, "error_message": str(registry_error)},
            )
            raise RuntimeError(f"Registry access failed: {registry_error}") from registry_error

        # Look for the actual Chief of Staff agent first
        chief_of_staff = None
        for agent in all_agents:
            agent_name = agent.agent_card.name.lower()
            if "chief" in agent_name and "staff" in agent_name:
                chief_of_staff = agent
                break

        if chief_of_staff:
            selected_agent = chief_of_staff
            logger.info("Found and selected Chief of Staff agent from registry")
        else:
            # Fail fast if Chief of Staff not found
            logger.error("Chief of Staff agent not found in registry - system requires Chief of Staff for coordination")
            raise ValueError("Chief of Staff agent not found in registry")

        logger.info(f"Selected agent: {selected_agent.agent_card.name}")

        # Return the MantisAgentCard directly - fail fast if validation fails
        return selected_agent

    def get_task_by_id(self, task_id: str) -> Optional[a2a_pb2.Task]:
        """Get active task by ID."""
        return self.active_tasks.get(task_id)

    def get_available_tools(self) -> Dict[str, Any]:
        """Get available tools for use by agents."""
        return self.tools.copy()

    def get_tasks_by_context(self, context: str) -> list[a2a_pb2.Task]:
        """Get tasks by context - compatibility method."""
        # For compatibility, return filtered active tasks
        matching_tasks = []
        for task in self.active_tasks.values():
            if hasattr(task, "context") and context in task.context:
                matching_tasks.append(task)
        return matching_tasks

    def _should_use_adk_routing(self, agent_card: mantis_persona_pb2.MantisAgentCard, disable_tools: bool) -> bool:
        """Determine if simulation should be routed through ADK."""
        import os

        # Check if ADK is enabled via environment variable
        adk_enabled = os.getenv("ENABLE_ADK", "false").lower() == "true"
        if not adk_enabled:
            return False

        # Don't use ADK if tools are disabled (max_depth <= 0)
        if disable_tools:
            logger.debug("ADK routing disabled due to tools being disabled")
            return False

        # Check if agent is Chief of Staff
        agent_name = agent_card.agent_card.name.lower()
        is_chief_of_staff = "chief" in agent_name and "staff" in agent_name

        logger.debug(
            "ADK routing decision",
            structured_data={
                "adk_enabled": adk_enabled,
                "disable_tools": disable_tools,
                "agent_name": agent_card.agent_card.name,
                "is_chief_of_staff": is_chief_of_staff,
                "will_use_adk": is_chief_of_staff and adk_enabled and not disable_tools,
            },
        )

        return is_chief_of_staff

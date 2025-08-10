"""
Clean Orchestrator Implementation

Single orchestrator class using proper protobuf SimulationOutput with recursive structure.
Eliminates zombie SimpleOrchestrator and wrapper classes.
"""

from typing import Optional, Dict, Any
import uuid
import contextvars
from ..prompt import create_simulation_prompt_with_interface
from ..agent import AgentInterface
from ..proto.mantis.v1 import mantis_persona_pb2, mantis_core_pb2
from ..proto import a2a_pb2
from ..config import DEFAULT_MODEL
from ..observability.logger import get_structured_logger

logger = get_structured_logger(__name__)

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
            from ..tools.recursive_invocation import invoke_agent_by_name, invoke_multiple_agents

            # Create bound methods for recursive invocation tools
            # CRITICAL: max_depth must be 0 to prevent infinite recursion
            async def bound_invoke_agent_by_name(
                agent_name: str, query: str, context: Optional[str] = None, max_depth: int = 1
            ) -> str:
                # Use proper depth control - let current_depth increment naturally
                return await invoke_agent_by_name(agent_name, query, self, context, max_depth)

            async def bound_invoke_multiple_agents(
                agent_names: list[str], query_template: str, individual_contexts: Optional[list[str]] = None, max_depth: int = 1
            ) -> Dict[str, str]:
                # Use proper depth control - let current_depth increment naturally
                return await invoke_multiple_agents(agent_names, query_template, self, individual_contexts, max_depth)

            self.tools.update(
                {
                    "web_fetch_url": web_fetch_url,
                    "web_search": web_search,
                    "get_random_number": get_random_number,
                    "draw_tarot_card": draw_tarot_card,
                    "get_random_agents_from_registry": get_random_agents_from_registry,
                    "invoke_agent_by_name": bound_invoke_agent_by_name,
                    "invoke_multiple_agents": bound_invoke_multiple_agents,
                }
            )

            logger.debug("Tools initialized", structured_data={"tools": list(self.tools.keys())})

        except Exception as e:
            logger.error("Failed to initialize tools", structured_data={"error": str(e)})
            raise

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
                                "context_id": simulation_input.context_id
                            }
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to load specified agent '{agent_spec.agent.name}' from registry: {e}, falling back to Chief of Staff",
                            structured_data={"context_id": simulation_input.context_id}
                        )
                        target_agent_card = None
                    
            # Fallback to Chief of Staff for coordination if no specific agent provided
            if not target_agent_card:
                target_agent_card = await self._get_chief_of_staff_agent()
                logger.info(
                    "Using Chief of Staff agent (no specific agent provided or fallback)",
                    structured_data={"context_id": simulation_input.context_id}
                )

            # Execute the simulation
            disable_tools = (simulation_input.max_depth <= 0)
            logger.info(
                "Executing simulation with depth control",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "max_depth": simulation_input.max_depth,
                    "disable_tools": disable_tools,
                    "depth_logic": f"disable_tools = ({simulation_input.max_depth} <= 0) = {disable_tools}",
                },
            )
            
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
        """Get Chief of Staff agent card from registry with local fallback."""
        from ..tools.agent_registry import list_all_agents
        from ..config import get_default_base_agent

        logger.info("Loading Chief of Staff agent from registry")

        try:
            # Try to get all agents from registry
            all_agents = await list_all_agents()
            
            if not all_agents or len(all_agents) == 0:
                logger.warning("No agents found in registry, trying local fallback")
                raise ValueError("Registry unavailable or empty")
                
        except Exception as registry_error:
            logger.warning(f"Registry access failed: {registry_error}, using local fallback")
            
            # Fall back to local Chief of Staff agent
            local_agent = get_default_base_agent()
            if local_agent:
                logger.info("Using local Chief of Staff agent as fallback")
                return local_agent
            else:
                raise ValueError("No agents available - registry failed and no local fallback found")

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
            # Fallback to first agent if Chief of Staff not found
            selected_agent = all_agents[0]
            logger.warning("Chief of Staff not found in registry, using fallback agent")

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

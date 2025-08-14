"""
MantisService - Primary orchestration service implementing PRD requirements.

Provides the main interface for context-threaded simulation execution,
multi-agent coordination, and team response synthesis as specified in
the Mantis Product Requirements Document.

Uses existing orchestrator infrastructure with enhanced context threading
and native A2A protocol support through SimulationOutput wrapper.
"""

from typing import List, Dict, Any
import uuid

from .orchestrator import SimulationOrchestrator
from ..prompt import ContextualPrompt, create_simulation_prompt_with_interface
from ..agent import AgentInterface
from .team import TeamFactory
from ..proto.mantis.v1 import mantis_core_pb2
from ..proto import a2a_pb2
from google.protobuf import timestamp_pb2
from ..observability.logger import get_structured_logger

logger = get_structured_logger(__name__)


# Using proper protobuf types from mantis_core_pb2 as per PRD requirements


class MantisService:
    """
    Primary orchestration service with deep A2A integration.

    Implements PRD core functional requirements:
    - FR-1: Context-Threaded Simulation Execution
    - FR-2: Multi-Agent Team Coordination
    - FR-3: Semantic Agent Discovery
    - FR-4: Real-time Orchestration Monitoring

    Follows coding guidelines: fail fast, fail clearly, fail observably.
    """

    def __init__(self) -> None:
        try:
            self.orchestrator = SimulationOrchestrator()
            logger.info(
                "Initialized MantisService successfully",
                structured_data={"version": "1.0", "orchestrator_tools": len(self.orchestrator.get_available_tools())},
            )
        except Exception as e:
            logger.error(
                "Failed to initialize MantisService",
                structured_data={"error_type": type(e).__name__, "error_message": str(e)},
            )
            raise RuntimeError(f"MantisService initialization failed: {str(e)}") from e

    async def process_simulation_input(
        self, simulation_input: mantis_core_pb2.SimulationInput, agent_interface: AgentInterface
    ) -> mantis_core_pb2.SimulationOutput:
        """
        Process individual agent simulation with A2A context threading (FR-1).

        Implements PRD requirement for context-threaded simulation execution
        with native A2A Message/Artifact/TaskState support.

        Args:
            simulation_input: SimulationInput with context_id, query, input_artifacts
            agent_interface: AgentInterface providing persona and capabilities

        Returns:
            SimulationOutput with A2A Message, Artifacts, Task, and TaskState
        """
        # Validation for protobuf inputs
        if not simulation_input.context_id or not simulation_input.context_id.strip():
            raise ValueError("context_id cannot be empty")
        if not simulation_input.query or not simulation_input.query.strip():
            raise ValueError("query cannot be empty")

        logger.info(
            "Processing simulation input",
            structured_data={
                "context_id": simulation_input.context_id,
                "parent_context_id": simulation_input.parent_context_id,
                "query_length": len(simulation_input.query),
                "input_artifacts_count": len(simulation_input.input_artifacts),
                "execution_strategy": simulation_input.execution_strategy,
            },
        )

        try:
            # Execute simulation using current orchestrator interface
            completed_task = await self.orchestrator.execute_simulation(simulation_input)

            # completed_task is already a SimulationOutput
            proto_output = completed_task

            logger.info(
                "Completed simulation processing",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "task_id": (
                        completed_task.simulation_task.id if completed_task.HasField("simulation_task") else "unknown"
                    ),
                    "final_state": completed_task.final_state,
                    "response_artifacts_count": len(proto_output.response_artifacts),
                },
            )

            return proto_output

        except Exception as e:
            logger.error(
                "Failed to process simulation input",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            # Create error response with proper protobuf construction
            proto_output = mantis_core_pb2.SimulationOutput()
            proto_output.context_id = simulation_input.context_id
            proto_output.final_state = a2a_pb2.TASK_STATE_FAILED

            # Create error message
            error_msg = a2a_pb2.Message()
            error_msg.message_id = f"error-{uuid.uuid4().hex[:12]}"
            error_msg.context_id = simulation_input.context_id
            error_msg.role = a2a_pb2.ROLE_AGENT

            # Create error part with text content
            error_part = a2a_pb2.Part()
            error_part.text = f"Simulation processing failed: {str(e)}"
            error_msg.content.append(error_part)

            proto_output.response_message.CopyFrom(error_msg)

            return proto_output

    def get_contextual_execution_status(self, context_id: str) -> List[mantis_core_pb2.SimulationOutput]:
        """
        Get execution status for all tasks in a context (context threading support).

        Implements context hierarchy tracking for conversation continuity.
        """
        logger.debug("Retrieving contextual execution status", structured_data={"context_id": context_id})

        # Get all tasks for this context
        context_tasks = self.orchestrator.get_tasks_by_context(context_id)

        results = []
        for task in context_tasks:
            # Convert to protobuf format
            proto_output = mantis_core_pb2.SimulationOutput()
            proto_output.context_id = task.context_id
            proto_output.final_state = task.status.state

            # Copy the A2A task
            proto_output.simulation_task.CopyFrom(task)

            # Add final response from task history if available
            if task.history:
                latest_message = task.history[-1]
                proto_output.response_message.CopyFrom(latest_message)

            # Copy artifacts from the task
            for artifact in task.artifacts:
                proto_output.response_artifacts.append(artifact)

            results.append(proto_output)

        logger.info(
            "Retrieved contextual execution status",
            structured_data={"context_id": context_id, "task_count": len(results)},
        )

        return results

    async def create_contextual_prompt_for_agent(
        self, base_query: str, agent_interface: AgentInterface, priority: int = 0
    ) -> ContextualPrompt:
        """
        Create contextual prompt with agent-specific customization.

        Supports the PRD template assembly pattern: prefix + base + suffix.
        """
        logger.debug(
            "Creating contextual prompt for agent",
            structured_data={"agent_name": agent_interface.name, "query_length": len(base_query), "priority": priority},
        )

        # Use enhanced ContextualPrompt with AgentInterface
        prompt = create_simulation_prompt_with_interface(query=base_query, agent_interface=agent_interface)

        logger.info(
            "Created contextual prompt",
            structured_data={
                "agent_name": agent_interface.name,
                "priority": priority,
                "assembled_length": len(prompt.assemble()),
            },
        )

        return prompt

    async def process_team_execution_request(
        self, team_request: mantis_core_pb2.TeamExecutionRequest
    ) -> mantis_core_pb2.TeamExecutionResult:
        """
        Process TeamExecutionRequest with ContextualPrompt assembly (FR-2).

        Implements PRD requirement for multi-agent team coordination using
        the modular prompt composition system and AgentInterface encapsulation.

        Args:
            team_request: TeamExecutionRequest with context_id, query, team_formation_strategy

        Returns:
            TeamExecutionResult with coordinated team responses
        """
        if not team_request.simulation_input.context_id or not team_request.simulation_input.context_id.strip():
            raise ValueError("team execution context_id cannot be empty")
        if not team_request.simulation_input.query or not team_request.simulation_input.query.strip():
            raise ValueError("team execution query cannot be empty")

        logger.info(
            "Processing team execution request",
            structured_data={
                "context_id": team_request.simulation_input.context_id,
                "formation_strategy": team_request.formation_strategy,
                "query_length": len(team_request.simulation_input.query),
                "team_size": team_request.team_size,
            },
        )

        try:
            # Create team using TeamFactory
            team_factory = TeamFactory()
            team = team_factory.create_team(team_request.formation_strategy)

            # Use the SimulationInput from the team request
            simulation_input = team_request.simulation_input

            # Select team members using registry
            team_members = await team.select_team_members(
                simulation_input=simulation_input, team_size=team_request.team_size
            )

            # Execute each team member with AgentInterface
            team_responses = []
            for i, agent_interface in enumerate(team_members):
                try:
                    # Process individual simulation for team member
                    member_output = await self.process_simulation_input(
                        simulation_input=simulation_input, agent_interface=agent_interface
                    )

                    team_responses.append(member_output)

                    logger.debug(
                        "Completed team member execution",
                        structured_data={
                            "context_id": getattr(team_request, "context_id", "unknown"),  # type: ignore[attr-defined]
                            "member_index": i,
                            "agent_name": agent_interface.name,
                            "final_state": member_output.final_state,
                        },
                    )

                except Exception as member_error:
                    logger.error(
                        "Team member execution failed - failing entire team execution fast",
                        structured_data={
                            "context_id": team_request.simulation_input.context_id,
                            "member_index": i,
                            "agent_name": agent_interface.name,
                            "error_type": type(member_error).__name__,
                            "error_message": str(member_error),
                        },
                    )
                    # Fail fast - team execution requires all members to succeed
                    raise RuntimeError(
                        f"Team member execution failed for {agent_interface.name}: {str(member_error)}"
                    ) from member_error

            # Create TeamExecutionResult
            team_result = mantis_core_pb2.TeamExecutionResult()
            team_result.context_id = team_request.simulation_input.context_id
            team_result.execution_strategy = team_request.preferred_execution_strategy

            # Add all team member messages and tasks
            for response in team_responses:
                if response.simulation_task:
                    team_result.member_tasks.append(response.simulation_task)
                if response.response_message:
                    team_result.member_messages.append(response.response_message)
                for artifact in response.response_artifacts:
                    team_result.member_artifacts.append(artifact)

            # Set overall execution status
            if team_responses:
                successful_responses = sum(1 for r in team_responses if r.final_state == a2a_pb2.TASK_STATE_COMPLETED)
                if successful_responses == len(team_responses):
                    team_result.team_final_state = a2a_pb2.TASK_STATE_COMPLETED
                else:
                    team_result.team_final_state = a2a_pb2.TASK_STATE_FAILED
            else:
                team_result.team_final_state = a2a_pb2.TASK_STATE_FAILED

            logger.info(
                "Completed team execution request",
                structured_data={
                    "context_id": team_request.simulation_input.context_id,
                    "team_size": len(team_members),
                    "successful_responses": len(team_responses),
                    "team_final_state": team_result.team_final_state,
                },
            )

            return team_result

        except Exception as e:
            logger.error(
                "Failed to process team execution request",
                structured_data={
                    "context_id": team_request.simulation_input.context_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )

            # Create error response
            error_result = mantis_core_pb2.TeamExecutionResult()
            error_result.context_id = team_request.simulation_input.context_id
            error_result.team_final_state = a2a_pb2.TASK_STATE_FAILED
            error_result.execution_strategy = team_request.preferred_execution_strategy

            raise RuntimeError(f"Team execution failed: {str(e)}") from e

    def get_active_contexts(self) -> List[str]:
        """Get all active context IDs for monitoring purposes."""
        context_ids = set()

        for task in self.orchestrator.active_tasks.values():
            if task.context_id:
                context_ids.add(task.context_id)

        logger.debug("Retrieved active contexts", structured_data={"context_count": len(context_ids)})

        return list(context_ids)

    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status for monitoring."""
        active_tasks = len(self.orchestrator.active_tasks)
        active_contexts = len(self.get_active_contexts())
        available_tools = len(self.orchestrator.get_available_tools())

        health_status = {
            "status": "healthy",
            "active_tasks": active_tasks,
            "active_contexts": active_contexts,
            "available_tools": available_tools,
            "timestamp": timestamp_pb2.Timestamp(),
        }

        # Set current timestamp
        try:
            health_status["timestamp"].GetCurrentTime()  # type: ignore[attr-defined]
        except AttributeError:
            # Method may not be available in all protobuf versions
            import time

            health_status["timestamp"].seconds = int(time.time())  # type: ignore[attr-defined]

        logger.debug("Retrieved service health status", structured_data=health_status)

        return health_status

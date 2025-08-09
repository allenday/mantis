"""
gRPC Service Implementation for Mantis

Implements the MantisServiceServicer with proper ProcessSimulationInput handling
for recursive agent invocation through the simulation architecture.
"""

import asyncio
import logging
import grpc
from grpc import aio

from ..proto.mantis.v1 import mantis_core_pb2, mantis_core_pb2_grpc
from ..core.orchestrator import SimulationOrchestrator

logger = logging.getLogger(__name__)


class MantisServiceServicer(mantis_core_pb2_grpc.MantisServiceServicer):
    """
    Implements the Mantis gRPC service for multi-agent orchestration.

    Provides recursive agent invocation through ProcessSimulationInput,
    enabling the Chief of Staff to coordinate team formation and execution.
    """

    def __init__(self):
        """Initialize the service with orchestrator."""
        self.orchestrator = SimulationOrchestrator()
        logger.info("MantisServiceServicer initialized")

    async def ProcessSimulationInput(
        self, request: mantis_core_pb2.SimulationInput, context: grpc.ServicerContext
    ) -> mantis_core_pb2.SimulationOutput:
        """
        PRIMARY METHOD: Process simulation input with context threading for recursive agent invocation.

        This enables the Chief of Staff to recursively invoke other agents through the
        proper simulation architecture using SimulationInput specifications.

        Args:
            request: SimulationInput with query, context, and agent specifications
            context: gRPC service context

        Returns:
            SimulationOutput with complete orchestration results
        """
        try:
            logger.info(f"ProcessSimulationInput called with context_id: {request.context_id}")
            logger.info(f"Query length: {len(request.query)} characters")
            logger.info(
                f"Execution strategy: {mantis_core_pb2.ExecutionStrategy.Name(request.execution_strategy) if request.execution_strategy else 'DEFAULT'}"
            )

            # Validate input
            if not request.query:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Query is required")
                return mantis_core_pb2.SimulationOutput()

            # Set defaults if not specified
            if not request.context_id:
                request.context_id = f"sim_{int(asyncio.get_event_loop().time())}"

            if not request.execution_strategy:
                request.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT

            if request.max_depth <= 0:
                request.max_depth = 3  # Default recursion depth

            # Execute simulation through orchestrator
            logger.info("Executing simulation with orchestrator")
            result = await self.orchestrator.execute_simulation(request)

            logger.info(f"Simulation completed successfully for context: {request.context_id}")
            return result

        except Exception as e:
            logger.error(f"Error in ProcessSimulationInput: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")

            # Return minimal error response
            error_output = mantis_core_pb2.SimulationOutput()
            error_output.context_id = request.context_id or "error"
            error_output.final_state = (
                mantis_core_pb2.TASK_STATE_FAILED if hasattr(mantis_core_pb2, "TASK_STATE_FAILED") else 0
            )
            return error_output

    async def ProcessUserRequest(
        self, request: mantis_core_pb2.UserRequest, context: grpc.ServicerContext
    ) -> mantis_core_pb2.SimulationOutput:
        """
        DEPRECATED: Process a single user request with direct agent execution.

        This method is maintained for backward compatibility but SimulationInput
        is the preferred approach for new implementations.
        """
        try:
            logger.warning("ProcessUserRequest is deprecated, consider using ProcessSimulationInput")

            # Convert UserRequest to SimulationInput
            simulation_input = mantis_core_pb2.SimulationInput()
            simulation_input.query = request.query
            simulation_input.context_id = f"user_{int(asyncio.get_event_loop().time())}"

            if request.context:
                simulation_input.context = request.context

            if request.execution_strategy:
                simulation_input.execution_strategy = request.execution_strategy

            if request.min_depth:
                simulation_input.min_depth = request.min_depth

            if request.max_depth:
                simulation_input.max_depth = request.max_depth

            # Copy agent specifications
            simulation_input.agents.extend(request.agents)

            # Delegate to ProcessSimulationInput
            return await self.ProcessSimulationInput(simulation_input, context)

        except Exception as e:
            logger.error(f"Error in ProcessUserRequest: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return mantis_core_pb2.SimulationOutput()

    async def ProcessTeamRequest(
        self, request: mantis_core_pb2.TeamExecutionRequest, context: grpc.ServicerContext
    ) -> mantis_core_pb2.TeamExecutionResult:
        """
        Process a team request with multi-agent coordination.

        Uses the simulation input and team formation strategies to coordinate
        multiple agents working together.
        """
        try:
            logger.info(f"ProcessTeamRequest called for team size: {request.team_size}")

            # Use the team formation and narrator patterns from the orchestrator
            if hasattr(self.orchestrator, "execute_team_with_formation"):
                result = await self.orchestrator.execute_team_with_formation(
                    request.simulation_input, request.team_size, request.formation_strategy
                )
                return result
            else:
                # Fallback to basic team execution
                logger.warning("execute_team_with_formation not available, using basic execution")
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details("Team execution not fully implemented")
                return mantis_core_pb2.TeamExecutionResult()

        except Exception as e:
            logger.error(f"Error in ProcessTeamRequest: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return mantis_core_pb2.TeamExecutionResult()

    async def ProcessNarratorRequest(
        self, request: mantis_core_pb2.NarratorRequest, context: grpc.ServicerContext
    ) -> mantis_core_pb2.AgentResponse:
        """
        Process a narrator request for synthesizing team responses.

        Uses the narrator patterns to synthesize multiple agent responses
        into a coherent narrative.
        """
        try:
            logger.info("ProcessNarratorRequest called")

            # Use the narrator patterns from the core system
            from ..core.narrator import TarotNarrator

            narrator = TarotNarrator(request.execution_strategy)

            # Convert UserRequest to SimulationInput for narrator context
            simulation_input = mantis_core_pb2.SimulationInput()
            simulation_input.query = request.user_request.query
            simulation_input.context_id = f"narrator_{int(asyncio.get_event_loop().time())}"

            # Synthesize narrative from team results
            response = await narrator.synthesize_narrative(simulation_input, request.team_result)
            return response

        except Exception as e:
            logger.error(f"Error in ProcessNarratorRequest: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")

            # Return minimal error response
            error_response = mantis_core_pb2.AgentResponse()
            error_response.text_response = f"Error in narrator processing: {str(e)}"
            return error_response


async def serve_grpc(port: int = 50051, host: str = "localhost"):
    """
    Start the gRPC server with MantisServiceServicer.

    Args:
        port: Port to listen on (default: 50051)
        host: Host to bind to (default: localhost)
    """
    server = aio.server()
    servicer = MantisServiceServicer()
    mantis_core_pb2_grpc.add_MantisServiceServicer_to_server(servicer, server)

    listen_addr = f"{host}:{port}"
    server.add_insecure_port(listen_addr)

    logger.info(f"Starting Mantis gRPC service on {listen_addr}")
    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        await server.stop(grace=5.0)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve_grpc())

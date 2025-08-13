"""
ADK Router FastAPI Server

Wraps the ChiefOfStaffRouter in a FastAPI application with A2A-compatible endpoints.
"""

from typing import Dict, Any, Union

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .router import ChiefOfStaffRouter
from ..proto.mantis.v1 import mantis_core_pb2
from ..observability.logger import get_structured_logger
from ..config import DEFAULT_MODEL

logger = get_structured_logger(__name__)


def create_adk_router_app(router: ChiefOfStaffRouter, name: str = "ADK Chief of Staff Router") -> FastAPI:
    """
    Create FastAPI application for ADK router.

    Args:
        router: ChiefOfStaffRouter instance
        name: Server name for identification

    Returns:
        FastAPI application with A2A-compatible endpoints
    """
    app = FastAPI(title=name, description="ADK-powered orchestration router with A2A boundaries", version="1.0.0")

    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint for ADK router."""
        try:
            health_status = await router.health_check()
            return health_status
        except Exception as e:
            logger.error("Health check failed", structured_data={"error": str(e)})
            raise HTTPException(status_code=503, detail=f"ADK router unhealthy: {str(e)}")

    @app.post("/simulate", response_model=None)
    async def simulate(request: Dict[str, Any]) -> Union[Dict[str, Any], JSONResponse]:
        """
        A2A-compatible simulation endpoint.

        Accepts A2A SimulationInput and returns A2A SimulationOutput via ADK routing.
        """
        try:
            # Convert dict to protobuf SimulationInput
            simulation_input = mantis_core_pb2.SimulationInput()

            # Basic field mapping - extend as needed
            if "query" in request:
                simulation_input.query = request["query"]
            if "context_id" in request:
                simulation_input.context_id = request["context_id"]
            else:
                import uuid

                simulation_input.context_id = f"adk-{uuid.uuid4().hex[:8]}"
            if "execution_strategy" in request:
                simulation_input.execution_strategy = request["execution_strategy"]
            else:
                simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
            if "max_depth" in request:
                simulation_input.max_depth = request["max_depth"]
            else:
                simulation_input.max_depth = 3

            logger.info(
                "ADK simulation request received",
                structured_data={
                    "context_id": simulation_input.context_id,
                    "query_length": len(simulation_input.query),
                },
            )

            # Route through ADK
            simulation_output = await router.route_simulation(simulation_input)

            # Convert protobuf response to dict
            from google.protobuf.json_format import MessageToDict

            response_dict = MessageToDict(simulation_output, preserving_proto_field_name=True)

            return JSONResponse(content=response_dict)

        except Exception as e:
            logger.error(
                "ADK simulation failed", structured_data={"error": str(e), "request_keys": list(request.keys())}
            )
            raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    @app.get("/")
    async def root() -> Dict[str, str]:
        """Root endpoint with ADK router information."""
        model_name = DEFAULT_MODEL.split(":", 1)[1] if ":" in DEFAULT_MODEL else DEFAULT_MODEL
        return {
            "service": name,
            "type": "pydantic_ai_router",
            "backend": "pydantic-ai",
            "model": model_name,
            "full_model_spec": DEFAULT_MODEL,
            "endpoints": "/simulate,/health",
            "status": "operational",
        }

    return app

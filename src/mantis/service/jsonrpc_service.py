"""
Clean JSON-RPC Service Implementation

Uses proper protobuf SimulationOutput without global state or wrapper classes.
Single clean orchestrator with dependency injection.
"""

import asyncio
import json
import logging
from typing import Dict, Any, cast
from aiohttp import web, web_request
from google.protobuf.json_format import MessageToDict

from ..proto.mantis.v1 import mantis_core_pb2
from ..core.orchestrator import SimulationOrchestrator

logger = logging.getLogger(__name__)


class JSONRPCError:
    """JSON-RPC error codes and messages."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    @staticmethod
    def create_error_response(request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create JSON-RPC error response."""
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data

        return {"jsonrpc": "2.0", "error": error, "id": request_id}


class MantisJSONRPCService:
    """
    Clean JSON-RPC service using protobuf SimulationOutput.

    No global state, clean dependency injection, proper protobuf usage.
    """

    def __init__(self) -> None:
        """Initialize service with clean orchestrator."""
        self.orchestrator = SimulationOrchestrator()
        self.methods = {
            "process_simulation_input": self.process_simulation_input,
            "process_narrator_request": self.process_narrator_request,
            "get_service_info": self.get_service_info,
            "health_check": self.health_check,
        }
        logger.info("Clean MantisJSONRPCService initialized")

    async def handle_request(self, request: web_request.Request) -> web.Response:
        """Handle incoming JSON-RPC requests."""
        try:
            # Parse JSON request
            try:
                body = await request.text()
                json_request = json.loads(body)
            except json.JSONDecodeError as e:
                return web.json_response(
                    JSONRPCError.create_error_response(None, JSONRPCError.PARSE_ERROR, f"Parse error: {str(e)}"),
                    status=400,
                )

            # Validate JSON-RPC structure
            if not isinstance(json_request, dict) or json_request.get("jsonrpc") != "2.0":
                return web.json_response(
                    JSONRPCError.create_error_response(
                        json_request.get("id"), JSONRPCError.INVALID_REQUEST, "Invalid Request"
                    ),
                    status=400,
                )

            method_name = json_request.get("method")
            params = json_request.get("params", {})
            request_id = json_request.get("id")

            # Check if method exists
            if method_name not in self.methods:
                return web.json_response(
                    JSONRPCError.create_error_response(
                        request_id, JSONRPCError.METHOD_NOT_FOUND, f"Method not found: {method_name}"
                    ),
                    status=404,
                )

            # Execute method
            try:
                method = self.methods[method_name]
                result = await method(params)

                return web.json_response({"jsonrpc": "2.0", "result": result, "id": request_id})

            except Exception as e:
                logger.error(f"Method execution failed: {method_name}", exc_info=True)
                return web.json_response(
                    JSONRPCError.create_error_response(
                        request_id, JSONRPCError.INTERNAL_ERROR, f"Internal error: {str(e)}"
                    ),
                    status=500,
                )

        except Exception as e:
            logger.error("Request handling failed", exc_info=True)
            return web.json_response(
                JSONRPCError.create_error_response(None, JSONRPCError.INTERNAL_ERROR, str(e)), status=500
            )

    async def process_simulation_input(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process SimulationInput using clean protobuf structure.

        Args:
            params: Dictionary containing SimulationInput data

        Returns:
            Dictionary containing SimulationOutput data with nested results
        """
        # Convert params to protobuf SimulationInput
        simulation_input = mantis_core_pb2.SimulationInput()

        # Required fields
        if "query" not in params:
            raise ValueError("Query is required")
        simulation_input.query = params["query"]

        # Optional fields with defaults
        simulation_input.context_id = params.get("context_id", f"sim_{int(asyncio.get_event_loop().time())}")
        simulation_input.parent_context_id = params.get("parent_context_id", "")
        simulation_input.context = params.get("context", "")
        simulation_input.min_depth = params.get("min_depth", 0)
        simulation_input.max_depth = params.get("max_depth", 3)

        if "execution_strategy" in params:
            strategy_map = {
                "DIRECT": mantis_core_pb2.EXECUTION_STRATEGY_DIRECT,
                "A2A": mantis_core_pb2.EXECUTION_STRATEGY_A2A,
            }
            simulation_input.execution_strategy = strategy_map.get(
                params["execution_strategy"], mantis_core_pb2.EXECUTION_STRATEGY_DIRECT
            )
        else:
            simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT

        # Execute simulation through clean orchestrator
        logger.info(f"Executing simulation with context_id: {simulation_input.context_id}")
        result = await self.orchestrator.execute_simulation(simulation_input)

        # Convert protobuf SimulationOutput to dictionary using native protobuf JSON conversion
        return cast(Dict[str, Any], MessageToDict(result, preserving_proto_field_name=True))

    async def get_service_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get service information."""
        return {
            "service_name": "Mantis JSON-RPC Service",
            "version": "1.0.0",
            "a2a_compliant": True,
            "supported_methods": list(self.methods.keys()),
        }

    async def health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Health check endpoint."""
        return {"status": "healthy", "orchestrator": self.orchestrator is not None}

    async def process_narrator_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process NarratorRequest for final synthesis and presentation.
        
        Args:
            params: Dictionary containing NarratorRequest data with:
                - narrator_strategy: Path to narrator agent card JSON file
                - team_result: Raw synthesis data from leader coordination
                - original_query: Original user query for context
                - context: Additional context information
                
        Returns:
            Dictionary containing final narrative presentation
        """
        # Load narrator agent card from strategy path
        if "narrator_strategy" not in params:
            raise ValueError("narrator_strategy (path to narrator agent card) is required")
        
        narrator_path = params["narrator_strategy"]
        
        try:
            import json
            from ..agent.card import load_agent_card_from_json
            
            # Load narrator agent card
            with open(narrator_path, 'r', encoding='utf-8') as f:
                narrator_card_json = json.load(f)
            
            narrator_card = load_agent_card_from_json(narrator_card_json)
            logger.info(f"Loaded narrator agent: {narrator_card.agent_card.name} from {narrator_path}")
            
        except Exception as e:
            raise ValueError(f"Failed to load narrator agent card from {narrator_path}: {e}")
        
        # Extract raw synthesis from team_result
        team_result = params.get("team_result", {})
        original_query = params.get("original_query", "")
        context = params.get("context", "")
        
        # Get the authentic narrator persona content
        narrator_persona = narrator_card.persona_characteristics.original_content
        
        # Create narrative synthesis prompt using narrator's authentic voice
        narrative_prompt = f"""{narrator_persona}

Original User Query: {original_query}

Raw Synthesis Results to Present:
{json.dumps(team_result, indent=2)}

Context: {context}

Your task as narrator:
Take the above raw synthesis results and present them to the user in your distinctive narrative style and voice. Transform the structured data into an engaging, coherent presentation that reflects your characteristic communication patterns, thinking style, and presentation approach as defined in your persona.

Maintain your authentic personality while ensuring the user receives all the key insights and information from the synthesis in a clear, compelling narrative form."""

        # Execute narrator using orchestrator
        try:
            from ..llm.structured_extractor import StructuredExtractor
            from ..config import DEFAULT_MODEL
            
            extractor = StructuredExtractor()
            
            # Generate final narrative presentation
            narrative_result = await extractor.extract_text_response(
                prompt=narrative_prompt,
                query=f"Present the synthesis results using your authentic narrative voice",
                model=DEFAULT_MODEL
            )
            
            # Return final narrative response
            return {
                "narrator_agent": narrator_card.agent_card.name,
                "narrative_response": narrative_result,
                "raw_synthesis": team_result,
                "status": "completed"
            }
            
        except Exception as e:
            logger.error(f"Narrator execution failed: {e}", exc_info=True)
            raise ValueError(f"Narrator synthesis failed: {e}")

    async def handle_info(self, request: web_request.Request) -> web.Response:
        """Handle GET /info requests for service information."""
        info = await self.get_service_info({})
        return web.json_response(info)

    async def handle_health(self, request: web_request.Request) -> web.Response:
        """Handle GET /health requests for health check."""
        health = await self.health_check({})
        # Add additional fields expected by litmus test
        health.update({"status": health["status"], "orchestrator_initialized": health["orchestrator"]})
        return web.json_response(health)


async def create_app() -> web.Application:
    """Create aiohttp application with clean JSON-RPC service."""
    service = MantisJSONRPCService()

    app = web.Application()
    app.router.add_post("/", service.handle_request)
    app.router.add_post("/jsonrpc", service.handle_request)  # Alternative endpoint

    # Add info and health endpoints for litmus test compatibility
    app.router.add_get("/info", service.handle_info)
    app.router.add_get("/health", service.handle_health)

    return app


async def start_service(host: str = "localhost", port: int = 8081) -> None:
    """Start the clean JSON-RPC service."""
    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    logger.info(f"Clean JSON-RPC service started on http://{host}:{port}")

    try:
        # Keep service running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down JSON-RPC service...")
    finally:
        await runner.cleanup()


# Alias for backwards compatibility
serve_jsonrpc = start_service

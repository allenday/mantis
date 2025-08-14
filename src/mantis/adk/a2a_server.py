#!/usr/bin/env python3
"""
Native ADK A2A Server using FastAPI.

This module implements a lightweight A2A protocol server that wraps ADK agents
directly, providing clean integration without FastA2A framework conflicts.
"""

import uuid
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google.adk import Agent  # type: ignore[import-untyped]
from google.genai import types

from ..observability.logger import get_structured_logger
from ..core.orchestrator import SimulationOrchestrator

logger = get_structured_logger(__name__)


# A2A Protocol Models
class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessagePart(BaseModel):
    kind: str = "text"
    text: str


class Message(BaseModel):
    role: str = "user"
    parts: List[MessagePart]
    kind: str = "message"
    messageId: str


class MessageSendParams(BaseModel):
    message: Message
    configuration: Optional[Dict[str, Any]] = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: str


class TaskStatus(BaseModel):
    state: TaskState
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class Task(BaseModel):
    id: str
    status: TaskStatus
    history: List[Message] = []
    result: Optional[str] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class ADKAgentCard(BaseModel):
    """A2A Agent Card for ADK-powered agents."""

    name: str
    description: str
    url: str
    version: str = "1.0.0"
    protocolVersion: str = "0.2.5"
    skills: List[Dict[str, str]] = []
    defaultInputModes: List[str] = ["application/json"]
    defaultOutputModes: List[str] = ["application/json"]
    capabilities: Dict[str, Any] = {"streaming": False, "pushNotifications": False, "stateTransitionHistory": False}
    provider: Dict[str, str] = {"organization": "Mantis AI", "url": "https://mantis.ai"}


class ADKA2AServer:
    """
    FastAPI-based A2A server that wraps ADK agents.

    This provides clean A2A protocol compliance while leveraging ADK's
    powerful agent runtime and tool integration capabilities.
    """

    def __init__(self, agent_name: str, description: str, port: int = 9053, leader_instruction: Optional[str] = None):
        """Initialize ADK A2A server."""
        self.agent_name = agent_name
        self.description = description
        self.port = port
        self.leader_instruction = leader_instruction
        self.tasks: Dict[str, Task] = {}
        self.sessions: Dict[str, str] = {}  # session_id -> user_id

        # Initialize ADK components
        self._initialize_adk_agent()
        self._initialize_fastapi_app()

        logger.info(
            f"ADK A2A Server initialized for {agent_name}",
            structured_data={
                "agent_name": agent_name,
                "port": port,
                "tools_count": len(getattr(self.orchestrator, "tools", {})),
            },
        )

    def _initialize_adk_agent(self) -> None:
        """Initialize ADK agent and orchestrator."""
        try:
            # Initialize orchestrator for tools
            self.orchestrator = SimulationOrchestrator()

            # Load API keys
            import os
            from dotenv import load_dotenv

            load_dotenv()

            # Get model from mantis config and translate to ADK format
            from ..config import DEFAULT_MODEL
            
            def translate_model_to_adk(mantis_model: str) -> str:
                """Translate mantis model format to ADK-compatible model."""
                # Handle mantis model format: "provider:model-name" or just "model-name"
                if ":" in mantis_model:
                    provider, model = mantis_model.split(":", 1)
                    if provider == "google" or provider == "gemini":
                        return model  # Use as-is for Google models
                    elif provider == "anthropic":
                        # For ADK, we need to use a Google model since ADK is Google's framework
                        logger.info(f"Translating Anthropic model {model} to Google model for ADK compatibility")
                        return "gemini-1.5-flash"  # Use stable Google model
                    elif provider == "openai":
                        logger.info(f"Translating OpenAI model {model} to Google model for ADK compatibility")
                        return "gemini-1.5-flash"
                    else:
                        # Default to stable Google model for unknown providers
                        logger.warning(f"Unknown provider {provider}, using gemini-1.5-flash for ADK")
                        return "gemini-1.5-flash"
                else:
                    # Assume it's already a Google model name
                    return mantis_model
            
            model_config = translate_model_to_adk(DEFAULT_MODEL)
            logger.info(f"Using ADK model: {model_config} (translated from mantis config: {DEFAULT_MODEL})")

            # Check for API key availability
            if not os.environ.get("GOOGLE_API_KEY") and not (os.environ.get("GOOGLE_CLOUD_PROJECT")):
                logger.warning("No GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT found - ADK agent may fail")
            else:
                logger.info("Google API credentials found - ADK agent can use real models")

            # Create ADK agent with tools (sanitize name for ADK validation)
            adk_agent_name = self.agent_name.replace(" ", "_").lower()

            # Convert orchestrator tools to ADK format
            self._convert_orchestrator_tools_to_adk()
            adk_tools = getattr(self, "adk_tools", [])

            # Use custom leader instruction if provided, otherwise use default
            instruction = (
                self.leader_instruction
                or f"""You are the {self.agent_name}, a senior coordinator and strategic advisor.

Your role is to:
1. Analyze incoming requests and determine the appropriate response approach
2. Break down complex tasks into manageable components  
3. Provide strategic guidance and high-level coordination
4. Coordinate team formation and delegate tasks to appropriate agents
5. Synthesize information from multiple sources when needed
6. Ensure clear, actionable communication

Available coordination tools:
- get_random_agents_from_registry: Discover agents from the registry for team formation
- invoke_agent_by_name: Delegate tasks to specific agents by name
- invoke_multiple_agents: Coordinate with multiple agents in parallel for diverse perspectives
- web_fetch_url: Fetch content from URLs for research
- web_search: Search the web for current information

Always think strategically about the user's ultimate goal and provide 
comprehensive, well-structured responses. When complex tasks require multiple 
perspectives or specialized knowledge, use your coordination tools to 
work with appropriate agents."""
            )

            self.adk_agent = Agent(
                name=adk_agent_name,
                description=self.description,
                instruction=instruction,
                model=model_config,
                tools=adk_tools,  # Provide converted orchestrator tools
            )

            # Create ADK runner with proper session service
            from google.adk.sessions import InMemorySessionService  # type: ignore[import-untyped]
            from google.adk.runners import Runner  # type: ignore[import-untyped]

            self.session_service = InMemorySessionService()
            self.app_name = "mantis_adk_a2a"

            self.adk_runner = Runner(agent=self.adk_agent, app_name=self.app_name, session_service=self.session_service)

            logger.info("ADK agent and runner initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ADK agent: {e}")
            raise

    def _convert_orchestrator_tools_to_adk(self) -> None:
        """Convert orchestrator tools to ADK FunctionTool format."""
        try:
            from google.adk.tools import FunctionTool  # type: ignore[import-untyped]

            adk_tools = []

            # Convert each orchestrator tool to ADK format
            for tool_name, tool_func in self.orchestrator.tools.items():
                logger.debug(f"Converting tool {tool_name} to ADK format")

                # Create ADK-compatible wrapper function with proper name
                wrapper_func = self._create_adk_wrapper(tool_func, tool_name)
                wrapper_func.__name__ = tool_name  # Set function name for ADK

                # Create ADK function tool
                adk_tool = FunctionTool(func=wrapper_func)
                adk_tools.append(adk_tool)

            logger.info(f"Converted {len(adk_tools)} orchestrator tools to ADK format")
            self.adk_tools = adk_tools

        except Exception as e:
            logger.error(f"Failed to convert orchestrator tools: {e}")
            self.adk_tools = []

    def _create_adk_wrapper(self, orchestrator_tool: Any, tool_name: str) -> Any:
        """Create ADK-compatible wrapper for orchestrator tools."""
        import inspect
        from google.adk.tools import ToolContext  # type: ignore[import-untyped]
        import functools

        # Get the original function signature
        original_sig = inspect.signature(orchestrator_tool)

        # Create wrapper that preserves signature but handles ToolContext
        @functools.wraps(orchestrator_tool)
        async def adk_tool_wrapper(*args: Any, tool_context: Optional[ToolContext] = None, **kwargs: Any) -> Any:
            """Wrapper that executes orchestrator tool in ADK context."""
            try:
                logger.debug(
                    f"Executing orchestrator tool {tool_name} via ADK wrapper with args={args}, kwargs={kwargs}"
                )

                # Remove tool_context from kwargs if present (ADK adds this)
                kwargs.pop("tool_context", None)

                # Call the orchestrator tool
                if inspect.iscoroutinefunction(orchestrator_tool):
                    result = await orchestrator_tool(*args, **kwargs)
                else:
                    result = orchestrator_tool(*args, **kwargs)

                logger.debug(f"Tool {tool_name} completed with result type: {type(result)}")
                return result

            except Exception as e:
                logger.error(f"ADK tool wrapper failed for {tool_name}: {e}")
                import traceback

                traceback.print_exc()
                return f"Error executing {tool_name}: {str(e)}"

        # Preserve the original signature for ADK inspection
        try:
            adk_tool_wrapper.__signature__ = original_sig  # type: ignore
        except AttributeError:
            # functools.wraps may not allow this - ignore if it fails
            pass

        return adk_tool_wrapper

    def _initialize_fastapi_app(self) -> None:
        """Initialize FastAPI application with A2A endpoints."""
        self.app = FastAPI(
            title=f"{self.agent_name} A2A Server",
            description=f"A2A Protocol server for ADK-powered {self.agent_name}",
            version="1.0.0",
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register A2A protocol endpoints
        self._register_a2a_endpoints()

        logger.info("FastAPI app initialized with A2A endpoints")

    def _register_a2a_endpoints(self) -> None:
        """Register A2A protocol endpoints."""

        @self.app.get("/.well-known/agent.json")
        async def get_agent_card() -> Dict[str, Any]:
            """Return A2A agent card."""
            return ADKAgentCard(
                name=self.agent_name,
                description=self.description,
                url=f"http://localhost:{self.port}",
                skills=[
                    {
                        "name": "strategic_coordination",
                        "description": "Strategic coordination and multi-agent orchestration capabilities",
                    }
                ],
            ).dict()

        @self.app.post("/")
        async def handle_a2a_request(request: JSONRPCRequest) -> Dict[str, Any]:
            """Handle A2A JSON-RPC requests."""
            try:
                if request.method == "message/send":
                    return await self._handle_message_send(request)
                elif request.method == "tasks/get":
                    return await self._handle_task_get(request)
                else:
                    raise HTTPException(status_code=400, detail=f"Unsupported method: {request.method}")
            except Exception as e:
                logger.error(f"A2A request failed: {e}")
                return JSONRPCResponse(id=request.id, error={"code": -32000, "message": str(e)}).dict()

        @self.app.get("/docs")
        async def get_docs() -> Dict[str, Any]:
            """Serve simple docs page."""
            return {
                "agent": self.agent_name,
                "description": self.description,
                "endpoints": {
                    "/.well-known/agent.json": "A2A agent card",
                    "/": "A2A JSON-RPC endpoint",
                    "/docs": "This documentation",
                },
                "supported_methods": ["message/send", "tasks/get"],
            }

    async def _handle_message_send(self, request: JSONRPCRequest) -> Dict[str, Any]:
        """Handle message/send A2A requests."""
        try:
            # Parse message/send parameters with metadata
            params = MessageSendParams(**request.params)
            message = params.message
            
            # Extract metadata for request typing (following A2A spec)
            request_metadata = request.params.get("metadata", {})

            logger.info(
                "Processing A2A message/send request",
                structured_data={
                    "message_id": message.messageId,
                    "text_length": len(message.parts[0].text if message.parts else ""),
                },
            )

            # Create task immediately (A2A protocol requirement)
            task_id = f"task-{uuid.uuid4().hex[:12]}"
            task = Task(id=task_id, status=TaskStatus(state=TaskState.PENDING), history=[message])
            self.tasks[task_id] = task

            # Start async processing (don't await - return task ID immediately)
            asyncio.create_task(self._process_task_async(task_id, message, request_metadata))

            # Return task ID immediately (A2A protocol compliance)
            return JSONRPCResponse(
                id=request.id, result={"id": task_id, "contextId": f"ctx-{uuid.uuid4().hex[:8]}"}
            ).dict()

        except Exception as e:
            logger.error(f"message/send failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _handle_task_get(self, request: JSONRPCRequest) -> Dict[str, Any]:
        """Handle tasks/get A2A requests."""
        try:
            task_id = request.params.get("id")
            if not task_id or task_id not in self.tasks:
                return JSONRPCResponse(id=request.id, error={"code": -32001, "message": "Task not found"}).dict()

            task = self.tasks[task_id]

            # Return task status and result
            result: Dict[str, Any] = {
                "id": task.id,
                "status": {"state": task.status.state.value, "timestamp": task.status.timestamp.isoformat()},
                "history": [msg.dict() for msg in task.history],
            }

            # Add result if completed
            if task.status.state == TaskState.COMPLETED and task.result:
                # Handle both protobuf and direct text results
                try:
                    if isinstance(task.result, str):
                        # Direct agent response (text)
                        result["result"] = task.result
                        logger.debug(f"Returned direct text result for task {task.id}")
                    else:
                        # Protobuf simulation response (binary)
                        from google.protobuf.json_format import MessageToDict
                        from ..proto.mantis.v1 import mantis_core_pb2
                        
                        # Deserialize protobuf and convert to dict
                        simulation_output = mantis_core_pb2.SimulationOutput()
                        simulation_output.ParseFromString(task.result)
                        result["result"] = MessageToDict(simulation_output)
                        logger.debug(f"Returned protobuf simulation result for task {task.id}")
                except Exception as e:
                    logger.error(f"Failed to deserialize task result for JSON: {e}")
                    # Fallback to text representation
                    result["result"] = "Processing completed but result serialization failed"
            elif task.status.state == TaskState.FAILED and task.status.error:
                result["status"]["error"] = task.status.error

            return JSONRPCResponse(id=request.id, result=result).dict()

        except Exception as e:
            logger.error(f"tasks/get failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def _process_task_async(self, task_id: str, message: Message, request_metadata: Dict[str, Any]) -> None:
        """Process task asynchronously using proper A2A metadata for request typing."""
        try:
            task = self.tasks[task_id]
            task.status.state = TaskState.RUNNING

            logger.info(f"Starting structured ADK processing for task {task_id}")

            # Extract text content from A2A message
            text_content = message.parts[0].text if message.parts else ""
            
            # Check request type from A2A metadata (proper approach)
            request_type = request_metadata.get("request_type", "unknown")
            proto_type = request_metadata.get("proto_type")
            
            logger.info(f"🔍 A2A REQUEST ANALYSIS: request_type={request_type}, proto_type={proto_type}, metadata_keys={list(request_metadata.keys())}")

            # Handle different request types properly
            if request_type == "simulation_request" and proto_type == "mantis.v1.SimulationInput":
                # Parse structured simulation request from JSON
                try:
                    import json
                    simulation_params = json.loads(text_content)
                    logger.info(f"Parsed simulation input: {list(simulation_params.keys())}")
                except Exception as e:
                    raise ValueError(f"Failed to parse SimulationInput JSON: {e}")
                    
            elif "JSON-RPC Call: process_simulation_input" in text_content:
                # Legacy support for old format (from simulation_proper_demo.py)
                try:
                    import json
                    import re
                    params_match = re.search(r"with params:\s*(\{.*\})", text_content, re.DOTALL)
                    if params_match:
                        params_str = params_match.group(1)
                        simulation_params = json.loads(params_str)
                        logger.info(f"Extracted legacy simulation params: {list(simulation_params.keys())}")
                        request_type = "simulation_request"  # Treat as simulation
                    else:
                        simulation_params = None
                except Exception as e:
                    logger.warning(f"Failed to parse legacy JSON-RPC params: {e}")
                    simulation_params = None
            else:
                simulation_params = None

            # Process based on request type
            if request_type == "simulation_request" and simulation_params:
                # Create proper SimulationInput for structured processing
                from ..proto.mantis.v1 import mantis_core_pb2

                simulation_input = mantis_core_pb2.SimulationInput()
                simulation_input.context_id = simulation_params.get("context_id", f"a2a-{task_id}")
                simulation_input.parent_context_id = simulation_params.get("parent_context_id", "")
                simulation_input.query = simulation_params.get("query", text_content)
                simulation_input.execution_strategy = getattr(
                    mantis_core_pb2,
                    f"EXECUTION_STRATEGY_{simulation_params.get('execution_strategy', 'DIRECT')}",
                    mantis_core_pb2.EXECUTION_STRATEGY_DIRECT,
                )
                simulation_input.max_depth = simulation_params.get("max_depth", 1)
                simulation_input.min_depth = simulation_params.get("min_depth", 0)

                # Add agent specs if provided
                if "agents" in simulation_params:
                    for agent_data in simulation_params["agents"]:
                        agent_spec = simulation_input.agents.add()
                        agent_spec.count = agent_data.get("count", 1)
                        # Note: agent details would be populated by orchestrator

                # Initialize AgentRouter with orchestrator
                if not hasattr(self, "router"):
                    from ..adk.router import AgentRouter

                    self.router = AgentRouter(tools=self.orchestrator.tools, orchestrator=self.orchestrator)
                    logger.info("Initialized AgentRouter for structured results")

                # Route through AgentRouter for structured results
                logger.info(f"🎯 A2A SERVER: Routing through AgentRouter for task {task_id}")

                # Process with timeout - increased for team coordination
                timeout_seconds = 120
                simulation_output = await asyncio.wait_for(
                    self.router.route_simulation(simulation_input), timeout=timeout_seconds
                )

                # CRITICAL FIX: Store the full SimulationOutput, not just text response
                from google.protobuf.json_format import MessageToDict

                # Extract text response first (needed for compatibility)
                response_text = (
                    simulation_output.response_message.content[0].text
                    if (simulation_output.response_message and simulation_output.response_message.content)
                    else "No response generated"
                )

                # Convert SimulationOutput to JSON-serializable dict
                try:
                    simulation_output_dict = MessageToDict(simulation_output)
                    response_data = {
                        "text_response": response_text,
                        "simulation_output": simulation_output_dict,
                        "structured_results_count": len(simulation_output.results),
                        "context_id": simulation_output.context_id,
                    }
                except Exception as e:
                    logger.error(f"Failed to serialize SimulationOutput: {e}")
                    response_data = {"text_response": response_text, "serialization_error": str(e)}

                # Store the structured output for debugging
                logger.info(
                    "🎯 A2A SERVER: AgentRouter returned structured output",
                    structured_data={
                        "task_id": task_id,
                        "context_id": simulation_output.context_id,
                        "structured_results_count": len(simulation_output.results),
                        "response_length": len(str(response_data.get("text_response", ""))),  # type: ignore[arg-type]
                    },
                )

            elif request_type == "direct_agent_request":
                # Handle direct agent requests (from recursive_invocation.py) - properly typed
                logger.info(
                    "Processing direct agent request via A2A metadata",
                    structured_data={
                        "task_id": task_id,
                        "request_type": request_type,
                        "text_content_preview": text_content[:100] + "..." if len(text_content) > 100 else text_content,
                    },
                )
                
                # Use ADK agent directly for simple agent-to-agent requests
                from google.genai import types
                
                # Convert text to ADK message format
                adk_message = types.Content(
                    role="user",
                    parts=[types.Part(text=text_content)]
                )
                
                # Generate a session for this request
                user_id = f"a2a-user-{task_id}"
                session_id = f"a2a-session-{task_id}"
                
                # CRITICAL FIX: Create session in session service first (async)
                session = await self.session_service.create_session(app_name=self.app_name, user_id=user_id, session_id=session_id)
                logger.info(f"Created ADK session {session_id} for user {user_id} with app {self.app_name} - session object: {session.id}")
                
                # Run ADK agent
                adk_events = await self._run_adk_agent_async(user_id, session_id, adk_message)
                response_text = self._extract_response_from_events(adk_events)
                
                if not response_text or response_text == "I processed your request but was unable to generate a visible response. Please try again.":
                    raise RuntimeError(f"ADK agent failed to generate response for task {task_id}")
                
                # Create structured response for compatibility
                response_data = {
                    "text_response": response_text,
                    "direct_agent_response": True,
                    "context_id": f"direct-{task_id}",
                }
                
                logger.info(
                    "🎯 A2A SERVER: Direct agent request processed successfully via metadata",
                    structured_data={
                        "task_id": task_id,
                        "response_length": len(response_text),
                        "processing_mode": "direct_adk_metadata",
                    },
                )

            else:
                # Unknown request type - fail fast
                logger.error(
                    "Unknown request type - failing fast", 
                    structured_data={
                        "task_id": task_id,
                        "request_type": request_type,
                        "proto_type": proto_type,
                        "available_metadata": list(request_metadata.keys()),
                    }
                )
                raise ValueError(f"Unsupported request type '{request_type}' with proto_type '{proto_type}'. Use proper A2A metadata.")

            # Update task with structured result
            if "response_data" in locals():
                if response_data.get("direct_agent_response"):
                    # For direct agent responses, store the text directly (simpler format)
                    task.result = response_data["text_response"]
                    logger.info(f"Stored direct agent response for task {task_id}")
                else:
                    # For simulation responses, use protobuf serialization
                    from google.protobuf.json_format import ParseDict
                    from ..proto.mantis.v1 import mantis_core_pb2

                    # Create SimulationOutput protobuf from response_data
                    simulation_output = mantis_core_pb2.SimulationOutput()
                    if response_data.get("simulation_output"):
                        ParseDict(response_data["simulation_output"], simulation_output)
                    
                    # Store serialized protobuf instead of JSON
                    task.result = simulation_output.SerializeToString()
                    logger.info(f"Stored simulation protobuf response for task {task_id}")
            else:
                # This should never happen after fallback removal - fail fast
                raise RuntimeError("No response_data available after processing - system error")
            task.status.state = TaskState.COMPLETED
            task.status.timestamp = datetime.utcnow()

            # Add agent response to history
            final_response_text = response_data.get("text_response", "No response generated")
            agent_response = Message(
                role="agent",
                parts=[MessagePart(text=final_response_text)],
                kind="message",
                messageId=f"agent-{uuid.uuid4().hex[:8]}",
            )
            task.history.append(agent_response)

            logger.info(
                f"Task {task_id} completed successfully",
                structured_data={"response_length": len(response_text), "processing_time": "< 30s"},
            )

        except asyncio.TimeoutError:
            logger.error(f"Task {task_id} timed out")
            task.status.state = TaskState.FAILED
            task.status.error = "Processing timed out after 120 seconds"
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            task.status.state = TaskState.FAILED
            task.status.error = str(e)

    async def _run_adk_agent_async(self, user_id: str, session_id: str, message: types.Content) -> List[Any]:
        """Run ADK agent and collect events."""
        events = []

        try:
            logger.info(f"Starting ADK runner with user_id={user_id}, session_id={session_id}, app_name={self.app_name}")
            # ADK runner.run_async returns an async generator - collect events properly
            async_events = self.adk_runner.run_async(user_id=user_id, session_id=session_id, new_message=message)

            # Collect all events from the async generator
            async for event in async_events:
                events.append(event)
                logger.debug(f"ADK event: {type(event).__name__}")

            logger.info(f"Collected {len(events)} events from ADK runner")
            return events

        except Exception as e:
            logger.error(f"ADK runner failed: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _extract_response_from_events(self, events: List[Any]) -> str:
        """Extract response text from ADK events."""
        response_texts = []

        for event in events:
            # Check for agent turn complete events
            if hasattr(event, "agent_turn_complete") and event.agent_turn_complete:
                if hasattr(event.agent_turn_complete, "output"):
                    output = event.agent_turn_complete.output
                    if hasattr(output, "parts") and output.parts:
                        for part in output.parts:
                            if hasattr(part, "text") and part.text:
                                response_texts.append(part.text)
                    elif hasattr(output, "text") and output.text:
                        response_texts.append(output.text)
                    elif str(output).strip():
                        response_texts.append(str(output))

            # Check for content events
            elif hasattr(event, "content") and event.content:
                if hasattr(event.content, "parts") and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_texts.append(part.text)
                elif hasattr(event.content, "text") and event.content.text:
                    response_texts.append(event.content.text)

            # Check for text events
            elif hasattr(event, "text") and event.text:
                response_texts.append(event.text)

            # Fallback: convert entire event to string if it contains meaningful content
            elif hasattr(event, "role") and str(event).strip():
                event_str = str(event).strip()
                if len(event_str) > 10 and not event_str.startswith("<"):  # Skip proto debug output
                    response_texts.append(event_str)

        if response_texts:
            return "\n".join(response_texts).strip()

        # Final fallback with debug info
        logger.warning(f"No response extracted from {len(events)} events")
        for i, event in enumerate(events):
            logger.info(f"Event {i}: {type(event).__name__} - {str(event)[:100]}")

        return "I processed your request but was unable to generate a visible response. Please try again."

    async def start_server(self) -> None:
        """Start the FastAPI server."""
        import uvicorn

        logger.info(f"Starting ADK A2A server on port {self.port}")

        config = uvicorn.Config(app=self.app, host="127.0.0.1", port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


# Convenience function for creating Chief of Staff A2A server
def create_chief_of_staff_a2a_server(port: int = 9053) -> ADKA2AServer:
    """Create ADK A2A server for Chief of Staff."""
    return create_leader_a2a_server_from_card("chief_of_staff", port=port)


def create_leader_a2a_server_from_card(leader_card_name: str, port: int = 9053) -> ADKA2AServer:
    """Create ADK A2A server for any leader from agent card."""
    try:
        from ..agent.card import load_leader_agent_card

        # Load the leader agent card
        leader_card = load_leader_agent_card(leader_card_name)
        if not leader_card:
            logger.warning(f"Leader card '{leader_card_name}' not found, falling back to default Chief of Staff")
            return ADKA2AServer(
                agent_name="Chief Of Staff",
                description="ADK-powered Chief of Staff for strategic coordination and multi-agent orchestration",
                port=port,
            )

        # Extract agent interface
        from ..agent import AgentInterface

        agent_interface = AgentInterface.from_agent_card(leader_card)  # type: ignore[arg-type]

        # Create leader-specific instruction
        leader_instruction = _create_leader_instruction(agent_interface, leader_card)

        return ADKA2AServer(
            agent_name=agent_interface.name,
            description=f"ADK-powered {agent_interface.name} for strategic coordination and multi-agent orchestration",
            port=port,
            leader_instruction=leader_instruction,
        )

    except Exception as e:
        logger.error(f"Failed to create leader server from card '{leader_card_name}': {e}")
        # Fallback to default
        return ADKA2AServer(
            agent_name="Chief Of Staff",
            description="ADK-powered Chief of Staff for strategic coordination and multi-agent orchestration",
            port=port,
        )


def _create_leader_instruction(agent_interface: Any, leader_card: Any) -> str:
    """Create leader instruction from agent card."""
    try:
        # Extract persona characteristics if available
        persona_content = ""
        if hasattr(leader_card, "persona_characteristics") and leader_card.persona_characteristics:
            chars = leader_card.persona_characteristics
            persona_content = getattr(chars, "original_content", "") or agent_interface.description
        else:
            persona_content = agent_interface.description

        # Create leader-specific instruction with coordination tools
        leader_instruction = f"""{persona_content}

## ADDITIONAL COORDINATION CAPABILITIES

As a strategic leader, you now have access to powerful coordination tools that enable you to:

1. **Discover Agents**: Use get_random_agents_from_registry to find agents from the registry for team formation
2. **Single Agent Coordination**: Use invoke_agent_by_name to delegate tasks to specific agents by name  
3. **Multi-Agent Coordination**: Use invoke_multiple_agents to coordinate with multiple agents in parallel for diverse perspectives
4. **Research Tools**: Use web_fetch_url and web_search for current information and research

When complex tasks require multiple perspectives or specialized knowledge, leverage your coordination tools to work with appropriate agents. Your role is to:

- Analyze incoming requests and determine the appropriate response approach
- Break down complex tasks into manageable components using your characteristic thinking patterns
- Coordinate team formation and delegate tasks to appropriate agents
- Synthesize information from multiple sources when needed
- Provide comprehensive, well-structured responses in your distinctive voice and style

Always maintain your core personality, communication style, and decision framework while utilizing these coordination capabilities."""

        return leader_instruction

    except Exception as e:
        logger.error(f"Failed to create leader instruction: {e}")
        return f"You are {agent_interface.name}, equipped with coordination tools for strategic leadership and multi-agent orchestration."


def create_adk_a2a_server_from_agent_card(agent_card: Any, port: int) -> ADKA2AServer:
    """Create ADK A2A server from any agent card."""
    try:
        from ..agent import AgentInterface

        # Create agent interface using the correct class method for base AgentCard
        agent_interface = AgentInterface.from_agent_card(agent_card)

        return ADKA2AServer(agent_name=agent_interface.name, description=agent_interface.description, port=port)
    except Exception as e:
        # Log the actual error for debugging
        from ..observability.logger import get_structured_logger

        logger = get_structured_logger(__name__)
        logger.error(
            f"Failed to create ADK A2A server from agent card: {e}",
            structured_data={"error": str(e), "agent_card_type": type(agent_card).__name__},
        )
        raise

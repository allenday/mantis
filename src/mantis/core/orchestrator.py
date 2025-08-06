"""
Core simulation orchestrator for executing multi-agent scenarios.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from ..proto.mantis.v1 import mantis_core_pb2
from ..proto.mantis.v1.prompt_composition_pb2 import ExecutionContext as ProtoExecutionContext, SimulationContext
from ..config import DEFAULT_MODEL


class ExecutionStrategy(ABC):
    """Abstract base class for execution strategies."""

    @abstractmethod
    async def execute_agent(
        self, simulation_input: mantis_core_pb2.SimulationInput, agent_spec: mantis_core_pb2.AgentSpec, agent_index: int
    ) -> mantis_core_pb2.AgentResponse:
        """Execute a single agent and return its response."""
        pass

    @abstractmethod
    def get_strategy_type(self) -> mantis_core_pb2.ExecutionStrategy:
        """Return the strategy type enum value."""
        pass


class DirectExecutor(ExecutionStrategy):
    """Direct execution using local pydantic-ai agents."""

    def __init__(self):
        self._model_cache: Dict[str, Any] = {}
        self._tools: Dict[str, Any] = {}
        self._initialize_tools()

    async def execute_agent(
        self, simulation_input: mantis_core_pb2.SimulationInput, agent_spec: mantis_core_pb2.AgentSpec, agent_index: int
    ) -> mantis_core_pb2.AgentResponse:
        """Execute agent directly using pydantic-ai with modular prompt composition."""
        from ..prompts import PromptCompositionEngine, CompositionStrategy
        from ..prompts.variables import create_composition_context
        from ..llm.structured_extractor import StructuredExtractor

        try:
            # For now, create minimal agent card since agent_card_path is not in protobuf
            # TODO: Add agent card loading mechanism to AgentSpec or pass separately
            mantis_card = self._create_minimal_agent_card()

            # Determine execution context and role using proto
            execution_context = ProtoExecutionContext()
            execution_context.current_depth = agent_spec.current_depth
            execution_context.max_depth = simulation_input.max_depth
            execution_context.team_size = 1
            execution_context.assigned_role = self._determine_agent_role(mantis_card, agent_spec)
            execution_context.agent_index = agent_index

            # Compose prompt using modular system
            composition_engine = PromptCompositionEngine()
            context = create_composition_context(
                mantis_card=mantis_card,
                simulation_input=simulation_input,
                agent_spec=agent_spec,
                execution_context=execution_context,
            )

            composed_prompt = await composition_engine.compose_prompt(
                context=context, strategy=CompositionStrategy.BLENDED
            )

            # Execute using structured extractor (LLM integration)
            extractor = StructuredExtractor()

            # Use the composed prompt as the system prompt
            model = simulation_input.model if simulation_input.model else DEFAULT_MODEL
            result = await extractor.extract_text_response(
                prompt=composed_prompt.final_prompt, query=simulation_input.query, model=model
            )

            # Create response
            response = mantis_core_pb2.AgentResponse()
            response.text_response = result
            response.output_modes.append("text/markdown")

            # Add metadata about prompt composition (if metadata field exists)
            try:
                response.metadata.update(
                    {
                        "modules_used": [m.get_module_name() for m in composed_prompt.modules_used],
                        "variables_resolved": len(composed_prompt.variables_resolved),
                        "composition_strategy": composed_prompt.strategy.value,
                    }
                )
            except AttributeError:
                # Metadata field doesn't exist in this protobuf version
                pass

            return response

        except Exception as e:
            # Fallback to simple execution
            response = mantis_core_pb2.AgentResponse()
            response.text_response = (
                f"Error in agent execution: {str(e)}\n\nFallback response for query: {simulation_input.query}"
            )
            response.output_modes.append("text/markdown")
            return response

    def get_strategy_type(self) -> mantis_core_pb2.ExecutionStrategy:
        return mantis_core_pb2.EXECUTION_STRATEGY_DIRECT

    def _initialize_tools(self):
        """Initialize available tools for agent execution."""
        try:
            from ..tools.web_fetch import WebFetchTool, WebFetchConfig
            from ..tools.web_search import WebSearchTool, WebSearchConfig
            from ..tools.git_operations import GitOperationsTool, GitOperationsConfig
            from ..tools.jira_integration import JiraTool, JiraConfig
            from ..tools.gitlab_integration import GitLabTool, GitLabConfig

            # Initialize WebFetchTool with secure defaults
            web_fetch_config = WebFetchConfig(
                timeout=30.0,
                user_agent="Mantis-Agent/1.0 (DirectExecutor)",
                rate_limit_requests=60,
                rate_limit_window=60,
                verify_ssl=True,
                max_content_size=10 * 1024 * 1024,  # 10MB limit
            )
            self._tools["web_fetch"] = WebFetchTool(web_fetch_config)

            # Initialize WebSearchTool
            web_search_config = WebSearchConfig(
                max_results=10,
                timeout=30.0,
                rate_limit_requests=30,
                rate_limit_window=60,
                enable_suggestions=True,
            )
            self._tools["web_search"] = WebSearchTool(web_search_config)

            # Initialize GitOperationsTool with secure defaults
            git_config = GitOperationsConfig(
                max_repo_size_mb=100.0,
                max_files=1000,
                allowed_schemes=["https"],
                blocked_domains=["localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10.", "172."],
                clone_timeout=300.0,
                temp_cleanup=True,
                max_search_results=50,
            )
            self._tools["git_operations"] = GitOperationsTool(git_config)

            # Initialize JiraTool with secure defaults
            try:
                jira_config = JiraConfig(
                    api_token="",  # Placeholder - agents can reconfigure as needed
                    email="",  # Placeholder - agents can reconfigure as needed
                    server_url="https://your-domain.atlassian.net",  # Default placeholder
                    read_only_mode=True,
                    timeout=30.0,
                )
                jira_tool = JiraTool(jira_config)
                self._tools.update(jira_tool.get_tools())
            except Exception as e:
                # Log Jira tool initialization failure but continue with other tools
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to initialize Jira tool: {e}")

            # Initialize GitLabTool with secure defaults
            try:
                gitlab_config = GitLabConfig(
                    personal_access_token="",  # Placeholder - agents can reconfigure as needed
                    read_only_mode=True,
                    timeout=30.0,
                )
                gitlab_tool = GitLabTool(gitlab_config)
                self._tools.update(gitlab_tool.get_tools())
            except Exception as e:
                # Log GitLab tool initialization failure but continue with other tools
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to initialize GitLab tool: {e}")

        except ImportError:
            # Tools not available, continue without them
            pass

    def get_available_tools(self) -> Dict[str, Any]:
        """Get dictionary of available tools."""
        return self._tools.copy()

    def _create_minimal_agent_card(self):
        """Create a minimal agent card for generic execution."""
        from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
        from ..proto.a2a_pb2 import AgentCard

        # Create minimal MantisAgentCard
        mantis_card = MantisAgentCard()

        # Create basic agent card
        agent_card = AgentCard()
        agent_card.name = "Generic Agent"
        agent_card.description = "A general-purpose agent for task execution"
        agent_card.version = "1.0.0"

        mantis_card.agent_card.CopyFrom(agent_card)
        return mantis_card

    def _determine_agent_role(self, mantis_card, simulation_input) -> str:
        """Determine the agent's role based on context and capabilities."""
        # For now, use simple heuristics
        # In the future, this could use the role assignment engine

        current_depth = simulation_input.current_depth
        max_depth = simulation_input.max_depth

        # Simple role assignment logic
        if current_depth == 0:
            return "leader"  # Top level is strategic leader
        elif current_depth >= max_depth - 1:
            return "follower"  # Near max depth focuses on execution
        else:
            # Check if agent has good leadership scores
            if mantis_card.competency_scores and mantis_card.competency_scores.role_adaptation:
                leader_score = mantis_card.competency_scores.role_adaptation.leader_score
                narrator_score = mantis_card.competency_scores.role_adaptation.narrator_score

                if leader_score > narrator_score and leader_score > 0.7:
                    return "leader"
                elif narrator_score > 0.7:
                    return "narrator"

            return "follower"  # Default to execution role


class A2AExecutor(ExecutionStrategy):
    """A2A execution using remote agents via FastA2A protocol."""

    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = registry_url

    async def execute_agent(
        self, simulation_input: mantis_core_pb2.SimulationInput, agent_spec: mantis_core_pb2.AgentSpec, agent_index: int
    ) -> mantis_core_pb2.AgentResponse:
        """Execute agent via A2A protocol."""
        # TODO: Implement FastA2A integration (Issue #25-27)
        # For now, return a placeholder response

        response = mantis_core_pb2.AgentResponse()
        response.text_response = f"[A2AExecutor] Would execute via A2A: {simulation_input.query}"
        response.output_modes.append("text/markdown")

        return response

    def get_strategy_type(self) -> mantis_core_pb2.ExecutionStrategy:
        return mantis_core_pb2.EXECUTION_STRATEGY_A2A


# Removed dataclass ExecutionContext - using proto SimulationContext instead


class SimulationOrchestrator:
    """
    Core orchestrator for multi-agent simulations.

    Handles the complete lifecycle from UserRequest to SimulationOutput,
    coordinating between different execution strategies and managing
    recursive agent interactions.
    """

    def __init__(self):
        self._strategies: Dict[mantis_core_pb2.ExecutionStrategy, ExecutionStrategy] = {
            mantis_core_pb2.EXECUTION_STRATEGY_DIRECT: DirectExecutor(),
            mantis_core_pb2.EXECUTION_STRATEGY_A2A: A2AExecutor(),
        }

    def user_request_to_simulation_input(
        self, user_request: mantis_core_pb2.UserRequest
    ) -> mantis_core_pb2.SimulationInput:
        """Convert UserRequest to SimulationInput with execution strategy."""
        simulation_input = mantis_core_pb2.SimulationInput()

        # Copy all fields from UserRequest
        simulation_input.query = user_request.query

        if user_request.HasField("context"):
            simulation_input.context = user_request.context

        if user_request.HasField("structured_data"):
            simulation_input.structured_data = user_request.structured_data

        if user_request.HasField("model_spec"):
            simulation_input.model_spec.CopyFrom(user_request.model_spec)

        if user_request.HasField("max_depth"):
            simulation_input.max_depth = user_request.max_depth

        # Copy agent specifications
        for agent_spec in user_request.agents:
            simulation_input.agents.append(agent_spec)

        # Set execution strategy (default to A2A for multi-agent scenarios)
        if len(user_request.agents) > 1 or any(
            agent.HasField("recursion_policy")
            and agent.recursion_policy in [mantis_core_pb2.RECURSION_POLICY_MAY, mantis_core_pb2.RECURSION_POLICY_MUST]
            for agent in user_request.agents
        ):
            simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_A2A
        else:
            simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT

        return simulation_input

    async def execute_simulation(self, user_request: mantis_core_pb2.UserRequest) -> mantis_core_pb2.SimulationOutput:
        """
        Execute a complete simulation from UserRequest to SimulationOutput.

        Args:
            user_request: The user's simulation request

        Returns:
            SimulationOutput with results, timing, and status
        """
        start_time = time.time()

        try:
            # Convert to SimulationInput
            simulation_input = self.user_request_to_simulation_input(user_request)

            # Create execution context using proto
            context = SimulationContext()
            context.start_time = start_time
            context.strategy = simulation_input.execution_strategy
            context.simulation_input.CopyFrom(simulation_input)
            context.current_depth = 0

            # Execute simulation
            simulation_output = await self._execute_simulation_internal(context)

            # Set execution metadata
            simulation_output.total_time = time.time() - start_time
            simulation_output.execution_strategies.append(simulation_input.execution_strategy)
            simulation_output.team_size = len(simulation_input.agents)
            simulation_output.recursion_depth = 0

            # Set success status
            execution_result = mantis_core_pb2.ExecutionResult()
            execution_result.status = mantis_core_pb2.EXECUTION_STATUS_SUCCESS
            simulation_output.execution_result.CopyFrom(execution_result)

            return simulation_output

        except Exception as e:
            # Create error response
            simulation_output = mantis_core_pb2.SimulationOutput()
            simulation_output.total_time = time.time() - start_time
            simulation_output.team_size = len(user_request.agents) if user_request.agents else 0

            # Create error info
            error_info = mantis_core_pb2.ErrorInfo()
            error_info.error_type = mantis_core_pb2.ERROR_TYPE_MODEL  # Default error type
            error_info.error_message = str(e)

            # Set error status
            execution_result = mantis_core_pb2.ExecutionResult()
            execution_result.status = mantis_core_pb2.EXECUTION_STATUS_FAILED
            execution_result.error_info.CopyFrom(error_info)
            simulation_output.execution_result.CopyFrom(execution_result)

            # Create error response
            error_response = mantis_core_pb2.AgentResponse()
            error_response.text_response = f"Simulation failed: {str(e)}"
            error_response.output_modes.append("text/plain")
            simulation_output.response.CopyFrom(error_response)

            return simulation_output

    async def _execute_simulation_internal(self, context: SimulationContext) -> mantis_core_pb2.SimulationOutput:
        """Internal simulation execution logic."""
        simulation_input = context.simulation_input
        strategy = self._strategies[context.strategy]

        # For now, execute all agents independently (no recursion yet)
        agent_responses: List[mantis_core_pb2.AgentResponse] = []

        for i, agent_spec in enumerate(simulation_input.agents):
            try:
                response = await strategy.execute_agent(simulation_input, agent_spec, i)
                agent_responses.append(response)
            except Exception as e:
                # Create error response for this agent
                error_response = mantis_core_pb2.AgentResponse()
                error_response.text_response = f"Agent {i} failed: {str(e)}"
                error_response.output_modes.append("text/plain")
                agent_responses.append(error_response)

        # Create simulation output
        simulation_output = mantis_core_pb2.SimulationOutput()

        # For single agent, use its response directly
        if len(agent_responses) == 1:
            simulation_output.response.CopyFrom(agent_responses[0])
        else:
            # For multiple agents, aggregate responses
            aggregated_response = self._aggregate_responses(agent_responses)
            simulation_output.response.CopyFrom(aggregated_response)

        return simulation_output

    def _aggregate_responses(self, responses: List[mantis_core_pb2.AgentResponse]) -> mantis_core_pb2.AgentResponse:
        """Aggregate multiple agent responses into a single response."""
        aggregated = mantis_core_pb2.AgentResponse()

        # Combine text responses
        text_parts = []
        for i, response in enumerate(responses):
            text_parts.append(f"**Agent {i + 1}:**\n{response.text_response}")

        aggregated.text_response = "\n\n".join(text_parts)
        aggregated.output_modes.append("text/markdown")

        # TODO: More sophisticated aggregation logic for:
        # - Extension merging
        # - Skill combination
        # - Confidence scoring
        # This will be enhanced in later issues

        return aggregated

    def get_available_strategies(self) -> List[mantis_core_pb2.ExecutionStrategy]:
        """Get list of available execution strategies."""
        return list(self._strategies.keys())

    def set_strategy(self, strategy_type: mantis_core_pb2.ExecutionStrategy, strategy: ExecutionStrategy):
        """Register or override an execution strategy."""
        self._strategies[strategy_type] = strategy

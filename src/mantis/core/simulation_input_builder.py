"""
SimulationInput builder for converting CLI arguments to protobuf messages.
"""

from typing import List, Optional, Union
import uuid
import asyncio

from ..proto.mantis.v1 import mantis_core_pb2
from ..config import DEFAULT_MAX_DEPTH


class SimulationInputBuilder:
    """
    Builds SimulationInput protobuf messages from CLI arguments.

    Handles conversion from command-line arguments to structured protobuf
    messages, including validation and default value handling.
    """

    def __init__(self) -> None:
        self._query: Optional[str] = None
        self._context: Optional[str] = None
        self._structured_data: Optional[str] = None
        self._model_spec: Optional[mantis_core_pb2.ModelSpec] = None
        self._max_depth: Optional[int] = None
        self._agents: List[mantis_core_pb2.AgentSpec] = []

    def query(self, query: str) -> "SimulationInputBuilder":
        """Set the main query/prompt text."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        self._query = query.strip()
        return self

    def context(self, context: str) -> "SimulationInputBuilder":
        """Set additional context for the request."""
        self._context = context.strip() if context else None
        return self

    def structured_data(self, data: Union[str, dict]) -> "SimulationInputBuilder":
        """Set structured data for the request."""
        if isinstance(data, dict):
            import json

            self._structured_data = json.dumps(data)
        elif isinstance(data, str):
            self._structured_data = data.strip() if data else None
        else:
            self._structured_data = str(data) if data else None
        return self

    def model_spec(self, model: Optional[str] = None, temperature: Optional[float] = None) -> "SimulationInputBuilder":
        """Set model specification."""
        if model or temperature is not None:
            spec = mantis_core_pb2.ModelSpec()
            if model:
                spec.model = model
            if temperature is not None:
                if not 0.0 <= temperature <= 2.0:
                    raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")
                spec.temperature = temperature
            self._model_spec = spec
        return self

    def max_depth(self, depth: int) -> "SimulationInputBuilder":
        """Set maximum depth for recursive processing."""
        if depth < 1:
            raise ValueError(f"Max depth must be at least 1, got {depth}")
        if depth > 10:
            raise ValueError(f"Max depth cannot exceed 10 for safety, got {depth}")
        self._max_depth = depth
        return self

    def add_agent(
        self,
        count: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        recursion_policy: Optional[Union[str, mantis_core_pb2.RecursionPolicy]] = None,
    ) -> "SimulationInputBuilder":
        """Add an agent specification."""
        spec = mantis_core_pb2.AgentSpec()

        if count is not None:
            if count < 1:
                raise ValueError(f"Agent count must be at least 1, got {count}")
            spec.count = count

        if model or temperature is not None:
            model_spec = mantis_core_pb2.ModelSpec()
            if model:
                model_spec.model = model
            if temperature is not None:
                if not 0.0 <= temperature <= 2.0:
                    raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")
                model_spec.temperature = temperature
            spec.model_spec.CopyFrom(model_spec)

        if recursion_policy is not None:
            if isinstance(recursion_policy, str):
                policy_map = {
                    "may": mantis_core_pb2.RECURSION_POLICY_MAY,
                    "must": mantis_core_pb2.RECURSION_POLICY_MUST,
                    "must_not": mantis_core_pb2.RECURSION_POLICY_MUST_NOT,
                    "no": mantis_core_pb2.RECURSION_POLICY_MUST_NOT,
                }
                policy = policy_map.get(recursion_policy.lower())
                if policy is None:
                    valid_policies = list(policy_map.keys())
                    raise ValueError(f"Invalid recursion policy '{recursion_policy}'. Valid options: {valid_policies}")
                spec.recursion_policy = policy
            else:
                spec.recursion_policy = recursion_policy

        self._agents.append(spec)
        return self

    def parse_agents_string(self, agents_str: str) -> "SimulationInputBuilder":
        """
        Parse agent specifications from comma-separated string.

        Formats supported:
        - "agent1,agent2" - Simple agent names (count=1 each)
        - "agent1:2,agent2:3" - Agent names with counts
        - "leader:1:may,follower:2:must_not" - Full specification
        """
        if not agents_str:
            return self

        agent_specs = [spec.strip() for spec in agents_str.split(",") if spec.strip()]

        for spec in agent_specs:
            parts = spec.split(":")

            if len(parts) == 1:
                # Simple format: just agent name
                self.add_agent(count=1)
            elif len(parts) == 2:
                # Format: name:count
                try:
                    count = int(parts[1])
                    self.add_agent(count=count)
                except ValueError:
                    raise ValueError(f"Invalid agent count in '{spec}': '{parts[1]}' is not a number")
            elif len(parts) == 3:
                # Format: name:count:policy
                try:
                    count = int(parts[1])
                    policy = parts[2]
                    self.add_agent(count=count, recursion_policy=policy)
                except ValueError as e:
                    raise ValueError(f"Invalid agent specification '{spec}': {e}")
            else:
                raise ValueError(
                    f"Invalid agent specification format '{spec}'. Expected format: 'name', 'name:count', or 'name:count:policy'"
                )

        return self

    def validate(self) -> List[str]:
        """Validate the current builder state and return list of errors."""
        errors = []

        if not self._query:
            errors.append("Query is required")

        if self._max_depth is not None and self._max_depth < 1:
            errors.append("Max depth must be at least 1")

        for i, agent in enumerate(self._agents):
            if agent.count <= 0:
                errors.append(f"Agent {i} count must be positive")

        return errors

    def build(self) -> mantis_core_pb2.SimulationInput:
        """Build the final SimulationInput protobuf message."""
        # Validate before building
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation failed: {'; '.join(errors)}")

        simulation_input = mantis_core_pb2.SimulationInput()
        simulation_input.query = self._query  # type: ignore  # Validated above

        # Generate unique context ID
        try:
            loop_time = asyncio.get_event_loop().time()
        except RuntimeError:
            import time

            loop_time = time.time()

        simulation_input.context_id = f"cli_{int(loop_time)}_{uuid.uuid4().hex[:8]}"

        if self._context:
            simulation_input.context = self._context

        if self._structured_data:
            # Note: SimulationInput doesn't have structured_data field in current schema
            # Store it in context for now as a workaround
            if simulation_input.context:
                simulation_input.context += f"\n\nStructured Data: {self._structured_data}"
            else:
                simulation_input.context = f"Structured Data: {self._structured_data}"

        if self._model_spec:
            simulation_input.model_spec.CopyFrom(self._model_spec)

        # Set execution strategy to DIRECT by default
        simulation_input.execution_strategy = mantis_core_pb2.EXECUTION_STRATEGY_DIRECT

        # Set depth
        if self._max_depth is not None:
            simulation_input.max_depth = self._max_depth
        else:
            simulation_input.max_depth = DEFAULT_MAX_DEPTH
        simulation_input.min_depth = 0

        # Add agent specifications - ensure at least one agent exists
        if not self._agents:
            # Add default agent if none specified
            default_agent = mantis_core_pb2.AgentSpec()
            default_agent.count = 1
            default_agent.recursion_policy = mantis_core_pb2.RECURSION_POLICY_MAY
            self._agents.append(default_agent)

        for agent_spec in self._agents:
            simulation_input.agents.append(agent_spec)

        return simulation_input

    @classmethod
    def from_cli_args(
        cls,
        query: str,
        context: Optional[str] = None,
        structured_data: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_depth: Optional[int] = None,
        agents: Optional[str] = None,
    ) -> mantis_core_pb2.SimulationInput:
        """Build SimulationInput from CLI arguments in a single call."""
        builder = cls().query(query)
        if context:
            builder = builder.context(context)
        if structured_data:
            builder = builder.structured_data(structured_data)
        if model or temperature is not None:
            builder = builder.model_spec(model=model, temperature=temperature)
        if max_depth is not None:
            builder = builder.max_depth(max_depth)
        if agents:
            builder = builder.parse_agents_string(agents)
        return builder.build()

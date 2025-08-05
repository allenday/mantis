"""
UserRequest builder for converting CLI arguments to protobuf messages.
"""

import re
from typing import List, Optional, Union, Dict, Any
from pathlib import Path

from ..proto.mantis.v1 import mantis_core_pb2
from ..config import DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_DEPTH


class UserRequestBuilder:
    """
    Builds UserRequest protobuf messages from CLI arguments.
    
    Handles conversion from command-line arguments to structured protobuf
    messages, including validation and default value handling.
    """

    def __init__(self):
        self._query: Optional[str] = None
        self._context: Optional[str] = None
        self._structured_data: Optional[str] = None
        self._model_spec: Optional[mantis_core_pb2.ModelSpec] = None
        self._max_depth: Optional[int] = None
        self._agents: List[mantis_core_pb2.AgentSpec] = []

    def query(self, query: str) -> "UserRequestBuilder":
        """Set the main query/prompt text."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        self._query = query.strip()
        return self

    def context(self, context: Optional[str]) -> "UserRequestBuilder":
        """Set optional context for the request."""
        self._context = context.strip() if context and context.strip() else None
        return self

    def structured_data(self, data: Optional[Union[str, Dict[str, Any]]]) -> "UserRequestBuilder":
        """Set structured data as JSON string."""
        if data is None:
            self._structured_data = None
        elif isinstance(data, dict):
            import json
            self._structured_data = json.dumps(data)
        else:
            self._structured_data = str(data)
        return self

    def model_spec(self, model: Optional[str] = None, temperature: Optional[float] = None) -> "UserRequestBuilder":
        """Set model specification with optional temperature."""
        if model is None and temperature is None:
            self._model_spec = None
            return self

        spec = mantis_core_pb2.ModelSpec()
        if model:
            spec.model = model
        if temperature is not None:
            if not 0.0 <= temperature <= 2.0:
                raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temperature}")
            spec.temperature = temperature

        self._model_spec = spec
        return self

    def max_depth(self, depth: Optional[int]) -> "UserRequestBuilder":
        """Set maximum recursion depth."""
        self._max_depth = depth
        return self

    def add_agent(
        self,
        count: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        recursion_policy: Optional[Union[str, mantis_core_pb2.RecursionPolicy]] = None,
    ) -> "UserRequestBuilder":
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

    def parse_agents_string(self, agents_str: Optional[str]) -> "UserRequestBuilder":
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
                    if "not a number" in str(e):
                        raise ValueError(f"Invalid agent count in '{spec}': '{parts[1]}' is not a number")
                    else:
                        raise e
            else:
                raise ValueError(f"Invalid agent specification format: '{spec}'. Use 'name', 'name:count', or 'name:count:policy'")

        return self

    def build(self) -> mantis_core_pb2.UserRequest:
        """Build the final UserRequest protobuf message."""
        # Validate before building
        errors = self.validate()
        if errors:
            raise ValueError(f"Validation failed: {'; '.join(errors)}")

        request = mantis_core_pb2.UserRequest()
        request.query = self._query

        if self._context:
            request.context = self._context

        if self._structured_data:
            request.structured_data = self._structured_data

        if self._model_spec:
            request.model_spec.CopyFrom(self._model_spec)

        if self._max_depth is not None:
            request.max_depth = self._max_depth
        else:
            request.max_depth = DEFAULT_MAX_DEPTH

        # Add agents
        for agent_spec in self._agents:
            request.agents.append(agent_spec)

        # If no agents specified, add a default one
        if not self._agents:
            default_agent = mantis_core_pb2.AgentSpec()
            default_agent.count = 1
            default_agent.recursion_policy = mantis_core_pb2.RECURSION_POLICY_MAY
            request.agents.append(default_agent)

        return request

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
    ) -> mantis_core_pb2.UserRequest:
        """
        Convenience method to build UserRequest from CLI arguments.
        
        Args:
            query: Main query/prompt text
            context: Optional context
            structured_data: Optional structured data as JSON string
            model: Optional model name
            temperature: Optional temperature (0.0-2.0)
            max_depth: Optional recursion depth limit (1-10)
            agents: Optional comma-separated agent specifications
            
        Returns:
            UserRequest protobuf message
        """
        builder = cls()
        builder.query(query)
        
        if context:
            builder.context(context)
            
        if structured_data:
            builder.structured_data(structured_data)
            
        if model or temperature is not None:
            builder.model_spec(model, temperature)
            
        if max_depth is not None:
            builder.max_depth(max_depth)
            
        if agents:
            builder.parse_agents_string(agents)
            
        return builder.build()

    def validate(self) -> List[str]:
        """
        Validate the current builder state and return any errors.
        
        Returns:
            List of error messages, empty if valid
        """
        errors = []

        if not self._query:
            errors.append("Query is required")

        if self._max_depth is not None:
            if self._max_depth < 1:
                errors.append(f"Max depth must be at least 1, got {self._max_depth}")
            elif self._max_depth > DEFAULT_MAX_DEPTH:
                errors.append(f"Max depth cannot exceed {DEFAULT_MAX_DEPTH} for safety, got {self._max_depth}")

        # Validate model spec if present
        if self._model_spec:
            if self._model_spec.HasField("temperature"):
                temp = self._model_spec.temperature
                if not 0.0 <= temp <= 2.0:
                    errors.append(f"Temperature must be between 0.0 and 2.0, got {temp}")

        # Validate agent specs
        for i, agent in enumerate(self._agents):
            if agent.HasField("count") and agent.count < 1:
                errors.append(f"Agent {i} count must be at least 1, got {agent.count}")
                
            if agent.HasField("model_spec") and agent.model_spec.HasField("temperature"):
                temp = agent.model_spec.temperature
                if not 0.0 <= temp <= 2.0:
                    errors.append(f"Agent {i} temperature must be between 0.0 and 2.0, got {temp}")

        return errors
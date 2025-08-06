"""
Registry access tool for agent recruitment and discovery.

This tool enables agents to access the registry for discovering and recruiting
additional agents during simulation execution. It provides semantic search,
agent recruitment workflows, and integration with the A2A registry service.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin

import aiohttp
from pydantic import BaseModel, Field, ConfigDict

logger = logging.getLogger(__name__)


class AgentCard(BaseModel):
    """Agent card information from registry."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: str = Field(..., description="Agent URL (primary identifier)")
    name: str = Field(..., description="Agent name")
    description: Optional[str] = Field(None, description="Agent description")
    version: str = Field("1.0.0", description="Agent version")
    provider: Dict[str, Any] = Field(default_factory=dict, description="Provider information")
    skills: List[Dict[str, Any]] = Field(default_factory=list, description="Agent skills and capabilities")
    competencies: List[str] = Field(default_factory=list, description="Agent competency areas")
    trust_level: str = Field("UNVERIFIED", description="Trust verification level")
    health_score: Optional[int] = Field(None, description="Agent health score (0-100)")
    status: str = Field("UNKNOWN", description="Current agent status")


class AgentSpec(BaseModel):
    """Agent specification for recruitment."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent_url: str = Field(..., description="Agent URL to recruit")
    role: str = Field(..., description="Role assignment for the agent")
    capabilities: List[str] = Field(default_factory=list, description="Required capabilities")
    priority: int = Field(1, description="Priority level (1=highest, 10=lowest)")
    max_interactions: Optional[int] = Field(None, description="Maximum interactions allowed")


class SearchFilters(BaseModel):
    """Filters for agent search operations."""

    required_capabilities: List[str] = Field(default_factory=list, description="Required capabilities")
    required_skills: List[str] = Field(default_factory=list, description="Required skill names")
    trust_levels: List[str] = Field(
        default_factory=lambda: ["VERIFIED", "OFFICIAL"], description="Acceptable trust levels"
    )
    min_health_score: Optional[int] = Field(None, description="Minimum health score")
    max_response_time_ms: Optional[int] = Field(None, description="Maximum response time")
    preferred_regions: List[str] = Field(default_factory=list, description="Preferred geographic regions")
    require_domain_verified: bool = Field(False, description="Require domain verification")


class RegistryConfig(BaseModel):
    """Configuration for registry access."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    registry_url: str = Field("http://localhost:8080", description="Registry server URL")
    timeout: float = Field(30.0, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    retry_delay: float = Field(1.0, description="Delay between retries in seconds")
    user_agent: str = Field("Mantis-RegistryTool/1.0", description="User agent for requests")
    enable_caching: bool = Field(True, description="Enable response caching")
    cache_ttl: int = Field(300, description="Cache time-to-live in seconds")


class RegistryError(Exception):
    """Exception raised when registry operations fail."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class RegistryTool:
    """Tool for accessing the agent registry for recruitment and discovery."""

    def __init__(self, config: Optional[RegistryConfig] = None):
        self.config = config or RegistryConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
        logger.info(f"Initialized RegistryTool with registry: {self.config.registry_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    async def _ensure_session(self):
        """Ensure aiohttp session is available."""
        if not self._session or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {"User-Agent": self.config.user_agent}
            self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)

    async def _call_registry_jsonrpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Call registry using JSON-RPC protocol.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            Dictionary containing the RPC response result

        Raises:
            RegistryError: If the RPC call fails
        """
        await self._ensure_session()
        assert self._session is not None, "Session should be initialized after _ensure_session"

        # Construct JSON-RPC request
        jsonrpc_url = urljoin(self.config.registry_url, "/jsonrpc")
        payload = {"jsonrpc": "2.0", "method": method, "params": params or {}, "id": 1}

        logger.debug(f"Calling registry JSON-RPC: {method} at {jsonrpc_url}")

        for attempt in range(self.config.max_retries):
            try:
                async with self._session.post(jsonrpc_url, json=payload) as response:
                    if response.status != 200:
                        raise RegistryError(f"HTTP {response.status}: {await response.text()}", response.status)

                    result = await response.json()

                    if "error" in result:
                        error_info = result["error"]
                        raise RegistryError(f"RPC Error: {error_info.get('message', 'Unknown error')}")

                    return result.get("result", {})

            except aiohttp.ClientError as e:
                if attempt == self.config.max_retries - 1:
                    raise RegistryError(f"Registry connection failed: {str(e)}")
                logger.warning(f"Registry call attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        raise RegistryError("Maximum retry attempts exceeded")

    async def list_all_agents(self, limit: int = 20, include_inactive: bool = False) -> List[AgentCard]:
        """
        List all agents in the registry.

        Args:
            limit: Maximum number of agents to return
            include_inactive: Whether to include inactive agents

        Returns:
            List of AgentCard objects
        """
        cache_key = f"list_agents_{limit}_{include_inactive}"

        if self.config.enable_caching and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if cached_data.get("timestamp", 0) + self.config.cache_ttl > asyncio.get_event_loop().time():
                logger.debug("Returning cached agent list")
                return cached_data["data"]

        try:
            # Use the currently available list_agents method
            result = await self._call_registry_jsonrpc(
                "list_agents", {"include_inactive": include_inactive, "page_size": limit}
            )

            agents_data = result.get("agents", [])
            agent_cards = []

            for agent_data in agents_data[:limit]:
                # Convert registry response to AgentCard
                agent_card = AgentCard(
                    url=agent_data.get("url", ""),
                    name=agent_data.get("name", "Unknown"),
                    description=agent_data.get("description"),
                    version=agent_data.get("version", "1.0.0"),
                    provider=agent_data.get("provider", {}),
                    skills=agent_data.get("skills", []),
                    competencies=[skill.get("name", "") for skill in agent_data.get("skills", [])],
                    trust_level=agent_data.get("trust_level", "UNVERIFIED"),
                    health_score=agent_data.get("health_score"),
                    status=agent_data.get("status", "UNKNOWN"),
                )
                agent_cards.append(agent_card)

            # Cache the results
            if self.config.enable_caching:
                self._cache[cache_key] = {"data": agent_cards, "timestamp": asyncio.get_event_loop().time()}

            logger.info(f"Listed {len(agent_cards)} agents from registry")
            return agent_cards

        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            raise RegistryError(f"Failed to list agents: {str(e)}")

    async def search_agents(
        self, query: str, limit: int = 5, filters: Optional[SearchFilters] = None
    ) -> List[AgentCard]:
        """
        Search for agents using semantic queries.

        Note: Advanced search functionality will be available in registry v0.1.3.
        Currently falls back to local text filtering on agent list.

        Args:
            query: Search query (natural language)
            limit: Maximum number of agents to return
            filters: Optional search filters

        Returns:
            List of matching AgentCard objects
        """
        logger.info(f"Searching agents with query: '{query}' (limit: {limit})")

        # TODO: Replace with actual SearchAgents RPC call when available in v0.1.3
        # For now, fall back to listing all agents and filtering locally
        all_agents = await self.list_all_agents(limit=100)

        # Apply local text filtering (similar to CLI implementation)
        query_lower = query.lower()
        filtered_agents = []

        for agent in all_agents:
            # Search in name, description, and skills
            searchable_text = (
                f"{agent.name} {agent.description or ''} "
                f"{' '.join(agent.competencies)} "
                f"{' '.join([skill.get('name', '') + ' ' + skill.get('description', '') for skill in agent.skills])}"
            ).lower()

            if query_lower in searchable_text:
                # Apply additional filters if provided
                if filters and not self._matches_filters(agent, filters):
                    continue
                filtered_agents.append(agent)

                if len(filtered_agents) >= limit:
                    break

        logger.info(f"Found {len(filtered_agents)} agents matching search criteria")
        return filtered_agents

    def _matches_filters(self, agent: AgentCard, filters: SearchFilters) -> bool:
        """Check if agent matches the provided filters."""

        # Check required capabilities
        if filters.required_capabilities:
            agent_caps = set(agent.competencies)
            if not set(filters.required_capabilities).issubset(agent_caps):
                return False

        # Check required skills
        if filters.required_skills:
            agent_skills = set(skill.get("name", "") for skill in agent.skills)
            if not set(filters.required_skills).issubset(agent_skills):
                return False

        # Check trust level
        if filters.trust_levels and agent.trust_level not in filters.trust_levels:
            return False

        # Check health score
        if filters.min_health_score is not None:
            if agent.health_score is None or agent.health_score < filters.min_health_score:
                return False

        return True

    async def get_agent_details(self, agent_url: str) -> AgentCard:
        """
        Get detailed information about a specific agent.

        Args:
            agent_url: URL of the agent to retrieve

        Returns:
            AgentCard with detailed information

        Raises:
            RegistryError: If agent is not found or request fails
        """
        cache_key = f"agent_details_{agent_url}"

        if self.config.enable_caching and cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if cached_data.get("timestamp", 0) + self.config.cache_ttl > asyncio.get_event_loop().time():
                logger.debug(f"Returning cached details for agent: {agent_url}")
                return cached_data["data"]

        try:
            # TODO: Use GetAgentCard RPC when available
            # For now, search through the agent list
            all_agents = await self.list_all_agents(limit=1000)

            for agent in all_agents:
                if agent.url == agent_url:
                    if self.config.enable_caching:
                        self._cache[cache_key] = {"data": agent, "timestamp": asyncio.get_event_loop().time()}
                    logger.info(f"Retrieved details for agent: {agent_url}")
                    return agent

            raise RegistryError(f"Agent not found: {agent_url}")

        except RegistryError:
            raise
        except Exception as e:
            logger.error(f"Failed to get agent details: {e}")
            raise RegistryError(f"Failed to get agent details: {str(e)}")

    async def recruit_agent(self, agent_url: str, role: str, **kwargs) -> AgentSpec:
        """
        Recruit an agent for a specific role.

        Args:
            agent_url: URL of the agent to recruit
            role: Role to assign to the agent
            **kwargs: Additional recruitment parameters

        Returns:
            AgentSpec for the recruited agent

        Raises:
            RegistryError: If recruitment fails
        """
        logger.info(f"Recruiting agent: {agent_url} for role: {role}")

        # Get agent details to validate existence and capabilities
        agent_details = await self.get_agent_details(agent_url)

        # Create agent specification
        agent_spec = AgentSpec(
            agent_url=agent_url,
            role=role,
            capabilities=agent_details.competencies,
            priority=kwargs.get("priority", 1),
            max_interactions=kwargs.get("max_interactions"),
        )

        # TODO: Add actual recruitment workflow when registry supports it
        # This might involve updating agent status, registering recruitment, etc.

        logger.info(f"Successfully recruited agent: {agent_url}")
        return agent_spec

    def get_tools(self) -> Dict[str, Any]:
        """Return dictionary of available tools for pydantic-ai integration."""
        return {
            "registry_search_agents": self,
            "registry_get_agent_details": self,
            "registry_recruit_agent": self,
            "registry_list_agents": self,
        }

    async def close(self):
        """Close the registry tool and cleanup resources."""
        if self._session:
            await self._session.close()
            self._session = None
        self._cache.clear()
        logger.info("Registry tool closed")

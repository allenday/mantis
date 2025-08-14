"""
Configuration settings for Mantis A2A system.
"""

import json
import os
from typing import Optional
from .proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard

# Default model configuration - matches cli.py default
DEFAULT_MODEL = "anthropic:claude-3-5-haiku-20241022"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_DEPTH = 1  # One level of recursion - CoS can invoke team, team cannot recurse

# Server configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_TIMEOUT = 300.0

# Registry
# Use environment variable or fallback to localhost
DEFAULT_REGISTRY = os.environ.get("REGISTRY_URL", "http://localhost:8080")
DEFAULT_REGISTRY_SIMILARITY_THRESHOLD = 0.1

# Redis configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# Persona Extension Registry - Maps URIs to protobuf message types
PERSONA_EXTENSION_REGISTRY = {
    "https://polyhegel.ai/extensions/persona-characteristics/v1": "PersonaCharacteristics",
    "https://polyhegel.ai/extensions/competency-scores/v1": "CompetencyScores",
    "https://polyhegel.ai/extensions/domain-expertise/v1": "DomainExpertise",
    "https://mantis.ai/extensions/persona-characteristics/v1": "PersonaCharacteristics",
    "https://mantis.ai/extensions/competency-scores/v1": "CompetencyScores",
    "https://mantis.ai/extensions/domain-expertise/v1": "DomainExpertise",
    "https://mantis.ai/extensions/skills-summary/v1": "SkillsSummary",
}


def _load_default_base_agent() -> Optional[MantisAgentCard]:
    """Load the default base agent from chief_of_staff.json."""
    try:
        # Get the path to the chief_of_staff.json file
        # From src/mantis/config.py, we need to go up to project root: src/mantis -> src -> mantis
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/mantis
        project_root = os.path.dirname(os.path.dirname(current_dir))  # mantis project root
        agent_card_path = os.path.join(project_root, "agents", "cards", "implementation", "chief_of_staff.json")

        if not os.path.exists(agent_card_path):
            return None

        with open(agent_card_path, "r") as f:
            agent_card_json = json.load(f)

        # Use the existing load_agent_card_from_json function
        from .agent.card import load_agent_card_from_json

        mantis_card = load_agent_card_from_json(agent_card_json)

        return mantis_card

    except Exception as e:
        # Raise error if we can't load the default agent
        raise Exception(f"Failed to load default base agent from {agent_card_path}: {e}")


# Default base agent - loaded lazily
DEFAULT_BASE_AGENT: Optional[MantisAgentCard] = None


def get_default_base_agent() -> Optional[MantisAgentCard]:
    """Get the default base agent, loading it if necessary."""
    global DEFAULT_BASE_AGENT
    if DEFAULT_BASE_AGENT is None:
        DEFAULT_BASE_AGENT = _load_default_base_agent()
    return DEFAULT_BASE_AGENT

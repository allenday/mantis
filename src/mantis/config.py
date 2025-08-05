"""
Configuration settings for Mantis A2A system.
"""

# Default model configuration - matches cli.py default
DEFAULT_MODEL = "anthropic:claude-3-5-haiku-20241022"
DEFAULT_TEMPERATURE = 0.7

# Server configuration
DEFAULT_HOST = "0.0.0.0"
DEFAULT_TIMEOUT = 300.0

# Registry
DEFAULT_REGISTRY = "http://localhost:8080"

# Redis configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# Persona Extension Registry - Maps URIs to protobuf message types
PERSONA_EXTENSION_REGISTRY = {
    "https://polyhegel.ai/extensions/persona-characteristics/v1": "PersonaCharacteristics",
    "https://polyhegel.ai/extensions/competency-scores/v1": "CompetencyScores", 
    "https://polyhegel.ai/extensions/domain-expertise/v1": "DomainExpertise",
}

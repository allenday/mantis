"""
AgentCard generation and display functionality.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
    from ..proto.a2a_pb2 import AgentCard


def generate(input_path: str, model: Optional[str] = None):
    """
    Generate MantisAgentCard from markdown file using LLM enhancement.

    Args:
        input_path: Path to markdown persona file
        model: Optional model specification (e.g., "anthropic:claude-3-5-haiku-20241022")

    Returns:
        MantisAgentCard protobuf object with rich LLM-extracted persona data
    """
    from pathlib import Path

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {input_path}")

    # Read markdown content
    content = path.read_text(encoding="utf-8")
    persona_name = path.stem.replace("_", " ").title()

    # Create base AgentCard
    base_card = _create_base_agent_card(persona_name, content, path)

    # Enhance with LLM (required)
    enhanced_card = _enhance_with_llm(base_card, content, persona_name, model)
    return enhanced_card


def _create_base_agent_card(name: str, content: str, path: Path):
    """Create base AgentCard using existing logic."""
    from ..proto.a2a_pb2 import AgentCard, AgentSkill, AgentCapabilities, AgentExtension, AgentProvider
    from google.protobuf.struct_pb2 import Struct

    description_lines = [line.strip() for line in content.split("\n") if line.strip()]
    description = description_lines[0] if description_lines else f"Persona: {name}"

    # Create AgentCard
    agent_card = AgentCard()
    agent_card.name = name
    agent_card.description = description
    agent_card.url = f"https://agents.mantis.ai/persona/{name.lower().replace(' ', '_')}"
    agent_card.version = "1.0.0"
    agent_card.protocol_version = "0.3.0"
    agent_card.preferred_transport = "JSONRPC"
    agent_card.documentation_url = f"https://mantis.ai/personas/{name.lower().replace(' ', '_')}"

    # Create provider
    provider = AgentProvider()
    provider.organization = "Mantis AI"
    provider.url = "https://mantis.ai"
    agent_card.provider.CopyFrom(provider)

    # Create basic skill based on persona
    skill = AgentSkill()
    skill.id = f"{name.lower().replace(' ', '_')}_primary_skill"
    skill.name = f"{name} Expertise"
    skill.description = description
    skill.tags.extend(["strategic_thinking", "analysis", "advice"])
    skill.examples.append(f"What would {name} think about this situation?")
    skill.input_modes.extend(["text/plain", "application/json"])
    skill.output_modes.extend(["text/plain", "text/markdown"])
    agent_card.skills.append(skill)

    # Create capabilities
    capabilities = AgentCapabilities()
    capabilities.push_notifications = False
    capabilities.streaming = True

    # Add basic persona extension
    extension = AgentExtension()
    extension.uri = "https://mantis.ai/extensions/persona-characteristics/v1"
    extension.description = f"Persona characteristics for {name}"
    extension.required = False

    # Add basic persona data
    params = Struct()
    params.update({"name": name, "original_content": content[:1000], "source_file": str(path.name)})  # First 1000 chars
    extension.params.CopyFrom(params)

    capabilities.extensions.append(extension)
    agent_card.capabilities.CopyFrom(capabilities)

    return agent_card


def _enhance_with_llm(base_card, content: str, persona_name: str, model_spec: Optional[str] = None):
    """Enhance AgentCard with LLM-extracted persona data."""
    from ..llm.structured_extractor import get_structured_extractor
    from ..proto.mantis.v1.mantis_persona_pb2 import (
        MantisAgentCard,
        PersonaCharacteristics,
        CompetencyScores,
        DomainExpertise,
    )

    try:
        extractor = get_structured_extractor(model_spec)

        # Extract persona characteristics
        characteristics = extractor.extract_protobuf_sync(
            content=content,
            protobuf_type=PersonaCharacteristics,
            system_prompt="""Extract persona characteristics from markdown content. Focus on:
- Core principles that guide decision-making (3-5 key principles)
- Decision framework: How the persona approaches choices and problems
- Communication style: Their typical tone, language patterns, and approach
- Thinking patterns: Characteristic ways of processing information
- Characteristic phrases: Typical expressions or sayings they would use
- Behavioral tendencies: Common behavioral patterns and habits

Be specific to the persona described, not generic. Extract authentic characteristics.""",
            user_prompt=f"Analyze this persona and extract detailed characteristics:\n\n{content}",
        )

        # Extract competency scores and role adaptation
        competencies = extractor.extract_protobuf_sync(
            content=content,
            protobuf_type=CompetencyScores,
            system_prompt="""Score competencies 0.0-1.0 based on persona description:
- strategic planning and long-term vision
- team leadership and inspiring others  
- decisive decision making under pressure
- clear and persuasive communication
- analytical thinking and logical reasoning
- creative innovation and design thinking
- risk assessment and mitigation planning
- stakeholder relationship management
- domain expertise and technical knowledge
- adaptability to changing circumstances

Scoring: 0.0-0.3 Limited/weak, 0.4-0.6 Moderate, 0.7-0.8 Strong, 0.9-1.0 Exceptional

Also assess role adaptation (all scores 0.0-1.0):
- Leader score: How well they guide, make decisions, set vision
- Follower score: How well they execute, specialize, support others
- Narrator score: How well they facilitate, synthesize, communicate stories
- Preferred role: 1=LEADER, 2=FOLLOWER, 3=NARRATOR based on strengths
- Role flexibility: Ability to adapt between roles""",
            user_prompt=f"Score this persona's competencies and role adaptation:\n\n{content}",
        )

        # Extract domain expertise
        expertise = extractor.extract_protobuf_sync(
            content=content,
            protobuf_type=DomainExpertise,
            system_prompt="""Extract domain expertise including:
- Primary domains: Main areas of deep expertise (3-5 domains)
- Secondary domains: Supporting knowledge areas (2-4 domains)
- Methodologies: Preferred approaches, frameworks, methods they use
- Tools and frameworks: Specific tools, systems, technologies they know

Be specific to the persona. Focus on what makes them uniquely valuable.""",
            user_prompt=f"Extract domain expertise from:\n\n{content}",
        )

        # Create enhanced MantisAgentCard
        mantis_card = MantisAgentCard()
        mantis_card.agent_card.CopyFrom(base_card)
        mantis_card.persona_characteristics.CopyFrom(characteristics)
        mantis_card.competency_scores.CopyFrom(competencies)
        mantis_card.domain_expertise.CopyFrom(expertise)
        mantis_card.persona_title = persona_name

        # Set original_content directly with full fidelity
        mantis_card.persona_characteristics.original_content = content

        # Add skill tags from domain expertise
        for domain in expertise.primary_domains[:3]:  # Top 3 domains
            mantis_card.skill_tags.append(domain.lower().replace(" ", "_"))

        return mantis_card

    except ImportError:
        # LLM dependencies not available
        raise Exception("LLM dependencies not available")
    except Exception as e:
        raise Exception(f"LLM enhancement failed: {e}")


def parse_extension_data(extension_uri: str, extension_params: Dict[str, Any]) -> Optional[Any]:
    """
    Parse AgentExtension params into strongly typed protobuf message.

    Args:
        extension_uri: The URI identifying the extension type
        extension_params: The params dict from AgentExtension

    Returns:
        Parsed protobuf message instance, or None if URI not recognized
    """
    from ..config import PERSONA_EXTENSION_REGISTRY

    if extension_uri not in PERSONA_EXTENSION_REGISTRY:
        return None

    message_type_name = PERSONA_EXTENSION_REGISTRY[extension_uri]

    try:
        # Import the appropriate protobuf message type
        from ..proto.mantis.v1.mantis_persona_pb2 import (
            PersonaCharacteristics,
            CompetencyScores,
            RoleAdaptation,
            DomainExpertise,
        )

        # Map message type names to classes
        message_types = {
            "PersonaCharacteristics": PersonaCharacteristics,
            "CompetencyScores": CompetencyScores,
            "RoleAdaptation": RoleAdaptation,
            "DomainExpertise": DomainExpertise,
        }

        message_class = message_types.get(message_type_name)
        if not message_class:
            return None

        # Create and populate the protobuf message
        message = message_class()

        # Parse based on message type
        if message_type_name == "PersonaCharacteristics":
            if "core_principles" in extension_params:
                message.core_principles.extend(extension_params["core_principles"])
            if "decision_framework" in extension_params:
                message.decision_framework = extension_params["decision_framework"]
            if "communication_style" in extension_params:
                message.communication_style = extension_params["communication_style"]
            if "thinking_patterns" in extension_params:
                message.thinking_patterns.extend(extension_params["thinking_patterns"])
            if "characteristic_phrases" in extension_params:
                message.characteristic_phrases.extend(extension_params["characteristic_phrases"])
            if "behavioral_tendencies" in extension_params:
                message.behavioral_tendencies.extend(extension_params["behavioral_tendencies"])
            if "original_content" in extension_params:
                message.original_content = extension_params["original_content"]

        elif message_type_name == "CompetencyScores":
            if "competency_scores" in extension_params:
                for comp_name, score in extension_params["competency_scores"].items():
                    message.competency_scores[comp_name] = float(score)
            if "role_adaptation" in extension_params:
                role_data = extension_params["role_adaptation"]
                if "leader_score" in role_data:
                    message.role_adaptation.leader_score = float(role_data["leader_score"])
                if "follower_score" in role_data:
                    message.role_adaptation.follower_score = float(role_data["follower_score"])
                if "narrator_score" in role_data:
                    message.role_adaptation.narrator_score = float(role_data["narrator_score"])
                if "preferred_role" in role_data:
                    message.role_adaptation.preferred_role = role_data["preferred_role"]
                if "role_flexibility" in role_data:
                    message.role_adaptation.role_flexibility = float(role_data["role_flexibility"])

        elif message_type_name == "DomainExpertise":
            if "primary_domains" in extension_params:
                message.primary_domains.extend(extension_params["primary_domains"])
            if "secondary_domains" in extension_params:
                message.secondary_domains.extend(extension_params["secondary_domains"])
            if "methodologies" in extension_params:
                message.methodologies.extend(extension_params["methodologies"])
            if "tools_and_frameworks" in extension_params:
                message.tools_and_frameworks.extend(extension_params["tools_and_frameworks"])

        return message

    except Exception as e:
        # If parsing fails, return None
        print(f"Warning: Failed to parse extension {extension_uri}: {e}")
        return None


def get_parsed_extensions(agent_card) -> Dict[str, Any]:
    """
    Get parsed extension data from an AgentCard.

    Args:
        agent_card: AgentCard object with extensions

    Returns:
        Dict mapping extension URIs to parsed protobuf messages
    """
    parsed_extensions = {}

    for extension in agent_card.capabilities.extensions:
        parsed_data = parse_extension_data(extension.uri, extension.params)
        if parsed_data:
            parsed_extensions[extension.uri] = parsed_data

    return parsed_extensions


def load_agent_card_from_json(agent_data: Dict[str, Any]) -> "MantisAgentCard":
    """
    Load AgentCard from JSON data, handling both MantisAgentCard and basic AgentCard formats.

    Args:
        agent_data: Dict with agent card JSON data

    Returns:
        MantisAgentCard object
    """
    from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
    from google.protobuf.json_format import ParseDict

    # If this has persona data, it's a MantisAgentCard JSON - load directly
    if "persona_characteristics" in agent_data or "competency_scores" in agent_data or "domain_expertise" in agent_data:
        return ParseDict(agent_data, MantisAgentCard(), ignore_unknown_fields=True)

    # Otherwise, load as basic AgentCard and convert
    base_card = json_to_protobuf_agent_card(agent_data)
    return ensure_mantis_agent_card(base_card)


def ensure_mantis_agent_card(agent_card) -> "MantisAgentCard":
    """
    Convert an AgentCard to a MantisAgentCard with parsed extension data.
    If already a MantisAgentCard, return as-is.

    Args:
        agent_card: AgentCard or MantisAgentCard object

    Returns:
        MantisAgentCard with parsed extension data
    """
    from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
    from ..config import PERSONA_EXTENSION_REGISTRY

    # If already a MantisAgentCard, return as-is
    if isinstance(agent_card, MantisAgentCard):
        return agent_card

    mantis_card = MantisAgentCard()
    mantis_card.agent_card.CopyFrom(agent_card)

    parsed_extensions = get_parsed_extensions(agent_card)

    for uri, parsed_data in parsed_extensions.items():
        message_type_name = PERSONA_EXTENSION_REGISTRY.get(uri)

        if message_type_name == "PersonaCharacteristics":
            mantis_card.persona_characteristics.CopyFrom(parsed_data)
        elif message_type_name == "CompetencyScores":
            mantis_card.competency_scores.CopyFrom(parsed_data)
        elif message_type_name == "DomainExpertise":
            mantis_card.domain_expertise.CopyFrom(parsed_data)

    mantis_card.persona_title = agent_card.name

    for skill in agent_card.skills:
        mantis_card.skill_tags.append(skill.name)

    return mantis_card


def ensure_agent_card(mantis_agent_card):
    """
    Extract the base AgentCard from a MantisAgentCard.

    Args:
        mantis_agent_card: MantisAgentCard object

    Returns:
        Base AgentCard object
    """
    return mantis_agent_card.agent_card


class FieldNamingConvention(Enum):
    """Field naming conventions for JSON/protobuf conversion."""

    CAMEL_CASE = "camelCase"
    SNAKE_CASE = "snake_case"


def json_to_protobuf_agent_card(
    agent_data: Dict[str, Any], input_convention: FieldNamingConvention = FieldNamingConvention.CAMEL_CASE
) -> "AgentCard":
    """
    Convert JSON agent data to protobuf AgentCard with flexible field name handling.

    Args:
        agent_data: Dict with agent card data (can be MantisAgentCard or basic AgentCard JSON)
        input_convention: Naming convention of input JSON fields

    Returns:
        Protobuf AgentCard object
    """
    from ..proto.a2a_pb2 import AgentCard
    from google.protobuf.json_format import ParseDict

    # If this is MantisAgentCard JSON, extract the nested agent_card
    if "agent_card" in agent_data:
        agent_data = agent_data["agent_card"]

    def convert_keys(obj):
        if isinstance(obj, dict):
            new_obj = {}
            for key, value in obj.items():
                # Handle field name conversion based on input convention
                if input_convention == FieldNamingConvention.CAMEL_CASE:
                    # Convert known camelCase fields to snake_case
                    if key == "stateTransitionHistory":
                        # Skip - not in current protobuf spec
                        continue
                    elif key == "pushNotifications":
                        new_key = "push_notifications"
                    else:
                        new_key = key
                else:
                    # Already snake_case, use as-is
                    new_key = key

                new_obj[new_key] = convert_keys(value)
            return new_obj
        elif isinstance(obj, list):
            return [convert_keys(item) for item in obj]
        else:
            return obj

    converted_data = convert_keys(agent_data)
    return ParseDict(converted_data, AgentCard(), ignore_unknown_fields=True)


def protobuf_to_json_agent_card(
    agent_card: "AgentCard", output_convention: FieldNamingConvention = FieldNamingConvention.SNAKE_CASE
) -> Dict[str, Any]:
    """
    Convert protobuf AgentCard to JSON dict with flexible field name handling.

    Args:
        agent_card: Protobuf AgentCard object
        output_convention: Desired naming convention for output JSON

    Returns:
        Dict with agent card data in specified convention
    """
    from google.protobuf.json_format import MessageToDict

    # Convert to dict with snake_case (protobuf default)
    data = MessageToDict(agent_card, preserving_proto_field_name=True)

    if output_convention == FieldNamingConvention.CAMEL_CASE:
        # Convert snake_case to camelCase
        def convert_keys(obj):
            if isinstance(obj, dict):
                new_obj = {}
                for key, value in obj.items():
                    if key == "push_notifications":
                        new_key = "pushNotifications"
                    else:
                        new_key = key
                    new_obj[new_key] = convert_keys(value)
                return new_obj
            elif isinstance(obj, list):
                return [convert_keys(item) for item in obj]
            else:
                return obj

        return convert_keys(data)
    else:
        return data

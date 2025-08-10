"""
AgentCard generation and display functionality.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
    from ..proto.a2a_pb2 import AgentCard


def generate(input_path: str, model: Optional[str] = None) -> "MantisAgentCard":
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


def _create_base_agent_card(name: str, content: str, path: Path) -> "AgentCard":
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

    # Create basic skill based on persona (will be enhanced with LLM-generated data)
    skill = AgentSkill()
    skill.id = f"{name.lower().replace(' ', '_')}_primary_skill"
    skill.name = f"{name} Expertise"
    skill.description = description
    # Tags and examples will be populated by LLM from SkillsSummary extension
    skill.input_modes.extend(["text/plain", "application/json"])
    skill.output_modes.extend(["text/plain", "text/markdown"])
    agent_card.skills.append(skill)

    # Create capabilities
    capabilities = AgentCapabilities()
    capabilities.push_notifications = False
    capabilities.streaming = True

    # Add basic persona-characteristics extension
    persona_extension = AgentExtension()
    persona_extension.uri = "https://mantis.ai/extensions/persona-characteristics/v1"
    persona_extension.description = f"Persona characteristics for {name}"
    persona_extension.required = False

    # Add basic persona data
    persona_params = Struct()
    persona_params.update(
        {"name": name, "original_content": content[:1000], "source_file": str(path.name)}
    )  # First 1000 chars
    persona_extension.params.CopyFrom(persona_params)
    capabilities.extensions.append(persona_extension)

    # Add competency-scores extension
    competency_extension = AgentExtension()
    competency_extension.uri = "https://mantis.ai/extensions/competency-scores/v1"
    competency_extension.description = f"Competency scores for {name}"
    competency_extension.required = False

    # Add placeholder competency data
    competency_params = Struct()
    competency_params.update({"name": name, "source_file": str(path.name)})
    competency_extension.params.CopyFrom(competency_params)
    capabilities.extensions.append(competency_extension)

    # Add domain-expertise extension
    domain_extension = AgentExtension()
    domain_extension.uri = "https://mantis.ai/extensions/domain-expertise/v1"
    domain_extension.description = f"Domain expertise for {name}"
    domain_extension.required = False

    # Add placeholder domain data
    domain_params = Struct()
    domain_params.update({"name": name, "source_file": str(path.name)})
    domain_extension.params.CopyFrom(domain_params)
    capabilities.extensions.append(domain_extension)

    # Add skills-summary extension
    skills_extension = AgentExtension()
    skills_extension.uri = "https://mantis.ai/extensions/skills-summary/v1"
    skills_extension.description = f"Skills summary for {name}"
    skills_extension.required = False

    # Add placeholder skills data
    skills_params = Struct()
    skills_params.update({"name": name, "source_file": str(path.name)})
    skills_extension.params.CopyFrom(skills_params)
    capabilities.extensions.append(skills_extension)
    agent_card.capabilities.CopyFrom(capabilities)

    return agent_card


def _enhance_with_llm(
    base_card: "AgentCard", content: str, persona_name: str, model_spec: Optional[str] = None
) -> "MantisAgentCard":
    """Enhance AgentCard with LLM-extracted persona data."""
    from ..llm.structured_extractor import get_structured_extractor
    from ..proto.mantis.v1.mantis_persona_pb2 import (
        MantisAgentCard,
        PersonaCharacteristics,
        CompetencyScores,
        DomainExpertise,
        SkillsSummary,
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

        # Extract skills summary with domain-specific skills
        # Extract skills summary with hybrid approach (simple pydantic + manual protobuf)
        from pydantic import BaseModel
        from typing import List as TypingList

        class SkillsSummaryData(BaseModel):
            primary_skill_tags: TypingList[str]
            secondary_skill_tags: TypingList[str]
            skill_overview: str
            signature_abilities: TypingList[str]

        class SkillData(BaseModel):
            id: str
            name: str
            description: str
            examples: TypingList[str]
            related_competencies: TypingList[str]
            proficiency_score: float

        # Generate summary fields (this works reliably)
        summary_data = extractor.extract_sync(
            content=content,
            result_type=SkillsSummaryData,
            system_prompt="""Generate domain-specific skills summary for this persona:
- primary_skill_tags: 5-7 specific skill tags for search/categorization (use readable text like "Political Strategy", "Power Dynamics" - avoid underscores and generic tags like "strategic_thinking", "analysis", "advice")
- secondary_skill_tags: 3-5 broader category tags (use readable text like "Political Philosophy", "Leadership Theory")
- skill_overview: paragraph summarizing the persona's overall skill profile
- signature_abilities: 3-5 unique capabilities that distinguish this persona (use readable text like "Strategic Political Analysis", "Power Structure Navigation")""",
            user_prompt=f"Generate skills summary for this persona:\n\n{content}",
        )

        # Generate detailed skills (simpler approach)
        skills_data = extractor.extract_sync(
            content=content,
            result_type=TypingList[SkillData],
            system_prompt="""Generate exactly 3 detailed skills for this persona. Each skill must have:
- id: snake_case identifier (e.g., "strategic_planning", "diplomatic_negotiation") 
- name: human-readable name (e.g., "Strategic Planning", "Diplomatic Negotiation")
- description: detailed description (2-3 sentences)
- examples: array of 2 specific examples showing how this persona demonstrates this skill
- related_competencies: array of 2 related skills or sub-competencies
- proficiency_score: 0.0-1.0 score based on persona's expertise level""",
            user_prompt=f"Generate 3 detailed skills for this persona:\n\n{content}",
        )

        # Create protobuf SkillsSummary manually
        skills_summary = SkillsSummary()
        skills_summary.primary_skill_tags.extend(summary_data.primary_skill_tags)
        skills_summary.secondary_skill_tags.extend(summary_data.secondary_skill_tags)
        skills_summary.skill_overview = summary_data.skill_overview
        skills_summary.signature_abilities.extend(summary_data.signature_abilities)

        # Add detailed skills to protobuf
        from ..proto.mantis.v1.mantis_persona_pb2 import SkillDefinition

        for skill_data in skills_data:
            skill_def = SkillDefinition()
            skill_def.id = skill_data.id
            skill_def.name = skill_data.name
            skill_def.description = skill_data.description
            skill_def.examples.extend(skill_data.examples)
            skill_def.related_competencies.extend(skill_data.related_competencies)
            skill_def.proficiency_score = skill_data.proficiency_score
            skills_summary.skills.append(skill_def)

        # Create enhanced MantisAgentCard
        mantis_card = MantisAgentCard()
        mantis_card.agent_card.CopyFrom(base_card)
        mantis_card.persona_characteristics.CopyFrom(characteristics)
        mantis_card.competency_scores.CopyFrom(competencies)
        mantis_card.domain_expertise.CopyFrom(expertise)
        mantis_card.skills_summary.CopyFrom(skills_summary)
        mantis_card.persona_title = persona_name

        # Set original_content directly with full fidelity
        mantis_card.persona_characteristics.original_content = content

        # Add skill tags from skills summary (primary source) and domain expertise (fallback)
        if skills_summary.primary_skill_tags:
            mantis_card.skill_tags.extend(skills_summary.primary_skill_tags[:5])  # Top 5 primary tags
        else:
            # Fallback to domain expertise if skills summary has no tags
            for domain in expertise.primary_domains[:3]:  # Top 3 domains
                mantis_card.skill_tags.append(domain.lower().replace(" ", "_"))

        # Update AgentSkill fields with data from SkillsSummary
        if mantis_card.agent_card.skills:
            primary_skill = mantis_card.agent_card.skills[0]  # Update the primary skill

            # If we have detailed skills, use the top skill for name/description/examples
            if skills_summary.skills:
                top_skill = skills_summary.skills[0]
                primary_skill.name = top_skill.name
                primary_skill.description = top_skill.description

                # Add LLM-generated examples
                del primary_skill.examples[:]
                if top_skill.examples:
                    primary_skill.examples.extend(top_skill.examples)

            # Always update tags from primary_skill_tags (fallback when detailed skills missing)
            del primary_skill.tags[:]
            if skills_summary.primary_skill_tags:
                primary_skill.tags.extend(skills_summary.primary_skill_tags[:5])

        # Update the extensions with full LLM-extracted data
        from google.protobuf.json_format import MessageToDict

        for extension in mantis_card.agent_card.capabilities.extensions:
            if extension.uri == "https://mantis.ai/extensions/persona-characteristics/v1":
                # Update persona extension with full characteristics data
                persona_dict = MessageToDict(characteristics, preserving_proto_field_name=True)
                persona_dict.update(
                    {"name": persona_name, "source_file": str(Path(content[:100]).stem if content else "generated")}
                )
                extension.params.Clear()
                extension.params.update(persona_dict)

            elif extension.uri == "https://mantis.ai/extensions/competency-scores/v1":
                # Update competency extension with full competency data
                competency_dict = MessageToDict(competencies, preserving_proto_field_name=True)
                competency_dict.update(
                    {"name": persona_name, "source_file": str(Path(content[:100]).stem if content else "generated")}
                )
                extension.params.Clear()
                extension.params.update(competency_dict)

            elif extension.uri == "https://mantis.ai/extensions/domain-expertise/v1":
                # Update domain extension with full expertise data
                domain_dict = MessageToDict(expertise, preserving_proto_field_name=True)
                domain_dict.update(
                    {"name": persona_name, "source_file": str(Path(content[:100]).stem if content else "generated")}
                )
                extension.params.Clear()
                extension.params.update(domain_dict)

            elif extension.uri == "https://mantis.ai/extensions/skills-summary/v1":
                # Update skills extension with full skills summary data
                skills_dict = MessageToDict(skills_summary, preserving_proto_field_name=True)
                skills_dict.update(
                    {"name": persona_name, "source_file": str(Path(content[:100]).stem if content else "generated")}
                )
                extension.params.Clear()
                extension.params.update(skills_dict)

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
            SkillsSummary,
            SkillDefinition,
        )

        # Map message type names to classes
        message_types = {
            "PersonaCharacteristics": PersonaCharacteristics,
            "CompetencyScores": CompetencyScores,
            "RoleAdaptation": RoleAdaptation,
            "DomainExpertise": DomainExpertise,
            "SkillsSummary": SkillsSummary,
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
                    # Convert string role preference to enum value
                    from ..proto.mantis.v1.mantis_persona_pb2 import RolePreference

                    role_str = role_data["preferred_role"]
                    if role_str == "ROLE_PREFERENCE_LEADER":
                        message.role_adaptation.preferred_role = RolePreference.ROLE_PREFERENCE_LEADER
                    elif role_str == "ROLE_PREFERENCE_FOLLOWER":
                        message.role_adaptation.preferred_role = RolePreference.ROLE_PREFERENCE_FOLLOWER
                    elif role_str == "ROLE_PREFERENCE_NARRATOR":
                        message.role_adaptation.preferred_role = RolePreference.ROLE_PREFERENCE_NARRATOR
                    else:
                        # Fallback to direct assignment for numeric values
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

        elif message_type_name == "SkillsSummary":
            if "skills" in extension_params:
                for skill_data in extension_params["skills"]:
                    skill_def = SkillDefinition()
                    if "id" in skill_data:
                        skill_def.id = skill_data["id"]
                    if "name" in skill_data:
                        skill_def.name = skill_data["name"]
                    if "description" in skill_data:
                        skill_def.description = skill_data["description"]
                    if "examples" in skill_data:
                        skill_def.examples.extend(skill_data["examples"])
                    if "related_competencies" in skill_data:
                        skill_def.related_competencies.extend(skill_data["related_competencies"])
                    if "proficiency_score" in skill_data:
                        skill_def.proficiency_score = float(skill_data["proficiency_score"])
                    message.skills.append(skill_def)

            if "primary_skill_tags" in extension_params:
                message.primary_skill_tags.extend(extension_params["primary_skill_tags"])
            if "secondary_skill_tags" in extension_params:
                message.secondary_skill_tags.extend(extension_params["secondary_skill_tags"])
            if "skill_overview" in extension_params:
                message.skill_overview = extension_params["skill_overview"]
            if "signature_abilities" in extension_params:
                message.signature_abilities.extend(extension_params["signature_abilities"])

        return message

    except Exception as e:
        # If parsing fails, return None
        print(f"Warning: Failed to parse extension {extension_uri}: {e}")
        return None


def get_parsed_extensions(agent_card: "AgentCard") -> Dict[str, Any]:
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


def validate_mantis_agent_card(mantis_card: "MantisAgentCard") -> None:
    """
    Validate that a MantisAgentCard has all required extensions.

    Args:
        mantis_card: MantisAgentCard to validate

    Raises:
        ValueError: If required extensions are missing
    """
    missing_extensions = []

    # Check for required extension data
    if (
        not mantis_card.persona_characteristics.core_principles
        and not mantis_card.persona_characteristics.communication_style
    ):
        missing_extensions.append("PersonaCharacteristics")

    if (
        not mantis_card.competency_scores.competency_scores
        and not mantis_card.competency_scores.role_adaptation.leader_score
    ):
        missing_extensions.append("CompetencyScores")

    if not mantis_card.domain_expertise.primary_domains and not mantis_card.domain_expertise.methodologies:
        missing_extensions.append("DomainExpertise")

    if not mantis_card.skills_summary.primary_skill_tags and not mantis_card.skills_summary.skill_overview:
        missing_extensions.append("SkillsSummary")

    if missing_extensions:
        raise ValueError(
            f"MantisAgentCard validation failed: Missing required extensions: {missing_extensions}. "
            f"A valid MantisAgentCard must have all 4 extensions: PersonaCharacteristics, "
            f"CompetencyScores, DomainExpertise, and SkillsSummary."
        )


def load_agent_card_from_json(agent_data: Dict[str, Any]) -> "MantisAgentCard":
    """
    Load AgentCard from JSON data, handling both MantisAgentCard and basic AgentCard formats.

    Args:
        agent_data: Dict with agent card JSON data

    Returns:
        MantisAgentCard object

    Raises:
        ValueError: If the card is missing required extensions
    """
    from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
    from google.protobuf.json_format import ParseDict

    # If this has persona data, it's a MantisAgentCard JSON - load directly
    if "persona_characteristics" in agent_data or "competency_scores" in agent_data or "domain_expertise" in agent_data:
        mantis_card = ParseDict(agent_data, MantisAgentCard(), ignore_unknown_fields=True)
        validate_mantis_agent_card(mantis_card)
        return mantis_card  # type: ignore[no-any-return]

    # Otherwise, load as basic AgentCard and convert
    base_card = json_to_protobuf_agent_card(agent_data)
    return ensure_mantis_agent_card(base_card)


def ensure_mantis_agent_card(agent_card: "AgentCard") -> "MantisAgentCard":
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

    # Track which required extensions we've found
    required_extensions = {
        "PersonaCharacteristics": False,
        "CompetencyScores": False,
        "DomainExpertise": False,
        "SkillsSummary": False,
    }

    for uri, parsed_data in parsed_extensions.items():
        message_type_name = PERSONA_EXTENSION_REGISTRY.get(uri)

        if message_type_name == "PersonaCharacteristics":
            mantis_card.persona_characteristics.CopyFrom(parsed_data)
            required_extensions["PersonaCharacteristics"] = True
        elif message_type_name == "CompetencyScores":
            mantis_card.competency_scores.CopyFrom(parsed_data)
            required_extensions["CompetencyScores"] = True
        elif message_type_name == "DomainExpertise":
            mantis_card.domain_expertise.CopyFrom(parsed_data)
            required_extensions["DomainExpertise"] = True
        elif message_type_name == "SkillsSummary":
            mantis_card.skills_summary.CopyFrom(parsed_data)
            required_extensions["SkillsSummary"] = True

    # Validate that all required extensions are present
    missing_extensions = [ext for ext, found in required_extensions.items() if not found]
    if missing_extensions:
        raise ValueError(
            f"MantisAgentCard validation failed: Missing required extensions: {missing_extensions}. "
            f"A valid MantisAgentCard must have all 4 extensions: PersonaCharacteristics, "
            f"CompetencyScores, DomainExpertise, and SkillsSummary."
        )

    mantis_card.persona_title = agent_card.name

    for skill in agent_card.skills:
        mantis_card.skill_tags.append(skill.name)

    return mantis_card


def ensure_agent_card(mantis_agent_card: "MantisAgentCard") -> "AgentCard":
    """
    Extract the base AgentCard from a MantisAgentCard.

    Args:
        mantis_agent_card: MantisAgentCard object

    Returns:
        Base AgentCard object
    """
    return mantis_agent_card.agent_card  # type: ignore[no-any-return]


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

    def convert_keys(obj: Any) -> Any:
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
    return ParseDict(converted_data, AgentCard(), ignore_unknown_fields=True)  # type: ignore[no-any-return]


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
        def convert_keys(obj: Any) -> Any:
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

        return convert_keys(data)  # type: ignore[no-any-return]
    else:
        return data  # type: ignore[no-any-return]

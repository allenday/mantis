"""
AgentCard generation and display functionality.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, Union
from rich.console import Console


def generate(input_path: str, model: Optional[str] = None):
    """
    Generate AgentCard from markdown file.
    
    Args:
        input_path: Path to markdown persona file
        model: Optional model specification
        
    Returns:
        AgentCard object
    """
    # Import persona creation function and AgentCard conversion
    from ..personas.personas import create_persona_from_markdown
    from ..registry.agent_cards import create_agent_card_from_persona

    # Create persona (pass model if specified)
    agent = create_persona_from_markdown(input_path, model=model)
    structured_persona = agent.structured_persona

    # Convert to AgentCard format (the final output format)
    agent_card = create_agent_card_from_persona(structured_persona)
    
    return agent_card


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
            DomainExpertise
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


def ensure_mantis_agent_card(agent_card) -> "MantisAgentCard":
    """
    Convert an AgentCard to a MantisAgentCard with parsed extension data.
    
    Args:
        agent_card: AgentCard object (from a2a proto)
        
    Returns:
        MantisAgentCard with parsed extension data
    """
    from ..proto.mantis.v1.mantis_persona_pb2 import MantisAgentCard
    from ..config import PERSONA_EXTENSION_REGISTRY
    
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


from enum import Enum

class FieldNamingConvention(Enum):
    """Field naming conventions for JSON/protobuf conversion."""
    CAMEL_CASE = "camelCase"
    SNAKE_CASE = "snake_case"


def json_to_protobuf_agent_card(
    agent_data: Dict[str, Any], 
    input_convention: FieldNamingConvention = FieldNamingConvention.CAMEL_CASE
) -> "AgentCard":
    """
    Convert JSON agent data to protobuf AgentCard with flexible field name handling.
    
    Args:
        agent_data: Dict with agent card data
        input_convention: Naming convention of input JSON fields
        
    Returns:
        Protobuf AgentCard object
    """
    from ..proto.a2a_pb2 import AgentCard
    from google.protobuf.json_format import ParseDict
    
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
    agent_card: "AgentCard",
    output_convention: FieldNamingConvention = FieldNamingConvention.SNAKE_CASE
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

#!/usr/bin/env python3
"""
Reusable LLM-powered structured data extractor using pydantic-ai.

This module provides a generic, reusable interface for extracting structured data
from text using various LLM providers. It can be used across multiple GitHub issues
for persona extraction, prompt composition, and other structured data tasks.
"""

import logging
from typing import TypeVar, Type, Optional, Any, List

# Load environment variables early
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Observability imports
try:
    from ..observability import trace_llm_interaction, get_structured_logger

    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False


# Handle pydantic-ai imports gracefully
try:
    from pydantic_ai import Agent
    from pydantic_ai.models import Model

    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    # Create placeholder aliases to avoid type errors
    Agent = Any  # type: ignore
    Model = Any  # type: ignore

logger = logging.getLogger(__name__)

# Observability logger
if OBSERVABILITY_AVAILABLE:
    obs_logger = get_structured_logger("structured_extractor")
else:
    obs_logger = None  # type: ignore

T = TypeVar("T")  # Generic type for structured data


class StructuredExtractionError(Exception):
    """Raised when structured data extraction fails."""

    pass


class StructuredExtractor:
    """
    Reusable LLM-powered structured data extractor.

    This class provides a generic interface for extracting structured data from text
    using pydantic-ai with various LLM providers. It supports both pydantic models
    and protobuf messages as result types.

    Usage:
        extractor = StructuredExtractor("anthropic:claude-3-5-haiku-20241022")

        # Extract with pydantic model
        result = extractor.extract_sync(
            content="Some text...",
            result_type=MyPydanticModel,
            system_prompt="Extract data from this text...",
            user_prompt="Here is the text: ..."
        )

        # Extract with protobuf message (converted on-the-fly)
        result = extractor.extract_protobuf_sync(
            content="Some text...",
            protobuf_type=MyProtobufMessage,
            system_prompt="Extract data...",
            user_prompt="Text: ..."
        )
    """

    def __init__(self, model_spec: Optional[str] = None):
        """
        Initialize the structured extractor.

        Args:
            model_spec: Model specification in format "provider:model" (e.g., "anthropic:claude-3-5-haiku-20241022")
                       If None, uses DEFAULT_MODEL from config
        """
        if not PYDANTIC_AI_AVAILABLE:
            raise StructuredExtractionError("pydantic-ai is not available. Install with: pip install pydantic-ai")

        self.model_spec = model_spec or self._get_default_model()
        self._model_cache: Optional[Model] = None

    def _get_default_model(self) -> str:
        """Get default model from config."""
        try:
            from ..config import DEFAULT_MODEL

            return DEFAULT_MODEL
        except ImportError:
            # Fallback if config not available
            return "anthropic:claude-3-5-haiku-20241022"

    def _create_model(self) -> Model:
        """Create LLM model instance with caching."""
        if self._model_cache is not None:
            return self._model_cache

        try:
            if ":" in self.model_spec:
                provider, model_name = self.model_spec.split(":", 1)
                model = self._create_provider_model(provider.lower(), model_name)
            else:
                # Default to anthropic if no provider specified
                model = self._create_provider_model("anthropic", self.model_spec)

            self._model_cache = model
            return model

        except ImportError as e:
            raise StructuredExtractionError(f"Missing LLM dependencies for {self.model_spec}: {e}")
        except Exception as e:
            raise StructuredExtractionError(f"Failed to create model {self.model_spec}: {e}")

    def _create_provider_model(self, provider: str, model_name: str) -> Model:
        """Create model for specific provider."""
        if provider == "anthropic":
            from pydantic_ai.models.anthropic import AnthropicModel

            return AnthropicModel(model_name)
        elif provider == "openai":
            from pydantic_ai.models.openai import OpenAIModel

            return OpenAIModel(model_name)
        elif provider == "google" or provider == "gemini":
            from pydantic_ai.models.gemini import GeminiModel

            return GeminiModel(model_name)
        elif provider == "groq":
            from pydantic_ai.models.groq import GroqModel

            return GroqModel(model_name)
        else:
            raise StructuredExtractionError(f"Unsupported provider: {provider}")

    async def extract_async(
        self, content: str, result_type: Type[T], system_prompt: str, user_prompt: str, **agent_kwargs
    ) -> T:
        """
        Extract structured data asynchronously.

        Args:
            content: The input text content to process
            result_type: Pydantic model class to extract data into
            system_prompt: System prompt defining the extraction task
            user_prompt: User prompt with the specific content/instructions
            **agent_kwargs: Additional arguments to pass to the pydantic-ai Agent

        Returns:
            Instance of result_type with extracted data

        Raises:
            StructuredExtractionError: If extraction fails
        """
        try:
            model = self._create_model()

            # Create pydantic-ai agent
            agent = Agent(model=model, result_type=result_type, system_prompt=system_prompt, **agent_kwargs)

            # Run extraction
            result = await agent.run(user_prompt)
            return result.data

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise StructuredExtractionError(f"LLM extraction failed: {e}")

    def extract_sync(
        self, content: str, result_type: Type[T], system_prompt: str, user_prompt: str, **agent_kwargs
    ) -> T:
        """
        Extract structured data synchronously.

        Args:
            content: The input text content to process
            result_type: Pydantic model class to extract data into
            system_prompt: System prompt defining the extraction task
            user_prompt: User prompt with the specific content/instructions
            **agent_kwargs: Additional arguments to pass to the pydantic-ai Agent

        Returns:
            Instance of result_type with extracted data

        Raises:
            StructuredExtractionError: If extraction fails
        """
        import asyncio

        try:
            # Handle event loop scenarios
            try:
                asyncio.get_running_loop()
                # We're in an event loop, run in thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            self.extract_async(content, result_type, system_prompt, user_prompt, **agent_kwargs)
                        )
                    )
                    return future.result()
            except RuntimeError:
                # No event loop, use asyncio.run
                return asyncio.run(self.extract_async(content, result_type, system_prompt, user_prompt, **agent_kwargs))

        except Exception as e:
            raise StructuredExtractionError(f"Synchronous extraction failed: {e}")

    def extract_protobuf_sync(
        self, content: str, protobuf_type: Type, system_prompt: str, user_prompt: str, **agent_kwargs
    ):
        """
        Extract data into protobuf message using on-the-fly pydantic conversion.

        Args:
            content: The input text content to process
            protobuf_type: Protobuf message class to extract data into
            system_prompt: System prompt defining the extraction task
            user_prompt: User prompt with the specific content/instructions
            **agent_kwargs: Additional arguments to pass to the pydantic-ai Agent

        Returns:
            Instance of protobuf_type with extracted data

        Raises:
            StructuredExtractionError: If extraction fails
        """
        try:
            # Convert protobuf to pydantic on-the-fly
            pydantic_model = self._protobuf_to_pydantic(protobuf_type)

            # Extract using pydantic model
            pydantic_result = self.extract_sync(content, pydantic_model, system_prompt, user_prompt, **agent_kwargs)

            # Convert back to protobuf
            return self._pydantic_to_protobuf(pydantic_result, protobuf_type)

        except Exception as e:
            raise StructuredExtractionError(f"Protobuf extraction failed: {e}")

    async def extract_text_response(self, prompt: str, query: str, model: Optional[str] = None) -> str:
        """
        Extract a text response using the composed prompt as system prompt.

        Args:
            prompt: The composed system prompt
            query: The user query
            model: Optional model override

        Returns:
            Text response from the LLM
        """
        # Determine final model spec
        final_model = model or self.model_spec
        provider = final_model.split(":")[0] if ":" in final_model else "unknown"

        # Start LLM interaction tracing if observability available
        if OBSERVABILITY_AVAILABLE and obs_logger:
            interaction = trace_llm_interaction(
                model_spec=final_model, provider=provider, system_prompt=prompt, user_prompt=query
            )
            obs_logger.info(f"Starting LLM text extraction with {final_model}")
        else:
            interaction = None

        try:
            # Override model if specified
            original_model = None
            if model:
                original_model = self.model_spec
                self.model_spec = model
                self._model_cache = None  # Clear cache to use new model

            model_instance = self._create_model()

            # Create a simple text agent (no structured output)
            agent = Agent(model=model_instance, system_prompt=prompt)

            # Run and get text response
            result = await agent.run(query)
            response_text = str(result.data)

            # Complete LLM interaction tracing
            if interaction and obs_logger:
                # complete_llm_interaction(interaction, response_text)  # TODO: Implement this function
                pass
                obs_logger.info(f"Completed LLM text extraction: {len(response_text)} chars")

            # Restore original model if we changed it
            if original_model:
                self.model_spec = original_model
                self._model_cache = None

            return response_text

        except Exception as e:
            # Complete LLM interaction with error
            if interaction and obs_logger:
                # complete_llm_interaction(interaction, "", error=str(e))  # TODO: Implement this function
                pass
                obs_logger.error(f"LLM text extraction failed: {e}")

            logger.error(f"Text response extraction failed: {e}")
            raise StructuredExtractionError(f"Text response extraction failed: {e}")

    async def extract_text_response_with_tools(
        self, prompt: str, query: str, model: Optional[str] = None, tools: Optional[dict] = None
    ) -> str:
        """
        Extract a text response with tool support enabled.

        Args:
            prompt: The composed system prompt
            query: The user query
            model: Optional model override
            tools: Dictionary of native pydantic-ai tool functions

        Returns:
            Text response from the LLM
        """
        # Determine final model spec
        final_model = model or self.model_spec
        provider = final_model.split(":")[0] if ":" in final_model else "unknown"

        # Start LLM interaction tracing if observability available
        if OBSERVABILITY_AVAILABLE and obs_logger:
            interaction = trace_llm_interaction(
                model_spec=final_model,
                provider=provider,
                system_prompt=prompt,
                user_prompt=query,
                tools_available=list(tools.keys()) if tools else [],
            )
            obs_logger.info(f"Starting tool-enabled LLM text extraction with {final_model}")
        else:
            interaction = None

        try:
            # Override model if specified
            original_model = None
            if model:
                original_model = self.model_spec
                self.model_spec = model
                self._model_cache = None  # Clear cache to use new model

            model_instance = self._create_model()

            # Tools are already native pydantic-ai functions - use them directly
            tool_functions: List[Any] = []
            if tools:
                # Tools should already be functions, extract them from the dictionary
                tool_functions = list(tools.values())
                if OBSERVABILITY_AVAILABLE and obs_logger:
                    obs_logger.info(f"Using {len(tool_functions)} native pydantic-ai tools: {list(tools.keys())}")

            # Create agent with native tools
            agent = Agent(
                model=model_instance,
                system_prompt=prompt,
                tools=tool_functions or None,  # type: ignore[arg-type]
            )

            # Run and get text response
            result = await agent.run(query)
            response_text = str(result.data)

            # Complete LLM interaction tracing
            if interaction and obs_logger:
                # complete_llm_interaction(interaction, response_text)  # TODO: Implement this function
                pass
                obs_logger.info(f"Completed tool-enabled LLM text extraction: {len(response_text)} chars")

            # Restore original model if we changed it
            if original_model:
                self.model_spec = original_model
                self._model_cache = None

            return response_text

        except Exception as e:
            # Complete LLM interaction with error
            if interaction and obs_logger:
                # complete_llm_interaction(interaction, "", error=str(e))  # TODO: Implement this function
                pass
                obs_logger.error(f"Tool-enabled LLM text extraction failed: {e}")

            logger.error(f"Tool-enabled text response extraction failed: {e}")
            raise StructuredExtractionError(f"Tool-enabled text response extraction failed: {e}")

    # Legacy conversion methods removed - we now use native pydantic-ai tools directly

    def _protobuf_to_pydantic(self, protobuf_type: Type) -> Type:
        """Convert protobuf message class to equivalent pydantic model."""
        try:
            # Try using protobuf-to-pydantic if available
            try:
                from protobuf_to_pydantic import msg_to_pydantic_dataclass

                return msg_to_pydantic_dataclass(protobuf_type)
            except ImportError:
                # Fallback: create pydantic model manually based on protobuf descriptor
                return self._create_pydantic_from_protobuf(protobuf_type)

        except Exception as e:
            raise StructuredExtractionError(f"Failed to convert protobuf to pydantic: {e}")

    def _create_pydantic_from_protobuf(self, protobuf_type: Type) -> Type:
        """Create pydantic model from protobuf descriptor (fallback method)."""
        from pydantic import BaseModel, Field
        from typing import Optional

        # Get protobuf descriptor
        descriptor = protobuf_type.DESCRIPTOR

        # Build field definitions and annotations
        fields = {}
        annotations = {}

        for field in descriptor.fields:
            field_type = self._get_python_type_for_protobuf_field(field)

            # Create field with default
            if field.label == field.LABEL_REPEATED:
                default_value = Field(default_factory=list)
                annotations[field.name] = field_type
            elif hasattr(field, "default_value") and field.default_value is not None:
                default_value = field.default_value
                # Make optional if has default
                annotations[field.name] = Optional[field_type] if field_type is not type(None) else field_type
            else:
                # Check if this is a list type and provide appropriate default
                from typing import get_origin

                try:
                    if get_origin(field_type) is list:
                        default_value = Field(default_factory=list)
                        annotations[field.name] = field_type
                    else:
                        default_value = Field(default=None)  # type: ignore
                        annotations[field.name] = Optional[field_type] if field_type is not type(None) else field_type
                except (TypeError, AttributeError):
                    # Fallback for simple types
                    if hasattr(field_type, "__origin__") and field_type.__origin__ is list:
                        default_value = Field(default_factory=list)
                        annotations[field.name] = field_type
                    else:
                        default_value = Field(default=None)  # type: ignore
                        annotations[field.name] = Optional[field_type] if field_type is not type(None) else field_type

            fields[field.name] = default_value

        # Create dynamic pydantic model class with proper annotations
        # Need to set annotations before creating the class
        fields["__annotations__"] = annotations  # type: ignore
        model_class = type(f"{protobuf_type.__name__}Pydantic", (BaseModel,), fields)

        return model_class

    def _get_python_type_for_protobuf_field(self, field):
        """Get Python type annotation for protobuf field."""
        from typing import List, Dict, Optional, Any

        # Check if this is a map field (map<key, value>)
        if hasattr(field, "message_type") and field.message_type and hasattr(field.message_type, "fields"):
            # Check if this looks like a map entry (has key and value fields)
            map_fields = {f.name: f for f in field.message_type.fields}
            if "key" in map_fields and "value" in map_fields:
                # For map fields, we'll use Dict[str, Any] as a fallback
                # since we can't dynamically create generic types at runtime
                return Dict[str, Any]

        # Check if this is a nested message field (not a map)
        if hasattr(field, "message_type") and field.message_type and field.type == field.TYPE_MESSAGE:
            # Recursively convert nested message types to pydantic models
            nested_protobuf_type = field.message_type._concrete_class
            nested_pydantic_type = self._protobuf_to_pydantic(nested_protobuf_type)

            # Handle repeated nested messages
            if field.label == field.LABEL_REPEATED:
                return List[nested_pydantic_type]  # type: ignore[valid-type]
            else:
                return nested_pydantic_type  # type: ignore[valid-type]

        # Handle repeated fields with specific scalar types
        if field.label == field.LABEL_REPEATED:
            scalar_type = self._get_scalar_type(field)
            return List[scalar_type]  # type: ignore[valid-type]

        # Handle optional fields with specific scalar types
        if field.label == field.LABEL_OPTIONAL:
            scalar_type = self._get_scalar_type(field)
            return Optional[scalar_type]  # type: ignore[valid-type]

        # For scalar fields, return specific type
        return self._get_scalar_type(field)

    def _get_scalar_type(self, field):
        """Get specific Python type for protobuf scalar field."""
        # Map protobuf field types to Python types
        if field.type == field.TYPE_STRING:
            return str
        elif field.type == field.TYPE_BOOL:
            return bool
        elif field.type == field.TYPE_INT32 or field.type == field.TYPE_INT64:
            return int
        elif field.type == field.TYPE_UINT32 or field.type == field.TYPE_UINT64:
            return int
        elif field.type == field.TYPE_FLOAT or field.type == field.TYPE_DOUBLE:
            return float
        elif field.type == field.TYPE_BYTES:
            return bytes
        else:
            # Fallback for unknown types
            from typing import Any

            return Any

    def _pydantic_to_protobuf(self, pydantic_obj, protobuf_type: Type):
        """Convert pydantic model instance to protobuf message."""
        protobuf_obj = protobuf_type()

        # Copy fields from pydantic to protobuf
        for field_name, value in pydantic_obj.dict().items():
            if hasattr(protobuf_obj, field_name) and value is not None:
                try:
                    field = getattr(protobuf_obj, field_name)

                    # Handle repeated fields
                    if hasattr(field, "extend") and isinstance(value, list):
                        # Check if this is a repeated nested message
                        if value and isinstance(value[0], dict):
                            # Get the protobuf field descriptor to find the nested message type
                            descriptor = protobuf_obj.DESCRIPTOR
                            proto_field = descriptor.fields_by_name.get(field_name)
                            if proto_field and hasattr(proto_field, "message_type") and proto_field.message_type:
                                # Convert each dict to a nested protobuf message
                                nested_type = proto_field.message_type._concrete_class
                                for item_dict in value:
                                    nested_obj = self._pydantic_dict_to_protobuf(item_dict, nested_type)
                                    field.append(nested_obj)
                            else:
                                field.extend(value)
                        else:
                            field.extend(value)
                    # Handle map fields (protobuf maps have .update() method)
                    elif hasattr(field, "update") and isinstance(value, dict):
                        field.update(value)
                    # Handle protobuf map fields that appear as dict in pydantic
                    elif isinstance(value, dict) and hasattr(field, "clear"):
                        field.clear()
                        field.update(value)
                    # Handle nested message fields (check if field has protobuf message methods)
                    elif hasattr(field, "CopyFrom") and isinstance(value, dict):
                        # Populate nested message fields
                        for sub_field_name, sub_value in value.items():
                            if hasattr(field, sub_field_name) and sub_value is not None:
                                try:
                                    setattr(field, sub_field_name, sub_value)
                                except (TypeError, ValueError):
                                    pass  # Skip invalid assignments
                    # Handle nested message fields that got returned as strings (fallback)
                    elif hasattr(field, "CopyFrom") and isinstance(value, str):
                        # Skip - can't convert string to nested message
                        pass
                    # Handle scalar fields
                    else:
                        try:
                            setattr(protobuf_obj, field_name, value)
                        except (TypeError, ValueError):
                            pass  # Skip invalid assignments

                except Exception:
                    pass  # Skip fields that can't be processed

        return protobuf_obj

    def _pydantic_dict_to_protobuf(self, data_dict: dict, protobuf_type: Type):
        """Convert a dictionary to a protobuf message (helper for nested messages)."""
        protobuf_obj = protobuf_type()
        for field_name, value in data_dict.items():
            if hasattr(protobuf_obj, field_name) and value is not None:
                try:
                    setattr(protobuf_obj, field_name, value)
                except (TypeError, ValueError):
                    pass  # Skip invalid assignments
        return protobuf_obj


# Global extractor instance for reuse
_global_extractor: Optional[StructuredExtractor] = None


def get_structured_extractor(model_spec: Optional[str] = None) -> StructuredExtractor:
    """
    Get or create global structured extractor instance.

    This provides a singleton pattern for reusing the extractor across
    different parts of the application (Issues #17, #19, persona extraction, etc.).

    Args:
        model_spec: Model specification. If provided, creates new extractor with this model.
                   If None, reuses existing extractor or creates with default model.

    Returns:
        StructuredExtractor instance
    """
    global _global_extractor

    if _global_extractor is None or model_spec is not None:
        _global_extractor = StructuredExtractor(model_spec)

    return _global_extractor


def extract_structured_data_sync(
    content: str,
    result_type: Type[T],
    system_prompt: str,
    user_prompt: str,
    model_spec: Optional[str] = None,
    **agent_kwargs,
) -> T:
    """
    Convenience function for one-off structured data extraction.

    Args:
        content: Input text content
        result_type: Pydantic model class to extract into
        system_prompt: System prompt for the extraction task
        user_prompt: User prompt with content/instructions
        model_spec: Optional model specification
        **agent_kwargs: Additional agent arguments

    Returns:
        Extracted structured data
    """
    extractor = get_structured_extractor(model_spec)
    return extractor.extract_sync(content, result_type, system_prompt, user_prompt, **agent_kwargs)


def extract_protobuf_data_sync(
    content: str,
    protobuf_type: Type,
    system_prompt: str,
    user_prompt: str,
    model_spec: Optional[str] = None,
    **agent_kwargs,
):
    """
    Convenience function for one-off protobuf data extraction.

    Args:
        content: Input text content
        protobuf_type: Protobuf message class to extract into
        system_prompt: System prompt for the extraction task
        user_prompt: User prompt with content/instructions
        model_spec: Optional model specification
        **agent_kwargs: Additional agent arguments

    Returns:
        Extracted protobuf message instance
    """
    extractor = get_structured_extractor(model_spec)
    return extractor.extract_protobuf_sync(content, protobuf_type, system_prompt, user_prompt, **agent_kwargs)

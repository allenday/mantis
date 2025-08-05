"""
Agent tools for external service integration.

This module provides tools that agents can use to interact with external
services and data sources, supporting both pydantic-ai and FastA2A execution.
"""

from .web_fetch import WebFetchTool

__all__ = ["WebFetchTool"]

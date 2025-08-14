"""
ADK Integration Module

This module provides integration between Mantis and Google's Agent Development Kit (ADK).
It implements the ADK router pattern using A2A as the external protocol boundary.
"""

from .router import AgentRouter

__all__ = ["AgentRouter"]

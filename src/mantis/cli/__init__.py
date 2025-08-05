#!/usr/bin/env python3
"""
CLI interface for Mantis agent generation.
"""

from .core import cli
from . import agent  # Import to register with CLI
from . import registry  # Import to register with CLI
from . import simulate  # Import to register with CLI

__all__ = ["cli", "agent", "registry", "simulate"]

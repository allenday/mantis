#!/usr/bin/env python3
"""
CLI interface for Mantis agent generation.
"""

from .core import cli
from . import agent  # Import to register with CLI

__all__ = ["cli"]

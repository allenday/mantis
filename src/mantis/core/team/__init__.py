"""
Team formation and coordination system.
"""

from .base import AbstractTeam, BaseTeam, TeamFactory
from .random import RandomTeam
from .homogeneous import HomogeneousTeam

__all__ = ["AbstractTeam", "BaseTeam", "TeamFactory", "RandomTeam", "HomogeneousTeam"]

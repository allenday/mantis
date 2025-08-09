"""
Team formation and coordination system.
"""

from .base import AbstractTeam, BaseTeam, TeamFactory
from .random import RandomTeam
from .homogeneous import HomogeneousTeam
from .tarot import TarotTeam

__all__ = [
    "AbstractTeam",
    "BaseTeam",
    "TeamFactory", 
    "RandomTeam",
    "HomogeneousTeam",
    "TarotTeam"
]
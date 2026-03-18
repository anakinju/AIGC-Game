"""
World State System - NPC Long-term Memory & Achievement Tracking.
This package handles the extraction of objective facts from dialogue and 
matches them against expected achievements or tasks.
"""

from npc.worldstate.worldstatedata import WorldState, Task, MatchResult
from npc.worldstate.generator import WorldStateGenerator
from npc.worldstate.matcher import EmbeddingService, TaskMatcher
from npc.worldstate.system import WorldStateSystem, WorldStatePool

__all__ = [
    'WorldState',
    'Task',
    'MatchResult',
    'WorldStateGenerator',
    'EmbeddingService',
    'TaskMatcher',
    'WorldStateSystem',
    'WorldStatePool'
]

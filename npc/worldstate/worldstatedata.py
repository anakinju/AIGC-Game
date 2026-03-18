"""
Data models for the World State system.
Contains dataclasses for WorldState, Task, and MatchResult.
"""

import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime

@dataclass
class WorldState:
    """
    Represents a concrete fact or change that has occurred in the game world.
    
    Attributes:
        id: Unique identifier for the state.
        text: Natural language description of the fact (e.g., "Player accepted the mission").
        turn: The turn number when this state was generated.
        embedding: Semantic vector representation for RAG matching.
        timestamp: ISO format string of when the state was created.
    """
    id: str
    text: str
    turn: int
    embedding: Optional[List[float]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the WorldState object to a dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldState':
        """Create a WorldState object from a dictionary."""
        return cls(**data)


@dataclass
class Task:
    """
    Represents a goal or expected world state change that the system is monitoring.
    
    Attributes:
        id: Unique identifier for the task.
        expected_text: The description of the state we are looking for.
        deadline_turn: The turn by which this task must be completed.
        status: Current status of the task (ONGOING, SUCCESS, FAIL).
        matched_state_id: The ID of the WorldState that satisfied this task.
        matched_score: The similarity score of the match.
        expected_embedding: Semantic vector of the expected_text.
        match_reason: AI-generated reasoning for the match (from AI Judge).
    """
    id: str
    expected_text: str
    deadline_turn: int
    status: str = "ONGOING"  # ONGOING | SUCCESS | FAIL
    matched_state_id: Optional[str] = None
    matched_score: Optional[float] = None
    expected_embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the Task object to a dictionary, including match_reason if present."""
        res = asdict(self)
        if hasattr(self, 'match_reason'):
            res['match_reason'] = self.match_reason
        return res
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create a Task object from a dictionary."""
        # Handle match_reason if it exists in the dict
        reason = data.pop('match_reason', None)
        task = cls(**data)
        if reason:
            task.match_reason = reason
        return task


@dataclass
class MatchResult:
    """
    Represents the result of a matching operation between a Task and a WorldState.
    
    Attributes:
        matched: Boolean indicating if a match was found.
        best_score: The highest similarity score found.
        matched_state_id: The ID of the state that matched.
        matched_text: The text of the state that matched.
        confidence: Confidence level of the match (low, medium, high).
        reason: AI-generated explanation for the match or rejection.
    """
    matched: bool
    best_score: float
    matched_state_id: Optional[str] = None
    matched_text: Optional[str] = None
    confidence: str = "low"
    reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the MatchResult object to a dictionary."""
        return asdict(self)

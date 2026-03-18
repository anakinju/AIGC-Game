"""
Matcher module for the World State system.
Handles semantic matching between extracted World States and expected Tasks using Embeddings and AI Judge.
"""

import numpy as np
from typing import List, Dict, Optional, Any, Callable
from npc.worldstate.worldstatedata import WorldState, Task, MatchResult, WorldState

class EmbeddingService:
    """
    Service to provide semantic vectorization and similarity calculation.
    """
    
    def __init__(self, embedding_function: Optional[Callable[[str], List[float]]] = None):
        """
        Initialize the Embedding Service.
        
        Args:
            embedding_function: Function that takes text and returns a list of floats.
        """
        self.embedding_function = embedding_function
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get the embedding vector for a given text."""
        if self.embedding_function is None:
            return None
        try:
            return self.embedding_function(text)
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return None
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate the cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0
        
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


class TaskMatcher:
    """
    Matches extracted World States against expected Tasks using a three-layer strategy:
    1. Fast Pass: Extremely high embedding similarity.
    2. AI Judge Zone: Moderate similarity requiring logical validation.
    3. Fast Fail: Low similarity.
    """
    
    # Threshold configurations
    EMBEDDING_HIGH_THRESHOLD = 0.95   # Direct success if text is nearly identical
    EMBEDDING_MIN_THRESHOLD = 0.4    # Minimum relevance required to trigger AI Judge
    
    def __init__(self, 
                 embedding_service: Optional[EmbeddingService] = None,
                 ai_judge_function: Optional[Callable[[str, str], Dict]] = None):
        """
        Initialize the Task Matcher.
        
        Args:
            embedding_service: Service for vector operations.
            ai_judge_function: AI function to logically judge if two descriptions match.
        """
        self.embedding_service = embedding_service
        self.ai_judge_function = ai_judge_function
    
    def match_task(self, states: List[WorldState], task: Task) -> MatchResult:
        """
        Match a single task against a list of world states.
        """
        if not states:
            return MatchResult(matched=False, best_score=0.0, confidence="high")
        
        # Ensure task has an embedding for vector matching
        if task.expected_embedding is None and self.embedding_service:
            task.expected_embedding = self.embedding_service.get_embedding(task.expected_text)
        
        # Strategy 1: Use Embedding for fast screening
        if task.expected_embedding and self.embedding_service:
            return self._match_with_embedding(states, task)
        
        # Strategy 2: Fallback to AI-only matching if no embeddings
        if self.ai_judge_function:
            return self._match_with_ai_only(states, task)
        
        # Strategy 3: Simple text matching as last resort
        return self._match_with_text(states, task)
    
    def _match_with_embedding(self, states: List[WorldState], task: Task) -> MatchResult:
        """
        Three-layer matching strategy using embeddings.
        """
        best_score = 0.0
        best_state = None
        
        # Find the state with the highest similarity
        for state in states:
            if state.embedding is None:
                continue
            
            score = self.embedding_service.cosine_similarity(
                task.expected_embedding,
                state.embedding
            )
            
            if score > best_score:
                best_score = score
                best_state = state
        
        # 1. Fast Pass: Extremely high similarity
        if best_score >= self.EMBEDDING_HIGH_THRESHOLD and best_state:
            return MatchResult(
                matched=True,
                best_score=best_score,
                matched_state_id=best_state.id,
                matched_text=best_state.text,
                confidence="high"
            )
        
        # 2. AI Judge Zone: Moderate relevance requiring logical check
        if best_score >= self.EMBEDDING_MIN_THRESHOLD and best_state and self.ai_judge_function:
            ai_result = self._ai_judge(task.expected_text, best_state.text)
            if ai_result.get("matched") is True:
                return MatchResult(
                    matched=True,
                    best_score=best_score,
                    matched_state_id=best_state.id,
                    matched_text=best_state.text,
                    confidence="medium",
                    reason=ai_result.get("reason")
                )
            else:
                reason = ai_result.get('reason')
                print(f"[WorldState] AI Judge rejected match: {task.expected_text} vs {best_state.text}. Reason: {reason}")
                return MatchResult(
                    matched=False,
                    best_score=best_score,
                    confidence="medium",
                    reason=reason
                )
        
        # 3. Fast Fail: Score too low
        return MatchResult(
            matched=False,
            best_score=best_score,
            confidence="high"
        )
    
    def _match_with_ai_only(self, states: List[WorldState], task: Task) -> MatchResult:
        """Match using only AI Judge (when embeddings are unavailable)."""
        for state in reversed(states):  # Match from newest to oldest
            ai_result = self._ai_judge(task.expected_text, state.text)
            if ai_result.get("matched"):
                return MatchResult(
                    matched=True,
                    best_score=ai_result.get("confidence", 0.9),
                    matched_state_id=state.id,
                    matched_text=state.text,
                    confidence="medium",
                    reason=ai_result.get("reason")
                )
        
        return MatchResult(matched=False, best_score=0.0, confidence="medium")
    
    def _match_with_text(self, states: List[WorldState], task: Task) -> MatchResult:
        """Simple substring matching (fallback)."""
        for state in states:
            if task.expected_text in state.text or state.text in task.expected_text:
                return MatchResult(
                    matched=True,
                    best_score=1.0,
                    matched_state_id=state.id,
                    matched_text=state.text,
                    confidence="low"
                )
        return MatchResult(matched=False, best_score=0.0, confidence="low")
    
    def _ai_judge(self, expected_text: str, state_text: str) -> Dict:
        """AI assisted judgment using Chain-of-Thought reasoning."""
        prompt = f"""You are a game task matching expert. Determine if these two descriptions express the same or similar game world facts.

Expected State: {expected_text}
Actual State: {state_text}

Let's think step by step to make an accurate judgment:

STEP 1: EXTRACT CORE COMPONENTS
Identify Subject, Action, Object, and Context for both descriptions.

STEP 2: COMPARE SEMANTIC MEANING
1. Do both describe the same subject performing an action?
2. Are the actions semantically equivalent?
3. Do they affect the same object or achieve the same outcome?

STEP 3: EVALUATE MATCH QUALITY
- "Player obtained document" vs "Player received document" → MATCH
- "Player agreed to proposal" vs "Player accepted suggestion" → MATCH
- "NPC assigned task" vs "Player accepted task" → NO MATCH (unless player explicitly said YES)

STEP 4: DETERMINE CONFIDENCE
- High (0.8-1.0), Medium (0.5-0.7), Low (0.0-0.4).

Return ONLY valid JSON format:
{{
  "matched": true/false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation of the reasoning"
}}
"""
        try:
            return self.ai_judge_function(prompt)
        except Exception as e:
            print(f"[WorldState] AI judgment failed: {e}")
            return {"matched": False, "confidence": 0.0, "reason": str(e)}

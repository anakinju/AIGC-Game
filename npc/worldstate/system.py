"""
System module for the World State system.
Orchestrates the entire flow: generation, pooling, and task matching.
"""

import json
import uuid
import os
from typing import List, Dict, Optional, Callable, Any
from datetime import datetime
from npc.scene_control.scene_data import SceneRegistry
from npc.worldstate.worldstatedata import WorldState, Task
from npc.worldstate.generator import WorldStateGenerator
from npc.worldstate.matcher import EmbeddingService, TaskMatcher

class WorldStatePool:
    """
    Manages a collection of World States with automatic deduplication.
    """
    
    def __init__(self):
        self.states: List[WorldState] = []
        self._text_set: set = set()  # For deduplication
    
    def append_states(self, turn: int, new_states: List[WorldState]) -> int:
        """
        Append new states to the pool.
        
        Returns:
            int: Number of unique states actually added.
        """
        added_count = 0
        for state in new_states:
            if state.text in self._text_set:
                continue
            self.states.append(state)
            self._text_set.add(state.text)
            added_count += 1
        return added_count
    
    def get_states_by_turn_range(self, start_turn: int, end_turn: Optional[int] = None) -> List[WorldState]:
        """Retrieve states within a specific turn range."""
        if end_turn is None:
            return [s for s in self.states if s.turn >= start_turn]
        return [s for s in self.states if start_turn <= s.turn <= end_turn]
    
    def clear(self):
        """Clear all states from the pool."""
        self.states.clear()
        self._text_set.clear()
    
    def to_dict(self) -> Dict:
        """Serialize the pool to a dictionary."""
        return {"states": [s.to_dict() for s in self.states]}
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorldStatePool':
        """Create a pool from a dictionary."""
        pool = cls()
        for state_data in data.get("states", []):
            state = WorldState.from_dict(state_data)
            pool.states.append(state)
            pool._text_set.add(state.text)
        return pool


class WorldStateSystem:
    """
    Main entry point for the World State system.
    Coordinates generation, storage (pool), and task matching.
    """
    
    def __init__(self,
                 ai_generate_function: Callable[[str], Dict],
                 embedding_function: Optional[Callable[[str], List[float]]] = None,
                 ai_judge_function: Optional[Callable[[str], Dict]] = None,
                 conversation_history_file: Optional[str] = None):
        """
        Initialize the system.
        """
        self.embedding_service = EmbeddingService(embedding_function) if embedding_function else None
        self.generator = WorldStateGenerator(ai_generate_function, self.embedding_service)
        self.matcher = TaskMatcher(self.embedding_service, ai_judge_function)
        self.pool = WorldStatePool()
        self.tasks: List[Task] = []
        
        # Conversation history storage
        self.conversation_history: List[Dict[str, Any]] = []
        self.conversation_history_file = conversation_history_file
        if self.conversation_history_file:
            self._load_conversation_history()
    
    def end_turn(self, turn: int, chat_log: str, npc_context: Dict = None, scene_context: Dict = None) -> Dict:
        """
        Process the end of a turn: generate states, update pool, and match tasks.
        
        Returns:
            Dict: Summary of the turn results.
        """
        if scene_context is None:
            current_scene = SceneRegistry.get_current_scene()
            if current_scene:
                scene_context = current_scene.raw_data

        # 0. Save history
        self._save_conversation_history(turn, chat_log)
        
        # 1. Generate states and summary
        gen_result = self.generator.generate_from_chat_log(chat_log, turn, npc_context, scene_context)
        new_states = gen_result.get("states", [])
        scene_summary = gen_result.get("scene_summary", "")
        
        # 2. Update pool
        added_count = self.pool.append_states(turn, new_states)
        
        # 3. Match tasks
        success_tasks = []
        failed_tasks = []
        
        for task in self.tasks:
            if task.status != "ONGOING":
                continue
            
            match_result = self.matcher.match_task(self.pool.states, task)
            
            if match_result.matched:
                task.status = "SUCCESS"
                task.matched_state_id = match_result.matched_state_id
                task.matched_score = match_result.best_score
                task.match_reason = match_result.reason
                success_tasks.append(task)
                print(f"[WorldState] Task SUCCESS: {task.expected_text} -> {match_result.matched_text}")
            elif turn > task.deadline_turn:
                task.status = "FAIL"
                failed_tasks.append(task)
                print(f"[WorldState] Task FAILED (deadline): {task.expected_text}")
        
        return {
            "turn": turn,
            "new_states_count": len(new_states),
            "added_states_count": added_count,
            "generated_states": [state.to_dict() for state in new_states],
            "scene_summary": scene_summary,
            "success_tasks": [t.to_dict() for t in success_tasks],
            "failed_tasks": [t.to_dict() for t in failed_tasks],
            "total_states": len(self.pool.states),
            "all_states": [state.to_dict() for state in self.pool.states]
        }
    
    def add_task(self, expected_text: str, deadline_turn: int) -> Task:
        """Add a new task to be monitored by the system."""
        task = Task(
            id=str(uuid.uuid4()),
            expected_text=expected_text,
            deadline_turn=deadline_turn
        )
        if self.embedding_service:
            task.expected_embedding = self.embedding_service.get_embedding(expected_text)
        self.tasks.append(task)
        return task

    def _save_conversation_history(self, turn: int, chat_log: str):
        """Internal method to save chat logs."""
        history_entry = {
            "turn": turn,
            "chat_log": chat_log,
            "timestamp": datetime.now().isoformat()
        }
        self.conversation_history.append(history_entry)
        if self.conversation_history_file:
            self._persist_conversation_history()

    def _persist_conversation_history(self):
        """Write chat logs to disk."""
        try:
            os.makedirs(os.path.dirname(self.conversation_history_file) or '.', exist_ok=True)
            with open(self.conversation_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WorldState] Failed to persist history: {e}")

    def _load_conversation_history(self):
        """Load chat logs from disk."""
        if os.path.exists(self.conversation_history_file):
            try:
                with open(self.conversation_history_file, 'r', encoding='utf-8') as f:
                    self.conversation_history = json.load(f)
            except Exception as e:
                print(f"[WorldState] Failed to load history: {e}")

    @staticmethod
    def extract_scene_context(scene_data: Dict = None) -> Dict:
        """
        Extract context information from scene data.
        
        Args:
            scene_data: Scene data dictionary.
            
        Returns:
            Dict: Extracted context information.
        """
        if scene_data is None:
            current_scene = SceneRegistry.get_current_scene()
            if current_scene:
                scene_data = current_scene.raw_data
            else:
                scene_data = {}

        return {
            "location": scene_data.get("location", ""),
            "current_topic": scene_data.get("current_topic", ""),
            "environment": scene_data.get("environment", ""),
            "interactive_environment_objects": scene_data.get("interactive_environment_objects", []),
            "time": scene_data.get("time", ""),
            "max_turns": scene_data.get("max_turns", 0),
            "scene_end_state_reference": scene_data.get("scene_end_state_reference", {}),
            "worldstate_tasks": scene_data.get("worldstate_tasks", [])
        }
    
    @staticmethod
    def extract_npc_context(scene_data: Dict = None, npc_name: str = "") -> Dict:
        """
        Extract context information for a specific NPC from scene data.
        
        Args:
            scene_data: Scene data dictionary.
            npc_name: Name of the NPC.
            
        Returns:
            Dict: NPC context information.
        """
        if scene_data is None:
            current_scene = SceneRegistry.get_current_scene()
            if current_scene:
                scene_data = current_scene.raw_data
            else:
                scene_data = {}

        interactive_npcs = scene_data.get("interactive_npc", [])
        
        # Handle interactive_npc as a list of dictionaries
        for npc in interactive_npcs:
            if isinstance(npc, dict) and npc.get("name") == npc_name:
                return {
                    "name": npc.get("name", ""),
                    "goal": npc.get("goal", ""),
                    "scene_goal": npc.get("goal", ""),
                    "knowledge": npc.get("npc_background", {}).get("knowledge", []),
                    "action_point_cost": npc.get("action_point_cost", 1)
                }
        
        # Handle interactive_npc as a list of strings, using npc_purposes
        if isinstance(interactive_npcs, list) and npc_name in interactive_npcs:
            npc_purposes = scene_data.get("npc_purposes", {})
            if npc_name in npc_purposes:
                npc_purpose = npc_purposes[npc_name]
                return {
                    "name": npc_name,
                    "goal": npc_purpose.get("goal", ""),
                    "scene_goal": npc_purpose.get("goal", ""),
                    "knowledge": npc_purpose.get("knowledge", []),
                    "action_point_cost": 1
                }
        
        return {}

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get a list of all active (ongoing) tasks."""
        return [task.to_dict() for task in self.tasks]

    def get_total_states_count(self) -> int:
        """Get the total number of world states in the pool."""
        return len(self.pool.states)

    def save_state(self, filepath: str):
        """Save the entire system state (pool, tasks, history) to a JSON file."""
        data = {
            "pool": self.pool.to_dict(),
            "tasks": [t.to_dict() for t in self.tasks],
            "conversation_history": self.conversation_history
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_state(self, filepath: str):
        """Load the entire system state from a JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.pool = WorldStatePool.from_dict(data["pool"])
        self.tasks = [Task.from_dict(t) for t in data["tasks"]]
        self.conversation_history = data.get("conversation_history", [])

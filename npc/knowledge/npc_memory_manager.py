import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class NPCMemoryManager:
    """
    Manages NPC-specific emotional logs and synthesized knowledge.
    Logs: npc/knowledge/npc_memories/{scene_id}_{timestamp}_{npc_name}.jsonl
    Knowledge: npc/knowledge/npc_knowledge/{npc_name}.json
    """
    
    def __init__(self, base_path: str = "npc/knowledge"):
        self.base_path = base_path
        self.memories_path = os.path.join(base_path, "npc_memories")
        self.knowledge_path = os.path.join(base_path, "npc_knowledge")
        self._knowledge_enabled = True
        
        for path in [self.memories_path, self.knowledge_path]:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                
    def set_knowledge_enabled(self, enabled: bool):
        """Enable or disable the knowledge system."""
        self._knowledge_enabled = enabled
        
    def is_enabled(self) -> bool:
        """Check if the knowledge system is enabled."""
        return self._knowledge_enabled

    def _get_log_file_path(self, scene_id: str) -> str:
        """Get the single log file for a specific scene."""
        safe_scene = "".join([c for c in scene_id if c.isalnum() or c in ('_', '-')]).strip()
        return os.path.join(self.memories_path, f"{safe_scene}.jsonl")

    def append_emotion_analysis(self, npc_name: str, analysis_result: Dict[str, Any], turn: int, scene_id: str, timestamp: str = None):
        """Append an NPC's emotion analysis to the scene's shared log file."""
        if not self._knowledge_enabled: return
        file_path = self._get_log_file_path(scene_id)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "scene_id": scene_id,
            "npc_name": npc_name,
            "turn": turn,
            "emotion": analysis_result.get("emotion"),
            "intensity": analysis_result.get("intensity"),
            "thought_process": analysis_result.get("thought_process") or analysis_result.get("psychological_activity"),
            "source": "ai_analyzer"
        }
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def log_system_event(self, npc_name: str, emotion: str, intensity: float, internal_thought: str, turn: int, scene_id: str, timestamp: str = None):
        """Append a system event for an NPC to the scene's shared log file."""
        if not self._knowledge_enabled: return
        file_path = self._get_log_file_path(scene_id)
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "scene_id": scene_id,
            "npc_name": npc_name,
            "turn": turn,
            "emotion": emotion,
            "intensity": intensity,
            "thought_process": internal_thought,
            "source": "system_rule"
        }
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def get_recent_logs(self, npc_name: str, scene_id: str, timestamp: str = None) -> List[Dict[str, Any]]:
        """Retrieve logs for a specific NPC from the scene's shared log file."""
        file_path = self._get_log_file_path(scene_id)
        if not os.path.exists(file_path): return []
        logs = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("npc_name") == npc_name:
                        logs.append(entry)
        return logs

    def _get_knowledge_file_path(self, npc_name: str) -> str:
        """Get the knowledge file path for a specific NPC."""
        safe_name = "".join([c for c in npc_name if c.isalnum() or c in ('_', '-')]).strip()
        return os.path.join(self.knowledge_path, f"{safe_name}.json")

    def save_synthesized_knowledge(self, npc_name: str, scene_id: str, summary: str):
        """Save or update synthesized knowledge for an NPC."""
        if not self._knowledge_enabled:
            return
            
        file_path = self._get_knowledge_file_path(npc_name)
        
        # Load existing knowledge
        knowledge = {}
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                knowledge = json.load(f)
                
        # Update with new scene knowledge
        knowledge[scene_id] = {
            "summary": summary,
            "timestamp": datetime.now().isoformat(),
            "scene_id": scene_id
        }
        
        # Save back to file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(knowledge, f, ensure_ascii=False, indent=2)


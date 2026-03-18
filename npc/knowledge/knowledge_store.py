from __future__ import annotations

import json
import os
from typing import Dict, List, Optional


MessageRecord = Dict[str, object]


class NpcKnowledgeStore:
    """
    In-memory NPC knowledge store.

    - knowledge_messages: past scenes only (chronological)
    - current_scene_messages: current scene only (chronological)
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.knowledge_messages: List[MessageRecord] = []
        self.current_scene_messages: List[MessageRecord] = []
        
        # Base directory for all knowledge files
        if base_dir:
            self.base_dir = base_dir
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.summary_dir = os.path.join(self.base_dir, "summaries")
        self.npc_mem_dir = os.path.join(self.base_dir, "npc_memories")
        
        # Ensure directories exist
        for d in [self.summary_dir, self.npc_mem_dir]:
            os.makedirs(d, exist_ok=True)

    def save_scene_summary(self, scene_id: str, summary: str) -> str:
        """Save summary of a scene."""
        file_path = os.path.join(self.summary_dir, f"scene_{scene_id}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(summary)
        return file_path

    def append_raw_memory(self, npc_name: str, scene_id: str, messages: List[MessageRecord]) -> str:
        """
        Append raw conversation logs to NPC's personal memory file.
        Only messages where the NPC was a speaker or listener are included.
        """
        file_path = os.path.join(self.npc_mem_dir, f"{npc_name}_raw.txt")
        
        relevant_msgs = [
            m for m in messages 
            if m.get("speaker") == npc_name or npc_name in (m.get("listeners") or [])
        ]
        
        if not relevant_msgs:
            return file_path

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n=== Scene: {scene_id} ===\n")
            for m in relevant_msgs:
                f.write(f"{m['speaker']}: {m['content']}\n")
        
        return file_path

    def save_npc_emotion_snapshot(self, npc_name: str, scene_id: str, emotion_data: Dict[str, Any]) -> str:
        """
        Save a snapshot of NPC's emotions at the end of a scene.
        """
        from datetime import datetime
        file_path = os.path.join(self.npc_mem_dir, f"{npc_name}_emotions.jsonl")
        snapshot = {
            "scene_id": scene_id,
            "timestamp": datetime.now().isoformat(),
            "emotion": emotion_data
        }
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
        return file_path

    def save_to_file(self, scene_name: Optional[str] = None, path: Optional[str] = None) -> str:
        """
        Save knowledge and current scene messages to a JSON file.
        If scene_name is provided, saves to a file named after the scene in conv_dir.
        Returns the path that was written.
        """

        if path:
            target_path = path
        elif scene_name:
            # Clean scene name for filename
            safe_name = "".join([c if c.isalnum() or c in " _-" else "_" for c in scene_name])
            target_path = os.path.join(self.conv_dir, f"knowledge_{safe_name}.json")
        else:
            target_path = self.default_store_path

        target_dir = os.path.dirname(os.path.abspath(target_path))
        if target_dir and not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        payload = {
            "scene_name": scene_name,
            "knowledge_messages": self.knowledge_messages,
            "current_scene_messages": self.current_scene_messages,
        }
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return target_path

    def load_from_file(self, path: Optional[str] = None) -> bool:
        """
        Load knowledge from a JSON file.
        After loading, current_scene_messages will be archived into knowledge_messages.
        Returns True if loaded, False if file not found.
        """

        target_path = path or self.default_store_path
        if not os.path.exists(target_path):
            return False

        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        knowledge = data.get("knowledge_messages", [])
        current_scene = data.get("current_scene_messages", [])
        self.knowledge_messages = self._normalize_records(knowledge)
        self.current_scene_messages = self._normalize_records(current_scene)

        if self.current_scene_messages:
            self.knowledge_messages.extend(
                [record.copy() for record in self.current_scene_messages]
            )
            self.current_scene_messages.clear()

        return True

    def _normalize_records(self, records: object) -> List[MessageRecord]:
        if not isinstance(records, list):
            return []
        normalized: List[MessageRecord] = []
        for item in records:
            if not isinstance(item, dict):
                continue
            speaker = item.get("speaker")
            listeners = item.get("listeners")
            content = item.get("content")
            if not speaker or content is None:
                continue
            if not isinstance(listeners, list):
                listeners = []
            normalized.append(
                {
                    "speaker": speaker,
                    "listeners": list(listeners),
                    "content": content,
                }
            )
        return normalized

    def add_message(
        self,
        speaker: str,
        listeners: List[str],
        content: str,
        *,
        to_current_scene: bool = True,
    ) -> MessageRecord:
        """
        Add a message record to current scene or past-scene knowledge.
        Caller decides when to write and where to write.
        """

        record: MessageRecord = {
            "speaker": speaker,
            "listeners": list(listeners),
            "content": content,
        }

        if to_current_scene:
            self.current_scene_messages.append(record)
        else:
            self.knowledge_messages.append(record)

        return record

    def get_npc_knowledge(self, npc_name: str) -> List[MessageRecord]:
        """
        Return past-scene messages that the NPC said or heard.
        """

        return [
            record.copy()
            for record in self.knowledge_messages
            if record.get("speaker") == npc_name
            or npc_name in (record.get("listeners") or [])
        ]

    def get_npc_heard(self, npc_name: str) -> List[MessageRecord]:
        """
        Return past-scene messages that the NPC heard (as listener).
        """

        return [
            record.copy()
            for record in self.knowledge_messages
            if npc_name in (record.get("listeners") or [])
        ]

    def get_npc_said(self, npc_name: str) -> List[MessageRecord]:
        """
        Return past-scene messages that the NPC said (as speaker).
        """

        return [
            record.copy()
            for record in self.knowledge_messages
            if record.get("speaker") == npc_name
        ]

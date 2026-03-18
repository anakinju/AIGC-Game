import os
from typing import List, Dict, Optional
from npc.knowledge.knowledge_store import NpcKnowledgeStore

class NpcMemoryHelper:
    """
    Helper class to retrieve NPC memories based on the MEMORY_SKILL.md guidelines.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.store = NpcKnowledgeStore(base_dir=base_dir)
        self.base_dir = self.store.base_dir
        self.skill_path = os.path.join(self.base_dir, "MEMORY_SKILL.md")

    def get_skill_guidelines(self) -> str:
        """Read the MEMORY_SKILL.md file to provide context for the AI."""
        if os.path.exists(self.skill_path):
            with open(self.skill_path, "r", encoding="utf-8") as f:
                return f.read()
        return "No MEMORY_SKILL.md found."

    def get_npc_full_context(self, npc_name: str) -> Dict[str, Any]:
        """
        Retrieve all relevant memory components for an NPC:
        1. Personal rolling memory (specific to this NPC)
        2. Last recorded emotion snapshot
        3. Scene summaries where this NPC was present
        """
        # 1. Get personal memory
        personal_mem_path = os.path.join(self.store.npc_mem_dir, f"{npc_name}.txt")
        personal_memory = ""
        if os.path.exists(personal_mem_path):
            with open(personal_mem_path, "r", encoding="utf-8") as f:
                personal_memory = f.read()

        # 2. Get last emotion snapshot
        emotion_path = os.path.join(self.store.npc_mem_dir, f"{npc_name}_emotions.jsonl")
        last_emotion = None
        if os.path.exists(emotion_path):
            with open(emotion_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    import json
                    last_emotion = json.loads(lines[-1]).get("emotion")

        # 3. Get scene summaries where NPC was present
        relevant_summaries = []
        if os.path.exists(self.store.summary_dir):
            files = sorted(os.listdir(self.store.summary_dir))
            for file in files:
                if file.endswith(".txt"):
                    path = os.path.join(self.store.summary_dir, file)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Check if NPC name is in the "NPCs Present:" list in the summary
                        if f"NPCs Present:" in content and npc_name in content:
                            relevant_summaries.append(f"--- {file} ---\n{content}")

        return {
            "npc_name": npc_name,
            "personal_memory": personal_memory or "No personal memory found.",
            "last_emotion": last_emotion,
            "scene_summaries": "\n\n".join(relevant_summaries) or "No relevant scene summaries found.",
            "guidelines": self.get_skill_guidelines()
        }

    def format_for_llm(self, npc_name: str) -> str:
        """Format the memory into a single string suitable for an LLM prompt."""
        context = self.get_npc_full_context(npc_name)
        
        emotion_text = f"Current Emotion State: {context['last_emotion']}" if context['last_emotion'] else "No previous emotion state recorded."

        prompt = f"""
### NPC Memory Context for: {npc_name}

#### Retrieval Guidelines (from MEMORY_SKILL.md):
{context['guidelines']}

#### Personal Rolling Memory:
{context['personal_memory']}

#### {emotion_text}

#### Past Scene Summaries:
{context['scene_summaries']}
"""
        return prompt

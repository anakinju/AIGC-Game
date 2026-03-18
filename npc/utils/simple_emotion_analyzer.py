from typing import Dict, Any, List, Optional
import json
from langchain_core.messages import HumanMessage, SystemMessage
from npc.utils.llm_factory import LLMFactory
from npc.utils.constants import LLMUsage
from npc.utils.emotion_analyzer import EMOTION_MODIFIERS

class SimpleEmotionAnalyzer:
    """
    Lightweight Emotion Analyzer for background NPCs.
    Optimized for speed by removing Chain-of-Thought and reducing context.
    """
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        self.llm = LLMFactory.create_chat_model(usage=LLMUsage.EMOTION, model_name=llm_model)
        self.available_emotions = list(EMOTION_MODIFIERS.keys())

    async def analyze_interaction_async(self, source_npc: str, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Fast analysis of NPC emotion for background reactions.
        """
        if not state:
            return {"emotion": "Calm", "intensity": 0.5, "psychological_activity": "No state provided."}

        # Load NPC static and dynamic information
        try:
            from npc.utils.npc_info_adapter import create_npc_loader
            from npc.scene_control.scene_data import SceneRegistry
            
            npc_info_loader = create_npc_loader(source_npc)
            npc_info = npc_info_loader.get_npc_info()
            
            static_info = npc_info.get("static_info", npc_info)
            personality = static_info.get("personality_and_speech", {}).get("traits", [])
            behavioral_logic = static_info.get("behavioral_logic", {})
            motivation = static_info.get("motivation_and_drive", {})
            hidden_desire = motivation.get("hidden_desire", "None")
            
            # Social hierarchy info
            core_identity = static_info.get("core_identity", {})
            npc_role = core_identity.get("role", "Unknown")
            npc_status = core_identity.get("status", "Unknown")
            hierarchy_info = f"Role: {npc_role}, Status: {npc_status} (relative to Player)"

            # Scene context and relationship data
            current_scene = SceneRegistry.get_current_scene()
            scene_data = current_scene.raw_data if current_scene else state.get("scene_context", {})
            
            scene_relationships = scene_data.get("npc_relationships", [])
            relationship_detail = "Neutral baseline."
            
            # Find relationship with player and other NPCs in the scene
            player_relationship = "Neutral"
            other_npc_relationships = []
            
            for rel in scene_relationships:
                c1 = rel.get("character1", "").lower()
                c2 = rel.get("character2", "").lower()
                s_npc = source_npc.lower()
                
                if (c1 == s_npc and c2 == "player") or (c2 == s_npc and c1 == "player"):
                    player_relationship = (
                        f"Category: {rel.get('category', 'Neutral')}, "
                        f"Initial Emotion: {rel.get('emotion_modifier', 'Calm')}, "
                        f"Intensity: {rel.get('intensity', 0.5)}, "
                        f"Recent Context: {rel.get('recent_interaction', 'None')}"
                    )
                elif c1 == s_npc or c2 == s_npc:
                    other_name = c2 if c1 == s_npc else c1
                    other_npc_relationships.append(
                        f"Relationship with {other_name}: {rel.get('category', 'Neutral')} ({rel.get('emotion_modifier', 'Calm')})"
                    )

            # NPC's current scene goal
            interactive_npcs = scene_data.get("interactive_npc", [])
            scene_goal = "Maintain interaction."
            for npc_item in interactive_npcs:
                if isinstance(npc_item, dict) and npc_item.get("name") == source_npc:
                    scene_goal = npc_item.get("goal", scene_goal)
                    break
            
        except Exception:
            personality = ["Professional"]
            behavioral_logic = {}
            hidden_desire = "None"
            scene_goal = "Continue conversation."
            hierarchy_info = "Unknown"
            player_relationship = "Neutral"
            other_npc_relationships = []

        # Extract minimal message history (last 5 messages instead of 15)
        message_store = state.get("message_store", []) or state.get("chat_history", []) or []
        recent_msgs = []
        last_speaker = "Unknown"
        for msg in message_store[-5:]:
            speaker = msg.get("speaker", "Unknown")
            content = msg.get("content", "")
            if isinstance(content, dict):
                content = content.get("utterance", str(content))
            recent_msgs.append(f"{speaker}: {content}")
            last_speaker = speaker
        conversation_text = "\n".join(recent_msgs)

        # Get current emotion for continuity
        npc_states = state.get("npc_states", {})
        current_emotion = "Calm"
        if source_npc in npc_states:
            current_emotion = npc_states[source_npc]["dynamic_state"].get("emotion", "Calm")

        # Improved Prompt: No CoT, direct JSON output, rich context
        prompt = f"""### EMOTION ANALYSIS TASK
Analyze {source_npc}'s emotional reaction to the latest dialogue.

### NPC PROFILE
**Name**: {source_npc}
**Personality**: {personality}
**Behavioral Logic**: {behavioral_logic}
**Hidden Desire**: {hidden_desire}

### SOCIAL CONTEXT
**Hierarchy Status**: {hierarchy_info}
**Relationship with Player**: {player_relationship}
**Other Relationships**: {", ".join(other_npc_relationships) if other_npc_relationships else "None"}

### SCENE OBJECTIVES
**Your Goal**: {scene_goal}

### CONVERSATION CONTEXT
Current Emotion: {current_emotion}
Available Emotions: {self.available_emotions}

Recent Dialogue:
{conversation_text}

### OUTPUT FORMAT
Return ONLY a JSON object:
{{
    "psychological_activity": "Short internal monologue reflecting the NPC's reaction",
    "emotion": "Chosen Emotion from the list",
    "intensity": 0.0-1.0,
    "guidance": "Direct instruction for the next dialogue"
}}"""

        messages = [
            SystemMessage(content=f"You are an observer of the conversation. The dialogue is currently taking place between the Player and the NPC named {source_npc}. Your task is to analyze {source_npc}'s emotional state based on their profile and relationships."),
            HumanMessage(content=prompt)
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            return json.loads(content)
        except Exception:
            return {
                "emotion": current_emotion, 
                "intensity": 0.5, 
                "psychological_activity": "Continuing as usual.",
                "guidance": "No change."
            }

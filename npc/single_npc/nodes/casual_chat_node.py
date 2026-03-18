import logging
from typing import Dict, List, Any
from npc.single_npc.nodes.base_npc_node import BaseNPCNode
from npc.scene_control.scene_data import SceneRegistry

logger = logging.getLogger(__name__)

class CasualChatNode(BaseNPCNode):
    """
    Specialized NPC node for handling Casual Chat mode.
    """
    
    def _build_casual_chat_prompt(self, state: Dict[str, Any], conversation_history: List[Dict]) -> str:
        """Build casual chat prompt - Optimized: Includes identity, emotional context and emphasizes returning to the main topic."""
        # 1. Get base casual chat information
        casual_info = self.npc_info.get_info_for_casual_chat()
        identity = casual_info.get("identity", {})
        nickname = identity.get("nickname", self.name)
        role = identity.get("role", "Unknown")
        status = identity.get("status", "Neutral")
        
        # 2. Get Scene Goal
        current_scene = SceneRegistry.get_current_scene()
        scene_context = current_scene.raw_data if current_scene else state.get("scene_context", {})
        scene_goals, _ = self._get_scene_goal_and_knowledge_from_interactive_npc(scene_context)
        
        # 3. Get emotional analysis and psychological state (Reference: PlayerInvolvedNode)
        npc_state = state.get("npc_state", {})
        current_emotion = npc_state.get("current_emotion", "Calm")
        emotion_analysis = state.get(f"emotion_analysis_{self.name}", {})
        emotion_guidance = emotion_analysis.get("guidance") or state.get(f"emotion_guidance_{self.name}") or npc_state.get("emotion_guidance", "Keep a natural tone.")
        
        # 4. Check for angry state (cooling down phase)
        angry_level = int(npc_state.get("angry_level", 0))
        is_cooling_down = npc_state.get("angry", False) and 1 <= angry_level <= 2
        
        # 5. Build Prompt with angry state consideration
        if is_cooling_down:
            angry_guidance = self._build_cooling_down_guidance(angry_level)
            situation_text = f"**ANGRY COOLING DOWN STATE** (Level {angry_level}): {angry_guidance}"
        else:
            situation_text = f"**SITUATION**: The player is currently making small talk or asking for information. Your response MUST be dictated by your **Status** and **Relationship** with the player:\n- **If you are a SUPERIOR**: You have NO obligation to answer trivial questions. You may choose to completely ignore their inquiry and directly state your objective or demand they focus on the task at hand.\n- **If you are an INFORMATION PROVIDER**: If the player's tone is disrespectful or too casual, you should be FIRM. Demand they speak properly and respect your position, or you will refuse to share anything.\n- **General Rule**: Your priority is your goal. Do not let the player's idle curiosity waste your time."
        
        prompt_parts = [
            f"# CASUAL CHAT: {self.name} (aka {nickname})",
            f"## YOUR IDENTITY & RELATIONSHIP\n- **Role**: {role}\n- **Status**: {status} (relative to the Player)\n- **Current Emotion**: {current_emotion}\n- **Behavioral Guidance**: {emotion_guidance}",
            f"## YOUR SCENE GOAL (CONTEXT)\n- **Goal**: {scene_goals if scene_goals else 'None specified'}\n\n{situation_text}",
            "## CONVERSATIONAL GUIDELINES:\n1. **Status-Driven Response**: A high-status NPC should maintain absolute dominance. If the player is being too casual, respond it strictly and shut it down. \n 2. **Conditional Cooperation**: If you are providing information, it is a privilege, not a right. Make the player earn it through proper conduct.\n3. **Natural Pivot/Direct Rejection**: Either bridge the answer back to your goal OR directly reject the off-topic chatter to re-establish the main topic.\n4. **Flow**: Keep it to 1-2 sentences. It should feel like a powerful, character-driven interaction.",
            f"## RECENT CONVERSATION:\n" + "\n".join([f"{m.get('speaker', 'unknown')}: {self._extract_utterance_from_message(m)}" for m in conversation_history[-3:]]),
            f"## RESPOND TO PLAYER'S OFF-TOPIC MESSAGE:\n\"{state.get('original_message')}\""
        ]
        
        return "\n\n".join(prompt_parts)

    def _build_cooling_down_guidance(self, angry_level: int) -> str:
        """Build guidance for angry cooling down state"""
        if angry_level == 2:
            return (
                "You are still annoyed with the player but not completely furious anymore. "
                "You've noticed their recent apology but you're still wary. "
                "**Be cautious and somewhat cold** - acknowledge their attempt to make amends but don't fully trust them yet. "
                "You may provide information reluctantly if it serves your goal, but make it clear they're on thin ice. "
                "**Hint that you want them to get back on topic** and prove they're serious about the conversation."
            )
        elif angry_level == 1:
            return (
                "You are in the final stages of calming down. The player seems to have learned their lesson. "
                "**Be cautious but more willing to cooperate** - you're giving them another chance but watching their behavior closely. "
                "You can engage more normally but should still **encourage them to focus on important matters** rather than idle chatter. "
                "If they stay on topic, you'll fully forgive and return to normal interaction."
            )
        else:
            return "Keep your normal personality."

    def _get_scene_goal_and_knowledge_from_interactive_npc(self, scene_context: Dict[str, Any]) -> tuple:
        """Get current NPC's goal and knowledge from scene context (Replicated from PlayerInvolvedNode)"""
        current = SceneRegistry.get_current_scene()
        interactive_npc = current.interactive_npc if current else scene_context.get("interactive_npc", [])
        for item in interactive_npc:
            if (isinstance(item, dict) and item.get("name") == self.name) or item == self.name:
                if isinstance(item, dict):
                    return item.get("goal", ""), item.get("npc_background", {}).get("knowledge", [])
        return "", []

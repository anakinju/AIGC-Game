from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
from npc.utils.emotion_analyzer import EmotionAnalyzer
from npc.utils.simple_emotion_analyzer import SimpleEmotionAnalyzer
from npc.knowledge.npc_memory_manager import NPCMemoryManager

class EmotionManager:
    """
    Emotion Manager - Handles the lifecycle of NPC emotional states.
    This class manages the interaction between the EmotionAnalyzer and the game state.
    """
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        self.analyzer = EmotionAnalyzer(llm_model)
        self.simple_analyzer = SimpleEmotionAnalyzer(llm_model)
        self.memory_manager = NPCMemoryManager()

    async def update_emotion_async(self, source_npc: str, state: Dict[str, Any], is_background: bool = False) -> Dict[str, Any]:
        """
        Analyze and update the NPC's emotional state in the global state object.
        
        Args:
            source_npc: Name of the NPC to update.
            state: Global game state.
            is_background: If True, use the lightweight SimpleEmotionAnalyzer.
            
        Returns:
            The analysis result from the analyzer.
        """
        if is_background:
            analysis_result = await self.simple_analyzer.analyze_interaction_async(source_npc, state)
        else:
            analysis_result = await self.analyzer.analyze_interaction_async(source_npc, state)
        
        new_emotion = analysis_result.get("emotion", "Calm")
        new_intensity = analysis_result.get("intensity", 0.5)
        guidance = analysis_result.get("guidance", "")
        thought_process = analysis_result.get("thought_process", {})
        
        # Store full psychological profile in state
        state[f"emotion_analysis_{source_npc}"] = {
            "thought": thought_process,
            "guidance": guidance,
            "emotion": new_emotion,
            "intensity": new_intensity
        }
        
        # Log to NPCMemoryManager
        current_turn = state.get("current_turn", 0)
        scene_id = state.get("scene_id", "unknown_scene")
        timestamp = state.get("scene_timestamp", "")
        self.memory_manager.append_emotion_analysis(source_npc, analysis_result, current_turn, scene_id, timestamp)
        
        # Maintain backward compatibility for keys used by other modules
        state[f"emotion_guidance_{source_npc}"] = guidance
        state[f"emotion_reasoning_{source_npc}"] = thought_process.get("internal_reaction", "")
        
        # Update NPC dynamic state if available
        npc_states = state.get("npc_states", {})
        if source_npc in npc_states:
            npc_states[source_npc]["dynamic_state"]["emotion"] = new_emotion
            npc_states[source_npc]["dynamic_state"]["emotion_intensity"] = new_intensity
            npc_states[source_npc]["last_updated"] = datetime.now().isoformat()
        
        # Update legacy npc_state structure if present
        if "npc_state" in state:
            state["npc_state"]["current_emotion"] = new_emotion
            state["npc_state"]["emotion_guidance"] = guidance
            
        print(f"[EmotionManager] Updated emotional profile and memory for {source_npc}: {new_emotion}")
        return analysis_result

    def update_emotion(self, source_npc: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous entry point for updating NPC emotion."""
        try:
            try:
                loop = asyncio.get_running_loop()
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.run(self.update_emotion_async(source_npc, state))
            except RuntimeError:
                return asyncio.run(self.update_emotion_async(source_npc, state))
        except Exception as e:
            print(f"[EmotionManager] Sync update error: {e}")
            return {
                "emotion": "Calm", 
                "intensity": 0.5, 
                "thought_process": {"internal_reaction": f"Error: {str(e)}"},
                "guidance": "Continue naturally."
            }

import os
import sys
from langchain.tools import BaseTool
from typing import Dict, Any, List, Optional
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from npc.multi_npc.managers.emotion_manager import EmotionManager

class EmotionManagerTool(BaseTool):
    """
    Tool for managing NPC emotions based on player interactions.
    """
    name: str = "emotion_manager"
    description: str = "Analyzes and updates NPC emotional state based on player input"
    emotion_manager: Optional[EmotionManager] = None
    
    def __init__(self, emotion_manager: Optional[EmotionManager] = None):
        """Initialize the tool with an emotion manager"""
        super().__init__()
        self.emotion_manager = emotion_manager
    
    def _run(self, source_npc: str, game_state: Dict[str, Any]) -> Dict:
        """
        Update emotion for a source NPC based on the current game state
        """
        if self.emotion_manager is None:
            self.emotion_manager = EmotionManager()
            
        analysis_result = self.emotion_manager.update_emotion(source_npc, game_state)
        
        return {
            "status": "success",
            "source_npc": source_npc,
            "emotion": analysis_result.get("emotion"),
            "intensity": analysis_result.get("intensity"),
            "reasoning": analysis_result.get("reasoning")
        }
    
    async def _arun(self, source_npc: str, game_state: Dict[str, Any], is_background: bool = False) -> Dict[str, Any]:
        """Async version of _run"""
        if self.emotion_manager is None:
            self.emotion_manager = EmotionManager()
            
        analysis_result = await self.emotion_manager.update_emotion_async(source_npc, game_state, is_background=is_background)
        
        return {
            "status": "success",
            "source_npc": source_npc,
            "emotion": analysis_result.get("emotion"),
            "intensity": analysis_result.get("intensity"),
            "reasoning": analysis_result.get("reasoning")
        }

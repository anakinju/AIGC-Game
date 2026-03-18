import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from npc.knowledge.npc_memory_manager import NPCMemoryManager

logger = logging.getLogger(__name__)

class PlayerStateManager:
    """
    专门处理玩家相关的 NPC 状态管理，包括愤怒等级、关系变化和记忆记录。
    """
    
    def __init__(self, memory_manager: Optional[NPCMemoryManager] = None):
        self.memory_manager = memory_manager or NPCMemoryManager()

    def update_angry_state(self, state: Dict[str, Any], validation_result: Dict[str, Any], 
                          selected_npcs: List[str], current_turn: int) -> Dict[str, Any]:
        """
        更新 NPC 的愤怒状态和关系。
        """
        updated_state = state.copy()
        message = state.get("message", "")
        scene_id = state.get("scene_id", "unknown_scene")
        timestamp = state.get("scene_timestamp") or datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 初始化 npc_state
        if "npc_state" not in updated_state:
            updated_state["npc_state"] = {"npc_relationships": [], "npc_goals": {}, "angry": False, "angry_level": 0}
        elif "angry_level" not in updated_state["npc_state"]:
            updated_state["npc_state"]["angry_level"] = 0
            
        npc_state = updated_state["npc_state"]
        is_apologizing = validation_result.get("is_apology", False)
        is_story_relevant = validation_result.get("category") == "STORY_RELEVANT"
        
        # 1. 处理强制发火 (Repeated Irrelevance)
        if validation_result.get("force_exit", False):
            return self._trigger_force_angry(updated_state, selected_npcs, current_turn, scene_id, timestamp)
            
        # 2. 处理现有愤怒状态的冷却或加重
        if npc_state.get("angry", False):
            return self._handle_angry_cooldown(updated_state, is_apologizing, is_story_relevant, 
                                             selected_npcs, current_turn, scene_id, timestamp)
        
        # 3. 平静状态下的反馈
        if not is_story_relevant and not is_apologizing:
            logger.debug("[PlayerStateManager] NPC 平静，玩家输入无关但未触发愤怒")
            
        return updated_state

    def _trigger_force_angry(self, state: Dict[str, Any], selected_npcs: List[str], 
                            current_turn: int, scene_id: str, timestamp: str) -> Dict[str, Any]:
        """触发强制发火逻辑"""
        state["npc_state"]["angry"] = True
        state["npc_state"]["angry_level"] = 3
        
        for npc in selected_npcs:
            self.memory_manager.log_system_event(
                npc_name=npc,
                emotion="Angry",
                intensity=0.9,
                internal_thought="Player is repeatedly off-topic. I've lost my patience.",
                turn=current_turn,
                scene_id=scene_id,
                timestamp=timestamp
            )
            
        self._update_relationships(state, category="Wary", emotion="Angry", intensity=0.8, 
                                  interaction="Repeatedly annoyed by player's nonsense.")
        logger.info("[PlayerStateManager] 触发强制发火：angry_level=3")
        return state

    def _handle_angry_cooldown(self, state: Dict[str, Any], is_apologizing: bool, 
                              is_story_relevant: bool, selected_npcs: List[str], 
                              current_turn: int, scene_id: str, timestamp: str) -> Dict[str, Any]:
        """处理愤怒冷却逻辑"""
        current_level = int(state["npc_state"]["angry_level"])
        
        if is_apologizing:
            for npc in selected_npcs:
                self.memory_manager.log_system_event(
                    npc_name=npc, emotion="Calm", intensity=0.5,
                    internal_thought="The player apologized. I'm willing to listen, but I'll remain cautious.",
                    turn=current_turn, scene_id=scene_id, timestamp=timestamp
                )
            
            reduction = 2 if is_story_relevant else 1
            new_level = max(0, current_level - reduction)
            state["npc_state"]["angry_level"] = new_level
            
            if new_level <= 0:
                state["npc_state"]["angry"] = False
                self._update_relationships(state, category="Cooperative", emotion="Calm", intensity=0.5,
                                         interaction="Player apologized; relationship repaired.")
                logger.info(f"[PlayerStateManager] 玩家道歉，NPC 完全消气")
            else:
                logger.info(f"[PlayerStateManager] 玩家道歉，消气中: {current_level} -> {new_level}")
                
        elif is_story_relevant:
            new_level = max(0, current_level - 1) if current_level > 1 else current_level
            state["npc_state"]["angry_level"] = new_level
            logger.info(f"[PlayerStateManager] 回归正题未道歉，轻微消气: {current_level} -> {new_level}")
        else:
            if current_level < 3:
                state["npc_state"]["angry_level"] = min(3, current_level + 1)
                logger.info(f"[PlayerStateManager] 继续无关话题，加重愤怒: {current_level} -> {state['npc_state']['angry_level']}")
                
        return state

    def _update_relationships(self, state: Dict[str, Any], category: str, emotion: str, 
                             intensity: float, interaction: str):
        """统一更新关系列表"""
        if "npc_relationships" in state["npc_state"]:
            for rel in state["npc_state"]["npc_relationships"]:
                if rel.get("character2", "").lower() == "player":
                    rel["category"] = category
                    rel["emotion_modifier"] = emotion
                    rel["intensity"] = intensity
                    rel["recent_interaction"] = interaction

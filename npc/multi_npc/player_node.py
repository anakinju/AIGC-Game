import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加项目路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.playervalidator import InputValidator
from npc.multi_npc.player_state_manager import PlayerStateManager

logger = logging.getLogger(__name__)

class PlayerNode:
    """
    Player节点类，用于处理玩家输入并进行验证。
    支持LangGraph工作流。
    """
    
    def __init__(self, scene_data: Optional[Dict[str, Any]] = None):
        self.validator = InputValidator()
        self.scene_data = scene_data
        self.player_inputs_log = []
        self.state_manager = PlayerStateManager()
        
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph调用接口"""
        sender = state.get("sender", "")
        message = state.get("message", "")
        current_turn = state.get("current_turn", 0)

        if sender.lower() != "player":
            return state
        
        if not message or not message.strip():
            return self._add_validation_result(state, {
                "category": "INVALID_INPUT",
                "reason": "Empty message",
                "send_to_bottom": False,
                "selected_npcs": [],
                "timestamp": datetime.now().isoformat()
            })
        
        selected_npcs = self._extract_selected_npcs(state)
        
        # 1. 处理退出命令
        if message.strip().lower() in ["exit", "quit", "退出", "结束"]:
            return self._handle_exit_command(state, message, selected_npcs)
        
        # 2. 验证玩家输入
        validation_result = self._validate_player_input(message, selected_npcs, state)
        self.validator.add_to_history("Player", message)
        
        # 3. 记录输入日志
        self._log_player_input(message, selected_npcs, validation_result, sender)
        
        # 4. 更新状态并添加验证结果
        updated_state = self._add_validation_result(state, {
            **validation_result,
            "selected_npcs": selected_npcs,
            "timestamp": datetime.now().isoformat()
        })

        # 5. 写入消息存储
        updated_state = self._store_player_message(updated_state, sender, message, selected_npcs, current_turn)
        
        # 6. 处理愤怒状态和关系 (委托给 PlayerStateManager)
        updated_state = self.state_manager.update_angry_state(
            updated_state, validation_result, selected_npcs, current_turn
        )
        
        # 7. 更新剩余回合数
        if validation_result.get("category") == "STORY_RELEVANT":
            current_remaining = updated_state.get("remaining_turns", 0)
            if current_remaining > 0:
                updated_state["remaining_turns"] = current_remaining - 1
                logger.info(f"[PlayerNode] 玩家有效输入，剩余回合数: {updated_state['remaining_turns']}")
        
        return updated_state

    def _handle_exit_command(self, state: Dict[str, Any], message: str, selected_npcs: List[str]) -> Dict[str, Any]:
        """处理玩家退出逻辑"""
        logger.info(f"[PlayerNode] 检测到玩家退出命令: {message}")
        updated_state = state.copy()
        updated_state["player_exit_requested"] = True
        updated_state["needs_worldstate_settlement"] = True
        
        exit_result = {
            "category": "EXIT_COMMAND",
            "reason": "Player requested to exit",
            "send_to_bottom": False,
            "selected_npcs": selected_npcs,
            "timestamp": datetime.now().isoformat()
        }
        return self._add_validation_result(updated_state, exit_result)

    def _log_player_input(self, message: str, selected_npcs: List[str], validation: Dict, sender: str):
        """记录输入日志"""
        self.player_inputs_log.append({
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "selected_npcs": selected_npcs,
            "validation": validation,
            "sender": sender
        })

    def _store_player_message(self, state: Dict, sender: str, message: str, 
                             selected_npcs: List[str], current_turn: int) -> Dict:
        """将玩家消息存入 message_store"""
        if "message_store" not in state:
            state["message_store"] = []
            
        message_entry = {
            "speaker": sender,
            "content": message,
            "allowed_npcs": state.get("chat_group", []),
            "timestamp": current_turn,
            "tags": {
                "sender": sender,
                "target": "multiple" if len(selected_npcs) > 1 else (selected_npcs[0] if selected_npcs else "unknown"),
                "allowed_npcs": state.get("chat_group", [])
            }
        }
        
        # 避免重复添加
        if not any(m.get("content") == message and m.get("speaker") == sender for m in state["message_store"][-1:]):
            state["message_store"].append(message_entry)
            logger.debug(f"[PlayerNode] 玩家消息已存入 message_store: {message[:20]}...")
        return state

    def _extract_selected_npcs(self, state: Dict[str, Any]) -> List[str]:
        """提取选择的NPC列表"""
        if state.get("responders"):
            return list(state["responders"])
        elif state.get("message_target"):
            target = state["message_target"]
            if isinstance(target, str) and target != "all":
                return [target]
            elif isinstance(target, list):
                return target
        
        chat_group = state.get("chat_group", [])
        return [npc for npc in chat_group if npc.lower() != "player"]

    def _validate_player_input(self, message: str, selected_npcs: List[str], state: Dict[str, Any]) -> Dict[str, Any]:
        """验证玩家输入"""
        if not self.scene_data:
            return {"category": "NO_SCENE_DATA", "reason": "No scene data", "send_to_bottom": False}
        
        enhanced_scene_data = self._build_enhanced_scene_data(state)
        self._update_validator_with_history(state)
        
        validation_result = self.validator.evaluate_player_input(
            message, enhanced_scene_data, state.get("message_store", [])
        )
        
        validation_result.update({
            "message_length": len(message),
            "selected_npc_count": len(selected_npcs),
            "current_turn": state.get("current_turn", 0)
        })
        return validation_result

    def _build_enhanced_scene_data(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """构建增强的场景数据"""
        if not self.scene_data: return {}
        enhanced = self.scene_data.copy()
        scene_context = state.get("scene_context", {})
        
        # 更新 key_question, NPC, location 等
        enhanced["key_question"] = scene_context.get("key_questions") or scene_context.get("key_question")
        
        interactive_npcs = enhanced.get("interactive_npc", [])
        npc_purposes = scene_context.get("npc_purposes", {})
        npc_background = scene_context.get("npc_background", {})
        npc_emotions = scene_context.get("npc_emotions", {})
        
        updated_npcs = []
        for npc in interactive_npcs:
            npc_dict = {"name": npc} if isinstance(npc, str) else npc.copy()
            npc_name = npc_dict.get("name", "")
            
            if npc_name in npc_purposes:
                purpose = npc_purposes[npc_name]
                npc_dict["goal"] = purpose.get("goal", "") if isinstance(purpose, dict) else purpose
            if npc_name in npc_background:
                npc_dict["background"] = npc_background[npc_name]
            if npc_name in npc_emotions:
                npc_dict["current_emotion"] = npc_emotions[npc_name]
            updated_npcs.append(npc_dict)
            
        enhanced["interactive_npc"] = updated_npcs
        enhanced["current_location"] = scene_context.get("current_location", "")
        enhanced["current_turn"] = state.get("current_turn", 0)
        return enhanced

    def _update_validator_with_history(self, state: Dict[str, Any]):
        """同步对话历史到验证器"""
        message_store = state.get("message_store", [])
        self.validator.conversation_history.clear()
        for msg in message_store:
            speaker = "Player" if msg.get("speaker", "").lower() == "player" else msg.get("speaker", "Unknown")
            utterance = self.validator._extract_utterance_from_message(msg)
            self.validator.add_to_history(speaker, utterance)

    def _add_validation_result(self, state: Dict[str, Any], validation_result: Dict[str, Any]) -> Dict[str, Any]:
        """将验证结果添加到状态中"""
        updated_state = state.copy()
        updated_state["player_validation"] = validation_result
        
        if "message_tags" not in updated_state:
            updated_state["message_tags"] = {}
        updated_state["message_tags"]["player_validation"] = validation_result
        
        if "player_inputs" not in updated_state:
            updated_state["player_inputs"] = []
        updated_state["player_inputs"].append({
            "message": state.get("message", ""),
            "validation": validation_result,
            "timestamp": validation_result.get("timestamp", datetime.now().isoformat())
        })
        return updated_state

def create_player_node(scene_data: Optional[Dict[str, Any]] = None) -> PlayerNode:
    return PlayerNode(scene_data)

__all__ = ['PlayerNode', 'create_player_node']

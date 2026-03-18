import random
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import END





from npc.utils.constants import ChatMode
from npc.multi_npc.router_strategies import (
    PlayerInvolvedStrategy, CasualChatStrategy, 
    AngryChatStrategy, NPCOnlyStrategy
)

class RouterNode:
    def __init__(self):
        self.max_turns = 5  # 最大对话轮数 npcmode
        self.max_inactive_turns = 3  # 最大不活跃轮次 npcmode
        self.strategies = {
            ChatMode.PLAYER_INVOLVED: PlayerInvolvedStrategy(),
            ChatMode.CASUAL_CHAT: CasualChatStrategy(),
            ChatMode.ANGRY_CHAT: AngryChatStrategy(),
            ChatMode.NPC_ONLY: NPCOnlyStrategy()
        }
        
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理输入状态并决定下一步路由"""
        msg_type = state["msg_type"]
        chat_mode = state.get("chat_mode", ChatMode.PLAYER_INVOLVED)
        
        # ... (保留退出检查和轮次检查逻辑) ...
        if state.get("player_exit_requested", False):
            state["needs_worldstate_settlement"] = True
            return {**state}
        
        remaining_turns = state.get("remaining_turns", 0)
        if remaining_turns <= 0:
            state["needs_worldstate_settlement"] = True
            return {**state}

        # 获取策略
        strategy = self.strategies.get(chat_mode, self.strategies[ChatMode.PLAYER_INVOLVED])

        if msg_type == "new":
            # 动态调整 chat_mode (保留原 logic)
            npc_state = state.get("npc_state", {})
            angry_level = int(npc_state.get("angry_level", 0))
            if npc_state.get("angry", False) and angry_level >= 3:
                chat_mode = ChatMode.ANGRY_CHAT
            else:
                player_validation = state.get("player_validation") or state.get("message_tags", {}).get("player_validation", {})
                if player_validation:
                    if player_validation.get("category") == "STORY_RELEVANT":
                        chat_mode = ChatMode.PLAYER_INVOLVED
                    else:
                        chat_mode = ChatMode.CASUAL_CHAT
            
            state["chat_mode"] = chat_mode
            strategy = self.strategies.get(chat_mode, strategy)
            return strategy.handle_new(state)
            
        elif msg_type == "response":
            return strategy.handle_response(state)
            
        return state
    
    def _check_goal_conditions(self, state: Dict[str, Any]) -> bool:
        """检查是否满足目标条件"""
        end_conditions = state.get("end_conditions", {})
        if not end_conditions:
            return False
        npc_state = state.get("npc_state", {})
        # TODO: 实现具体的目标检查逻辑（可结合 npc_state["npc_goals"]）
        return False
        
    def _check_relationship_state(self, relationship_data: Dict[str, Any], required_state: str) -> bool:
        """检查关系状态"""
        pass
        
    def _check_relationship_trend(self, relationship_data: Dict[str, Any], required_trend: str) -> bool:
        """检查关系趋势"""
        pass
        
    def _handle_new_message(self, state: Dict[str, Any], chat_mode: str, npc_state: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理新消息"""
        # 优先检查是否处于发火状态
        angry_level = int(npc_state.get("angry_level", 0))
        is_angry = npc_state.get("angry", False) and angry_level >= 3
        
        if is_angry:
            chat_mode = "angry_chat"
        else:
            # 正常逻辑：根据玩家输入验证结果决定模式
            player_validation = state.get("player_validation", {})
            if not player_validation:
                message_tags = state.get("message_tags", {})
                player_validation = message_tags.get("player_validation", {})
            
            if player_validation:
                validation_category = player_validation.get("category", "")
                if validation_category == "STORY_RELEVANT":
                    chat_mode = "player_involved"
                elif validation_category == "NOT_STORY_RELEVANT":
                    chat_mode = "casual_chat"
        
        if chat_mode in ["player_involved", "casual_chat", "angry_chat"]:
            result = self._handle_player_message(state, npc_state, scene_context)
        else:
            result = self._handle_npc_message(state, npc_state, scene_context)
            
        result["chat_mode"] = chat_mode
        return result
        
    def _handle_player_message(self, state: Dict[str, Any], npc_state: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理玩家消息"""
        responders = state.get("responders", [])
        if not responders:
            responders = state.get("chat_group", [])
            responders = [npc for npc in responders if npc != "player"]
        if not responders:
            return {**state}
        message_tags = {
            "sender": state["sender"],
            "target": "multiple" if len(responders) > 1 else responders[0],
            "allowed_npcs": state["chat_group"]
        }
        message_entry = {
            "speaker": state["sender"],
            "content": state["message"],
            "allowed_npcs": state["chat_group"],
            "timestamp": state.get("current_turn", 0),
            "tags": message_tags
        }
        message_store = state.get("message_store", [])
        message_store.append(message_entry)
        return {
            **state,
            "msg_type": "response",
            "responders": responders,
            "original_message": state["message"],
            "original_sender": state["sender"],
            "previous_speaker": state["sender"],
            "npc_state": npc_state,
            "scene_context": scene_context,
            "need_add_player_message": True,
            "processed_npcs": [],
            "message_tags": message_tags,
            "message_store": message_store
        }
        
    def _handle_npc_message(self, state: Dict[str, Any], npc_state: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理NPC消息"""
        current_turn = state.get("current_turn", 0)
        inactive_turns = state.get("inactive_turns", {})
        
        if current_turn >= self.max_turns:
            # 达到最大轮次
            return {**state}
            
        initiator = state["sender"]
        initial_message = state["message"]
        
        # 排除发起者
        available_npcs = [
            npc for npc in state["chat_group"]
            if npc != initiator
        ]
        
        if not available_npcs:
            return {**state}
            
        # 检查是否有NPC已经连续三轮未发言，需要强制发言
        forced_speakers = []
        for npc, inactive_count in inactive_turns.items():
            if inactive_count >= 3 and npc in available_npcs:
                forced_speakers.append(npc)
        
        # 如果有强制发言者，从中随机选择一个
        if forced_speakers:
            first_responder = random.choice(forced_speakers)
        else:
            # 否则随机选择一个可用的NPC
            first_responder = random.choice(available_npcs)
        
        message_tags = {
            "sender": state["sender"],
            "target": "all",
            "allowed_npcs": state["chat_group"]
        }
        
        message_entry = {
            "speaker": state["sender"],
            "content": state["message"],
            "allowed_npcs": state["chat_group"],
            "timestamp": current_turn,
            "tags": message_tags
        }
        
        message_store = state.get("message_store", [])
        message_store.append(message_entry)
        
        # 生成新的turn_id
        turn_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        updated_inactive_turns = inactive_turns.copy()
        for npc in state["chat_group"]:
            if npc != first_responder:
                updated_inactive_turns[npc] = updated_inactive_turns.get(npc, 0) + 1
            else:
                updated_inactive_turns[npc] = 0
                
        return {
            **state,
            "responders": [first_responder],
            "msg_type": "response",
            "original_sender": initiator,
            "original_message": initial_message,
            "inactive_turns": updated_inactive_turns,
            "previous_speaker": first_responder,
            "current_turn_id": turn_id,
            "npc_state": npc_state,
            "scene_context": scene_context,
            "need_add_initial_message": True,
            "processed_npcs": [],
            "message_tags": message_tags,
            "message_store": message_store
        }
        
    def _handle_response(self, state: Dict[str, Any], chat_mode: str, npc_state: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理响应消息"""
        current_speaker = state["sender"]
        previous_speaker = state.get("previous_speaker")
        
        if current_speaker in state.get("responders", []) and state.get("message"):
            response_tags = {
                "sender": current_speaker,
                "target": "player" if chat_mode in ["player_involved", "casual_chat", "angry_chat"] else "all",
                "allowed_npcs": state["chat_group"]
            }
            
        if chat_mode == "casual_chat":
            return self._handle_casual_chat_response(state, current_speaker, npc_state, scene_context)
        elif chat_mode == "angry_chat":
            # 发火模式下，通常也只让一个 NPC 回复（或者按需调整）
            return self._handle_casual_chat_response(state, current_speaker, npc_state, scene_context)
        elif chat_mode == "player_involved":
            return self._handle_player_involved_response(state, current_speaker, npc_state, scene_context)
        else:
            current_turn = state.get("current_turn", 0)
            if current_turn >= self.max_turns:
                return {**state}
            return self._handle_npc_only_response(state, current_speaker, previous_speaker, npc_state, scene_context)
            
    def _handle_casual_chat_response(self, state: Dict[str, Any], current_speaker: str, npc_state: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理casual chat模式的响应 - 只让一个NPC回复后结束"""
        # 更新processed_npcs列表，标记当前NPC已处理
        processed_npcs = state.get("processed_npcs", [])
        if current_speaker not in processed_npcs:
            processed_npcs.append(current_speaker)
        
        return {
            **state, 
            "processed_npcs": processed_npcs
        }
    
    def _handle_player_involved_response(self, state: Dict[str, Any], current_speaker: str, npc_state: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理玩家参与模式的响应"""
        processed_npcs = state.get("processed_npcs", [])
        if current_speaker not in processed_npcs:
            processed_npcs.append(current_speaker)
        all_npcs = [npc for npc in state["chat_group"] if npc != "player"]
        if set(processed_npcs) >= set(all_npcs):
            return {**state}
        return {
            **state,
            "previous_speaker": current_speaker,
            "npc_state": npc_state,
            "scene_context": scene_context,
            "processed_npcs": processed_npcs
        }
        
    def _handle_npc_only_response(self, state: Dict[str, Any], current_speaker: str, previous_speaker: str, npc_state: Dict[str, Any], scene_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理NPC-only模式的响应"""
        updated_inactive_turns = state.get("inactive_turns", {})
        # 排除当前发言者和上一轮发言者
        available_npcs = [npc for npc in state["chat_group"]
                         if npc != current_speaker]
                         
        if not available_npcs:
            return {**state}
            
        # 检查是否有NPC已经连续三轮未发言，需要强制发言
        forced_speakers = []
        for npc, inactive_count in updated_inactive_turns.items():
            if inactive_count >= 3 and npc in available_npcs:
                forced_speakers.append(npc)
                
        # 如果有强制发言者，从中随机选择一个
        if forced_speakers:
            next_responder = random.choice(forced_speakers)
        else:
            # 否则随机选择一个可用的NPC
            next_responder = random.choice(available_npcs)
        
        # 更新不活跃轮次计数
        for npc in state["chat_group"]:
            if npc != next_responder:
                updated_inactive_turns[npc] = updated_inactive_turns.get(npc, 0) + 1
            else:
                updated_inactive_turns[npc] = 0
        
        # 递增当前轮次计数
        current_turn = state.get("current_turn", 0) + 1
        
        # 检查是否达到最大轮次
        if current_turn >= self.max_turns:
            return {**state}
                
        return {
            **state,
            "responders": [next_responder],
            "msg_type": "response",
            "current_turn": current_turn,
            "sender": next_responder,
            "inactive_turns": updated_inactive_turns,
            "previous_speaker": next_responder,
            "npc_state": npc_state,
            "scene_context": scene_context
        }

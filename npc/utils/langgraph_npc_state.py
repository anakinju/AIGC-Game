#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph 集成的 NPC 状态管理
将 NPC 信息集成到 LangGraph 的 State 中
"""

from typing import Dict, Any, TypedDict, Annotated, Optional, List
from langgraph.graph import add_messages
import operator

from npc.utils.npc_state_manager import NPCState, npc_state_manager


class ChatStateWithNPCs(TypedDict):
    """扩展的聊天状态，包含 NPC 状态管理"""
    # 原有的聊天状态字段
    messages: Annotated[List[Any], add_messages]
    message_store: List[Dict[str, Any]]
    chat_group: List[str]
    chat_mode: str
    current_turn: int
    scene_data: Dict[str, Any]
    
    # NPC 状态管理字段
    npc_states: Annotated[Dict[str, Dict[str, Any]], operator.add]  # NPC 名称 -> NPC 状态字典
    active_npcs: List[str]  # 当前场景中活跃的 NPC
    npc_updates: Dict[str, Dict[str, Any]]  # 本轮更新的 NPC 信息
    
    # Turn 管理字段
    max_turns: int  # 最大回合数（从场景中读取，默认10）
    remaining_turns: int  # 剩余回合数


class NPCStateNode:
    """NPC 状态管理节点 - 用于 LangGraph 工作流"""
    
    def __init__(self):
        self.state_manager = npc_state_manager
    
    def initialize_npcs(self, state: ChatStateWithNPCs) -> ChatStateWithNPCs:
        """
        初始化场景中的所有 NPC 状态
        
        Args:
            state: 包含场景信息的状态
            
        Returns:
            更新后的状态，包含所有 NPC 的完整信息
        """
        # 从场景数据中获取 NPC 列表
        scene_data = state.get("scene_data", {})
        npc_names = scene_data.get("npcs", [])
        
        if not npc_names:
            # 从 chat_group 中获取 NPC 名称
            chat_group = state.get("chat_group", [])
            npc_names = [name for name in chat_group if name != "Player"]
        
        # 初始化 NPC 状态
        npc_states = {}
        for npc_name in npc_names:
            try:
                npc_state = self.state_manager.get_npc_state(npc_name)
                npc_states[npc_name] = npc_state.to_dict()
            except Exception as e:
                print(f"Warning: Failed to load NPC {npc_name}: {e}")
        
        # 更新状态
        state["npc_states"] = npc_states
        state["active_npcs"] = npc_names
        state["npc_updates"] = {}
        
        return state
    
    def get_npc_for_tool(self, state: ChatStateWithNPCs, npc_name: str) -> Dict[str, Any]:
        """
        为工具调用准备 NPC 信息
        
        Args:
            state: 当前状态
            npc_name: NPC 名称
            
        Returns:
            工具所需的 NPC 完整信息
        """
        # 优先从状态中获取最新信息
        if npc_name in state.get("npc_states", {}):
            npc_state_dict = state["npc_states"][npc_name]
            npc_state = NPCState.from_dict(npc_state_dict)
        else:
            # 如果状态中没有，从管理器加载
            npc_state = self.state_manager.get_npc_state(npc_name)
        
        # 返回工具格式的数据
        return {
            'name': npc_state.name,
            'basic_information': npc_state.basic_information,
            'extended_profile': npc_state.extended_profile,
            'current_relationships': npc_state.dynamic_state.get('relationships', {}),
            'current_emotion': npc_state.dynamic_state.get('emotion'),
            'current_goals': npc_state.dynamic_state.get('goals', []),
            'last_updated': npc_state.last_updated
        }
    
    def update_npc_in_state(self, state: ChatStateWithNPCs, npc_name: str, 
                           update_type: str, update_data: Dict[str, Any]) -> ChatStateWithNPCs:
        """
        在状态中更新 NPC 信息
        
        Args:
            state: 当前状态
            npc_name: NPC 名称
            update_type: 更新类型 ('relationship', 'emotion', 'goal', etc.)
            update_data: 更新数据
            
        Returns:
            更新后的状态
        """
        # 确保 NPC 状态存在
        if npc_name not in state.get("npc_states", {}):
            # 如果不存在，先加载
            npc_state = self.state_manager.get_npc_state(npc_name)
            state.setdefault("npc_states", {})[npc_name] = npc_state.to_dict()
        
        # 获取当前 NPC 状态
        npc_state_dict = state["npc_states"][npc_name]
        npc_state = NPCState.from_dict(npc_state_dict)
        
        # 根据更新类型进行更新
        if update_type == "relationship":
            target_npc = update_data.get("target_npc")
            relationship_data = update_data.get("relationship_data", {})
            if target_npc:
                npc_state.update_relationship(target_npc, relationship_data)
        
        elif update_type == "emotion":
            emotion_data = update_data.get("emotion_data", {})
            npc_state.update_emotion(emotion_data)
        
        elif update_type == "goal":
            goals = update_data.get("goals", [])
            npc_state.dynamic_state["goals"] = goals
        
        # 更新状态
        state["npc_states"][npc_name] = npc_state.to_dict()
        
        # 记录更新
        state.setdefault("npc_updates", {})[npc_name] = {
            "type": update_type,
            "data": update_data,
            "timestamp": npc_state.last_updated
        }
        
        return state
    
    def sync_to_manager(self, state: ChatStateWithNPCs) -> ChatStateWithNPCs:
        """
        将状态中的 NPC 更新同步到全局管理器
        
        Args:
            state: 当前状态
            
        Returns:
            状态（无变化）
        """
        npc_states = state.get("npc_states", {})
        
        for npc_name, npc_state_dict in npc_states.items():
            # 导入到全局管理器
            self.state_manager.import_state(npc_name, npc_state_dict)
        
        return state


# 全局 NPC 状态节点实例
npc_state_node = NPCStateNode()


def get_npc_for_tool_from_state(state: ChatStateWithNPCs, npc_name: str) -> Dict[str, Any]:
    """
    便捷函数：从 LangGraph 状态中获取 NPC 信息供工具使用
    
    Args:
        state: LangGraph 状态
        npc_name: NPC 名称
        
    Returns:
        工具所需的 NPC 信息
    """
    return npc_state_node.get_npc_for_tool(state, npc_name)


def update_npc_relationship_in_state(state: ChatStateWithNPCs, npc_name: str, 
                                    target_npc: str, relationship_data: Dict[str, Any]) -> ChatStateWithNPCs:
    """
    便捷函数：在状态中更新 NPC 关系
    """
    return npc_state_node.update_npc_in_state(
        state, npc_name, "relationship", 
        {"target_npc": target_npc, "relationship_data": relationship_data}
    )


def update_npc_emotion_in_state(state: ChatStateWithNPCs, npc_name: str, 
                               emotion_data: Dict[str, Any]) -> ChatStateWithNPCs:
    """
    便捷函数：在状态中更新 NPC 情绪
    """
    return npc_state_node.update_npc_in_state(
        state, npc_name, "emotion", 
        {"emotion_data": emotion_data}
    )
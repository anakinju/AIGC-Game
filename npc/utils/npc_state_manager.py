#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPC 状态管理器 - 基于 LangChain State 的统一 NPC 信息管理
精简版：仅管理情绪和目标等动态状态，不再管理动态关系
"""

from typing import Dict, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
import json
import os
from datetime import datetime

from npc.utils.npc_info import get_npc_info


class NPCDynamicStateDict(TypedDict):
    """NPC 动态状态字典类型定义 - 只包含可变的状态信息"""
    name: str
    dynamic_state: Dict[str, Any]  # 动态变化的状态（情绪、目标等）
    last_updated: str


@dataclass
class NPCDynamicState:
    """NPC 动态状态类 - 只管理可变的状态信息"""
    name: str
    dynamic_state: Dict[str, Any] = field(default_factory=dict)
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> NPCDynamicStateDict:
        """转换为字典格式"""
        return NPCDynamicStateDict(
            name=self.name,
            dynamic_state=self.dynamic_state,
            last_updated=self.last_updated
        )
    
    @classmethod
    def from_dict(cls, data: NPCDynamicStateDict) -> 'NPCDynamicState':
        """从字典创建实例"""
        return cls(**data)
    
    def get_complete_info(self) -> Dict[str, Any]:
        """获取完整信息（静态+动态）"""
        # 获取静态信息
        static_info = get_npc_info(self.name)
        
        # 组合完整信息
        return {
            "name": self.name,
            "static_info": static_info,  # 来自 characters.json 的静态信息
            "dynamic_state": self.dynamic_state,  # 动态状态信息
            "last_updated": self.last_updated
        }
    
    def update_emotion(self, emotion_data: str, intensity: float = 0.5):
        """更新情绪状态"""
        self.dynamic_state['emotion'] = emotion_data
        self.dynamic_state['emotion_intensity'] = intensity
        self.last_updated = datetime.now().isoformat()
    
    def get_current_emotion(self) -> Optional[str]:
        """获取当前情绪状态"""
        return self.dynamic_state.get('emotion')


class NPCDynamicStateManager:
    """NPC 动态状态管理器 - 单例模式，只管理动态状态"""
    
    _instance = None
    _npc_dynamic_states: Dict[str, NPCDynamicState] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._npc_dynamic_states = {}
    
    def get_npc_dynamic_state(self, npc_name: str, force_reload: bool = False) -> NPCDynamicState:
        """
        获取 NPC 动态状态
        """
        if npc_name not in self._npc_dynamic_states or force_reload:
            self._initialize_dynamic_state(npc_name)
        
        return self._npc_dynamic_states[npc_name]
    
    def _initialize_dynamic_state(self, npc_name: str):
        """初始化 NPC 动态状态"""
        try:
            # 只创建动态状态，不包含静态信息
            dynamic_state = NPCDynamicState(
                name=npc_name,
                dynamic_state={
                    'emotion': 'Calm',
                    'emotion_intensity': 0.5,
                    'goals': [],
                    'memory': [],
                    'scene_knowledge': {}  # 场景特定的知识
                }
            )
            
            self._npc_dynamic_states[npc_name] = dynamic_state
            
        except Exception as e:
            raise ValueError(f"Failed to initialize dynamic state for {npc_name}: {e}")
    
    def update_npc_emotion(self, npc_name: str, emotion: str, intensity: float = 0.5):
        """更新 NPC 情绪"""
        dynamic_state = self.get_npc_dynamic_state(npc_name)
        dynamic_state.update_emotion(emotion, intensity)
    
    def get_npc_for_tool(self, npc_name: str) -> Dict[str, Any]:
        """
        为工具调用准备 NPC 信息（完整信息：静态+动态）
        """
        dynamic_state = self.get_npc_dynamic_state(npc_name)
        
        # 获取完整信息（静态信息会在这里自动获取）
        complete_info = dynamic_state.get_complete_info()
        
        # 为工具调用格式化数据
        tool_data = {
            'name': complete_info['name'],
            'static_info': complete_info['static_info'],  # 静态背景信息
            'dynamic_state': complete_info['dynamic_state'],  # 动态状态信息
            'current_emotion': complete_info['dynamic_state'].get('emotion'),
            'current_goals': complete_info['dynamic_state'].get('goals', []),
            'scene_knowledge': complete_info['dynamic_state'].get('scene_knowledge', {}),
            'last_updated': complete_info['last_updated']
        }
        
        return tool_data
    
    def get_all_npc_names(self) -> list[str]:
        """获取所有已加载的 NPC 名称"""
        return list(self._npc_dynamic_states.keys())
    
    def clear_cache(self):
        """清除所有缓存"""
        self._npc_dynamic_states.clear()
    
    def export_dynamic_state(self, npc_name: str) -> Dict[str, Any]:
        """导出 NPC 动态状态用于持久化"""
        if npc_name in self._npc_dynamic_states:
            return self._npc_dynamic_states[npc_name].to_dict()
        return {}
    
    def import_dynamic_state(self, npc_name: str, state_data: Dict[str, Any]):
        """导入 NPC 动态状态"""
        self._npc_dynamic_states[npc_name] = NPCDynamicState.from_dict(state_data)


# 全局动态状态管理器实例
npc_dynamic_state_manager = NPCDynamicStateManager()

def get_npc_state_for_tool(npc_name: str) -> Dict[str, Any]:
    """便捷函数：为工具获取 NPC 状态"""
    return npc_dynamic_state_manager.get_npc_for_tool(npc_name)

def update_npc_emotion_global(npc_name: str, emotion: str, intensity: float = 0.5):
    """便捷函数：全局更新 NPC 情绪"""
    npc_dynamic_state_manager.update_npc_emotion(npc_name, emotion, intensity)

def get_npc_basic_info(npc_name: str) -> Dict[str, Any]:
    """便捷函数：获取 NPC 基础信息（从静态文件）"""
    static_info = get_npc_info(npc_name)
    return static_info.get('basic_information', {}) if static_info else {}

def get_npc_complete_info(npc_name: str) -> Dict[str, Any]:
    """便捷函数：获取 NPC 完整信息（静态+动态）"""
    dynamic_state = npc_dynamic_state_manager.get_npc_dynamic_state(npc_name)
    return dynamic_state.get_complete_info()

# 向后兼容的别名
npc_state_manager = npc_dynamic_state_manager

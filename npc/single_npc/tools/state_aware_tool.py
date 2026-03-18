#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
状态感知工具基类
为工具提供统一的状态访问和更新接口
"""

import os
import sys
from typing import Dict, Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langchain.tools import BaseTool
from pydantic import BaseModel

# 避免循环导入
if TYPE_CHECKING:
    from npc.multi_npc.chat_env import ChatState


class StateAwareToolBase(BaseTool, ABC):
    """
    状态感知工具基类
    
    提供统一的接口来访问和更新 ChatState 中的 NPC 状态
    所有需要访问 NPC 状态的工具都应该继承此类
    """
    
    def __init__(self, npc_name: str, **kwargs):
        super().__init__(**kwargs)
        self._npc_name = npc_name
        self._chat_state: Optional['ChatState'] = None
        self._chat_env = None  # ChatEnvironment 实例的引用
    
    @property
    def npc_name(self) -> str:
        """获取 NPC 名称"""
        return self._npc_name
    
    def set_chat_state(self, chat_state: 'ChatState', chat_env=None):
        """
        设置聊天状态和环境引用
        
        Args:
            chat_state: 当前的聊天状态
            chat_env: ChatEnvironment 实例（可选）
        """
        self._chat_state = chat_state
        self._chat_env = chat_env
    
    def get_npc_state(self, npc_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取 NPC 状态信息
        
        Args:
            npc_name: NPC 名称，默认为当前工具的 NPC
            
        Returns:
            Dict[str, Any]: NPC 状态信息
        """
        target_npc = npc_name or self._npc_name
        
        if self._chat_env and hasattr(self._chat_env, 'get_npc_state_for_tool'):
            return self._chat_env.get_npc_state_for_tool(target_npc)
        elif self._chat_state:
            # 直接从状态获取动态信息，并自动获取静态信息
            npc_states = self._chat_state.get("npc_states", {})
            if target_npc in npc_states:
                dynamic_state_dict = npc_states[target_npc]
                
                # 获取静态信息
                from npc.utils.npc_info import get_npc_info
                static_info = get_npc_info(target_npc) or {}
                
                return {
                    'name': dynamic_state_dict['name'],
                    'static_info': static_info,  # 静态背景信息
                    'dynamic_state': dynamic_state_dict['dynamic_state'],  # 动态状态信息
                    'current_relationships': dynamic_state_dict['dynamic_state'].get('relationships', {}),
                    'current_emotion': dynamic_state_dict['dynamic_state'].get('emotion'),
                    'current_goals': dynamic_state_dict['dynamic_state'].get('goals', []),
                    'scene_knowledge': dynamic_state_dict['dynamic_state'].get('scene_knowledge', {}),
                    'last_updated': dynamic_state_dict['last_updated']
                }
        
        # 回退到全局状态管理器
        from npc.utils.npc_state_manager import npc_state_manager
        return npc_state_manager.get_npc_for_tool(target_npc)
    
    def get_complete_npc_info(self, npc_name: str = None) -> Dict[str, Any]:
        """
        获取完整的 NPC 信息（静态背景信息 + 动态状态信息）
        
        Args:
            npc_name: NPC 名称，默认为当前工具的 NPC
            
        Returns:
            Dict[str, Any]: 完整的 NPC 信息
        """
        target_npc = npc_name or self._npc_name
        
        # 1. 获取静态背景信息（从 characters.json）
        try:
            from npc.utils.npc_info import get_npc_info
            static_info = get_npc_info(target_npc)
        except Exception as e:
            print(f"[StateAwareTool] 警告: 无法获取 {target_npc} 的静态信息: {e}")
            static_info = {}
        
        # 2. 获取动态状态信息（从 LangGraph 状态）
        dynamic_info = self.get_npc_state(target_npc)
        
        # 3. 合并信息 - 现在 get_npc_state 已经返回了完整信息
        complete_info = {
            "name": target_npc,
            "static_info": dynamic_info.get("static_info", static_info),  # 静态背景信息
            "dynamic_state": dynamic_info.get("dynamic_state", {}),       # 动态状态信息
            "scene_knowledge": dynamic_info.get("scene_knowledge", {}),   # 场景特定知识
            "current_goals": dynamic_info.get("current_goals", []),       # 当前目标
            "current_relationships": dynamic_info.get("current_relationships", {}),  # 当前关系
            "current_emotion": dynamic_info.get("current_emotion", {}),   # 当前情绪
        }
        
        return complete_info
    
    def update_npc_relationship(self, target_npc: str, relationship_data: Dict[str, Any]):
        """
        更新 NPC 关系
        
        Args:
            target_npc: 目标 NPC 名称
            relationship_data: 关系数据
        """
        if self._chat_env and hasattr(self._chat_env, 'update_npc_state'):
            self._chat_env.update_npc_state(
                self._npc_name, 
                "relationship", 
                {"target_npc": target_npc, "relationship_data": relationship_data}
            )
        else:
            # 回退到全局更新
            from npc.utils.npc_state_manager import update_npc_relationship_global
            update_npc_relationship_global(self._npc_name, target_npc, relationship_data)
    
    def update_npc_emotion(self, emotion_data: Dict[str, Any]):
        """
        更新 NPC 情绪
        
        Args:
            emotion_data: 情绪数据
        """
        if self._chat_env and hasattr(self._chat_env, 'update_npc_state'):
            self._chat_env.update_npc_state(
                self._npc_name, 
                "emotion", 
                {"emotion_data": emotion_data}
            )
        else:
            # 回退到全局更新
            from npc.utils.npc_state_manager import update_npc_emotion_global
            update_npc_emotion_global(self._npc_name, emotion_data)
    
    def update_npc_goals(self, goals: list[str]):
        """
        更新 NPC 目标
        
        Args:
            goals: 目标列表
        """
        if self._chat_env and hasattr(self._chat_env, 'update_npc_state'):
            self._chat_env.update_npc_state(
                self._npc_name, 
                "goal", 
                {"goals": goals}
            )
        else:
            # 回退到全局更新
            from npc.utils.npc_state_manager import update_npc_goals_global
            update_npc_goals_global(self._npc_name, goals)
    
    def get_current_relationships(self) -> Dict[str, Any]:
        """获取当前 NPC 的所有关系"""
        npc_state = self.get_npc_state()
        return npc_state.get('current_relationships', {})
    
    def get_current_emotion(self) -> Optional[Dict[str, Any]]:
        """获取当前 NPC 的情绪状态"""
        npc_state = self.get_npc_state()
        return npc_state.get('current_emotion')
    
    def get_current_goals(self) -> list[str]:
        """获取当前 NPC 的目标列表"""
        npc_state = self.get_npc_state()
        return npc_state.get('current_goals', [])
    
    def get_basic_information(self) -> Dict[str, Any]:
        """获取 NPC 基础信息"""
        npc_state = self.get_npc_state()
        return npc_state.get('basic_information', {})
    
    def get_extended_profile(self) -> Dict[str, Any]:
        """获取 NPC 扩展档案"""
        npc_state = self.get_npc_state()
        return npc_state.get('extended_profile', {})
    
    @abstractmethod
    def _run(self, *args, **kwargs) -> str:
        """
        工具的具体执行逻辑
        子类必须实现此方法
        """
        pass
    
    async def _arun(self, *args, **kwargs) -> str:
        """异步执行，默认调用同步版本"""
        return self._run(*args, **kwargs)


class StateAwareToolManager:
    """
    状态感知工具管理器
    
    管理一组状态感知工具，并为它们提供统一的状态访问
    """
    
    def __init__(self, npc_name: str):
        self.npc_name = npc_name
        self.tools: Dict[str, StateAwareToolBase] = {}
        self._chat_state: Optional['ChatState'] = None
        self._chat_env = None
    
    def add_tool(self, tool: StateAwareToolBase):
        """添加工具到管理器"""
        self.tools[tool.name] = tool
        if self._chat_state:
            tool.set_chat_state(self._chat_state, self._chat_env)
    
    def set_chat_state(self, chat_state: 'ChatState', chat_env=None):
        """为所有工具设置聊天状态"""
        self._chat_state = chat_state
        self._chat_env = chat_env
        
        for tool in self.tools.values():
            tool.set_chat_state(chat_state, chat_env)
    
    def get_tool(self, tool_name: str) -> Optional[StateAwareToolBase]:
        """获取指定名称的工具"""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> list[StateAwareToolBase]:
        """获取所有工具"""
        return list(self.tools.values())
    
    def execute_tool(self, tool_name: str, *args, **kwargs) -> str:
        """执行指定工具"""
        tool = self.get_tool(tool_name)
        if tool:
            return tool._run(*args, **kwargs)
        else:
            raise ValueError(f"Tool {tool_name} not found")


def create_state_aware_tool_manager(npc_name: str, chat_state: 'ChatState', chat_env=None) -> StateAwareToolManager:
    """
    便捷函数：创建状态感知工具管理器
    
    Args:
        npc_name: NPC 名称
        chat_state: 聊天状态
        chat_env: ChatEnvironment 实例
        
    Returns:
        StateAwareToolManager: 配置好的工具管理器
    """
    manager = StateAwareToolManager(npc_name)
    manager.set_chat_state(chat_state, chat_env)
    return manager
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPC 管理器扩展 - 从 ChatEnvironment 中分离出的 NPC 管理功能
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.base_npc import NPCAgent
from npc.utils.npc_state_manager import npc_state_manager
from npc.utils.npc_info import NPCInfoLoader


class NPCManagerExtended:
    """NPC 管理器扩展 - 处理 NPC 加载、状态管理和信息处理"""
    
    def __init__(self):
        self.npc_agents: Dict[str, NPCAgent] = {}
        self.npc_info_cache: Dict[str, Dict[str, Any]] = {}
    
    def load_npc_base_info(self, npc_name: str) -> Optional[Dict[str, Any]]:
        """
        加载NPC基础信息
        
        Args:
            npc_name: NPC名称
            
        Returns:
            Optional[Dict[str, Any]]: NPC信息，如果找不到则返回None
        """
        # 检查缓存
        if npc_name in self.npc_info_cache:
            return self.npc_info_cache[npc_name]
        
        try:
            from npc.utils.npc_info import NPCInfoLoader
        except ImportError:
            return None
        
        try:
            # 尝试从characters.json加载
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
            characters_path = os.path.join(project_root, "data", "npc_info", "characters.json")
            
            if os.path.exists(characters_path):
                loader = NPCInfoLoader(npc_name)
                npc_info = loader.get_npc_info()
                basic_info = loader.get_basic_info()
                
                if npc_info:
                    # 构建完整信息
                    full_info = {
                        "name": loader.get_npc_name(),
                        "basic_info": basic_info,
                        "full_info": npc_info
                    }
                    
                    # 缓存结果
                    self.npc_info_cache[npc_name] = full_info
                    return full_info
            
            return None
            
        except Exception as e:
            return None
    
    def merge_npc_base_info(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        合并NPC基础信息
        
        Args:
            target: 目标字典
            source: 源字典
        """
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(target[key], dict) and isinstance(value, dict):
                self.merge_npc_base_info(target[key], value)
            elif isinstance(target[key], list) and isinstance(value, list):
                # 合并列表，避免重复
                for item in value:
                    if item not in target[key]:
                        target[key].append(item)
    
    def load_all_npcs_from_characters_file(self, characters_file: str) -> Dict[str, NPCAgent]:
        """
        从characters文件加载所有NPC
        
        Args:
            characters_file: characters文件路径
            
        Returns:
            Dict[str, NPCAgent]: NPC代理字典
        """
        npc_agents = {}
        
        if not characters_file or not os.path.exists(characters_file):
            return npc_agents
        
        try:
            with open(characters_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理不同的文件格式
            characters = []
            if isinstance(data, dict) and 'characters' in data:
                characters = data['characters']
            elif isinstance(data, list):
                characters = data
            
            # 为每个角色创建NPCAgent
            for character in characters:
                if isinstance(character, dict) and 'name' in character:
                    npc_name = character['name']
                    try:
                        npc_agents[npc_name] = NPCAgent(npc_name)
                    except Exception as e:
                        pass
            
            return npc_agents
            
        except Exception as e:
            return npc_agents
    
    def load_npcs_from_characters_file(self, characters_file: str, npc_names: List[str]) -> Dict[str, NPCAgent]:
        """
        从characters文件加载指定的NPC
        
        Args:
            characters_file: characters文件路径
            npc_names: 要加载的NPC名称列表
            
        Returns:
            Dict[str, NPCAgent]: NPC代理字典
        """
        npc_agents = {}
        
        if not characters_file or not os.path.exists(characters_file):
            return npc_agents
        
        try:
            # 为指定的NPC创建代理
            for npc_name in npc_names:
                try:
                    npc_agents[npc_name] = NPCAgent(npc_name)
                except Exception as e:
                    pass
            
            return npc_agents
            
        except Exception as e:
            return npc_agents
    
    def initialize_npc_states(self, npc_names: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """
        初始化场景中所有 NPC 的状态
        
        Args:
            npc_names: NPC 名称列表
            
        Returns:
            tuple: (npc_states_dict, active_npcs_list)
        """
        npc_states = {}
        active_npcs = []
        
        for npc_name in npc_names:
            try:
                # 使用动态状态管理器加载 NPC 动态状态
                dynamic_state = npc_state_manager.get_npc_dynamic_state(npc_name)
                npc_states[npc_name] = dynamic_state.to_dict()  # 只包含动态状态
                active_npcs.append(npc_name)
            except Exception as e:
                pass
        
        return npc_states, active_npcs
    
    def get_npc_state_for_tool(self, npc_name: str, npc_states: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        为工具获取 NPC 状态信息
        
        Args:
            npc_name: NPC 名称
            npc_states: 当前 NPC 状态字典
            
        Returns:
            Dict[str, Any]: NPC 状态信息
        """
        if npc_name in npc_states:
            # 从当前动态状态获取信息，并自动获取静态信息
            dynamic_state_dict = npc_states[npc_name]
            
            # 获取静态信息
            from npc.utils.npc_info import get_npc_info
            static_info = get_npc_info(npc_name) or {}
            
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
        else:
            # 回退到状态管理器
            return npc_state_manager.get_npc_for_tool(npc_name)
    
    def update_npc_state(self, npc_name: str, update_type: str, update_data: Dict[str, Any], 
                        npc_states: Dict[str, Dict[str, Any]], npc_updates: Dict[str, Dict[str, Any]]) -> None:
        """
        更新 NPC 状态
        
        Args:
            npc_name: NPC 名称
            update_type: 更新类型 ('relationship', 'emotion', 'goal')
            update_data: 更新数据
            npc_states: NPC 状态字典
            npc_updates: NPC 更新记录字典
        """
        if npc_name not in npc_states:
            return
        
        npc_state_dict = npc_states[npc_name]
        
        # 根据更新类型进行更新
        if update_type == "relationship":
            target_npc = update_data.get("target_npc")
            relationship_data = update_data.get("relationship_data", {})
            if target_npc:
                if 'relationships' not in npc_state_dict['dynamic_state']:
                    npc_state_dict['dynamic_state']['relationships'] = {}
                npc_state_dict['dynamic_state']['relationships'][target_npc] = relationship_data
        
        elif update_type == "emotion":
            emotion_data = update_data.get("emotion_data", {})
            npc_state_dict['dynamic_state']['emotion'] = emotion_data
        
        elif update_type == "goal":
            goals = update_data.get("goals", [])
            npc_state_dict['dynamic_state']['goals'] = goals
        
        # 更新时间戳
        npc_state_dict['last_updated'] = datetime.now().isoformat()
        
        # 记录更新
        npc_updates[npc_name] = {
            "type": update_type,
            "data": update_data,
            "timestamp": npc_state_dict['last_updated']
        }
    
    def get_available_npcs(self, npc_behaviors: Dict[str, Any]) -> List[str]:
        """
        获取可用的NPC列表
        
        Args:
            npc_behaviors: NPC行为字典
            
        Returns:
            List[str]: 可用的NPC名称列表
        """
        return list(npc_behaviors.keys())
    
    def is_valid_npc(self, npc_name: str, npc_behaviors: Dict[str, Any]) -> bool:
        """
        检查NPC是否有效
        
        Args:
            npc_name: NPC名称
            npc_behaviors: NPC行为字典
            
        Returns:
            bool: 是否有效
        """
        return npc_name in npc_behaviors
    
    def get_npc_agent(self, npc_name: str) -> Optional[NPCAgent]:
        """
        获取 NPC 代理
        
        Args:
            npc_name: NPC 名称
            
        Returns:
            Optional[NPCAgent]: NPC 代理实例
        """
        return self.npc_agents.get(npc_name)
    
    def add_npc_agent(self, npc_name: str, agent: NPCAgent) -> None:
        """
        添加 NPC 代理
        
        Args:
            npc_name: NPC 名称
            agent: NPC 代理实例
        """
        self.npc_agents[npc_name] = agent
    
    def clear_cache(self) -> None:
        """清除所有缓存"""
        self.npc_info_cache.clear()
        self.npc_agents.clear()
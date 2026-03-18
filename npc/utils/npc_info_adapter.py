#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPC 信息适配器 - 提供向后兼容的接口
在迁移期间，现有代码可以通过这个适配器逐步切换到新的状态管理系统
"""

from typing import Dict, Any, Optional, List
import os
import sys

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.npc_info import NPCInfoLoader as OriginalNPCInfoLoader
from npc.utils.npc_state_manager import (
    npc_state_manager, 
    get_npc_state_for_tool,
    get_npc_basic_info
)


class NPCInfoLoaderAdapter:
    """
    NPC 信息加载器适配器
    
    提供与原 NPCInfoLoader 相同的接口，但内部使用新的状态管理系统
    这样现有代码可以无缝切换，同时享受新架构的性能优势
    """
    
    def __init__(self, npc_name: str, use_new_system: bool = True):
        """
        初始化适配器
        
        Args:
            npc_name: NPC 名称
            use_new_system: 是否使用新的状态管理系统
        """
        self.npc_name = npc_name
        self.use_new_system = use_new_system
        
        if not use_new_system:
            # 回退到原系统
            self._original_loader = OriginalNPCInfoLoader(npc_name)
        else:
            self._original_loader = None
    
    def get_npc_info(self) -> Dict[str, Any]:
        """获取 NPC 完整信息"""
        if self.use_new_system:
            return get_npc_state_for_tool(self.npc_name)
        else:
            return self._original_loader.get_npc_info()
    
    def get_basic_info(self) -> Dict[str, Any]:
        """获取 NPC 基础信息"""
        if self.use_new_system:
            return get_npc_basic_info(self.npc_name)
        else:
            return self._original_loader.get_basic_info()
    
    def get_relationships(self) -> Dict[str, Any]:
        """获取 NPC 关系信息 (现在仅返回静态配置的关系)"""
        if self.use_new_system:
            # 从静态信息中获取
            full_info = self.get_npc_info()
            return full_info.get("static_info", {}).get("social_and_emotional", {}).get("relationships", {})
        else:
            return self._original_loader.get_relationships()
    
    def get_npc_name(self) -> str:
        """获取 NPC 名称"""
        return self.npc_name
    
    def get_nickname(self) -> str:
        """获取 NPC 昵称"""
        if self.use_new_system:
            basic_info = get_npc_basic_info(self.npc_name)
            return basic_info.get('nickname', '')
        else:
            return self._original_loader.get_nickname()
    
    def get_narrative_threads(self) -> List[str]:
        """获取 NPC 叙事线索"""
        if self.use_new_system:
            basic_info = get_npc_basic_info(self.npc_name)
            threads = basic_info.get('narrative_threads', [])
            if isinstance(threads, list):
                return threads
            return []
        else:
            return self._original_loader.get_narrative_threads()
    
    def get_current_status(self) -> str:
        """获取 NPC 当前状态"""
        if self.use_new_system:
            basic_info = get_npc_basic_info(self.npc_name)
            return basic_info.get('current_status', '')
        else:
            return self._original_loader.get_current_status()
    
    def get_appearance(self) -> str:
        """获取 NPC 外观描述"""
        if self.use_new_system:
            basic_info = get_npc_basic_info(self.npc_name)
            return basic_info.get('appearance', '')
        else:
            return self._original_loader.get_appearance()
    
    def get_obsession(self) -> str:
        """获取 NPC 执念"""
        if self.use_new_system:
            basic_info = get_npc_basic_info(self.npc_name)
            return basic_info.get('obsession', '')
        else:
            return self._original_loader.get_obsession()
    
    def get_attitude_toward_human_yokai(self) -> str:
        """获取 NPC 对人类妖怪的态度"""
        if self.use_new_system:
            basic_info = get_npc_basic_info(self.npc_name)
            return basic_info.get('attitude_toward_human_yokai', '')
        else:
            return self._original_loader.get_attitude_toward_human_yokai()
    
    def get_personality_traits(self) -> List[str]:
        """获取 NPC 性格特征"""
        if self.use_new_system:
            basic_info = get_npc_basic_info(self.npc_name)
            traits = basic_info.get('personality_traits', [])
            if isinstance(traits, list):
                return traits
            elif isinstance(traits, str):
                return [traits]
            return []
        else:
            return self._original_loader.get_personality_traits()

    # --- 新增模块化信息提取接口 ---

    def get_info_for_relationship_analysis(self) -> Dict[str, Any]:
        """提取用于分析关系和情绪的信息"""
        if self.use_new_system:
            # 新系统下，从 get_npc_info() 获取完整信息并按新结构提取
            full_info = self.get_npc_info()
            return {
                "personality": full_info.get("personality_and_speech", {}),
                "social_rules": full_info.get("social_and_emotional", {}),
                "world_attitude": full_info.get("narrative_context", {}).get("world_attitude", "")
            }
        else:
            return self._original_loader.get_info_for_relationship_analysis()

    def get_info_for_intention(self) -> Dict[str, Any]:
        """提取用于生成 NPC 意图的信息"""
        if self.use_new_system:
            full_info = self.get_npc_info()
            return {
                "identity": full_info.get("core_identity", {}),
                "motivation": full_info.get("motivation_and_drive", {}),
                "logic": full_info.get("behavioral_logic", {})
            }
        else:
            return self._original_loader.get_info_for_intention()



    def get_info_for_casual_chat(self) -> Dict[str, Any]:
        """提取用于闲聊的信息"""
        if self.use_new_system:
            full_info = self.get_npc_info()
            return {
                "nickname": full_info.get("core_identity", {}).get("nickname", self.npc_name),
                "personality": full_info.get("personality_and_speech", {}),
                "background": full_info.get("narrative_context", {}).get("background", "")
            }
        else:
            return self._original_loader.get_info_for_casual_chat()

    def get_info_for_angry_response(self) -> Dict[str, Any]:
        """提取用于发火响应的信息"""
        if self.use_new_system:
            full_info = self.get_npc_info()
            return {
                "identity": full_info.get("core_identity", {}),
                "principles": full_info.get("behavioral_logic", {}).get("principles", []),
                "triggers": full_info.get("social_and_emotional", {}).get("triggers", "")
            }
        else:
            return self._original_loader.get_info_for_angry_response()
    
    def validate_npc_data(self) -> bool:
        """验证 NPC 数据"""
        if self.use_new_system:
            try:
                npc_state = npc_state_manager.get_npc_state(self.npc_name)
                # 检查必要字段
                if not npc_state.name:
                    return False
                if not npc_state.basic_information:
                    return False
                basic_info = npc_state.basic_information
                # 检查关键字段
                required_fields = ['background']
                for field in required_fields:
                    if field not in basic_info:
                        return False
                return True
            except Exception:
                return False
        else:
            return self._original_loader.validate_npc_data()


# 全局配置：是否默认使用新系统
USE_NEW_SYSTEM_BY_DEFAULT = True


def create_npc_loader(npc_name: str, force_new_system: Optional[bool] = None) -> NPCInfoLoaderAdapter:
    """
    创建 NPC 加载器
    
    Args:
        npc_name: NPC 名称
        force_new_system: 强制使用新/旧系统，None 则使用默认配置
        
    Returns:
        NPCInfoLoaderAdapter: 适配器实例
    """
    use_new = USE_NEW_SYSTEM_BY_DEFAULT if force_new_system is None else force_new_system
    return NPCInfoLoaderAdapter(npc_name, use_new_system=use_new)


def get_npc_info_unified(npc_name: str, use_new_system: Optional[bool] = None) -> Dict[str, Any]:
    """
    统一的 NPC 信息获取函数
    
    Args:
        npc_name: NPC 名称
        use_new_system: 是否使用新系统，None 则使用默认配置
        
    Returns:
        NPC 完整信息
    """
    loader = create_npc_loader(npc_name, use_new_system)
    return loader.get_npc_info()


# 向后兼容的别名
NPCInfoLoader = NPCInfoLoaderAdapter
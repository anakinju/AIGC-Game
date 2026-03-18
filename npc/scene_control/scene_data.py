#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景数据类 - 用于存储和管理场景的静态数据
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class SceneData:
    """场景数据类，存储场景的静态配置信息"""
    name: str
    location: str
    time: str = "Morning"
    max_turns: int = 10
    environment: str = ""
    current_topic: str = ""
    key_npcs: List[str] = field(default_factory=list)
    interactive_npc: List[Dict[str, Any]] = field(default_factory=list)
    npc_relationships: List[Dict[str, Any]] = field(default_factory=list)
    interactive_environment_objects: List[Dict[str, Any]] = field(default_factory=list)
    scene_end_state_reference: Dict[str, Any] = field(default_factory=dict)
    worldstate_tasks: List[Dict[str, Any]] = field(default_factory=list)
    trigger_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # 原始数据备份
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SceneData':
        """从字典创建 SceneData 实例"""

        return cls(
            name=data.get("name", "Unknown"),
            location=data.get("location", "Unknown"),
            time=data.get("time", "Morning"),
            max_turns=data.get("max_turns", 10),
            environment=data.get("environment", ""),
            current_topic=data.get("current_topic", ""),
            key_npcs=data.get("key_npcs", []),
            interactive_npc=data.get("interactive_npc", []),
            npc_relationships=data.get("npc_relationships", []),
            interactive_environment_objects=data.get("interactive_environment_objects", []),
            scene_end_state_reference=data.get("scene_end_state_reference", {}),
            worldstate_tasks=data.get("worldstate_tasks", []),
            trigger_conditions=data.get("trigger_conditions", {}),
            raw_data=data
        )

class SceneRegistry:
    """场景注册表 - 单例模式，用于全局访问场景数据，支持按索引切换与按路径加载"""
    _instance = None
    _scenes: Dict[int, SceneData] = {}
    _current_scene_index: Optional[int] = None
    _current_scene_override: Optional[SceneData] = None  # 按路径加载时的当前场景，优先于 index

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SceneRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_scene(cls, index: int, scene_data: SceneData):
        """注册场景数据（用于从集合文件加载时）"""
        cls._scenes[index] = scene_data

    @classmethod
    def get_scene(cls, index: int) -> Optional[SceneData]:
        """根据索引获取场景数据（不改变当前场景）"""
        return cls._scenes.get(index)

    @classmethod
    def set_current_scene(cls, index: int):
        """按索引切换当前场景（清除路径加载的覆盖）"""
        cls._current_scene_index = index
        cls._current_scene_override = None

    @classmethod
    def set_current_scene_override(cls, scene_data: SceneData):
        """按路径加载时设置当前场景（覆盖索引方式）"""
        cls._current_scene_override = scene_data
        cls._current_scene_index = None

    @classmethod
    def get_current_scene(cls) -> Optional[SceneData]:
        """获取当前活跃场景数据（优先返回路径加载的覆盖，否则按索引）"""
        if cls._current_scene_override is not None:
            return cls._current_scene_override
        if cls._current_scene_index is not None:
            return cls.get_scene(cls._current_scene_index)
        return None

    @classmethod
    def get_current_scene_index(cls) -> Optional[int]:
        """获取当前场景索引（仅当按索引切换时有效）"""
        return cls._current_scene_index

    @classmethod
    def clear(cls):
        """清空注册表"""
        cls._scenes.clear()
        cls._current_scene_index = None
        cls._current_scene_override = None

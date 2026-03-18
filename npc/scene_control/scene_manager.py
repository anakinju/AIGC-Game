#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
场景管理器 - 从 ChatEnvironment 中分离出的场景管理功能
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.scene_control.scene_status import SceneStatus


from npc.scene_control.scene_data import SceneData, SceneRegistry

class SceneManager:
    """场景管理器 - 处理场景加载、选择和初始化"""
    
    def __init__(self):
        self.scene_status = SceneStatus()
        self.current_scene = None
        self.registry = SceneRegistry()
    
    def get_current_scene_data(self) -> Optional[SceneData]:
        """从注册表获取当前场景的 SceneData（切换后始终为当前场景）"""
        return self.registry.get_current_scene()

    def get_scene_data_by_index(self, index: int) -> Optional[SceneData]:
        """根据索引获取场景的 SceneData（不改变当前场景，需已通过 load_all_scenes 加载）"""
        return self.registry.get_scene(index)
    
    def prompt_scene_selection(self) -> Optional[int]:
        """
        提示用户选择场景
        
        Returns:
            Optional[int]: 选择的场景索引，如果用户取消则返回None
        """
        try:
            # 获取所有可用场景
            scenes = self.get_all_available_scenes()
            
            if not scenes:
                print("没有找到可用的场景文件")
                return None
            
            print("\n可用场景:")
            for i, scene in enumerate(scenes):
                print(f"{i}: {scene['name']} - {scene['description']}")
            
            while True:
                try:
                    choice = input(f"\n请选择场景 (0-{len(scenes)-1}), 或输入 'q' 退出: ").strip()
                    if choice.lower() == 'q':
                        return None
                    
                    scene_index = int(choice)
                    if 0 <= scene_index < len(scenes):
                        return scene_index
                    else:
                        print(f"请输入 0-{len(scenes)-1} 之间的数字")
                except ValueError:
                    print("请输入有效的数字")
                    
        except Exception as e:
            print(f"场景选择过程中出现错误: {e}")
            return None
    
    def get_all_available_scenes(self) -> List[Dict]:
        """
        获取所有可用场景的信息
        
        Returns:
            List[Dict]: 场景信息列表
        """
        return self.scene_status.get_all_scenes()
    
    def load_scene_by_index(self, scene_index: int) -> bool:
        """
        根据索引加载场景
        
        Args:
            scene_index: 场景索引
            
        Returns:
            bool: 是否加载成功
        """
        success = self.scene_status.load_scene_by_index(scene_index)
        if success:
            self.current_scene = self.scene_status.current_scene
        return success
    
    def load_scene_by_path(self, scene_path: str, auto_select: bool = True) -> bool:
        """
        根据路径加载场景
        
        Args:
            scene_path: 场景文件路径
            auto_select: 如果文件包含多个场景，是否自动让用户选择
            
        Returns:
            bool: 是否加载成功
        """
        if not os.path.isfile(scene_path):
            print(f"场景文件不存在: {scene_path}")
            return False
        
        try:
            with open(scene_path, "r", encoding="utf-8") as f:
                scene_data = json.load(f)
            
            # 检查是否是场景列表
            if isinstance(scene_data, list):
                if not scene_data:
                    print("场景列表为空")
                    return False
                
                # 如果只有一个场景，直接使用
                if len(scene_data) == 1:
                    selected_scene = scene_data[0]
                elif auto_select:
                    # 让用户选择场景
                    selected_index = self._select_scene_from_list(scene_data)
                    if selected_index is None:
                        return False
                    selected_scene = scene_data[selected_index]
                else:
                    # 不自动选择，返回第一个
                    selected_scene = scene_data[0]
                
                # 使用选中的场景
                self.current_scene = selected_scene
                # 通过 scene_status 加载并初始化
                self._initialize_scene_status(selected_scene, scene_path)
                
                return True
            else:
                # 单个场景字典
                self.current_scene = scene_data
                self._initialize_scene_status(scene_data, scene_path)
                return True
                
        except Exception as e:
            print(f"加载场景文件失败: {e}")
            return False
    
    def _select_scene_from_list(self, scene_list: List[Dict[str, Any]]) -> Optional[int]:
        """
        从场景列表中选择场景
        
        Args:
            scene_list: 场景列表
            
        Returns:
            Optional[int]: 选择的场景索引，如果取消则返回None
        """
        print(f"\n发现 {len(scene_list)} 个场景，请选择:")
        print("-" * 60)
        
        for i, scene in enumerate(scene_list):
            scene_name = scene.get("name", scene.get("title", f"场景 {i+1}"))
            scene_location = scene.get("location", "")
            scene_time = scene.get("time", "")
            scene_topic = scene.get("current_topic", "")
            
            print(f"{i}: {scene_name}")
            if scene_location:
                print(f"   地点: {scene_location}")
            if scene_time:
                print(f"   时间: {scene_time}")
            if scene_topic:
                print(f"   主题: {scene_topic[:50]}..." if len(scene_topic) > 50 else f"   主题: {scene_topic}")
            print()
        
        while True:
            try:
                choice = input(f"请选择场景 (0-{len(scene_list)-1}), 或输入 'q' 退出: ").strip()
                if choice.lower() == 'q':
                    return None
                
                scene_index = int(choice)
                if 0 <= scene_index < len(scene_list):
                    return scene_index
                else:
                    print(f"请输入 0-{len(scene_list)-1} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
            except KeyboardInterrupt:
                print("\n取消选择")
                return None
    
    def get_npc_names_from_scene(self, scene: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        从场景中获取NPC名称列表
        
        Args:
            scene: 场景数据，如果为None则使用当前场景
            
        Returns:
            List[str]: NPC名称列表
        """
        if scene is None:
            scene = self.current_scene
            
        if not scene:
            return []
        
        npc_names = []
        
        # 从不同可能的字段中提取NPC名称
        if "key_npcs" in scene:
            # demo.json 使用 key_npcs 字段
            key_npcs = scene["key_npcs"]
            if isinstance(key_npcs, list):
                # 过滤掉 "Player"
                npc_names.extend([npc for npc in key_npcs if npc != "Player"])
        
        if "npcs" in scene:
            if isinstance(scene["npcs"], list):
                npc_names.extend(scene["npcs"])
            elif isinstance(scene["npcs"], dict):
                npc_names.extend(scene["npcs"].keys())
        
        if "characters" in scene:
            if isinstance(scene["characters"], list):
                npc_names.extend(scene["characters"])
            elif isinstance(scene["characters"], dict):
                npc_names.extend(scene["characters"].keys())
        
        if "participants" in scene:
            participants = scene["participants"]
            if isinstance(participants, list):
                # 过滤掉 "Player"
                npc_names.extend([p for p in participants if p != "Player"])
            elif isinstance(participants, dict):
                npc_names.extend([k for k in participants.keys() if k != "Player"])
        
        # 去重并返回
        return list(set(npc_names))
    
    def enhance_game_state_for_player_mode(self, game_state: Dict[str, Any], scene: Optional[Dict[str, Any]] = None) -> None:
        """
        为player_involved模式增强游戏状态
        
        Args:
            game_state: 游戏状态字典
            scene: 场景数据，如果为None则使用当前场景
        """
        if scene is None:
            scene = self.current_scene
            
        if not scene:
            return
        
        # 添加场景特定信息
        if "scene_description" in scene:
            game_state["scene_description"] = scene["scene_description"]
        
        if "background" in scene:
            game_state["background"] = scene["background"]
        
        if "objectives" in scene:
            game_state["objectives"] = scene["objectives"]
        
        if "environment" in scene:
            game_state["environment"] = scene["environment"]
        
        # 添加场景元数据
        game_state["scene_metadata"] = {
            "title": scene.get("title", scene.get("name", "")),
            "type": scene.get("type", "conversation"),
            "difficulty": scene.get("difficulty", "normal")
        }
    
    def initialize_npc_only_mode(self, scene: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        初始化npc_only模式的游戏状态
        
        Args:
            scene: 场景数据，如果为None则使用当前场景
            
        Returns:
            Dict[str, Any]: 初始化的游戏状态
        """
        if scene is None:
            scene = self.current_scene
            
        if not scene:
            return {}
        
        # 创建简化的游戏状态
        game_state = {
            "mode": "npc_only",
            "scene_info": {
                "title": scene.get("title", scene.get("name", "")),
                "description": scene.get("description", ""),
                "background": scene.get("background", "")
            },
            "npcs": self.get_npc_names_from_scene(scene),
            "current_turn": 0,
            "conversation_history": []
        }
        
        # 添加场景特定的配置
        if "npc_only_config" in scene:
            config = scene["npc_only_config"]
            game_state.update(config)
        
        # 添加默认的对话设置
        if "conversation_settings" not in game_state:
            game_state["conversation_settings"] = {
                "max_turns": 20,
                "allow_interruption": True,
                "topic_drift_allowed": True
            }
        
        return game_state
    
    def _initialize_scene_status(self, scene_data: Dict[str, Any], scene_path: str) -> None:
        """
        初始化 scene_status 的场景数据
        
        Args:
            scene_data: 场景数据字典
            scene_path: 场景文件路径
        """
        # 设置场景数据
        self.scene_status.current_scene = scene_data
        self.scene_status.scene_file_path = scene_path
        
        # 提取场景环境信息
        self.scene_status.scene_environment = {
            "name": scene_data.get("title", scene_data.get("name", "")),
            "location": scene_data.get("location", ""),
            "description": scene_data.get("environment", ""),
            "interactive_objects": scene_data.get("interactive_environment_objects", [])
        }
        
        # 提取场景条件
        self.scene_status.scene_conditions = {
            "trigger": scene_data.get("trigger_conditions", {}),
            "end": scene_data.get("scene_end_state_reference", {})
        }
        
        # 提取NPC信息并初始化
        if hasattr(self.scene_status, '_extract_npc_information'):
            self.scene_status._extract_npc_information(scene_data)
        
        # 按路径加载时写入 SceneRegistry，便于各处统一读取当前场景
        scene_data_obj = SceneData.from_dict(scene_data)
        self.registry.set_current_scene_override(scene_data_obj)
    
    def get_current_scene(self) -> Optional[Dict[str, Any]]:
        """获取当前场景数据"""
        return self.current_scene
    
    def get_scene_info(self) -> Optional[Dict[str, Any]]:
        """获取当前场景的基本信息"""
        if not self.current_scene:
            return None
            
        return {
            "title": self.current_scene.get("title", self.current_scene.get("name", "")),
            "description": self.current_scene.get("description", ""),
            "npcs": self.get_npc_names_from_scene(),
            "type": self.current_scene.get("type", "conversation")
        }
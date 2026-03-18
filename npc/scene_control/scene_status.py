import sys
import os
import json
from typing import Any, Dict, List, Tuple, Optional
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..",".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)



from npc.scene_control.scene_data import SceneData, SceneRegistry

class SceneStatus:
    def __init__(self):
        """Initialize scene status controller"""
        self.current_scene: Dict = {}  # 当前场景数据
        self.active_npcs: List[Dict] = []  # 活跃NPC列表
        self.scene_environment: Dict = {}  # 场景环境信息
        self.scene_conditions: Dict = {}  # 场景条件
        # 修改场景文件夹路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        self.scene_folder_path = os.path.join(project_root, "data", "scene_data")  # 场景文件夹路径
        self.npc_states: Dict[str, Dict] = {}  # NPC状态
        self.scene_file_path = ""  # 当前场景文件路径
        self.all_scenes: List[Dict] = []  # 所有可用场景列表
        # 场景集合文件路径（包含所有场景的JSON文件，默认为demo.json）
        self.scenes_collection_file = os.path.join(self.scene_folder_path, "demo.json")
        self.registry = SceneRegistry()

    def load_all_scenes(self, scenes_file_path: Optional[str] = None) -> bool:
        """
        从场景集合文件中加载所有场景信息并注册到 SceneRegistry
        """
        try:
            # 如果提供了文件路径，使用它；否则使用默认路径
            file_path = scenes_file_path if scenes_file_path else self.scenes_collection_file
            
            with open(file_path, 'r', encoding='utf-8') as f:
                scenes_data = json.load(f)
            
            if isinstance(scenes_data, list):
                self.all_scenes = scenes_data
                self.registry.clear()
                for i, data in enumerate(scenes_data):
                    scene_data_obj = SceneData.from_dict(data)
                    self.registry.register_scene(i, scene_data_obj)
                print(f"成功从 {os.path.basename(file_path)} 加载了 {len(self.all_scenes)} 个场景并注册到 SceneRegistry")
                return True
            else:
                print(f"错误: {os.path.basename(file_path)} 应该包含场景列表")
                return False
                
        except Exception as e:
            print(f"加载场景集合文件失败 ({os.path.basename(file_path) if 'file_path' in locals() else 'unknown'}): {str(e)}")
            return False

    def get_all_scenes(self) -> List[Dict]:
        """
        获取所有可用场景列表
        
        Returns:
            List[Dict]: 所有场景的列表
        """
        if not self.all_scenes:
            self.load_all_scenes()
        return self.all_scenes

    def get_scene_by_index(self, index: int) -> Optional[Dict]:
        """
        根据索引获取场景数据
        
        Args:
            index: 场景索引（从0开始）
            
        Returns:
            Optional[Dict]: 场景数据，如果索引无效则返回None
        """
        if not self.all_scenes:
            self.load_all_scenes()
        
        if 0 <= index < len(self.all_scenes):
            return self.all_scenes[index]
        return None

    def get_scene_by_name(self, scene_name: str) -> Optional[Dict]:
        """
        根据场景名称获取场景数据
        
        Args:
            scene_name: 场景名称
            
        Returns:
            Optional[Dict]: 场景数据，如果找不到则返回None
        """
        if not self.all_scenes:
            self.load_all_scenes()
        
        for scene in self.all_scenes:
            if scene.get("name") == scene_name:
                return scene
        return None

    def get_scene_file_path(self, scene_name: str) -> str:
        """
        根据场景名称获取场景文件路径
        
        Args:
            scene_name: 场景文件名（例如 "scene2.json"）
            
        Returns:
            str: 场景文件的完整路径
        """
        # 如果提供的是完整路径，直接返回
        if os.path.isfile(scene_name):
            return scene_name
            
        # 使用相对路径查找场景文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        scene_path = os.path.join(project_root, "data", "scene_data", scene_name)
        
        if os.path.isfile(scene_path):
            return scene_path
                
        raise FileNotFoundError(f"找不到场景文件: {scene_name}，已尝试路径：{scene_path}")

    def load_scene(self, scene_identifier: str) -> bool:
        """
        加载场景数据
        
        Args:
            scene_identifier: 场景文件名、路径或场景名称
            
        Returns:
            bool: 是否成功加载场景
        """
        try:
            scene_data = None
            
            # 首先尝试从场景集合文件中查找场景
            if not self.all_scenes:
                self.load_all_scenes()
            
            # 尝试按场景名称查找
            scene_data = self.get_scene_by_name(scene_identifier)
            
            # 如果没找到，尝试作为文件路径处理
            if scene_data is None:
                try:
                    # 获取场景文件路径
                    scene_file_path = self.get_scene_file_path(scene_identifier)
                    
                    # 读取场景JSON文件
                    with open(scene_file_path, 'r', encoding='utf-8') as f:
                        scene_data = json.load(f)
                    
                    self.scene_file_path = scene_file_path
                except:
                    # 如果文件路径也不行，返回失败
                    print(f"无法找到场景: {scene_identifier}")
                    return False
            
            # 更新场景数据
            self.current_scene = scene_data
        
            # 提取场景环境信息
            self.scene_environment = {
                "name": scene_data.get("title", scene_data.get("name", "")),
                "location": scene_data.get("location", ""),
                "description": scene_data.get("environment", ""),
                "interactive_objects": scene_data.get("interactive_environment_objects", [])
            }
            
            # 提取场景条件
            self.scene_conditions = {
                "trigger": scene_data.get("trigger_conditions", {}),
                "end": scene_data.get("scene_end_state_reference", {})
            }
            
            # 提取NPC信息并初始化
            self._extract_npc_information(scene_data)
            self._initialize_npcs()
            
            print(f"Scene Loaded: {self.scene_environment['name']}")
            return True
            
        except Exception as e:
            print(f"Scene load failure: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def load_scene_by_index(self, scene_index: int) -> bool:
        """
        根据索引加载场景
        
        Args:
            scene_index: 场景索引（从0开始）
            
        Returns:
            bool: 是否成功加载场景
        """
        scene_data = self.get_scene_by_index(scene_index)
        if scene_data is None:
            print(f"无效的场景索引: {scene_index}")
            return False
        
        try:
            # 更新注册表中的当前场景
            self.registry.set_current_scene(scene_index)
            
            # 更新场景数据
            self.current_scene = scene_data
        
            # 提取场景环境信息
            self.scene_environment = {
                "name": scene_data.get("title", scene_data.get("name", "")),
                "location": scene_data.get("location", ""),
                "description": scene_data.get("environment", ""),
                "interactive_objects": scene_data.get("interactive_environment_objects", [])
            }
            
            # 提取场景条件
            self.scene_conditions = {
                "trigger": scene_data.get("trigger_conditions", {}),
                "end": scene_data.get("scene_end_state_reference", {})
            }
            
            # 提取NPC信息并初始化
            self._extract_npc_information(scene_data)
            self._initialize_npcs()
            
            print(f"Scene Loaded by index {scene_index}: {self.scene_environment['name']}")
            return True
            
        except Exception as e:
            print(f"Scene load failure: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _extract_npc_information(self, scene_data: Dict) -> None:
        """
        从场景数据中提取NPC信息
        
        Args:
            scene_data: 场景数据
        """
        self.active_npcs = []
        
        # 处理不同格式的interactive_npc
        if "interactive_npc" in scene_data:
            # 新格式：interactive_npc是字符串列表
            if isinstance(scene_data["interactive_npc"], list) and (len(scene_data["interactive_npc"]) == 0 or isinstance(scene_data["interactive_npc"][0], str)):
                npc_names = scene_data["interactive_npc"]
                
                # 如果有npc_emotion_pools，使用它来构建NPC信息
                if "npc_emotion_pools" in scene_data:
                    for name in npc_names:
                        if name in scene_data["npc_emotion_pools"]:
                            npc_info = {
                                "name": name,
                                "emotion_pool": scene_data["npc_emotion_pools"].get(name, [])
                            }
                            
                            # 添加目标信息
                            if "npc_purposes" in scene_data and name in scene_data["npc_purposes"]:
                                npc_info["goal"] = scene_data["npc_purposes"][name].get("goal", "")
                                
                            self.active_npcs.append(npc_info)
                else:
                    # 没有emotion_pools，创建简单的NPC信息
                    for name in npc_names:
                        self.active_npcs.append({"name": name})
            else:
                # 旧格式：interactive_npc是对象列表
                self.active_npcs = scene_data["interactive_npc"]
        # fallback: 尝试从 npc_emotion_pools 获取
        elif "npc_emotion_pools" in scene_data:
            for name, pool in scene_data["npc_emotion_pools"].items():
                npc_info = {"name": name, "emotion_pool": pool}
                
                # 添加目标信息
                if "npc_purposes" in scene_data and name in scene_data["npc_purposes"]:
                    npc_info["goal"] = scene_data["npc_purposes"][name].get("goal", "")
                    
                self.active_npcs.append(npc_info)
                
        if not self.active_npcs:
            print("警告: 场景中没有找到NPC信息")
            self.active_npcs = []
        else:
            print(f"Found {len(self.active_npcs)} NPC")
            for npc in self.active_npcs:
                print(f"NPC Name: {npc.get('name', 'Unknown')}")

    def _initialize_npcs(self) -> None:
        """
        初始化场景中的NPC
        """
        self.npc_states.clear()
        for npc in self.active_npcs:
            print("--------------------------------")
            print("NPC:")
            print(npc)
            print("--------------------------------")
            npc_name = npc["name"]
            npc_data = {
                "name": npc_name,
                "basic_information": {
                    "background": npc.get("background", ""),
                    "personality": npc.get("personality_traits", ""),
                    "goals": [emotion.get("goal", "") for emotion in npc.get("emotion_pool", [])],
                    "current_goal": npc.get("goal", ""),
                    "emotion_states": npc.get("emotion_pool", [])
                }
            }
            
            self.npc_states[npc_name] = {
                "npc_data": npc_data,
                "scene": self.scene_environment,
                "conversation_history": [],
                "messages": [],
                "player_input": ""
            }

    def get_active_npcs(self) -> List[Dict]:
        """获取活跃的NPC列表"""
        return self.active_npcs

    def get_npc_names(self) -> List[str]:
        """获取所有NPC的名称列表"""
        return [npc["name"] for npc in self.active_npcs]

    def get_npc_state(self, npc_name: str) -> Dict:
        """获取指定NPC的状态"""
        return self.npc_states.get(npc_name, {})

    def get_npc_data(self, npc_name: str) -> Optional[Dict]:
        """获取指定NPC的原始数据"""
        for npc in self.active_npcs:
            if npc["name"] == npc_name:
                return npc
        return None

    def get_game_state(self) -> Dict[str, Any]:
        """
        获取当前游戏状态
        
        Returns:
            Dict[str, Any]: 包含当前游戏状态的字典
        """
        game_state = {
            "recent_events": [self.scene_environment["name"]],
            "current_location": self.scene_environment["location"],
            "environment": self.scene_environment["description"],
            "npc_emotion_pool": {},
            "npc_emotions": {},
            "npc_goals": {},
            "npc_relationships": self.current_scene.get("npc_relationships", []),
            "npc_background": self.current_scene.get("npc_background", {}),
            "npc_purposes": self.current_scene.get("npc_purposes", {}),
            "key_npcs": self.current_scene.get("key_npcs", self.get_npc_names()),
            # 新增：场景特定的NPC信息（避免与npc_background混淆）
            "scene_npc_goals": {},
            "scene_npc_knowledge": {}
        }
        
        # 从interactive_npc中提取场景特定的目标和知识信息
        interactive_npcs = self.current_scene.get("interactive_npc", [])
        for npc_info in interactive_npcs:
            if isinstance(npc_info, dict):
                npc_name = npc_info.get("name")
                if npc_name:
                    # 提取场景特定的目标
                    if "goal" in npc_info:
                        game_state["scene_npc_goals"][npc_name] = npc_info["goal"]
                    
                    # 提取场景特定的知识
                    if "npc_background" in npc_info and "knowledge" in npc_info["npc_background"]:
                        game_state["scene_npc_knowledge"][npc_name] = npc_info["npc_background"]["knowledge"]
        
        # 调试信息
        print(f"[SceneStatus] 从场景读取 npc_relationships: {type(game_state['npc_relationships'])}, 数量: {len(game_state['npc_relationships']) if isinstance(game_state['npc_relationships'], (dict, list)) else 'N/A'}")
        print(f"[SceneStatus] 从场景读取 npc_background: {list(game_state['npc_background'].keys()) if isinstance(game_state['npc_background'], dict) else 'N/A'}")
        print(f"[SceneStatus] 从interactive_npc提取 scene_npc_goals: {list(game_state['scene_npc_goals'].keys())}")
        print(f"[SceneStatus] 从interactive_npc提取 scene_npc_knowledge: {list(game_state['scene_npc_knowledge'].keys())}")
        
        # 为每个NPC添加情绪和目标信息
        for npc in self.active_npcs:
            npc_name = npc["name"]
            game_state["npc_emotion_pool"][npc_name] = npc.get("emotion_pool", [])
            game_state["npc_emotions"][npc_name] = "0"  # 设置初始情绪ID
            game_state["npc_goals"][npc_name] = npc.get("goal", "")
            
        return game_state

    def update_npc_state(self, npc_name: str, new_state: Dict) -> None:
        """
        Update NPC states with scene-specific information
        """
        if npc_name in self.npc_states:
            self.npc_states[npc_name].update(new_state)

    def check_scene_transition(self, new_scene) -> Tuple[bool, str]:
        """
        检查是否需要切换场景（从bottom layer获取信号）
        返回：
            Tuple[bool, str]: (是否需要切换场景, 新场景名称)
        """
        # TODO: 实现与bottom layer的通信逻辑
        # 这里需要实现从bottom layer获取场景切换信号和新场景名称的逻辑
        # 暂时返回示例值
        return True, new_scene

    def get_scene_info(self) -> Dict:
        """
        Get current scene environment information
        """
        return {
            "scene": self.scene_environment,
            "npcs": self.get_active_npcs(),
            "conditions": self.scene_conditions,
            "npc_states": self.npc_states
        }

    def update_scene_state(self, new_state: Dict) -> None:
        """
        Update current scene state
        """
        if "environment" in new_state:
            self.scene_environment.update(new_state["environment"])
        
        if "npcs" in new_state:
            for npc_update in new_state["npcs"]:
                for npc in self.active_npcs:
                    if npc["name"] == npc_update["name"]:
                        npc.update(npc_update)


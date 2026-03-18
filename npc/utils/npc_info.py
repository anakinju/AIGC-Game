import os
import json
import copy
from typing import Dict, Any, List

class NPCInfoLoader:
    """
    NPC信息加载器 - 优化版
    支持根据不同的 Prompt 类型提取特定的 NPC 信息模块
    """
    def __init__(self, npc_name: str):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        self.npc_info_path = os.path.join(project_root, "data", "npc_info", "characters.json")
        
        self.npc_name = npc_name
        self.npc_info = self._load_npc_info()

    def _load_npc_info(self) -> Dict[str, Any]:
        try:
            with open(self.npc_info_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict) and 'characters' in data:
                for npc in data['characters']:
                    if npc.get('name') == self.npc_name:
                        return npc
            return {}
        except Exception as e:
            print(f"[NPCInfoLoader] Error loading {self.npc_name}: {e}")
            return {}

    # --- 针对不同 Prompt 的信息提取方法 ---

    def get_info_for_relationship_analysis(self) -> Dict[str, Any]:
        """提取用于分析关系和情绪的信息"""
        return {
            "personality": self.npc_info.get("personality_and_speech", {}),
            "social_rules": self.npc_info.get("social_and_emotional", {}),
            "world_attitude": self.npc_info.get("narrative_context", {}).get("world_attitude", "")
        }

    def get_info_for_intention(self) -> Dict[str, Any]:
        """提取用于生成 NPC 意图的信息"""
        return {
            "identity": self.npc_info.get("core_identity", {}),
            "personality": self.npc_info.get("personality_and_speech", {}), 
            "motivation": self.npc_info.get("motivation_and_drive", {}),
            "logic": self.npc_info.get("behavioral_logic", {}),
            "emotion_expressions": self.npc_info.get("social_and_emotional", {}).get("emotion_expressions", {}),
            "narrative_context": self.npc_info.get("narrative_context", {})
        }

    def get_info_for_casual_chat(self) -> Dict[str, Any]:
        """提取用于闲聊的信息 - 增强版，包含身份和行为逻辑以维持人设"""
        return {
            "identity": self.npc_info.get("core_identity", {}),
            "personality": self.npc_info.get("personality_and_speech", {}),
            "motivation": self.npc_info.get("motivation_and_drive", {}),
            "logic": self.npc_info.get("behavioral_logic", {}),
            "background": self.npc_info.get("narrative_context", {}).get("background", "")
        }

    def get_info_for_angry_response(self) -> Dict[str, Any]:
        """提取用于发火响应的信息 - 增强版，包含核心动机和处事原则"""
        return {
            "identity": self.npc_info.get("core_identity", {}),
            "personality": self.npc_info.get("personality_and_speech", {}),
            "motivation": self.npc_info.get("motivation_and_drive", {}),
            "logic": self.npc_info.get("behavioral_logic", {}),
            "triggers": self.npc_info.get("social_and_emotional", {}).get("triggers", ""),
            "emotion_expressions": self.npc_info.get("social_and_emotional", {}).get("emotion_expressions", {})
        }

    # --- 兼容旧接口 ---
    def get_npc_name(self) -> str:
        """获取 NPC 名称"""
        return self.npc_name

    def get_relationships(self) -> Dict[str, Any]:
        """获取 NPC 关系信息"""
        return self.npc_info.get("social_and_emotional", {}).get("relationships", {})

    def get_npc_info(self) -> Dict[str, Any]:
        return self.npc_info

    def get_basic_info(self) -> Dict[str, Any]:
        # 整合基础信息供旧系统使用
        core = self.npc_info.get("core_identity", {})
        ps = self.npc_info.get("personality_and_speech", {})
        md = self.npc_info.get("motivation_and_drive", {})
        nc = self.npc_info.get("narrative_context", {})
        
        return {
            "background": nc.get("background", ""),
            "personality": ", ".join(ps.get("traits", [])),
            "initial_goals": md.get("core_drive", ""),
            "nickname": core.get("nickname", ""),
            "current_status": core.get("status", "")
        }

def get_npc_info(npc_name: str) -> Dict[str, Any]:
    loader = NPCInfoLoader(npc_name)
    return loader.get_npc_info()

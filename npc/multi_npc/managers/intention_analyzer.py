#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图分析器 - 从 ChatEnvironment 中分离出的 NPC 意图和目标分析功能
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

from langchain_openai import ChatOpenAI


class IntentionAnalyzer:
    """意图分析器 - 处理 NPC 意图和目标的分析与更新"""
    
    def __init__(self, llm_model_name: str = "gpt-4o-mini"):
        """
        初始化意图分析器
        
        Args:
            llm_model_name: 使用的语言模型名称
        """
        self.llm = ChatOpenAI(model_name=llm_model_name)
    
    def analyze_npc_intentions_and_goals(self, history: List[Dict], scene_path: str, 
                                       npc_info_paths: List[str], llm_model_name: str = "gpt-4o-mini") -> Dict[str, Any]:
        """
        分析NPC的意图和目标
        
        Args:
            history: 对话历史
            scene_path: 场景文件路径
            npc_info_paths: NPC信息文件路径列表
            llm_model_name: 语言模型名称
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        try:
            # 加载场景信息
            scene_info = self._load_scene_info(scene_path)
            
            # 加载NPC信息
            npc_infos = self._load_npc_infos(npc_info_paths)
            
            # 构建分析提示
            analysis_prompt = self._build_intention_analysis_prompt(history, scene_info, npc_infos)
            
            # 使用LLM进行分析
            llm = ChatOpenAI(model_name=llm_model_name)
            response = llm.invoke(analysis_prompt)
            
            # 解析响应
            analysis_result = self._parse_intention_analysis_response(response.content)
            
            return {
                "success": True,
                "analysis": analysis_result,
                "scene_path": scene_path,
                "npc_count": len(npc_infos)
            }
            
        except Exception as e:
            print(f"意图分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scene_path": scene_path
            }
    
    def update_npc_intention_to_goal(self, history: List[Dict], scene_path: str, npc_info_paths: List[str]) -> Dict[str, Any]:
        """
        将NPC意图更新为具体目标
        
        Args:
            history: 对话历史
            scene_path: 场景文件路径
            npc_info_paths: NPC信息文件路径列表
            
        Returns:
            Dict[str, Any]: 更新结果
        """
        try:
            # 首先分析意图
            intention_analysis = self.analyze_npc_intentions_and_goals(history, scene_path, npc_info_paths)
            
            if not intention_analysis["success"]:
                return intention_analysis
            
            # 将意图转换为具体目标
            goals_update = self._convert_intentions_to_goals(intention_analysis["analysis"])
            
            return {
                "success": True,
                "intentions": intention_analysis["analysis"],
                "goals": goals_update,
                "scene_path": scene_path
            }
            
        except Exception as e:
            print(f"意图到目标更新失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "scene_path": scene_path
            }
    
    def _load_scene_info(self, scene_path: str) -> Dict[str, Any]:
        """
        加载场景信息
        
        Args:
            scene_path: 场景文件路径
            
        Returns:
            Dict[str, Any]: 场景信息
        """
        try:
            with open(scene_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载场景信息失败 {scene_path}: {e}")
            return {}
    
    def _load_npc_infos(self, npc_info_paths: List[str]) -> List[Dict[str, Any]]:
        """
        加载NPC信息
        
        Args:
            npc_info_paths: NPC信息文件路径列表
            
        Returns:
            List[Dict[str, Any]]: NPC信息列表
        """
        npc_infos = []
        
        for path in npc_info_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    npc_info = json.load(f)
                    npc_infos.append(npc_info)
            except Exception as e:
                print(f"加载NPC信息失败 {path}: {e}")
        
        return npc_infos
    
    def _build_intention_analysis_prompt(self, history: List[Dict], scene_info: Dict[str, Any], 
                                       npc_infos: List[Dict[str, Any]]) -> str:
        """
        构建意图分析提示
        
        Args:
            history: 对话历史
            scene_info: 场景信息
            npc_infos: NPC信息列表
            
        Returns:
            str: 分析提示
        """
        prompt_parts = [
            "请分析以下对话中每个NPC的意图和目标。",
            "",
            "场景信息:",
            json.dumps(scene_info, ensure_ascii=False, indent=2),
            "",
            "NPC信息:",
        ]
        
        for i, npc_info in enumerate(npc_infos):
            prompt_parts.append(f"NPC {i+1}:")
            prompt_parts.append(json.dumps(npc_info, ensure_ascii=False, indent=2))
            prompt_parts.append("")
        
        prompt_parts.extend([
            "对话历史:",
            json.dumps(history, ensure_ascii=False, indent=2),
            "",
            "请分析每个NPC的:",
            "1. 当前意图 (immediate intention)",
            "2. 长期目标 (long-term goal)", 
            "3. 情绪状态 (emotional state)",
            "4. 与其他角色的关系变化 (relationship changes)",
            "",
            "请以JSON格式返回分析结果。"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_intention_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        解析意图分析响应
        
        Args:
            response: LLM响应内容
            
        Returns:
            Dict[str, Any]: 解析后的分析结果
        """
        try:
            # 尝试直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果不是纯JSON，尝试提取JSON部分
            try:
                start = response.find('{')
                end = response.rfind('}') + 1
                if start != -1 and end != 0:
                    json_part = response[start:end]
                    return json.loads(json_part)
            except:
                pass
            
            # 如果都失败了，返回原始文本
            return {
                "raw_analysis": response,
                "parsed": False
            }
    
    def _convert_intentions_to_goals(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        将意图转换为具体目标
        
        Args:
            analysis: 意图分析结果
            
        Returns:
            Dict[str, Any]: 目标更新结果
        """
        goals_update = {}
        
        # 遍历分析结果中的每个NPC
        for npc_name, npc_analysis in analysis.items():
            if isinstance(npc_analysis, dict):
                npc_goals = []
                
                # 从意图中提取目标
                if "immediate_intention" in npc_analysis:
                    intention = npc_analysis["immediate_intention"]
                    if isinstance(intention, str):
                        npc_goals.append(f"短期目标: {intention}")
                
                if "long_term_goal" in npc_analysis:
                    goal = npc_analysis["long_term_goal"]
                    if isinstance(goal, str):
                        npc_goals.append(f"长期目标: {goal}")
                
                # 从情绪状态中推导目标
                if "emotional_state" in npc_analysis:
                    emotion = npc_analysis["emotional_state"]
                    if isinstance(emotion, str):
                        npc_goals.append(f"情绪目标: 维持或改善 {emotion} 状态")
                
                goals_update[npc_name] = npc_goals
        
        return goals_update
    
    def get_npc_current_intentions(self, npc_name: str, recent_history: List[Dict]) -> Dict[str, Any]:
        """
        获取特定NPC的当前意图
        
        Args:
            npc_name: NPC名称
            recent_history: 最近的对话历史
            
        Returns:
            Dict[str, Any]: NPC当前意图
        """
        try:
            # 过滤出与该NPC相关的对话
            npc_related_history = [
                msg for msg in recent_history 
                if msg.get("sender") == npc_name or npc_name in msg.get("content", "")
            ]
            
            if not npc_related_history:
                return {"intention": "观察和等待", "confidence": 0.5}
            
            # 构建简化的意图分析提示
            prompt = f"""
            基于以下对话历史，分析 {npc_name} 的当前意图：
            
            {json.dumps(npc_related_history, ensure_ascii=False, indent=2)}
            
            请简要分析该NPC的：
            1. 当前主要意图
            2. 可能的下一步行动
            3. 意图的确信度 (0-1)
            
            以JSON格式返回结果。
            """
            
            response = self.llm.invoke(prompt)
            return self._parse_intention_analysis_response(response.content)
            
        except Exception as e:
            print(f"获取NPC意图失败 {npc_name}: {e}")
            return {"intention": "未知", "confidence": 0.0, "error": str(e)}
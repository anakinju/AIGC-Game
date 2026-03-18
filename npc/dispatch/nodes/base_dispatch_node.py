import os
import sys
import logging
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import json

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.llm_factory import LLMFactory
from npc.utils.npc_info import NPCInfoLoader

logger = logging.getLogger(__name__)

class BaseDispatchNode(ABC):
    """
    Dispatch节点的基类，包含通用的初始化、LLM调用和prompt构建逻辑。
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        初始化基础dispatch节点
        
        Args:
            model_name: 使用的LLM模型名称
        """
        # 创建LLM实例
        self.llm = LLMFactory.create_chat_model(model_name=model_name)
        
        # NPC信息加载器缓存
        self._npc_info_cache: Dict[str, NPCInfoLoader] = {}
    
    def get_npc_info_loader(self, npc_name: str) -> NPCInfoLoader:
        """
        获取或创建NPC信息加载器
        
        Args:
            npc_name: NPC名称
        
        Returns:
            NPCInfoLoader实例
        """
        if npc_name not in self._npc_info_cache:
            self._npc_info_cache[npc_name] = NPCInfoLoader(npc_name)
        return self._npc_info_cache[npc_name]
    
    def get_npc_context(self, npc_name: str, context_type: str = "intention") -> Dict[str, Any]:
        """
        获取NPC上下文信息
        
        Args:
            npc_name: NPC名称
            context_type: 上下文类型 ("intention", "casual_chat", "angry", "basic")
        
        Returns:
            NPC上下文信息字典
        """
        loader = self.get_npc_info_loader(npc_name)
        
        if context_type == "intention":
            return loader.get_info_for_intention()
        elif context_type == "casual_chat":
            return loader.get_info_for_casual_chat()
        elif context_type == "angry":
            return loader.get_info_for_angry_response()
        elif context_type == "basic":
            return loader.get_basic_info()
        else:
            return loader.get_info_for_intention()
    
    def extract_json_from_response(self, response_content: str) -> Dict[str, Any]:
        """
        从LLM响应中提取JSON内容
        
        Args:
            response_content: LLM响应内容
        
        Returns:
            解析后的JSON字典，失败时返回空字典
        """
        try:
            content = response_content.strip()
            
            # 处理markdown代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif content.startswith("```") and content.endswith("```"):
                # 移除普通代码块标记
                lines = content.split('\n')
                if len(lines) > 2:
                    content = '\n'.join(lines[1:-1])
            
            # 尝试解析JSON
            return json.loads(content)
            
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse JSON from response: {e}")
            logger.error(f"Raw content: {response_content[:200]}...")
            return {}
    
    def build_character_section(self, npc_info: Dict[str, Any], npc_name: str) -> str:
        """
        构建角色信息部分
        
        Args:
            npc_info: NPC信息字典
            npc_name: NPC名称
        
        Returns:
            格式化的角色信息字符串
        """
        identity = npc_info.get("identity", {})
        personality = npc_info.get("personality", {})
        
        lines = [f"# ROLE: {npc_name}"]
        
        # 身份信息
        role = identity.get("role", "")
        status = identity.get("status", "")
        if role:
            lines.append(f"# IDENTITY: {role}")
        if status:
            lines.append(f"# STATUS: {status}")
        
        # 性格特征
        traits = personality.get("traits") or personality.get("personality_traits", [])
        if traits:
            traits_str = ", ".join(traits) if isinstance(traits, list) else str(traits)
            lines.append(f"# PERSONALITY: {traits_str}")
        
        # 说话风格
        speech_style = personality.get("speech_style", "")
        if speech_style:
            lines.append(f"# SPEECH_STYLE: {speech_style}")
        
        return "\n".join(lines)
    
    def build_motivation_section(self, npc_info: Dict[str, Any]) -> str:
        """
        构建动机信息部分
        
        Args:
            npc_info: NPC信息字典
        
        Returns:
            格式化的动机信息字符串
        """
        motivation = npc_info.get("motivation", {})
        if not motivation:
            return ""
        
        lines = ["# MOTIVATION:"]
        
        core_drive = motivation.get("core_drive", "")
        if core_drive:
            lines.append(f"- Core Drive: {core_drive}")
        
        obsession = motivation.get("obsession", "")
        if obsession:
            lines.append(f"- Obsession: {obsession}")
        
        short_term_goals = motivation.get("short_term_goals", [])
        if short_term_goals:
            goals_str = "; ".join(short_term_goals) if isinstance(short_term_goals, list) else str(short_term_goals)
            lines.append(f"- Short-term Goals: {goals_str}")
        
        return "\n".join(lines) if len(lines) > 1 else ""
    
    def build_logic_section(self, npc_info: Dict[str, Any]) -> str:
        """
        构建行为逻辑部分
        
        Args:
            npc_info: NPC信息字典
        
        Returns:
            格式化的行为逻辑字符串
        """
        logic = npc_info.get("logic", {})
        if not logic:
            return ""
        
        lines = ["# BEHAVIORAL_LOGIC:"]
        
        principles = logic.get("principles", [])
        if principles:
            principles_str = "; ".join(principles) if isinstance(principles, list) else str(principles)
            lines.append(f"- Principles: {principles_str}")
        
        on_ethics_conflict = logic.get("on_ethics_conflict", "")
        if on_ethics_conflict:
            lines.append(f"- On Ethics Conflict: {on_ethics_conflict}")
        
        return "\n".join(lines) if len(lines) > 1 else ""
    
    async def invoke_llm_async(self, prompt: str) -> str:
        """
        异步调用LLM
        
        Args:
            prompt: 输入提示
        
        Returns:
            LLM响应内容
        """
        try:
            if hasattr(self.llm, 'ainvoke'):
                response = await self.llm.ainvoke(prompt)
            else:
                response = self.llm.invoke(prompt)
            
            return response.content
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}", exc_info=True)
            return ""
    
    @abstractmethod
    async def process_async(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步处理方法，子类必须实现
        
        Args:
            state: 当前状态字典
        
        Returns:
            处理结果字典
        """
        pass
    
    @abstractmethod
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        构建prompt，子类必须实现
        
        Args:
            state: 当前状态字典
        
        Returns:
            格式化的prompt字符串
        """
        pass
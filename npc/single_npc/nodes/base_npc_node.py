import os
import sys
import re
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Awaitable, TypeVar
import logging
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

T = TypeVar('T')

def safe_run_async(coro: Awaitable[T]) -> T:
    """安全地运行异步协程"""
    try:
        loop = asyncio.get_running_loop()
        if loop and loop.is_running():
            raise RuntimeError("Cannot use safe_run_async in running event loop. Use await instead.")
    except RuntimeError:
        return asyncio.run(coro)

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.base_npc import NPCAgent
from npc.single_npc.tools.tool_manager import ToolManager
from npc.scene_control.scene_data import SceneRegistry
from npc.multi_npc.managers.emotion_manager import EmotionManager
from npc.single_npc.tools.emotion_tool import EmotionManagerTool
from npc.utils.npc_info_adapter import create_npc_loader
from npc.single_npc.tools.state_aware_tool import StateAwareToolManager

from npc.utils.constants import ChatMode

class BaseNPCNode:
    """
    NPC 节点的基类，包含通用的初始化、工具管理和状态处理逻辑。
    """
    def __init__(self, name: str, agent: NPCAgent, tool_manager: ToolManager,
                 enable_memory_system: bool = False,
                 simple_memory_file: str = "simple_memory.json"):
        self.name = name
        self.agent = agent
        self.tool_manager = tool_manager
        self.enable_memory_system = enable_memory_system
        
        
        # 初始化情绪管理器 (替换关系管理器)
        self.emotion_manager = EmotionManager()
        
        # 创建工具实例
        self.emotion_tool = EmotionManagerTool(emotion_manager=self.emotion_manager)
        
        # 初始化工具
        self._initialize_tools()

        # 加载 NPC 信息
        self.npc_info = create_npc_loader(self.name)
        
        # 创建状态感知工具管理器
        self.state_aware_tool_manager = StateAwareToolManager(self.name)

    def _set_system_prompt(self, state: Dict[str, Any]):
        """
        [Template Method] 设置NPC的基础系统提示。
        定义了构建 Prompt 的标准流程，子类可以通过覆盖特定钩子方法来定制内容。
        """
        chat_mode = state.get("chat_mode", ChatMode.PLAYER_INVOLVED)
        
        # 1. 获取基础数据
        full_info = self.npc_info.get_npc_info()
        static_info = full_info.get("static_info", full_info)
        dynamic_state = full_info.get("dynamic_state", {})
        
        # 2. 根据模式获取特定信息
        mode_info = self._get_mode_specific_info(chat_mode)
        
        # 3. 构建 Prompt 各部分
        prompt_parts = []
        prompt_parts.append(self._build_identity_section(mode_info, static_info))
        prompt_parts.append(self._build_dynamic_state_section(dynamic_state))
        prompt_parts.append(self._build_mode_instruction_section(chat_mode, mode_info, static_info))
        prompt_parts.append(self._build_scene_context_section(state))
        prompt_parts.append(self._build_constraints_section())
        
        base_prompt = "\n".join([p for p in prompt_parts if p])
        
        if hasattr(self.agent, 'state') and isinstance(self.agent.state, dict):
            self.agent.state["system_prompt"] = base_prompt
        
        return base_prompt

    def _get_mode_specific_info(self, chat_mode: str) -> Dict[str, Any]:
        """钩子方法：获取模式特定的信息"""
        if chat_mode == ChatMode.PLAYER_INVOLVED:
            return self.npc_info.get_info_for_intention()
        elif chat_mode == ChatMode.CASUAL_CHAT:
            return self.npc_info.get_info_for_casual_chat()
        elif chat_mode == ChatMode.ANGRY_CHAT:
            return self.npc_info.get_info_for_angry_response()
        return self.npc_info.get_basic_info()

    def _build_identity_section(self, info: Dict[str, Any], static_info: Dict[str, Any]) -> str:
        """构建身份信息部分"""
        nickname = (info.get("nickname") or 
                    info.get("identity", {}).get("nickname") or 
                    static_info.get("core_identity", {}).get("nickname") or 
                    self.name)
        
        traits = info.get("personality", {}).get("traits") or \
                 info.get("personality", {}).get("personality_traits") or \
                 static_info.get("personality_and_speech", {}).get("traits", [])
        
        background = info.get("background") or \
                     info.get("narrative_context", {}).get("background") or \
                     static_info.get("narrative_context", {}).get("background", "")
        
        return f"You are {self.name}.\nNickname: {nickname}\nPersonality: {', '.join(traits) if isinstance(traits, list) else traits}\nBackground: {background}"

    def _build_dynamic_state_section(self, dynamic_state: Dict[str, Any]) -> str:
        """构建动态状态部分"""
        parts = []
        emotion = dynamic_state.get("emotion")
        if emotion:
            parts.append(f"Current Emotion: {emotion}")
            
        goals = dynamic_state.get("goals", [])
        if goals:
            formatted_goals = [g if isinstance(g, str) else (g.get("description") or str(g)) for g in goals]
            parts.append(f"Current Goals: {'; '.join(formatted_goals)}")
        return "\n".join(parts)

    def _build_mode_instruction_section(self, chat_mode: str, info: Dict[str, Any], static_info: Dict[str, Any]) -> str:
        """构建模式特定指令部分"""
        if chat_mode == ChatMode.ANGRY_CHAT:
            principles = info.get("principles") or static_info.get("behavioral_logic", {}).get("principles", [])
            return f"\n[CURRENT STATUS: ANGRY]\nYour Principles: {'; '.join(principles)}\nTrigger: {info.get('triggers', 'Repeated irrelevant input')}\nINSTRUCTION: You are offended. Refuse information and demand an apology."
        elif chat_mode == ChatMode.CASUAL_CHAT:
            return "\n[CURRENT STATUS: CASUAL CHAT]\nINSTRUCTION: The player is off-topic. Respond naturally but keep it brief and stay in character."
        elif chat_mode == ChatMode.PLAYER_INVOLVED:
            motivation = info.get("motivation") or static_info.get("motivation_and_drive", {})
            logic = info.get("logic") or static_info.get("behavioral_logic", {})
            return f"\n[CURRENT STATUS: STORY INVOLVED]\nCore Drive: {motivation.get('core_drive', '')}\nBehavioral Logic: {'; '.join(logic.get('principles', []))}\nINSTRUCTION: Analyze the situation and generate an Intention JSON including your final response (utterance)."
        return ""

    def _build_scene_context_section(self, state: Dict[str, Any]) -> str:
        """构建场景上下文部分"""
        current_scene = SceneRegistry.get_current_scene()
        scene_context = current_scene.raw_data if current_scene else state.get("scene_context", {})
        npc_background = scene_context.get("npc_background", {}).get(self.name, {})
        
        parts = []
        if npc_background.get("goal"):
            parts.append(f"Immediate Scene Goal: {npc_background['goal']}")
        if npc_background.get("background"):
            parts.append(f"Additional Context: {npc_background['background']}")
        return "\n".join(parts)

    def _build_constraints_section(self) -> str:
        """构建通用约束部分"""
        return "\nCONVERSATION RULES:\n1. Stay in character at all times.\n2. Use only direct speech - no actions, narration, or asterisks (*).\n3. Keep responses concise (2-3 sentences)."

    def _initialize_tools(self):
        """初始化基础工具"""
        if hasattr(self.agent, 'tools'):
            self.agent.tools = []
        else:
            self.agent.tools = []
        self.tool_manager.register_tool(self.emotion_tool)

    def _update_tools_for_mode(self, chat_mode: str):
        """根据聊天模式更新可用工具"""
        self.agent.tools = []
        base_tools = self.tool_manager.get_all_tools()
        self.agent.tools.extend(base_tools)
        self.agent.tools.append(self.emotion_tool)

    def _extract_utterance_from_message(self, msg: Dict[str, Any]) -> str:
        """从消息中提取 utterance 内容，支持字符串和字典格式"""
        content = msg.get("content", "")
        if not content:
            return ""
        
        # 如果 content 本身就是字典，尝试提取 utterance
        if isinstance(content, dict):
            return content.get("utterance", str(content))
            
        content_str = str(content).strip()
        # 处理 JSON 字符串格式
        if content_str.startswith("{") or content_str.startswith("```json"):
            try:
                json_content = content_str
                if json_content.startswith("```json"):
                    json_content = json_content[7:]
                if json_content.endswith("```"):
                    json_content = json_content[:-3]
                json_content = json_content.strip()
                parsed = json.loads(json_content)
                if isinstance(parsed, dict) and "utterance" in parsed:
                    return parsed["utterance"]
                return content_str
            except (json.JSONDecodeError, ValueError):
                return content_str
        return content_str

    def process_history(self, context: List[Dict]) -> List[Dict]:        
        history = []
        if context:
            for msg in context:
                if isinstance(msg, dict):
                    content = self._extract_utterance_from_message(msg)
                    if content:
                        history.append({
                            "speaker": msg.get("speaker", "unknown"),
                            "content": content
                        })
        return history

    async def process_tools_async(self, state: Dict[str, Any], context: List[Dict]) -> None:
        """异步处理工具"""
        self._set_system_prompt(state)
        chat_mode = state.get("chat_mode", ChatMode.PLAYER_INVOLVED)
        self._update_tools_for_mode(chat_mode)
        
        print(f"DEBUG: [BaseNPCNode] {self.name} process_tools_async, mode={chat_mode}")
        
        # Process emotion for ALL modes to ensure background NPCs also react
        npc_emotion_processed = state.get(f"emotion_processed_{self.name}", False)
        print(f"DEBUG: [BaseNPCNode] {self.name} npc_emotion_processed={npc_emotion_processed}")
        if not npc_emotion_processed:
            # For non-player-involved modes, we still want to run a lightweight emotion check
            # so the Unity frontend can show their reactions.
            await self._process_with_tools_async(state, context)
            state[f"emotion_processed_{self.name}"] = True
            
        # Ensure state flag is set
        if chat_mode != ChatMode.PLAYER_INVOLVED:
            state["emotion_processed"] = True

    async def _process_with_tools_async(self, state: Dict[str, Any], context: List[Dict]) -> None:
        """异步处理消息并更新状态"""
        # Always process emotion to capture reactions even if not the primary responder
        await self._process_emotion_tool_async(state, context)

    async def _process_emotion_tool_async(self, state: Dict[str, Any], context: List[Dict]) -> Dict[str, Any]:
        """异步处理情绪工具"""
        try:
            chat_mode = state.get("chat_mode", ChatMode.PLAYER_INVOLVED)
            
            # 只有在 PLAYER_INVOLVED 模式下才进行情绪分析
            if chat_mode != ChatMode.PLAYER_INVOLVED:
                print(f"[BaseNPCNode] {self.name} skipped emotion analysis: non-PLAYER_INVOLVED mode ({chat_mode})")
                return {"status": "skipped", "reason": f"non-player mode: {chat_mode}"}

            # 确定 target_npc：首先检查 state 中的 target_npc，如果没有则从 responders 获取第一个
            target_npc = state.get("target_npc")
            if not target_npc:
                responders = state.get("responders", [])
                target_npc = responders[0] if responders else None
            
            # 如果还是没有 target，从 message 的 tags 中获取
            if not target_npc and context:
                last_msg = context[-1] if context else {}
                tags = last_msg.get("tags", {})
                target_npc = tags.get("target")
            
            # Determine if this NPC is a background NPC (not the primary target)
            is_background = (target_npc != self.name)
            
            # Background NPCs 使用简单分析器 (SimpleEmotionAnalyzer)
            if is_background:
                print(f"[BaseNPCNode] {self.name} (background) using SimpleEmotionAnalyzer")
            
            print(f"[BaseNPCNode] {self.name} emotion analysis - target_npc: {target_npc}, is_background: {is_background}")
            print(f"[BaseNPCNode] {self.name} starting emotion analysis ({'BG' if is_background else 'Target'})...")

            if "scene_context" in state and isinstance(state.get("scene_context"), dict):
                npc_background = state["scene_context"].get("npc_background", None)
                if isinstance(npc_background, dict) and len(npc_background) > 0:
                    if self.name not in npc_background:
                        print(f"[BaseNPCNode] {self.name} skipped emotion analysis: not in npc_background")
                        return {"status": "skipped", "reason": "npc not in npc_background"}

            # 确保传递最新的 message_store
            result = await self.emotion_tool._arun(self.name, state, is_background=is_background)
            print(f"[BaseNPCNode] {self.name} ({'BG' if is_background else 'Target'}) emotion analysis result: {result.get('emotion')} (Intensity: {result.get('intensity')})")
            return result
        except Exception as e:
            logger.error(f"Error processing emotion tool: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    def _clean_response(self, response: str) -> str:
        """清理响应中的动作描述和格式问题"""
        response = re.sub(r'\*[^*]*\*', '', response)
        response = re.sub(r'\s+', ' ', response)
        response = response.strip()
        if response.startswith(f"{self.name}:"):
            response = response[len(f"{self.name}:"):].strip()
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        return response

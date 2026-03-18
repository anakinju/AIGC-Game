import os
import sys
import logging
import asyncio
from typing import Dict, List, Any
from npc.utils.base_npc import NPCAgent
from npc.single_npc.tools.tool_manager import ToolManager
from npc.utils.message_processor import MessageProcessor

# 导入新定义的节点类
from npc.single_npc.nodes.base_npc_node import BaseNPCNode
from npc.single_npc.nodes.player_involved_node import PlayerInvolvedNode
from npc.single_npc.nodes.casual_chat_node import CasualChatNode
from npc.single_npc.nodes.npc_angry_node import NPCAngryNode

logger = logging.getLogger(__name__)

class NPCNode:
    """
    LangGraph NPC 节点。
    根据当前 state 中的 chat_mode 和 angry 状态，调度到不同的子节点处理逻辑。
    """
    
    def __init__(self, name: str, agent: NPCAgent, tool_manager: ToolManager, 
                 enable_memory_system: bool = False):
        self.name = name
        self.agent = agent
        self.tool_manager = tool_manager
        self.enable_memory_system = enable_memory_system
        self.message_processor = MessageProcessor()
        
        # 初始化各个子节点逻辑类
        self.nodes = {
            "player_involved": PlayerInvolvedNode(name, agent, tool_manager, enable_memory_system),
            "casual_chat": CasualChatNode(name, agent, tool_manager, enable_memory_system),
            "angry": NPCAngryNode(name, agent, tool_manager, enable_memory_system)
        }

    def _get_active_node(self, state: Dict[str, Any]):
        """根据状态选择当前活跃的逻辑节点"""
        chat_mode = state.get("chat_mode", "player_involved")
        
        if chat_mode == "angry_chat":
            return self.nodes["angry"]
        
        return self.nodes.get(chat_mode, self.nodes["player_involved"])

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 同步调用接口 - 强制使用异步逻辑以确保工具被 await"""
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                # 如果在运行中的 loop，必须使用 run_coroutine_threadsafe 或类似机制
                # 但在 LangGraph 中，通常建议直接通过 workflow.ainvoke 调用异步版本
                return asyncio.run_coroutine_threadsafe(self.__call_async__(state), loop).result()
            else:
                return asyncio.run(self.__call_async__(state))
        except RuntimeError:
            return asyncio.run(self.__call_async__(state))
        except Exception as e:
            logger.error(f"Error in NPCNode.__call__: {e}")
            return state

    async def __call_async__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """LangGraph 异步调用接口"""
        state = self._preprocess_state(state)
        chat_group = state.get("chat_group", [])
        print(f"DEBUG: [NPCNode] {self.name} __call_async__, chat_group={chat_group}")
        if self.name not in chat_group:
            print(f"DEBUG: [NPCNode] {self.name} not in chat_group, skipping.")
            return state

        active_node = self._get_active_node(state)
        message_store = state.get("message_store", [])
        
        # 显式打印调试信息，确认进入了工具处理流程
        print(f"DEBUG: [NPCNode] {self.name} processing tools for mode: {state.get('chat_mode')}")
        print(f"DEBUG: [NPCNode] {self.name} message_store length before tools: {len(message_store)}")
        if message_store:
            print(f"DEBUG: [NPCNode] {self.name} last message: {message_store[-1]}")
        await active_node.process_tools_async(state, message_store)

        if state.get("emotion_only", False):
            return state

        # Player Involved logic: only the primary responders or addressed NPC should generate a response
        # Background NPCs in this mode still run emotion analysis but don't generate text
        chat_mode = state.get("chat_mode")
        if chat_mode == "player_involved":
            primaries = state.get("primary_responders", [])
            # If I'm not a primary responder, I only do emotion analysis (already done above)
            if primaries and self.name not in primaries:
                processed_npcs = state.get("processed_npcs", [])
                if self.name not in processed_npcs:
                    processed_npcs.append(self.name)
                return {**state, "processed_npcs": processed_npcs}

        # 按照workflow处理：target_npc优先处理并生成回复，background NPCs只做情绪分析
        target_npc = state.get("target_npc")
        responders = state.get("responders", [])
        
        # 调试信息
        print(f"[NPCNode] {self.name} decision logic - target_npc: {target_npc}, responders: {responders}")
        print(f"[NPCNode] {self.name} is_target: {self.name == target_npc}, in_responders: {self.name in responders}")
        
        # 核心逻辑：如果我是 target_npc，或者没有明确 target_npc 时我是第一个 responder
        should_respond = False
        if target_npc:
            if self.name == target_npc:
                should_respond = True
        elif responders and self.name == responders[0]:
            should_respond = True

        if should_respond:
            # Target NPC: 情绪分析 + 生成回复 (调用player_involved_node)
            print(f"[NPCNode] {self.name} (target) generating response via player_involved_node")
            return await self._generate_and_format_response_async(state, active_node)
        elif self.name in responders:
            # Background NPC: 仅情绪分析，不生成回复
            processed_npcs = state.get("processed_npcs", [])
            if self.name not in processed_npcs:
                processed_npcs.append(self.name)
            print(f"[NPCNode] {self.name} (background) completed simple emotion analysis only")
            return {**state, "processed_npcs": processed_npcs}
        
        return state

    def _preprocess_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """通用的消息存储和标记预处理"""
        message_store = state.get("message_store", [])
        chat_group = state.get("chat_group", [])
        target_npcs = state.get("responders", []) or state.get("message_target", [])
        
        # 调试：检查sender信息
        original_sender = state.get("original_sender", "unknown")
        print(f"DEBUG: [NPCNode] {self.name} _preprocess_state - original_sender: '{original_sender}'")
        print(f"DEBUG: [NPCNode] {self.name} _preprocess_state - need_add_initial_message: {state.get('need_add_initial_message', False)}")
        print(f"DEBUG: [NPCNode] {self.name} _preprocess_state - need_add_player_message: {state.get('need_add_player_message', False)}")
        
        state["message_tags"] = self.message_processor.create_message_tags(
            original_sender, target_npcs, chat_group
        )
        
        if state.get("need_add_initial_message"):
            entry = self.message_processor.format_message_entry(
                state["original_sender"], state["original_message"], target_npcs, chat_group
            )
            message_store.append(entry)
            state["need_add_initial_message"] = False
            
        if state.get("need_add_player_message"):
            sender = "Player" if original_sender.lower() == "player" else original_sender
            print(f"DEBUG: [NPCNode] {self.name} adding player message - sender: '{sender}', original_sender: '{original_sender}'")
            entry = self.message_processor.format_message_entry(
                sender, state["original_message"], target_npcs, chat_group
            )
            message_store.append(entry)
            print(f"DEBUG: [NPCNode] {self.name} added message entry: {entry}")
            state["need_add_player_message"] = False
            
        return state

    def _generate_and_format_response(self, state: Dict[str, Any], active_node: BaseNPCNode) -> Dict[str, Any]:
        """同步生成并格式化响应"""
        return asyncio.run(self._generate_and_format_response_async(state, active_node))

    async def _generate_and_format_response_async(self, state: Dict[str, Any], active_node: BaseNPCNode) -> Dict[str, Any]:
        """异步生成并格式化响应"""
        message_store = state.get("message_store", [])
        chat_mode = state.get("chat_mode", "player_involved")
        npc_state = state.get("npc_state", {})
        angry_level = int(npc_state.get("angry_level", 0))
        
        # 调度响应生成
        if isinstance(active_node, PlayerInvolvedNode):
            cooling_down = (angry_level == 1)
            response_dict = await active_node.generate_response_async(state, message_store, cooling_down=cooling_down)
        elif isinstance(active_node, NPCAngryNode):
            response_dict = await active_node.generate_response_async(state, message_store)
        else:
            # 闲聊和 NPC-only 模式暂时使用基类的 generate_response (需在子类实现或在此处理)
            # 这里简化处理，后续可继续完善子类
            prompt = ""
            if isinstance(active_node, CasualChatNode):
                prompt = active_node._build_casual_chat_prompt(state, active_node.process_history(message_store))
            
            # 调用 LLM 生成文本
            response_text = await self._call_llm_async(state, prompt)
            response_dict = {
                "action": {"id": "RESPOND"},
                "utterance": response_text,
                "real_intent": "General response"
            }



        # 统一格式化输出
        utterance = response_dict.get("utterance", "...")
        entry = self.message_processor.format_message_entry(
            self.name, response_dict, state.get("message_target", []), state.get("chat_group", [])
        )
        message_store.append(entry)
        
        processed_npcs = state.get("processed_npcs", [])
        if self.name not in processed_npcs: processed_npcs.append(self.name)

        return {
            **state,
            "message": utterance,
            "message_store": message_store,
            "sender": self.name,
            "processed_npcs": processed_npcs,
            "last_intention": response_dict
        }

    async def _call_llm_async(self, state: Dict[str, Any], prompt: str) -> str:
        """通用的 LLM 调用"""
        from langchain.schema import SystemMessage, HumanMessage
        # 使用节点生成的最新系统提示
        system_prompt = self.agent.state.get("system_prompt", "")
        if not system_prompt:
            system_prompt = self.agent.get_system_prompt()
            
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        if hasattr(self.agent.llm, 'ainvoke'):
            response = await self.agent.llm.ainvoke(messages)
        else:
            response = self.agent.llm.invoke(messages)
        return response.content.strip()

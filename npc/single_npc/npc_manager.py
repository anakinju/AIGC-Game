import logging
from typing import Dict, List, Any, Optional
from npc.single_npc.nodes.base_npc_node import BaseNPCNode
from npc.single_npc.nodes.player_involved_node import PlayerInvolvedNode
from npc.single_npc.nodes.casual_chat_node import CasualChatNode
from npc.single_npc.nodes.npc_only_node import NPCOnlyNode
from npc.single_npc.nodes.npc_angry_node import NPCAngryNode

logger = logging.getLogger(__name__)

class NPCManager(BaseNPCNode):
    """
    Legacy NPCManager class, now refactored to use modular nodes.
    This class is kept for backward compatibility.
    """
    def __init__(self, name: str, agent: Any, tool_manager: Any,
                 enable_memory_system: bool = False,
                 simple_memory_file: str = "simple_memory.json"):
        super().__init__(name, agent, tool_manager, enable_memory_system, simple_memory_file)
        
        # 实例化各个模式的逻辑类
        self.player_involved_node = PlayerInvolvedNode(name, agent, tool_manager, enable_memory_system)
        self.casual_chat_node = CasualChatNode(name, agent, tool_manager, enable_memory_system)
        self.npc_only_node = NPCOnlyNode(name, agent, tool_manager, enable_memory_system)
        self.npc_angry_node = NPCAngryNode(name, agent, tool_manager, enable_memory_system)

    async def generate_response_async(self, state: Dict[str, Any], context: List[Dict]) -> Dict[str, Any]:
        """
        Legacy dispatch method.
        """
        npc_state = state.get("npc_state", {})
        angry_level = int(npc_state.get("angry_level", 0))
        is_angry = npc_state.get("angry", False) and angry_level >= 3
        
        if is_angry:
            return await self.npc_angry_node.generate_response_async(state, context)
        
        chat_mode = state.get("chat_mode", "player_involved")
        
        if chat_mode == "player_involved":
            cooling_down = (angry_level == 1)
            return await self.player_involved_node.generate_response_async(state, context, cooling_down=cooling_down)
        elif chat_mode == "casual_chat":
            prompt = self.casual_chat_node._build_casual_chat_prompt(state, self.process_history(context))
            response_text = await self._call_llm_async(state, prompt)
            return {"action": {"id": "RESPOND"}, "utterance": response_text, "real_intent": "Casual chat"}
        elif chat_mode == "angry_chat":
            return await self.npc_angry_node.generate_response_async(state, context)
        elif chat_mode == "npc_only":
            prompt = self.npc_only_node._build_npc_only_prompt(state, self.process_history(context))
            response_text = await self._call_llm_async(state, prompt)
            return {"action": {"id": "RESPOND"}, "utterance": response_text, "real_intent": "NPC interaction"}
        
        return {"action": {"id": "EVADE"}, "utterance": "...", "real_intent": "Unknown mode"}

    async def _call_llm_async(self, state: Dict[str, Any], prompt: str) -> str:
        from langchain.schema import SystemMessage, HumanMessage
        # 尝试从 agent.state 获取由节点生成的系统提示
        system_prompt = getattr(self.agent, 'state', {}).get("system_prompt", "")
        if not system_prompt:
            system_prompt = self.agent.get_system_prompt()
            
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]
        if hasattr(self.agent.llm, 'ainvoke'):
            response = await self.agent.llm.ainvoke(messages)
        else:
            response = self.agent.llm.invoke(messages)
        return response.content.strip()


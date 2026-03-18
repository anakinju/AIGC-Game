import json
import logging
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, SystemMessage
from npc.single_npc.nodes.base_npc_node import BaseNPCNode
from npc.scene_control.scene_data import SceneRegistry

logger = logging.getLogger(__name__)

class NPCAngryNode(BaseNPCNode):
    """
    专门处理 NPC 生气状态（Angry）的节点。
    拒绝透露信息，要求道歉。
    """
    
    async def generate_response_async(self, state: Dict[str, Any], context: List[Dict]) -> Dict[str, Any]:
        """异步生成发火响应"""
        try:
            # 1. 构建基础系统提示
            base_system_prompt = self._set_system_prompt(state)
            
            # 2. 构建发火专用提示
            prompt = self._build_angry_response_prompt(state, context)
            
            messages = [
                SystemMessage(content=base_system_prompt), 
                HumanMessage(content=prompt)
            ]
            
            if hasattr(self.agent.llm, 'ainvoke'):
                response = await self.agent.llm.ainvoke(messages)
            else:
                response = self.agent.llm.invoke(messages)
            
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:]
            if content.endswith("```"): content = content[:-3]
            content = content.strip()
            
            try:
                return json.loads(content)
            except:
                return {
                    "action": {"id": "INTIMIDATE"},
                    "utterance": "Enough! I have no more patience for your nonsense. Get out of my sight!",
                    "real_intent": "Expelling the player due to repeated irrelevance"
                }
        except Exception as e:
            logger.error(f"Error in NPCAngryNode: {e}", exc_info=True)
            return {"action": {"id": "INTIMIDATE"}, "utterance": "I've had enough. Leave now!", "real_intent": "Forcefully ending conversation"}

    def _build_angry_response_prompt(self, state: Dict[str, Any], conversation_history: List[Dict]) -> str:
        """构建发火响应的提示"""
        angry_info = self.npc_info.get_info_for_angry_response()
        identity = angry_info.get("identity", {})
        personality_info = angry_info.get("personality", {})
        motivation = angry_info.get("motivation", {})
        logic = angry_info.get("logic", {})
        triggers = angry_info.get("triggers", "")
        
        current_scene = SceneRegistry.get_current_scene()
        scene_context = current_scene.raw_data if current_scene else state.get("scene_context", {})
        npc_background = scene_context.get("npc_background", {}).get(self.name, {})
        
        # 权力关系判断
        role = identity.get("role", "")
        status = identity.get("status", "")
        role_hint = (npc_background.get("role_relative_to_player") or npc_background.get("role") or 
                     (scene_context.get("npc_roles") or {}).get(self.name) or role)
        
        is_superior = any(k in str(role_hint).lower() or k in str(status).lower() 
                         for k in ["boss", "superior", "officer", "employer", "上级", "上司", "长官", "老板", "主管"])
        
        # 历史与意图判断
        history_lines = [f"{m.get('speaker', 'unknown')}: {self._extract_utterance_from_message(m)}" for m in conversation_history[-5:]]
        last_player_content = self._extract_utterance_from_message(conversation_history[-1]) if conversation_history else ""
        last_player = str(last_player_content).lower()
        player_asking_info = any(w in last_player for w in ["where", "what", "how", "why", "tell", "know", "information", "secret", "哪里", "什么", "怎么", "为什么", "告诉", "知道"])
        
        if is_superior:
            instruction = f"You are the player's {status or 'superior'}. **Maintain absolute authority**. Threaten consequences (fire, expel, report) if they don't apologize. Do NOT reveal info."
        elif player_asking_info:
            instruction = "Player is asking for secrets. **Refuse to share**. Tell them you won't discuss anything until they apologize. Stay firm."
        else:
            instruction = "**Refuse to engage**. Demand an apology first."
            
        traits = personality_info.get("traits") or personality_info.get("personality_traits", [])
        personality_str = ", ".join(traits) if isinstance(traits, list) else str(traits)

        prompt_parts = [
            "# NPC ANGRY RESPONSE — REFUSE INFO & DEMAND APOLOGY",
            "The player has repeatedly wasted your time. You are now **Wary** and **Angry**.",
            "\n## YOUR CHARACTER",
            f"**Name**: {self.name}",
            f"**Identity**: {role} ({status})",
            f"**Personality**: {personality_str}",
            f"**Core Motivation**: {motivation.get('core_drive', '')}",
            f"**Angry Triggers**: {triggers}",
            "\n## MANDATORY BEHAVIOR",
            "1. **Do NOT reveal** key plot or secret info.",
            "2. **Demand an apology** before cooperation.",
            f"3. **Instruction**: {instruction}",
            "\nRECENT CONVERSATION:",
            "\n".join(history_lines),
            "\n## JSON OUTPUT ONLY",
            "{\n  \"action\": {\"id\": \"INTIMIDATE\"},\n  \"utterance\": \"Your response: refuse info and demand apology\",\n  \"real_intent\": \"Refusing information until apology\"\n}"
        ]

        return "\n".join(prompt_parts)

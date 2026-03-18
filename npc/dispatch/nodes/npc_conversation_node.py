import logging
from typing import Dict, List, Any, Optional
from .base_dispatch_node import BaseDispatchNode

logger = logging.getLogger(__name__)

class NPCConversationNode(BaseDispatchNode):
    """
    处理NPC间对话的节点。
    支持两种模式：发起对话和响应对话。
    """
    
    async def process_async(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步处理NPC对话
        
        Args:
            state: 包含对话信息的状态字典
                - conversation_mode: "initiate" | "respond"
                - requester_npc: 发起对话的NPC
                - target_npc: 目标NPC
                - inquiry_topic: 询问的话题
                - dialogue_history: 对话历史
                - current_turn: 当前轮次
                - relationship_between_npcs: NPC间关系
        
        Returns:
            对话结果字典:
            - dialogue_history: 更新后的对话历史
            - current_turn: 更新后的轮次
        """
        try:
            conversation_mode = state.get("conversation_mode", "initiate")
            
            if conversation_mode == "initiate":
                return await self._handle_initiate_conversation(state)
            elif conversation_mode == "respond":
                return await self._handle_respond_conversation(state)
            else:
                logger.error(f"Unknown conversation mode: {conversation_mode}")
                return self._create_default_response(state)
                
        except Exception as e:
            logger.error(f"Error in NPCConversationNode: {e}", exc_info=True)
            return self._create_default_response(state)
    
    async def _handle_initiate_conversation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理发起对话的情况"""
        prompt = self.build_initiate_prompt(state)
        response_content = await self.invoke_llm_async(prompt)
        
        if not response_content:
            response_content = "Let me ask you about something..."
        
        requester_npc = state.get('requester_npc', 'Unknown')
        current_turn = state.get('current_turn', 0)
        
        new_message = {"role": requester_npc, "content": response_content.strip()}
        
        return {
            "dialogue_history": [new_message],
            "current_turn": current_turn + 1
        }
    
    async def _handle_respond_conversation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """处理响应对话的情况"""
        prompt = self.build_respond_prompt(state)
        response_content = await self.invoke_llm_async(prompt)
        
        if not response_content:
            response_content = "I see... let me think about that."
        
        target_npc = state.get('target_npc', 'Unknown')
        
        new_message = {"role": target_npc, "content": response_content.strip()}
        
        return {
            "dialogue_history": [new_message]
        }
    
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        构建对话prompt（通用接口）
        
        Args:
            state: 当前状态字典
        
        Returns:
            格式化的prompt字符串
        """
        conversation_mode = state.get("conversation_mode", "initiate")
        
        if conversation_mode == "initiate":
            return self.build_initiate_prompt(state)
        else:
            return self.build_respond_prompt(state)
    
    def build_initiate_prompt(self, state: Dict[str, Any]) -> str:
        """
        构建发起对话的prompt
        """
        requester_npc = state.get('requester_npc', 'Unknown')
        target_npc = state.get('target_npc', 'Unknown')
        inquiry_topic = state.get('inquiry_topic', 'general information')
        
        # 获取发起者的NPC信息
        npc_info = self.get_npc_context(requester_npc, "intention")
        
        # 构建prompt各个部分
        character_section = self.build_character_section(npc_info, requester_npc)
        motivation_section = self.build_motivation_section(npc_info)
        logic_section = self.build_logic_section(npc_info)
        conversation_context = self._build_initiate_context(state)
        guidance_section = self._build_initiate_guidance()
        
        prompt_parts = [
            character_section,
            motivation_section,
            logic_section,
            conversation_context,
            guidance_section
        ]
        
        return "\n\n".join([part for part in prompt_parts if part])
    
    def build_respond_prompt(self, state: Dict[str, Any]) -> str:
        """
        构建响应对话的prompt
        """
        target_npc = state.get('target_npc', 'Unknown')
        requester_npc = state.get('requester_npc', 'Unknown')
        
        # 获取响应者的NPC信息
        npc_info = self.get_npc_context(target_npc, "intention")
        
        # 构建prompt各个部分
        character_section = self.build_character_section(npc_info, target_npc)
        motivation_section = self.build_motivation_section(npc_info)
        logic_section = self.build_logic_section(npc_info)
        conversation_context = self._build_respond_context(state)
        guidance_section = self._build_respond_guidance()
        
        prompt_parts = [
            character_section,
            motivation_section,
            logic_section,
            conversation_context,
            guidance_section
        ]
        
        return "\n\n".join([part for part in prompt_parts if part])
    
    def _build_initiate_context(self, state: Dict[str, Any]) -> str:
        """构建发起对话的上下文信息"""
        target_npc = state.get('target_npc', 'Unknown')
        inquiry_topic = state.get('inquiry_topic', 'general information')
        relationship = state.get('relationship_between_npcs', 'Neutral')
        dialogue_history = state.get('dialogue_history', [])
        
        context_lines = [
            f"# CONVERSATION OBJECTIVE",
            f"**Target NPC**: {target_npc}",
            f"**Your Goal**: Find out about '{inquiry_topic}' from {target_npc}",
            f"**Your Relationship with {target_npc}**: {relationship}"
        ]
        
        if dialogue_history:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" 
                                    for msg in dialogue_history[-5:]])
            context_lines.extend([
                "",
                "# CONVERSATION HISTORY",
                history_text
            ])
        
        return "\n".join(context_lines)
    
    def _build_respond_context(self, state: Dict[str, Any]) -> str:
        """构建响应对话的上下文信息"""
        requester_npc = state.get('requester_npc', 'Unknown')
        target_npc = state.get('target_npc', 'Unknown')
        relationship = state.get('relationship_between_npcs', 'Neutral')
        dialogue_history = state.get('dialogue_history', [])
        
        # 获取目标NPC的知识和秘密信息
        npc_info = self.get_npc_context(target_npc, "intention")
        knowledge = npc_info.get("narrative_context", {}).get("background", "")
        
        context_lines = [
            f"# CONVERSATION CONTEXT",
            f"**Speaking with**: {requester_npc}",
            f"**Your Relationship with {requester_npc}**: {relationship}"
        ]
        
        if knowledge:
            context_lines.extend([
                "",
                f"# YOUR KNOWLEDGE/SECRETS",
                knowledge[:300] + ("..." if len(knowledge) > 300 else "")
            ])
        
        if dialogue_history:
            history_text = "\n".join([f"{msg['role']}: {msg['content']}" 
                                    for msg in dialogue_history[-5:]])
            context_lines.extend([
                "",
                "# CONVERSATION HISTORY",
                history_text
            ])
        
        return "\n".join(context_lines)
    
    def _build_initiate_guidance(self) -> str:
        """构建发起对话的指导原则"""
        return """# CONVERSATION GUIDANCE

You need to approach the other NPC to learn information. Consider:

1. **Approach Strategy**: 
   - Be natural and not overly direct if your personality is cautious
   - Use your relationship history to determine the right tone
   - Consider starting with small talk if appropriate

2. **Information Gathering**: 
   - Don't immediately ask for sensitive information
   - Build rapport first if the relationship isn't strong
   - Be persistent but respectful of boundaries

3. **Character Consistency**: 
   - Stay true to your personality and speech style
   - Use language and tone that fits your status and role
   - Remember your own motivations and goals

**Output**: Provide only your natural dialogue response. Do NOT use actions or narration."""
    
    def _build_respond_guidance(self) -> str:
        """构建响应对话的指导原则"""
        return """# RESPONSE GUIDANCE

The other NPC is talking to you. Decide how to respond based on:

1. **Information Sharing**: 
   - Consider your relationship before revealing secrets
   - Strong positive relationship: More willing to share
   - Weak/negative relationship: More guarded and cautious
   - Neutral relationship: Conditional sharing based on context

2. **Character Consistency**: 
   - Stay true to your personality - suspicious characters remain suspicious
   - Maintain your speech style and mannerisms
   - Consider your own goals and how this conversation fits them

3. **Strategic Thinking**: 
   - What do you gain from sharing or not sharing?
   - Could this information put you or others at risk?
   - Does helping align with your principles and motivations?

**Output**: Provide only your natural dialogue response. Decide how much to reveal based on your relationship and personality."""
    
    def _create_default_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """创建默认响应"""
        conversation_mode = state.get("conversation_mode", "initiate")
        current_turn = state.get('current_turn', 0)
        
        if conversation_mode == "initiate":
            requester_npc = state.get('requester_npc', 'Unknown')
            return {
                "dialogue_history": [{"role": requester_npc, "content": "Hello, I wanted to talk to you about something."}],
                "current_turn": current_turn + 1
            }
        else:
            target_npc = state.get('target_npc', 'Unknown')
            return {
                "dialogue_history": [{"role": target_npc, "content": "I see. What did you want to know?"}]
            }
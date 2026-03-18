import logging
from typing import Dict, List, Any, Optional
from .base_dispatch_node import BaseDispatchNode

logger = logging.getLogger(__name__)

class RequestEvaluationNode(BaseDispatchNode):
    """
    专门处理玩家请求评估的节点。
    决定NPC是否愿意帮助玩家完成请求。
    """
    
    async def process_async(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步评估玩家请求
        
        Args:
            state: 包含请求信息的状态字典
                - requester_npc: 发起请求的NPC名称
                - player_request: 玩家的请求内容
                - relationship_to_player: 与玩家的关系评分 (0.0-1.0)
        
        Returns:
            评估结果字典:
            - is_accepted: 是否接受请求
            - refusal_reason: 拒绝理由（如果拒绝的话）
            - report_to_player: 向玩家汇报的内容
        """
        try:
            prompt = self.build_prompt(state)
            response_content = await self.invoke_llm_async(prompt)
            
            if not response_content:
                logger.error("Empty response from LLM in request evaluation")
                return self._create_default_response(state)
            
            result = self.extract_json_from_response(response_content)
            
            if not result or not self._validate_response(result):
                logger.error(f"Invalid response format: {result}")
                return self._create_default_response(state)
            
            return {
                "is_accepted": result.get("is_accepted", True),
                "refusal_reason": result.get("reason") if not result.get("is_accepted") else None,
                "report_to_player": result.get("reason", "")
            }
            
        except Exception as e:
            logger.error(f"Error in RequestEvaluationNode: {e}", exc_info=True)
            return self._create_default_response(state)
    
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        构建请求评估的prompt
        
        Args:
            state: 当前状态字典
        
        Returns:
            格式化的prompt字符串
        """
        requester_npc = state.get('requester_npc', 'Unknown')
        player_request = state.get('player_request', '')
        relationship_score = state.get('relationship_to_player', 0.5)
        
        # 获取NPC信息
        npc_info = self.get_npc_context(requester_npc, "intention")
        
        # 构建prompt各个部分
        character_section = self.build_character_section(npc_info, requester_npc)
        motivation_section = self.build_motivation_section(npc_info)
        logic_section = self.build_logic_section(npc_info)
        request_section = self._build_request_section(state)
        guidance_section = self._build_evaluation_guidance()
        output_section = self._build_output_format()
        
        # 组合完整prompt
        prompt_parts = [
            character_section,
            motivation_section,
            logic_section,
            request_section,
            guidance_section,
            output_section
        ]
        
        return "\n\n".join([part for part in prompt_parts if part])
    
    def _build_request_section(self, state: Dict[str, Any]) -> str:
        """构建请求信息部分"""
        player_request = state.get('player_request', '')
        relationship_score = state.get('relationship_to_player', 0.5)
        
        # 根据关系评分判断关系状态
        if relationship_score >= 0.8:
            relationship_desc = "Very Good (Trusted ally)"
        elif relationship_score >= 0.6:
            relationship_desc = "Good (Friendly)"
        elif relationship_score >= 0.4:
            relationship_desc = "Neutral (Cautious)"
        elif relationship_score >= 0.2:
            relationship_desc = "Poor (Distrustful)"
        else:
            relationship_desc = "Very Poor (Hostile)"
        
        return f"""# PLAYER REQUEST EVALUATION

**Player's Request**: "{player_request}"

**Your Relationship with Player**: {relationship_desc} (Score: {relationship_score:.1f}/1.0)"""
    
    def _build_evaluation_guidance(self) -> str:
        """构建评估指导原则"""
        return """# EVALUATION GUIDANCE

Consider the following factors when deciding whether to help:

1. **Relationship Factor**: 
   - High relationship (0.7+): More likely to help
   - Medium relationship (0.3-0.7): Conditional help based on personality
   - Low relationship (0.3-): Less likely to help unless it aligns with your goals

2. **Personality Alignment**: 
   - Does this request align with your principles?
   - Does it conflict with your core beliefs or goals?
   - How does it affect your standing with others?

3. **Risk Assessment**: 
   - What are the potential consequences?
   - Does this put you at personal risk?
   - Could this harm your reputation or interests?

4. **Strategic Value**: 
   - Does helping advance your own goals?
   - Could this create future opportunities?
   - Is there potential for mutual benefit?

**Decision Criteria**: Be true to your character. If you're naturally suspicious, don't easily agree. If you're loyal and the relationship is good, be more helpful."""
    
    def _build_output_format(self) -> str:
        """构建输出格式说明"""
        return """# OUTPUT FORMAT

Respond ONLY in JSON format:

{
    "is_accepted": true/false,
    "reason": "Your in-character response to the player explaining your decision"
}

**Guidelines for 'reason'**:
- If accepting: Express willingness and perhaps mention why you're helping
- If refusing: Give a character-appropriate explanation (but don't reveal too much)
- Stay true to your personality and relationship with the player
- Keep it concise but natural"""
    
    def _validate_response(self, result: Dict[str, Any]) -> bool:
        """验证响应格式是否正确"""
        required_fields = ["is_accepted", "reason"]
        
        # 检查必需字段
        for field in required_fields:
            if field not in result:
                return False
        
        # 检查字段类型
        if not isinstance(result["is_accepted"], bool):
            return False
        
        if not isinstance(result["reason"], str) or not result["reason"].strip():
            return False
        
        return True
    
    def _create_default_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """创建默认响应（当LLM调用失败时）"""
        requester_npc = state.get('requester_npc', 'Unknown')
        relationship_score = state.get('relationship_to_player', 0.5)
        
        # 基于关系评分决定默认行为
        if relationship_score >= 0.6:
            return {
                "is_accepted": True,
                "refusal_reason": None,
                "report_to_player": f"{requester_npc}: I'll help you with that."
            }
        else:
            return {
                "is_accepted": False,
                "refusal_reason": f"{requester_npc}: I'm not sure about this request.",
                "report_to_player": f"{requester_npc}: I'm not sure about this request."
            }
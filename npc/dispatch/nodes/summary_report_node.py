import logging
from typing import Dict, List, Any, Optional
from .base_dispatch_node import BaseDispatchNode

logger = logging.getLogger(__name__)

class SummaryReportNode(BaseDispatchNode):
    """
    处理总结和汇报的节点。
    NPC完成调查后，总结收集到的信息并向玩家汇报。
    """
    
    async def process_async(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步处理总结和汇报
        
        Args:
            state: 包含对话信息的状态字典
                - requester_npc: 发起请求的NPC
                - target_npc: 目标NPC
                - inquiry_topic: 调查的话题
                - dialogue_history: 完整的对话历史
                - investigation_success: 调查是否成功
        
        Returns:
            汇报结果字典:
            - final_summary: 总结内容
            - report_to_player: 向玩家的汇报
            - success_level: 成功程度 ("high", "medium", "low", "failed")
        """
        try:
            prompt = self.build_prompt(state)
            response_content = await self.invoke_llm_async(prompt)
            
            if not response_content:
                logger.error("Empty response from LLM in summary report")
                return self._create_default_response(state)
            
            # 尝试解析JSON格式的响应
            result = self.extract_json_from_response(response_content)
            
            if result and self._validate_response(result):
                return {
                    "final_summary": result.get("summary", ""),
                    "report_to_player": result.get("report_to_player", ""),
                    "success_level": result.get("success_level", "medium")
                }
            else:
                # 如果不是JSON格式，直接使用文本作为汇报内容
                success_level = self._analyze_success_level(state)
                return {
                    "final_summary": response_content,
                    "report_to_player": response_content,
                    "success_level": success_level
                }
                
        except Exception as e:
            logger.error(f"Error in SummaryReportNode: {e}", exc_info=True)
            return self._create_default_response(state)
    
    def build_prompt(self, state: Dict[str, Any]) -> str:
        """
        构建总结汇报的prompt
        
        Args:
            state: 当前状态字典
        
        Returns:
            格式化的prompt字符串
        """
        requester_npc = state.get('requester_npc', 'Unknown')
        target_npc = state.get('target_npc', 'Unknown')
        inquiry_topic = state.get('inquiry_topic', 'general information')
        
        # 获取汇报NPC的信息
        npc_info = self.get_npc_context(requester_npc, "intention")
        
        # 构建prompt各个部分
        character_section = self.build_character_section(npc_info, requester_npc)
        investigation_context = self._build_investigation_context(state)
        analysis_section = self._build_analysis_guidance()
        output_section = self._build_output_format()
        
        prompt_parts = [
            character_section,
            investigation_context,
            analysis_section,
            output_section
        ]
        
        return "\n\n".join([part for part in prompt_parts if part])
    
    def _build_investigation_context(self, state: Dict[str, Any]) -> str:
        """构建调查上下文信息"""
        target_npc = state.get('target_npc', 'Unknown')
        inquiry_topic = state.get('inquiry_topic', 'general information')
        dialogue_history = state.get('dialogue_history', [])
        
        context_lines = [
            f"# INVESTIGATION REPORT",
            f"**Task**: Find out about '{inquiry_topic}' from {target_npc}",
            f"**Target NPC**: {target_npc}"
        ]
        
        if dialogue_history:
            # 格式化对话历史
            history_text = "\n".join([f"  {msg['role']}: {msg['content']}" 
                                    for msg in dialogue_history])
            context_lines.extend([
                "",
                f"# CONVERSATION WITH {target_npc.upper()}",
                history_text
            ])
        else:
            context_lines.extend([
                "",
                f"# CONVERSATION RESULT",
                f"No conversation took place with {target_npc}."
            ])
        
        return "\n".join(context_lines)
    
    def _build_analysis_guidance(self) -> str:
        """构建分析指导原则"""
        return """# REPORTING INSTRUCTIONS

Analyze the conversation and create a report for the player. Consider:

1. **Information Extraction**: 
   - What specific information did you learn about the inquiry topic?
   - Did the target NPC reveal any secrets or important details?
   - Was the information complete or partial?

2. **Success Assessment**: 
   - High Success: Got detailed, valuable information
   - Medium Success: Got some useful information but not complete
   - Low Success: Got minimal information or vague responses  
   - Failed: Got no useful information or was refused

3. **Character Voice**: 
   - Report in your own character's voice and style
   - Include your personal interpretation of what happened
   - Mention any difficulties or resistance you encountered

4. **Player Value**: 
   - Focus on information that would be useful to the player
   - Don't include irrelevant conversational details
   - Summarize key points clearly"""
    
    def _build_output_format(self) -> str:
        """构建输出格式说明"""
        return """# OUTPUT OPTIONS

You can respond in either format:

**Option 1: JSON Format** (preferred for structured data):
{
    "summary": "Technical summary of what was learned",
    "report_to_player": "Your in-character report to the player", 
    "success_level": "high/medium/low/failed"
}

**Option 2: Direct Text** (simpler format):
Just provide your natural, in-character report to the player about what you discovered.

**Guidelines for report_to_player**:
- Speak naturally in your character's voice
- Be informative but stay in character
- If you failed, explain what happened (resistance, refusal, etc.)
- If successful, share the key information you learned"""
    
    def _validate_response(self, result: Dict[str, Any]) -> bool:
        """验证响应格式是否正确"""
        if not isinstance(result, dict):
            return False
        
        # 检查基本必需字段
        if "report_to_player" not in result:
            return False
        
        # 检查内容不为空
        if not result["report_to_player"] or not result["report_to_player"].strip():
            return False
        
        # 验证成功级别（如果提供的话）
        success_level = result.get("success_level", "")
        if success_level and success_level not in ["high", "medium", "low", "failed"]:
            return False
        
        return True
    
    def _analyze_success_level(self, state: Dict[str, Any]) -> str:
        """基于对话历史分析成功程度"""
        dialogue_history = state.get('dialogue_history', [])
        
        if not dialogue_history:
            return "failed"
        
        # 简单的启发式分析
        total_messages = len(dialogue_history)
        
        # 分析对话内容中的关键词
        all_content = " ".join([msg.get('content', '') for msg in dialogue_history]).lower()
        
        # 失败指标
        failure_indicators = ['refuse', 'no', "won't", "can't tell", "secret", "private", "none of your business"]
        failure_count = sum(1 for indicator in failure_indicators if indicator in all_content)
        
        # 成功指标
        success_indicators = ['yes', 'sure', 'tell you', 'know', 'here', 'information', 'details']
        success_count = sum(1 for indicator in success_indicators if indicator in all_content)
        
        if failure_count > success_count:
            return "low" if total_messages > 2 else "failed"
        elif success_count > failure_count * 2:
            return "high" if total_messages > 3 else "medium"
        else:
            return "medium"
    
    def _create_default_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """创建默认响应"""
        requester_npc = state.get('requester_npc', 'Unknown')
        inquiry_topic = state.get('inquiry_topic', 'general information')
        target_npc = state.get('target_npc', 'Unknown')
        
        default_report = f"{requester_npc}: I tried to ask {target_npc} about {inquiry_topic}, but I wasn't able to get clear information."
        
        return {
            "final_summary": f"Investigation of {inquiry_topic} from {target_npc} was inconclusive.",
            "report_to_player": default_report,
            "success_level": "low"
        }
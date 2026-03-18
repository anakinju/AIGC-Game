import logging
from typing import Dict, List, Any, TypedDict, Annotated, Optional
import operator
from langgraph.graph import StateGraph, END
from npc.dispatch.nodes import get_factory

logger = logging.getLogger(__name__)

class DispatchState(TypedDict):
    """NPC Dispatch Workflow State"""
    # Basic Info
    requester_npc: str          # The NPC sent by the player
    target_npc: str             # The NPC to be questioned
    player_request: str         # Original request from player
    inquiry_topic: str          # Extracted topic
    
    # Context
    relationship_to_player: float # 0.0 to 1.0
    relationship_between_npcs: str # e.g., "Friend", "Enemy"
    
    # Conversation
    dialogue_history: Annotated[List[Dict[str, str]], operator.add]
    current_turn: int
    max_turns: int
    
    # Results
    is_accepted: bool
    refusal_reason: Optional[str]
    gathered_knowledge: List[str]
    final_summary: str
    report_to_player: str

def create_dispatch_graph():
    factory = get_factory()
    workflow = StateGraph(DispatchState)
    
    # 定义节点函数，将新节点系统与LangGraph集成
    async def evaluate_request(state: DispatchState) -> Dict[str, Any]:
        """评估请求节点"""
        evaluation_node = factory.get_request_evaluation_node()
        return await evaluation_node.process_async(state)
    
    async def npc_a_talk(state: DispatchState) -> Dict[str, Any]:
        """NPC A发起对话节点"""
        conversation_node = factory.get_npc_conversation_node()
        # 设置对话模式为发起对话
        state_with_mode = dict(state)
        state_with_mode["conversation_mode"] = "initiate"
        return await conversation_node.process_async(state_with_mode)
    
    async def npc_b_respond(state: DispatchState) -> Dict[str, Any]:
        """NPC B响应对话节点"""
        conversation_node = factory.get_npc_conversation_node()
        # 设置对话模式为响应对话
        state_with_mode = dict(state)
        state_with_mode["conversation_mode"] = "respond"
        return await conversation_node.process_async(state_with_mode)
    
    async def summarize_and_report(state: DispatchState) -> Dict[str, Any]:
        """总结汇报节点"""
        summary_node = factory.get_summary_report_node()
        return await summary_node.process_async(state)
    
    workflow.add_node("evaluate", evaluate_request)
    workflow.add_node("npc_a_talk", npc_a_talk)
    workflow.add_node("npc_b_respond", npc_b_respond)
    workflow.add_node("summarize", summarize_and_report)
    
    workflow.set_entry_point("evaluate")
    
    def should_continue(state: DispatchState):
        if not state["is_accepted"]:
            return "end"
        if state["current_turn"] >= state["max_turns"]:
            return "summarize"
        return "continue"

    workflow.add_conditional_edges(
        "evaluate",
        lambda x: "npc_a_talk" if x["is_accepted"] else END
    )
    
    workflow.add_edge("npc_a_talk", "npc_b_respond")
    
    workflow.add_conditional_edges(
        "npc_b_respond",
        should_continue,
        {
            "continue": "npc_a_talk",
            "summarize": "summarize",
            "end": END
        }
    )
    
    workflow.add_edge("summarize", END)
    
    return workflow.compile()

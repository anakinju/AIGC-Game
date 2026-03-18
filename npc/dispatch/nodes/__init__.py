"""
Dispatch Nodes Package

这个包包含了用于处理NPC dispatch功能的各种节点类。
每个节点专门负责dispatch流程中的特定步骤。

模块说明:
- base_dispatch_node: 基础dispatch节点类，提供通用功能
- request_evaluation_node: 处理请求评估的节点
- npc_conversation_node: 处理NPC间对话的节点  
- summary_report_node: 处理总结和汇报的节点
- dispatch_node_factory: 节点工厂类，用于创建和管理节点实例
"""

from .base_dispatch_node import BaseDispatchNode
from .request_evaluation_node import RequestEvaluationNode
from .npc_conversation_node import NPCConversationNode
from .summary_report_node import SummaryReportNode
from .dispatch_node_factory import DispatchNodeFactory, get_factory, reset_factory

__all__ = [
    'BaseDispatchNode',
    'RequestEvaluationNode', 
    'NPCConversationNode',
    'SummaryReportNode',
    'DispatchNodeFactory',
    'get_factory',
    'reset_factory'
]
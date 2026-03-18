import logging
from typing import Dict, Any, Type, Optional
from .base_dispatch_node import BaseDispatchNode
from .request_evaluation_node import RequestEvaluationNode
from .npc_conversation_node import NPCConversationNode
from .summary_report_node import SummaryReportNode

logger = logging.getLogger(__name__)

class DispatchNodeFactory:
    """
    Dispatch节点工厂类，负责创建和管理不同类型的dispatch节点。
    """
    
    # 节点类型映射
    NODE_TYPES: Dict[str, Type[BaseDispatchNode]] = {
        "request_evaluation": RequestEvaluationNode,
        "npc_conversation": NPCConversationNode,
        "summary_report": SummaryReportNode,
    }
    
    def __init__(self, default_model_name: str = "gpt-4o-mini"):
        """
        初始化工厂
        
        Args:
            default_model_name: 默认使用的LLM模型名称
        """
        self.default_model_name = default_model_name
        self._node_instances: Dict[str, BaseDispatchNode] = {}
    
    def create_node(self, 
                   node_type: str, 
                   model_name: Optional[str] = None,
                   force_new: bool = False) -> BaseDispatchNode:
        """
        创建或获取节点实例
        
        Args:
            node_type: 节点类型 ("request_evaluation", "npc_conversation", "summary_report")
            model_name: 使用的模型名称，如果不指定则使用默认模型
            force_new: 是否强制创建新实例（默认会复用已存在的实例）
        
        Returns:
            节点实例
        
        Raises:
            ValueError: 未知的节点类型
        """
        if node_type not in self.NODE_TYPES:
            available_types = ", ".join(self.NODE_TYPES.keys())
            raise ValueError(f"Unknown node type '{node_type}'. Available types: {available_types}")
        
        # 构建缓存键
        used_model = model_name or self.default_model_name
        cache_key = f"{node_type}_{used_model}"
        
        # 如果不是强制创建新实例，且缓存中存在，则返回缓存的实例
        if not force_new and cache_key in self._node_instances:
            return self._node_instances[cache_key]
        
        # 创建新实例
        node_class = self.NODE_TYPES[node_type]
        node_instance = node_class(model_name=used_model)
        
        # 缓存实例
        self._node_instances[cache_key] = node_instance
        
        logger.info(f"Created new {node_type} node with model {used_model}")
        return node_instance
    
    def get_request_evaluation_node(self, model_name: Optional[str] = None) -> RequestEvaluationNode:
        """获取请求评估节点"""
        return self.create_node("request_evaluation", model_name)
    
    def get_npc_conversation_node(self, model_name: Optional[str] = None) -> NPCConversationNode:
        """获取NPC对话节点"""
        return self.create_node("npc_conversation", model_name)
    
    def get_summary_report_node(self, model_name: Optional[str] = None) -> SummaryReportNode:
        """获取总结汇报节点"""
        return self.create_node("summary_report", model_name)
    
    def clear_cache(self):
        """清空节点实例缓存"""
        self._node_instances.clear()
        logger.info("Cleared dispatch node cache")
    
    def get_available_node_types(self) -> list:
        """获取所有可用的节点类型"""
        return list(self.NODE_TYPES.keys())
    
    def is_valid_node_type(self, node_type: str) -> bool:
        """检查节点类型是否有效"""
        return node_type in self.NODE_TYPES

# 全局工厂实例（单例模式）
_factory_instance: Optional[DispatchNodeFactory] = None

def get_factory(default_model_name: str = "gpt-4o-mini") -> DispatchNodeFactory:
    """
    获取全局工厂实例
    
    Args:
        default_model_name: 默认模型名称
    
    Returns:
        全局工厂实例
    """
    global _factory_instance
    
    if _factory_instance is None:
        _factory_instance = DispatchNodeFactory(default_model_name=default_model_name)
    
    return _factory_instance

def reset_factory():
    """重置全局工厂实例"""
    global _factory_instance
    _factory_instance = None
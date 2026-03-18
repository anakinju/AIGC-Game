#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流管理器 - 从 ChatEnvironment 中分离出的 LangGraph 工作流管理功能
"""

import os
import sys
from typing import Dict, Any, TYPE_CHECKING

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入 LangGraph（必需依赖）
try:
    from langgraph.graph import StateGraph, END
except ImportError as e:
    raise ImportError(
        "langgraph 包未安装。请运行: pip install langgraph langgraph-core\n"
        f"原始错误: {e}"
    )

# 避免循环导入
if TYPE_CHECKING:
    from npc.multi_npc.chat_env import ChatState


class WorkflowManager:
    """工作流管理器 - 处理 LangGraph 工作流的创建和管理"""
    
    def __init__(self, router_node, npc_behaviors: Dict[str, Any], player_node=None):
        """
        初始化工作流管理器
        
        Args:
            router_node: 路由节点实例
            npc_behaviors: NPC 行为字典
            player_node: 玩家节点实例（可选）
        """
        self.router = router_node
        self.npc_behaviors = npc_behaviors
        self.player_node = player_node
        self.workflow = None
        self._setup_workflow()
    
    def _setup_workflow(self) -> StateGraph:
        """
        设置LangGraph工作流
        
        Returns:
            StateGraph: 配置好的工作流图
        """
        try:
            # 验证必要的组件
            if not self.router:
                raise ValueError("RouterNode 未正确初始化")
            
            if not self.npc_behaviors:
                raise ValueError("NPC behaviors 字典为空，无法创建工作流")
            
            # 导入ChatState类型
            from npc.multi_npc.chat_env import ChatState
            
            # 创建状态图
            workflow = StateGraph(ChatState)
            
            # 如果有PlayerNode，将其作为入口点
            if self.player_node:
                workflow.add_node("player_validator", self.player_node)
                workflow.set_entry_point("player_validator")
            
            # 添加路由节点
            workflow.add_node("router", self.router)
            
            # 为每个NPC添加节点
            for npc_name, npc_behavior in self.npc_behaviors.items():
                if npc_behavior is None:
                    continue
                # 关键修复：
                # 上层 ChatRunner 大量使用 `asyncio.run(...)`，每次输入都会新建并关闭事件循环。
                # 若走 `NPCNode.__call__`，它在 loop 运行时只会 create_task(process_tools_async) 而不 await，
                # 任务会在 loop 关闭时被取消，导致 relationship_manager 的 LLM 根本没机会被调用。
                # 所以这里强制优先使用可 await 的 `__call_async__`（如果存在）。
                call_async = getattr(npc_behavior, "__call_async__", None)
                workflow.add_node(npc_name, call_async if call_async is not None else npc_behavior)
            
            # 验证是否有有效的NPC节点
            valid_npc_names = [name for name, behavior in self.npc_behaviors.items() if behavior is not None]
            if not valid_npc_names:
                raise ValueError("没有有效的 NPC behavior，无法创建工作流")
            
            # 如果没有PlayerNode，直接以router为入口点
            if not self.player_node:
                workflow.set_entry_point("router")
            else:
                # 添加从player_validator到router的条件边
                workflow.add_conditional_edges(
                    "player_validator",
                    self._decide_chat_mode,
                    {"router": "router", "END": END}
                )
            
            # 添加条件边：从router到各个NPC或END
            workflow.add_conditional_edges(
                "router",
                self._decide_next_node,
                {npc_name: npc_name for npc_name in valid_npc_names} | {"END": END}
            )
            
            # 为每个有效的NPC添加回到router的边
            for npc_name in valid_npc_names:
                workflow.add_edge(npc_name, "router")
            
            # 编译工作流
            self.workflow = workflow.compile()
            return self.workflow
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise
    
    def _decide_next_node(self, state: 'ChatState') -> str:
        """
        决定下一个节点
        
        Args:
            state: 当前聊天状态
            
        Returns:
            str: 下一个节点名称
        """
        # 检查玩家是否请求退出
        if state.get("player_exit_requested", False):
            print("[WorkflowManager] 检测到玩家退出请求，结束对话")
            return "END"
        
        # 检查是否需要进行 worldstate 结算
        if state.get("needs_worldstate_settlement", False):
            print("[WorkflowManager] 检测到需要场景结算，结束对话")
            return "END"
        
        # 检查剩余回合数
        remaining_turns = state.get("remaining_turns", 0)
        if remaining_turns <= 0:
            print(f"[WorkflowManager] 剩余回合数为 0，结束对话")
            return "END"
        
        # 获取响应者列表
        responders = state.get("responders", [])
        
        if not responders:
            return "END"
        
        # 检查是否有未处理的NPC
        processed_npcs = state.get("processed_npcs", [])
        
        for npc_name in responders:
            if npc_name not in processed_npcs and npc_name in self.npc_behaviors:
                return npc_name
        
        # 如果所有NPC都处理完了，结束
        return "END"
    
    def _decide_chat_mode(self, state: 'ChatState') -> str:
        """
        根据PlayerNode的验证结果决定聊天模式
        
        Args:
            state: 当前聊天状态
            
        Returns:
            str: 下一个节点名称 ("router" 或 "END")
        """
        # 检查PlayerNode的验证结果
        validation_result = state.get("player_validation", {})
        
        # 如果顶层没有，尝试从message_tags中获取
        if not validation_result:
            message_tags = state.get("message_tags", {})
            validation_result = message_tags.get("player_validation", {})
        
        if not validation_result:
            return "END"
        
        category = validation_result.get("category", "NOT_STORY_RELEVANT")
        send_to_bottom = validation_result.get("send_to_bottom", False)
        
        # 检查是否为退出命令
        if category == "EXIT_COMMAND":
            print("[WorkflowManager] 检测到退出命令，直接进入router进行结算")
            return "router"
        
        if send_to_bottom and category == "STORY_RELEVANT":
            # 故事相关，设置为player_involved模式，继续到router
            state["chat_mode"] = "player_involved"
            return "router"
        elif category == "NOT_STORY_RELEVANT" or category == "STORY_RELEVANT":
            # 无论是否故事相关，只要不是退出，都应该进入 router 处理消息存储
            state["chat_mode"] = "player_involved" if category == "STORY_RELEVANT" else "casual_chat"
            return "router"
        else:
            # 其他情况，进入 router 进行默认处理
            return "router"
    
    def get_workflow(self) -> StateGraph:
        """
        获取编译后的工作流
        
        Returns:
            StateGraph: 编译后的工作流图
        """
        return self.workflow
    
    def update_npc_behaviors(self, npc_behaviors: Dict[str, Any]) -> None:
        """
        更新 NPC 行为并重新构建工作流
        
        Args:
            npc_behaviors: 新的 NPC 行为字典
        """
        self.npc_behaviors = npc_behaviors
        self._setup_workflow()
    
    def add_npc_behavior(self, npc_name: str, npc_behavior: Any) -> None:
        """
        添加新的 NPC 行为
        
        Args:
            npc_name: NPC 名称
            npc_behavior: NPC 行为实例
        """
        self.npc_behaviors[npc_name] = npc_behavior
        self._setup_workflow()
    
    def remove_npc_behavior(self, npc_name: str) -> None:
        """
        移除 NPC 行为
        
        Args:
            npc_name: 要移除的 NPC 名称
        """
        if npc_name in self.npc_behaviors:
            del self.npc_behaviors[npc_name]
            self._setup_workflow()
    
    def get_available_nodes(self) -> list[str]:
        """
        获取所有可用的节点名称
        
        Returns:
            list[str]: 节点名称列表
        """
        return ["router"] + list(self.npc_behaviors.keys())
    
    def validate_workflow(self) -> bool:
        """
        验证工作流是否有效
        
        Returns:
            bool: 工作流是否有效
        """
        try:
            # 检查是否有NPC行为
            if not self.npc_behaviors:
                return False
            
            # 检查工作流是否已编译
            if self.workflow is None:
                return False
            
            return True
            
        except Exception as e:
            return False
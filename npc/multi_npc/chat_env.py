#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重构后的 ChatEnvironment - 核心聊天环境管理类
只保留核心功能和异步方法，其他功能委托给专职管理器
"""

from typing import Any, Dict, List, Optional, Union
from typing_extensions import TypedDict, Annotated
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langgraph.graph import StateGraph, END

# 导入管理器
from npc.multi_npc.managers import (
   NPCManagerExtended, WorkflowManager,
     MemoryManagerExtended, WorldStateManager
)
from npc.scene_control.scene_manager import SceneManager
# 导入其他必要组件
from npc.multi_npc.router_node import RouterNode
from npc.single_npc.npc_node import NPCNode
from npc.utils.base_npc import NPCAgent
from npc.single_npc.tools.tool_manager import ToolManager
from npc.multi_npc.player_node import PlayerNode

# 加载环境变量
load_dotenv()

# Langsmith配置
langsmith_key = os.getenv("LANGSMITH_API_KEY")
langsmith_project = os.getenv("LANGSMITH_PROJECT")
langsmith_tracing = os.getenv("LANGSMITH_TRACING", "true")
if langsmith_key:
    os.environ["LANGCHAIN_API_KEY"] = langsmith_key
if langsmith_project:
    os.environ["LANGCHAIN_PROJECT"] = langsmith_project
if langsmith_tracing:
    os.environ["LANGCHAIN_TRACING_V2"] = langsmith_tracing
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"


class ChatState(TypedDict):
    """聊天状态定义"""
    sender: Annotated[str, "last"]                    # 当前发送者
    message: Annotated[str, "last"]                   # 当前消息
    chat_group: Annotated[List[str], "last"]          # 聊天组成员
    msg_type: Annotated[str, "last"]                  # 消息类型
    current_turn: Annotated[int, "last"]              # 当前轮次
    message_target: Annotated[Optional[str], "last"]  # 消息目标
    message_tags: Annotated[Dict[str, Any], "last"]   # 消息标签
    original_sender: Annotated[str, "last"]           # 原始发送者
    original_message: Annotated[str, "last"]          # 原始消息
    message_store: Annotated[List[Dict], "last"]      # 消息存储
    responders: Annotated[List[str], "last"]          # 响应者列表
    npc_state: Annotated[Dict[str, Any], "last"]      # NPC 动态状态：current_emotion, npc_goals, angry, angry_level
    chat_mode: Annotated[str, "last"]                 # 聊天模式
    previous_speaker: Annotated[str, "last"]          # 上一个发言者
    inactive_turns: Annotated[Dict[str,Any],"last"]   # 未活跃轮次
    processed_npcs: Annotated[List[str], "last"]      # 已处理的NPC
    streaming_enabled: Annotated[bool, "last"] = False # 是否启用流式输出
    
    # NPC 状态管理字段
    npc_states: Annotated[Dict[str, Dict[str, Any]], "last"]  # NPC 状态字典
    active_npcs: Annotated[List[str], "last"]         # 当前场景活跃的 NPC
    npc_updates: Annotated[Dict[str, Dict[str, Any]], "last"]  # 本轮 NPC 更新记录
    streaming_callback: Annotated[Optional[callable], "last"] = None # 流式输出回调函数
    
    # Turn 管理字段
    max_turns: Annotated[int, "last"] = 10            # 最大回合数（从场景中读取，默认10）
    remaining_turns: Annotated[int, "last"] = 10      # 剩余回合数


class ChatEnvironment:
    """重构后的聊天环境管理类 - 使用专职管理器架构"""
    
    def __init__(
        self,
        scene_path: str = None,
        characters_file: str = None,
        npc_behaviors: Optional[Dict[str, Any]] = None,
        chat_mode: str = "player_involved",
        enable_player_validation: bool = False,
        enable_streaming: bool = False,
        streaming_callback: Optional[callable] = None,
        enable_memory_system: bool = False,
        scene_index: Optional[int] = None
    ):
        """
        初始化重构后的聊天环境
        
        Args:
            scene_path: 场景文件路径
            characters_file: 角色文件路径
            npc_behaviors: NPC行为字典（可选）
            chat_mode: 聊天模式
            enable_player_validation: 是否启用玩家验证
            enable_streaming: 是否启用流式输出
            streaming_callback: 流式输出回调
            enable_memory_system: 是否启用内存系统 (由于 memory 模块已删除，此参数现在始终被视为 False)
            scene_index: 场景索引
        """
        # 初始化管理器
        self.scene_manager = SceneManager()
        self.npc_manager = NPCManagerExtended()
        self.memory_manager = MemoryManagerExtended(False) # 强制禁用内存系统
        self.worldstate_manager = WorldStateManager(scene_manager=self.scene_manager)  # 传入scene_manager引用
        
        # 基本配置
        self.chat_mode = chat_mode
        self.enable_player_validation = enable_player_validation
        self.enable_streaming = enable_streaming
        self.streaming_callback = streaming_callback
        
        # 加载场景
        self._load_scene(scene_path, scene_index)
        
        # 加载和初始化 NPC
        self._initialize_npcs(characters_file, npc_behaviors)
        
        # 验证 NPC behaviors 是否正确初始化
        if not self.npc_behaviors:
            raise ValueError("没有成功初始化任何 NPC，无法创建工作流")
        
        # 初始化玩家节点
        if enable_player_validation:
            self.player_node = PlayerNode(self.scene_manager.get_current_scene())
        else:
            self.player_node = None
        
        # 初始化工作流
        try:
            router_node = RouterNode()
            self.workflow_manager = WorkflowManager(router_node, self.npc_behaviors, self.player_node)
        except Exception as e:
            raise ValueError(f"工作流初始化失败: {e}")
        
        # 创建初始聊天状态
        self._initialize_chat_state()
        
        # 初始化 WorldState 系统
        current_scene = self.scene_manager.get_current_scene()
        if current_scene:
            self.worldstate_manager.initialize_world_state_system(
                current_scene, self.chat_state.get("current_turn", 0)
            )
        
        # 历史记录
        self.history = []
    
    def _load_scene(self, scene_path: Optional[str], scene_index: Optional[int]) -> None:
        """加载场景：支持按路径加载场景集合后按索引切换"""
        if scene_path:
            # 先从指定路径加载场景集合并注册到 SceneRegistry
            if not self.scene_manager.scene_status.load_all_scenes(scene_path):
                raise ValueError(f"无法从路径加载场景集合: {scene_path}")
        if scene_index is not None:
            if not self.scene_manager.load_scene_by_index(scene_index):
                raise ValueError(f"无法通过索引加载场景: {scene_index}")
        elif scene_path:
            if not self.scene_manager.load_scene_by_path(scene_path):
                raise ValueError(f"无法通过路径加载场景: {scene_path}")
        else:
            selected_scene_index = self.scene_manager.prompt_scene_selection()
            if selected_scene_index is None:
                raise ValueError("未选择场景")
            if not self.scene_manager.load_scene_by_index(selected_scene_index):
                raise ValueError(f"无法通过索引加载场景: {selected_scene_index}")
    
    def _initialize_npcs(self, characters_file: Optional[str], npc_behaviors: Optional[Dict[str, Any]]) -> None:
        """初始化 NPC"""
        # 获取场景中的 NPC 名称
        npc_names = self.scene_manager.get_npc_names_from_scene()
        if not npc_names:
            raise ValueError("场景中没有找到 NPC")
        
        # 创建 NPC 行为
        if npc_behaviors is None:
            # 直接为场景中的 NPC 创建行为节点，不依赖 characters.json 验证
            npc_behaviors = {}
            successful_npcs = []
            failed_npcs = []
            
            for npc_name in npc_names:
                try:
                    # 创建 NPCAgent（会通过 npc_info.py 自动加载静态信息）
                    agent = NPCAgent(npc_name)
                    tool_manager = ToolManager()
                    npcnode = NPCNode(npc_name, agent, tool_manager, 
                                    enable_memory_system=self.memory_manager.is_memory_system_enabled())
                    npc_behaviors[npc_name] = npcnode
                    successful_npcs.append(npc_name)
                except Exception as e:
                    failed_npcs.append(npc_name)
                    import traceback
                    traceback.print_exc()
            
            # 检查是否至少有一个NPC成功初始化
            if not successful_npcs:
                raise ValueError(f"所有 NPC 初始化都失败了。失败的 NPC: {failed_npcs}")
        
        self.npc_behaviors = npc_behaviors
        self.memory_manager.set_npc_behaviors(npc_behaviors)
    
    def _initialize_chat_state(self) -> None:
        """初始化聊天状态"""
        # 场景静态快照
        current_scene = self.scene_manager.get_current_scene()
        scene_id = "unknown_scene"
        scene_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if current_scene:
            # Try to get scene_id from various possible keys
            scene_id = current_scene.get("id") or current_scene.get("scene_id") or current_scene.get("name") or current_scene.get("title") or "unknown_scene"
            print(f"DEBUG: [ChatEnvironment] Scene ID: {scene_id} from scene: {current_scene.get('name', 'Unknown')}")
        
        # NPC 动态状态：仅保留情绪和目标
        npc_state = {
            "current_emotion": "Calm",
            "npc_goals": {},
            "angry": False,
            "angry_level": 0
        }
        max_turns = current_scene.get("max_turns", 10) if current_scene else 10
        npc_states, active_npcs = self.npc_manager.initialize_npc_states(list(self.npc_behaviors.keys()))
        
        # 不再合并场景中的关系信息到 dynamic_state
        self.chat_state = {
            "sender": "player",
            "message": "",
            "chat_group": list(self.npc_behaviors.keys()),
            "msg_type": "new",
            "current_turn": 0,
            "message_target": None,
            "message_tags": {},
            "original_sender": "",
            "original_message": "",
            "message_store": [],
            "responders": [],
            "npc_state": npc_state,
            "chat_mode": self.chat_mode,
            "previous_speaker": "",
            "inactive_turns": {},
            "processed_npcs": [],
            "scene_id": scene_id,
            "scene_timestamp": scene_timestamp,
            "streaming_enabled": self.enable_streaming,
            "streaming_callback": self.streaming_callback,
            "npc_states": npc_states,
            "active_npcs": active_npcs,
            "npc_updates": {},
            "max_turns": max_turns,
            "remaining_turns": max_turns,
            "scene_id": scene_id,
            "scene_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
        }
    
    async def process_message(self, message: str, sender: str) -> Dict[str, Any]:
        """
        处理消息（异步版本）
        
        Args:
            message: 消息内容
            sender: 发送者
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 验证工作流是否正确初始化
            if not self.workflow_manager:
                raise ValueError("WorkflowManager 未初始化")
            
            workflow = self.workflow_manager.get_workflow()
            if not workflow:
                raise ValueError("Workflow 未正确编译")
            
            # 更新聊天状态（保留 scene_id 和 scene_timestamp）
            scene_id = self.chat_state.get("scene_id", "unknown_scene")
            scene_timestamp = self.chat_state.get("scene_timestamp", "")
            
            self.chat_state.update({
                "sender": sender,
                "message": message,
                "original_sender": sender,
                "original_message": message,
                "msg_type": "new",
                "processed_npcs": [],
                "scene_id": scene_id,
                "scene_timestamp": scene_timestamp,
            })
            
            # 使用工作流处理消息
            result = await workflow.ainvoke(self.chat_state)
            
            # 保留重要字段并更新聊天状态
            preserved_scene_id = self.chat_state.get("scene_id", "unknown_scene")
            preserved_scene_timestamp = self.chat_state.get("scene_timestamp", "")
            
            self.chat_state.update(result)
            
            # 确保重要字段不被覆盖
            self.chat_state["scene_id"] = preserved_scene_id
            self.chat_state["scene_timestamp"] = preserved_scene_timestamp
            
            # 提取 NPC 响应
            npc_responses = []
            message_store = result.get("message_store", [])
            
            # 从消息存储中提取最新的 NPC 响应
            for msg in reversed(message_store):
                msg_speaker = msg.get("speaker", msg.get("sender", ""))
                if msg_speaker != sender and msg_speaker != "player":
                    npc_responses.append({
                        "npc_name": msg_speaker,
                        "response": msg.get("content", "")
                    })
            
            # 更新回合数
            self.chat_state["current_turn"] += 1
            
            # 更新 WorldState 管理器的回合数
            self.worldstate_manager.update_current_turn(self.chat_state["current_turn"])
            
            # 检查是否需要进行场景结算
            worldstate_result = None
            chat_ended = False
            exit_reason = None
            
            # 检查各种退出条件
            if result.get("player_exit_requested", False):
                print("[ChatEnvironment] 玩家请求退出，触发场景结算")
                exit_reason = "player_exit"
                worldstate_result = await self.settle_scene_with_worldstate()
                chat_ended = True
            elif result.get("needs_worldstate_settlement", False):
                print("[ChatEnvironment] 需要场景结算，触发结算")
                exit_reason = result.get("exit_reason", "unknown")
                worldstate_result = await self.settle_scene_with_worldstate()
                chat_ended = True
            elif result.get("remaining_turns", 1) <= 0:
                print("[ChatEnvironment] 回合数耗尽，触发场景结算")
                exit_reason = "max_turns_reached"
                worldstate_result = await self.settle_scene_with_worldstate()
                chat_ended = True
                
            return {
                    "success": True,
                    "npc_responses": npc_responses,
                    "current_turn": self.chat_state["current_turn"],
                    "message_count": len(message_store),
                    "remaining_turns": result.get("remaining_turns", 0),
                    "chat_ended": chat_ended,
                    "exit_reason": exit_reason,
                    "worldstate_result": worldstate_result
                }
                
        except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "npc_responses": []
                }
    
    async def process_message_streaming(self, message: str, sender: str, 
                                      streaming_callback: callable) -> Dict[str, Any]:
        """
        处理消息（流式输出异步版本）
        
        Args:
            message: 消息内容
            sender: 发送者
            streaming_callback: 流式输出回调函数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 设置流式回调
            self.chat_state["streaming_enabled"] = True
            self.chat_state["streaming_callback"] = streaming_callback
            
            # 调用普通处理方法
            result = await self.process_message(message, sender)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "npc_responses": []
            }
    
    async def set_player_input(self, message: str, target_npc: Union[str, List[str]]) -> Dict[str, Any]:
        """
        设置玩家输入（异步版本）
        
        Args:
            message: 玩家消息
            target_npc: 目标 NPC（单个或列表）
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 确定响应者
            if isinstance(target_npc, str):
                responders = [target_npc] if self.is_valid_npc(target_npc) else []
            else:
                responders = [npc for npc in target_npc if self.is_valid_npc(npc)]
            
            if not responders:
                return {
                    "success": False,
                    "error": "没有有效的目标 NPC",
                    "npc_responses": []
                }
            
            # 设置响应者
            self.chat_state["responders"] = responders
            self.chat_state["message_target"] = responders[0] if len(responders) == 1 else None
            
            # 处理消息
            return await self.process_message(message, "player")
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "npc_responses": []
            }
    
    async def run_npc_free_chat(self, original_message: str, original_sender: str) -> Dict[str, Any]:
        """
        运行 NPC 自由聊天（异步版本）
        
        Args:
            original_message: 原始消息
            original_sender: 原始发送者
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            # 设置为 NPC 自由聊天模式
            self.chat_state.update({
                "chat_mode": "npc_only",
                "original_message": original_message,
                "original_sender": original_sender,
                "responders": list(self.npc_behaviors.keys())
            })
            
            # 处理消息
            result = await self.process_message(original_message, original_sender)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "npc_responses": []
            }
    
    # 委托方法 - 将调用委托给相应的管理器
    def get_available_npcs(self) -> List[str]:
        """获取可用的 NPC 列表"""
        return self.npc_manager.get_available_npcs(self.npc_behaviors)
    
    def is_valid_npc(self, npc_name: str) -> bool:
        """检查 NPC 是否有效"""
        return self.npc_manager.is_valid_npc(npc_name, self.npc_behaviors)
    
    def get_npc_state_for_tool(self, npc_name: str) -> Dict[str, Any]:
        """为工具获取 NPC 状态"""
        return self.npc_manager.get_npc_state_for_tool(npc_name, self.chat_state.get("npc_states", {}))
    
    def update_npc_state(self, npc_name: str, update_type: str, update_data: Dict[str, Any]):
        """更新 NPC 状态"""
        self.npc_manager.update_npc_state(
            npc_name, update_type, update_data,
            self.chat_state.get("npc_states", {}),
            self.chat_state.get("npc_updates", {})
        )
    
    def get_npc_memory(self) -> List[Dict[str, Any]]:
        """获取 NPC 内存"""
        return self.memory_manager.get_npc_memory()
    
    def get_player_memory(self) -> List[Dict[str, Any]]:
        """获取玩家内存"""
        return self.memory_manager.get_player_memory()
    
    def get_all_memory_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取所有内存数据"""
        return self.memory_manager.get_all_memory_data()
    
    def is_memory_system_enabled(self) -> bool:
        """检查内存系统是否启用"""
        return self.memory_manager.is_memory_system_enabled()
    
    async def settle_scene_with_worldstate(self) -> Optional[Dict[str, Any]]:
        """场景结算 - 从chatstate获取信息，scene数据从scene_manager获取"""
        return await self.worldstate_manager.settle_scene_with_worldstate(
            self.chat_state.get("message_store", []),
            self.chat_state.get("current_turn", 0),
            scene_data=None,  # 不传入scene_data，让worldstate_manager从scene_manager获取
            scene_id=self.chat_state.get("scene_id", "unknown"),
            timestamp=self.chat_state.get("scene_timestamp", "")
        )
    
    
    def update_npc_state(self, new_npc_state: Dict[str, Any]) -> None:
        """更新 NPC 动态状态（npc_relationships、npc_goals）"""
        if "npc_state" not in self.chat_state:
            self.chat_state["npc_state"] = {"npc_relationships": [], "npc_goals": {}}
        self.chat_state["npc_state"].update(new_npc_state)
    
    def reset(self):
        """重置环境"""
        # 重置聊天状态
        self._initialize_chat_state()
        
        # 清除历史
        self.history.clear()
        
        # 重置管理器
        self.npc_manager.clear_cache()
        if self.memory_manager.is_memory_system_enabled():
            self.memory_manager.clear_all_memories()
    
    def get_history(self) -> List:
        """获取历史记录"""
        return self.history


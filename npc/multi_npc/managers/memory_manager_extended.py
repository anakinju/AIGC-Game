#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
内存管理器扩展 - 从 ChatEnvironment 中分离出的内存管理功能
"""

import os
import sys
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class MemoryManagerExtended:
    """内存管理器扩展 - 处理 NPC 和玩家的内存管理"""
    
    def __init__(self, enable_memory_system: bool = False):
        """
        初始化内存管理器
        
        Args:
            enable_memory_system: 是否启用内存系统 (由于 memory 模块已删除，此参数现在始终被视为 False)
        """
        self.enable_memory_system = False
        self.npc_behaviors = {}
        
        print("[MemoryManager] 内存系统已禁用 (memory 模块已移除)")
    
    def set_npc_behaviors(self, npc_behaviors: Dict[str, Any]) -> None:
        """
        设置 NPC 行为字典
        
        Args:
            npc_behaviors: NPC 行为字典
        """
        self.npc_behaviors = npc_behaviors
    
    def get_npc_memory(self) -> List[Dict[str, Any]]:
        """
        获取所有NPC的内存数据
        
        Returns:
            List[Dict[str, Any]]: NPC内存数据列表
        """
        if not self.enable_memory_system:
            return []
        
        npc_memories = []
        
        try:
            for npc_name, npc_behavior in self.npc_behaviors.items():
                # 检查NPC是否有RAG管理器
                if hasattr(npc_behavior, 'rag_manager') and npc_behavior.rag_manager:
                    try:
                        # 获取该NPC的内存数据
                        npc_memory_data = npc_behavior.rag_manager.get_memory_data()
                        
                        if npc_memory_data:
                            npc_memories.append({
                                "npc_name": npc_name,
                                "memory_data": npc_memory_data,
                                "memory_count": len(npc_memory_data) if isinstance(npc_memory_data, list) else 1
                            })
                    except Exception as e:
                        print(f"获取NPC内存失败 {npc_name}: {e}")
                        npc_memories.append({
                            "npc_name": npc_name,
                            "memory_data": [],
                            "error": str(e)
                        })
            
            return npc_memories
            
        except Exception as e:
            print(f"获取NPC内存数据失败: {e}")
            return []
    
    def get_player_memory(self) -> List[Dict[str, Any]]:
        """
        获取玩家内存数据
        
        Returns:
            List[Dict[str, Any]]: 玩家内存数据列表
        """
        if not self.enable_memory_system:
            return []
        
        try:
            # 目前玩家内存主要通过对话历史记录
            # 这里可以扩展为更复杂的玩家内存系统
            player_memory = []
            
            # 可以从各个NPC的RAG管理器中提取与玩家相关的记忆
            for npc_name, npc_behavior in self.npc_behaviors.items():
                if hasattr(npc_behavior, 'rag_manager') and npc_behavior.rag_manager:
                    try:
                        # 获取与玩家相关的记忆
                        player_related_memories = npc_behavior.rag_manager.get_player_related_memories()
                        
                        if player_related_memories:
                            player_memory.extend([{
                                "source_npc": npc_name,
                                "memory": memory,
                                "timestamp": memory.get("timestamp", "")
                            } for memory in player_related_memories])
                            
                    except AttributeError:
                        # 如果RAG管理器没有get_player_related_memories方法，跳过
                        continue
                    except Exception as e:
                        print(f"获取玩家相关内存失败 {npc_name}: {e}")
            
            return player_memory
            
        except Exception as e:
            print(f"获取玩家内存数据失败: {e}")
            return []
    
    def get_all_memory_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取所有内存数据
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: 包含NPC和玩家内存的字典
        """
        if not self.enable_memory_system:
            return {
                "npc_memories": [],
                "player_memories": [],
                "memory_system_enabled": False
            }
        
        return {
            "npc_memories": self.get_npc_memory(),
            "player_memories": self.get_player_memory(),
            "memory_system_enabled": True,
            "total_npc_count": len(self.npc_behaviors)
        }
    
    def is_memory_system_enabled(self) -> bool:
        """
        检查内存系统是否启用
        
        Returns:
            bool: 内存系统是否启用
        """
        return self.enable_memory_system
    
    def store_conversation_memory(self, conversation_data: Dict[str, Any]) -> bool:
        """
        存储对话内存
        
        Args:
            conversation_data: 对话数据
            
        Returns:
            bool: 是否存储成功
        """
        if not self.enable_memory_system:
            return False
        
        try:
            # 为每个参与的NPC存储对话记忆
            participants = conversation_data.get("participants", [])
            
            for npc_name in participants:
                if npc_name in self.npc_behaviors and npc_name != "Player":
                    npc_behavior = self.npc_behaviors[npc_name]
                    
                    if hasattr(npc_behavior, 'rag_manager') and npc_behavior.rag_manager:
                        try:
                            # 存储对话记忆
                            npc_behavior.rag_manager.store_conversation(conversation_data)
                        except Exception as e:
                            print(f"为NPC存储对话记忆失败 {npc_name}: {e}")
            
            return True
            
        except Exception as e:
            print(f"存储对话记忆失败: {e}")
            return False
    
    def clear_all_memories(self) -> bool:
        """
        清除所有内存
        
        Returns:
            bool: 是否清除成功
        """
        if not self.enable_memory_system:
            return True
        
        try:
            success_count = 0
            total_count = len(self.npc_behaviors)
            
            for npc_name, npc_behavior in self.npc_behaviors.items():
                if hasattr(npc_behavior, 'rag_manager') and npc_behavior.rag_manager:
                    try:
                        npc_behavior.rag_manager.clear_memory()
                        success_count += 1
                    except Exception as e:
                        print(f"清除NPC内存失败 {npc_name}: {e}")
            
            print(f"内存清除完成: {success_count}/{total_count} 个NPC")
            return success_count == total_count
            
        except Exception as e:
            print(f"清除所有内存失败: {e}")
            return False
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """
        获取内存统计信息
        
        Returns:
            Dict[str, Any]: 内存统计信息
        """
        if not self.enable_memory_system:
            return {
                "memory_system_enabled": False,
                "total_npcs": 0,
                "total_memories": 0
            }
        
        stats = {
            "memory_system_enabled": True,
            "total_npcs": len(self.npc_behaviors),
            "npc_memory_stats": {},
            "total_memories": 0
        }
        
        try:
            for npc_name, npc_behavior in self.npc_behaviors.items():
                if hasattr(npc_behavior, 'rag_manager') and npc_behavior.rag_manager:
                    try:
                        memory_count = npc_behavior.rag_manager.get_memory_count()
                        stats["npc_memory_stats"][npc_name] = memory_count
                        stats["total_memories"] += memory_count
                    except Exception as e:
                        stats["npc_memory_stats"][npc_name] = f"错误: {str(e)}"
                else:
                    stats["npc_memory_stats"][npc_name] = "无RAG管理器"
            
            return stats
            
        except Exception as e:
            stats["error"] = str(e)
            return stats
    
    def backup_memories(self, backup_path: str) -> bool:
        """
        备份所有内存数据
        
        Args:
            backup_path: 备份文件路径
            
        Returns:
            bool: 是否备份成功
        """
        if not self.enable_memory_system:
            return False
        
        try:
            import json
            from datetime import datetime
            
            backup_data = {
                "backup_timestamp": datetime.now().isoformat(),
                "memory_system_enabled": True,
                "npc_memories": self.get_npc_memory(),
                "player_memories": self.get_player_memory(),
                "statistics": self.get_memory_statistics()
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            print(f"内存备份完成: {backup_path}")
            return True
            
        except Exception as e:
            print(f"内存备份失败: {e}")
            return False

from typing import Dict, Any, List, Optional
from datetime import datetime

class MessageProcessor:
    """消息处理器，负责处理消息的格式化和内存管理"""
    
    @staticmethod
    def create_message_tags(sender: str, target_npcs: List[str], chat_group: List[str]) -> Dict[str, Any]:
        """创建消息标签"""
        return {
            "sender": sender,
            "targets": target_npcs,
            "allowed_npcs": chat_group,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def format_message_entry(speaker: str, content: str, target_npcs: List[str], chat_group: List[str]) -> Dict[str, Any]:
        """格式化单条消息"""
        return {
            "speaker": speaker,
            "content": content,
            "allowed_npcs": chat_group,
            "timestamp": datetime.now().isoformat(),
            "tags": MessageProcessor.create_message_tags(speaker, target_npcs, chat_group)
        }
    
    @staticmethod
    def record_conversation_turn(sender: str, message: str, message_store: List[Dict], 
                               history: List[Dict], current_turn_start_index: int) -> Dict[str, Any]:
        """记录一轮对话"""
        # 创建基本记录
        record = {
            "sender": sender,
            "message": message,
            "responses": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # 收集当前轮次的回复
        if current_turn_start_index < len(message_store):
            record["responses"] = [
                {
                    "speaker": msg.get("speaker"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp")
                }
                for msg in message_store[current_turn_start_index:]
                if msg.get("speaker") != sender
            ]
        
        history.append(record)
        return record
    
    @staticmethod
    def extract_npc_responses(message_store: List[Dict], target_npcs: List[str]) -> List[Dict[str, str]]:
        """提取NPC回复"""
        responses = []
        
        # 首先检查是否有任何消息
        if not message_store:
            # 如果没有消息，为每个目标NPC创建一个默认响应
            for npc in target_npcs:
                responses.append({
                    "npc_name": npc,
                    "response": "对不起，我暂时无法回应。"
                })
            return responses
        
        # 如果有消息，提取NPC回复
        for npc in target_npcs:
            # 查找此NPC的最新消息
            npc_messages = [msg for msg in message_store if msg.get("speaker") == npc]
            
            if npc_messages:
                # 使用最新的消息
                latest_msg = npc_messages[-1]
                responses.append({
                    "npc_name": npc,
                    "response": latest_msg.get("content", "对不起，我暂时无法回应。")
                })
            else:
                # 如果没有找到此NPC的消息，添加默认响应
                responses.append({
                    "npc_name": npc,
                    "response": "对不起，我暂时无法回应。"
                })
        
        return responses
    
    @staticmethod
    def format_memory_data(history: List[Dict], chat_group: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """格式化对话历史为内存数据"""
        memory_data = []  # NPC格式
        player_memory = []  # Player格式
        
        for record in history:
            # 处理玩家消息
            if record.get("sender") == "player":
                responding_npcs = [resp["speaker"] for resp in record.get("responses", [])]
                player_memory.extend([
                    {
                        "content": record.get("message", ""),
                        "dialogue_pair": f"Player->{npc}",
                        "permissions": [n for n in chat_group if n.lower() != "player"]
                    }
                    for npc in responding_npcs
                ])
            
            # 处理NPC回复
            memory_data.extend([
                {
                    "npc": response["speaker"],
                    "content": response["content"],
                    "permissions": [npc for npc in chat_group if npc.lower() != "player"],
                    "dialogue_pair": f"{response['speaker']}->Player"
                }
                for response in record.get("responses", [])
            ])
        
        return {
            "memory_data": memory_data,
            "player_memory": player_memory
        }
    
    @staticmethod
    def validate_message_input(message: str, target_npcs: List[str], available_npcs: List[str]) -> Dict[str, Any]:
        """验证消息输入"""
        if not message or not message.strip():
            return {"valid": False, "error": "消息不能为空", "invalid_npcs": []}
        
        invalid_npcs = [npc for npc in target_npcs if npc not in available_npcs]
        
        return {
            "valid": not invalid_npcs,
            "error": f"无效的NPC: {', '.join(invalid_npcs)}。可用的NPC: {', '.join(available_npcs)}" if invalid_npcs else "",
            "invalid_npcs": invalid_npcs
        }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WorldState 管理器 - 从 ChatEnvironment 中分离出的 WorldState 系统管理功能
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.worldstate import WorldStateSystem
from npc.knowledge.memory_synthesizer import MemorySynthesizer


class WorldStateManager:
    """WorldState 管理器 - 处理场景结算和世界状态管理"""
    
    def __init__(self, scene_manager=None):
        """
        初始化 WorldState 管理器
        
        Args:
            scene_manager: SceneManager实例，用于获取当前场景数据
        """
        self.world_state_system: Optional[WorldStateSystem] = None
        self.current_turn = 0
        self.scene_manager = scene_manager  # 存储scene_manager引用
        self.memory_synthesizer = MemorySynthesizer()
    
    def initialize_world_state_system(self, scene: Dict[str, Any], current_turn: int = 0) -> Optional[WorldStateSystem]:
        """
        初始化 WorldState 系统
        
        Args:
            scene: 场景数据
            current_turn: 当前回合数
            
        Returns:
            Optional[WorldStateSystem]: WorldState 系统实例，如果场景中没有 worldstate_tasks 则返回 None
        """
        self.current_turn = current_turn
        
        # 检查场景中是否有 worldstate_tasks
        worldstate_tasks = scene.get("worldstate_tasks", [])
        if not worldstate_tasks:
            print("[WorldState] 场景中没有 worldstate_tasks，WorldState 系统已禁用")
            return None
        
        try:
            # AI 生成函数 - 使用优化后的CoT prompt
            def ai_generate_function(prompt: str) -> Dict[str, Any]:
                """使用项目中的 LLM 生成 World States (CoT Enhanced)"""
                try:
                    from langchain_openai import ChatOpenAI
                    
                    llm = ChatOpenAI(model_name="gpt-4o-mini")
                    response = llm.invoke(prompt)
                    
                    # 尝试解析JSON响应
                    import json
                    try:
                        # 优化后的worldstate.py返回的是包含"states"键的字典
                        result = json.loads(response.content)
                        if isinstance(result, dict) and "states" in result:
                            return result
                        elif isinstance(result, list):
                            return {"states": result}
                        else:
                            return {"states": [{"text": response.content}]}
                    except json.JSONDecodeError:
                        # 如果JSON解析失败，尝试提取状态信息
                        content = response.content.strip()
                        if content:
                            return {"states": [{"text": content}]}
                        else:
                            return {"states": [{"text": "Failed to generate states"}]}
                        
                except Exception as e:
                    print(f"[WorldState] AI generation error: {e}")
                    return {"states": [{"text": f"Generation failed: {str(e)}"}]}
            
            # 嵌入函数 - 单个文本版本（适配优化后的worldstate.py）
            def embedding_function(text: str) -> List[float]:
                """生成单个文本的嵌入向量"""
                try:
                    from langchain_openai import OpenAIEmbeddings
                    
                    embeddings = OpenAIEmbeddings()
                    # embed_query 返回单个向量，embed_documents 返回向量列表
                    return embeddings.embed_query(text)
                    
                except Exception as e:
                    print(f"[WorldState] Embedding error: {e}")
                    # 返回随机嵌入作为后备
                    import random
                    return [random.random() for _ in range(1536)]
            
            # AI 判断函数 - 使用优化后的CoT判断
            def ai_judge_function(prompt: str) -> Dict[str, Any]:
                """使用 AI 进行CoT增强的语义判断"""
                try:
                    from langchain_openai import ChatOpenAI
                    
                    llm = ChatOpenAI(model_name="gpt-4o-mini")
                    response = llm.invoke(prompt)
                    
                    # 尝试解析JSON响应
                    import json
                    try:
                        result = json.loads(response.content)
                        if isinstance(result, dict) and "matched" in result:
                            return result
                        else:
                            # 兜底处理：尝试从文本中提取判断结果
                            content = response.content.lower()
                            if "true" in content or "match" in content or "yes" in content:
                                return {"matched": True, "confidence": 0.7, "reason": "Text analysis fallback"}
                            else:
                                return {"matched": False, "confidence": 0.7, "reason": "Text analysis fallback"}
                    except json.JSONDecodeError:
                        # JSON解析失败，使用文本分析
                        content = response.content.lower()
                        if "true" in content or "match" in content or "yes" in content:
                            return {"matched": True, "confidence": 0.5, "reason": "Fallback text analysis"}
                        else:
                            return {"matched": False, "confidence": 0.5, "reason": "Fallback text analysis"}
                        
                except Exception as e:
                    print(f"[WorldState] AI judgment error: {e}")
                    return {"matched": False, "confidence": 0.0, "reason": f"Error: {str(e)}"}
            
            # 创建 WorldState 系统 - 使用优化后的接口（不写入对话历史文件）
            world_state_system = WorldStateSystem(
                ai_generate_function=ai_generate_function,
                embedding_function=embedding_function,
                ai_judge_function=ai_judge_function
            )
            
            # 添加场景中定义的任务
            for task_data in worldstate_tasks:
                expected_text = task_data.get("expected_text", "")
                deadline_turn = task_data.get("deadline_turn", current_turn + 10)
                if expected_text:
                    world_state_system.add_task(expected_text, deadline_turn)
                    print(f"[WorldState] 添加任务: {expected_text} (截止回合: {deadline_turn})")
            
            self.world_state_system = world_state_system
            return world_state_system
            
        except Exception as e:
            print(f"[WorldState] 初始化失败: {e}")
            return None
    
    async def settle_scene_with_worldstate(self, message_store: List[Dict], current_turn: int, scene_data: Dict[str, Any] = None, scene_id: str = "unknown", timestamp: str = "") -> Optional[Dict[str, Any]]:
        """
        场景结算：使用 WorldState 系统处理对话历史 (CoT Enhanced)
        同时触发 NPC 记忆合成 (Memory Synthesis)
        """
        if not self.world_state_system:
            return None
        
        # 格式化对话历史
        chat_log = self._format_chat_history_for_worldstate(message_store)
        
        # 从scene_manager获取场景数据（如果未提供scene_data）
        if scene_data is None and self.scene_manager:
            scene_data = self.scene_manager.get_current_scene()
        
        # 提取上下文信息
        scene_context = None
        npc_context = None
        if scene_data:
            scene_context = self.world_state_system.extract_scene_context(scene_data)
            interactive_npcs = scene_data.get("interactive_npc", [])
            if interactive_npcs:
                main_npc_name = interactive_npcs[0].get("name") if isinstance(interactive_npcs[0], dict) else interactive_npcs[0]
                if main_npc_name:
                    npc_context = self.world_state_system.extract_npc_context(scene_data, main_npc_name)
        
        # 调用 WorldState 系统处理
        try:
            result = self.world_state_system.end_turn(
                turn=current_turn, 
                chat_log=chat_log,
                npc_context=npc_context,
                scene_context=scene_context
            )
            
            # --- 触发 NPC 记忆合成 (Memory Synthesis) ---
            world_summary = result.get("scene_summary", "")
            synthesized_memories = {}
            
            if world_summary and scene_data:
                interactive_npcs = scene_data.get("interactive_npc", [])
                for npc_item in interactive_npcs:
                    npc_name = npc_item.get("name") if isinstance(npc_item, dict) else npc_item
                    if npc_name:
                        print(f"[WorldState] 为 {npc_name} 生成综合记忆...")
                        try:
                            summary = await self.memory_synthesizer.synthesize_scene_knowledge(
                                npc_name=npc_name,
                                world_state_summary=world_summary,
                                scene_id=scene_id,
                                timestamp=timestamp,
                                scene_name=scene_data.get("name", "Unknown Scene")
                            )
                            synthesized_memories[npc_name] = summary
                        except Exception as e:
                            print(f"[WorldState] 记忆合成失败 ({npc_name}): {e}")
            
            result["synthesized_memories"] = synthesized_memories
            return result
        except Exception as e:
            print(f"[WorldState] Settlement error: {e}")
            return {"error": str(e), "success": False}
            
            # 显示场景约束信息
            if scene_context:
                print(f"  Scene Location: {scene_context.get('location', 'N/A')}")
                if scene_context.get('scene_end_state_reference'):
                    print(f"  Scene End Conditions: {list(scene_context['scene_end_state_reference'].keys())}")
                if scene_context.get('worldstate_tasks'):
                    print(f"  Expected Tasks: {len(scene_context['worldstate_tasks'])}")
                    for i, task in enumerate(scene_context['worldstate_tasks'], 1):
                        if isinstance(task, dict):
                            print(f"    Task {i}: {task.get('expected_text', str(task))}")
            
            if npc_context:
                print(f"  NPC: {npc_context.get('name', 'N/A')}")
                if npc_context.get('scene_goal'):
                    print(f"  NPC Scene Goal: {npc_context['scene_goal']}")
            
            print(f"  Generated new states: {result['new_states_count']}")
            print(f"  Added states (after deduplication): {result['added_states_count']}")
            print(f"  Total states: {result['total_states']}")
            
            # 显示CoT推理生成的状态
            if result.get('generated_states'):
                print(f"\n  [CoT Generated States]:")
                for i, state in enumerate(result['generated_states'], 1):
                    state_text = state.get('text', str(state))
                    print(f"    {i}. {state_text}")
            else:
                print(f"\n  [CoT Generated States]: None (this is correct if no meaningful conversation occurred)")
            
            # 显示成功匹配的任务
            if result['success_tasks']:
                print(f"\n  [Successful Task Matches]:")
                for task in result['success_tasks']:
                    matched_text = task.get('matched_text', 'N/A')
                    confidence = task.get('matched_score', 0)
                    print(f"    ✓ Task: {task['expected_text']}")
                    print(f"      Matched: {matched_text} (confidence: {confidence:.2f})")
            
            # 显示失败的任务
            if result['failed_tasks']:
                print(f"\n  [Failed Tasks]:")
                for task in result['failed_tasks']:
                    deadline = task.get('deadline_turn', 'N/A')
                    print(f"    ✗ {task['expected_text']} (deadline: turn {deadline})")
            
            # 添加上下文信息到结果中
            result['context_used'] = {
                'scene_context': scene_context is not None,
                'npc_context': npc_context is not None,
                'scene_location': scene_context.get('location') if scene_context else None,
                'npc_name': npc_context.get('name') if npc_context else None
            }
            
            return result
            
        except Exception as e:
            print(f"[WorldState] Settlement error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "success": False}
    
    def _format_chat_history_for_worldstate(self, message_store: List[Dict]) -> str:
        """
        格式化对话历史为 WorldState 系统可用的格式
        
        Args:
            message_store: 消息存储列表
            
        Returns:
            str: 格式化后的对话历史
        """
        if not message_store:
            return ""
        
        def _extract_utterance_from_message(msg: Dict[str, Any]) -> str:
            """
            参考 `npc/single_npc/npc_manager.py` 的做法：
            - 如果消息是 intention dict / JSON，则只提取 `utterance`
            - 否则回退到普通文本
            """
            if not isinstance(msg, dict):
                return ""

            # 已经是处理过的格式
            if "utterance" in msg and isinstance(msg["utterance"], str):
                return msg["utterance"].strip()

            content = msg.get("content", "")
            if content is None:
                return ""

            # content 本身就是 dict（intention格式）
            if isinstance(content, dict):
                if isinstance(content.get("utterance"), str):
                    return content["utterance"].strip()
                # 兜底：尽量提取可读字段
                for k in ("message", "text"):
                    if isinstance(content.get(k), str) and content.get(k).strip():
                        return content[k].strip()
                return ""

            content_str = str(content).strip()
            if not content_str:
                return ""

            # 尝试解析 JSON 字符串（可能包含 ```json fences）
            if content_str.startswith("{") or content_str.startswith("```json"):
                try:
                    json_content = content_str
                    if json_content.startswith("```json"):
                        json_content = json_content[7:]
                    if json_content.endswith("```"):
                        json_content = json_content[:-3]
                    json_content = json_content.strip()

                    parsed = json.loads(json_content)
                    if isinstance(parsed, dict) and isinstance(parsed.get("utterance"), str):
                        return parsed["utterance"].strip()
                except Exception:
                    # 不是有效JSON就按普通文本处理
                    pass

            return content_str

        formatted_lines: List[str] = []

        for msg in message_store:
            if not isinstance(msg, dict):
                continue

            # multi_npc 的 message_store 标准字段是 speaker/content（见 router_node.py）
            speaker = (
                msg.get("speaker")
                or msg.get("sender")
                or msg.get("npc_name")
                or msg.get("name")
                or "unknown"
            )
            speaker_str = str(speaker).strip().lower() if speaker is not None else "unknown"

            utterance = _extract_utterance_from_message(msg)
            if not utterance:
                continue

            # 回合号：multi_npc 通常用 timestamp 存 current_turn
            turn = msg.get("turn", None)
            if turn is None:
                turn = msg.get("timestamp", None)

            if turn is not None and str(turn).strip() != "":
                formatted_lines.append(f"[turn {turn}] {speaker_str}: {utterance}")
            else:
                formatted_lines.append(f"{speaker_str}: {utterance}")

        return "\n".join(formatted_lines)
    
    def add_task(self, expected_text: str, deadline_turn: int) -> bool:
        """
        添加新任务
        
        Args:
            expected_text: 任务描述
            deadline_turn: 截止回合
            
        Returns:
            bool: 是否添加成功
        """
        if not self.world_state_system:
            return False
        
        try:
            self.world_state_system.add_task(expected_text, deadline_turn)
            print(f"[WorldState] 添加任务: {expected_text} (截止回合: {deadline_turn})")
            return True
        except Exception as e:
            print(f"[WorldState] 添加任务失败: {e}")
            return False
    
    def get_current_tasks(self) -> List[Dict[str, Any]]:
        """
        获取当前任务列表
        
        Returns:
            List[Dict[str, Any]]: 任务列表
        """
        if not self.world_state_system:
            return []
        
        try:
            return self.world_state_system.get_active_tasks()
        except Exception as e:
            print(f"[WorldState] 获取任务列表失败: {e}")
            return []
    
    def get_world_states_summary(self) -> Dict[str, Any]:
        """
        获取世界状态摘要
        
        Returns:
            Dict[str, Any]: 世界状态摘要
        """
        if not self.world_state_system:
            return {"enabled": False, "total_states": 0}
        
        try:
            return {
                "enabled": True,
                "total_states": self.world_state_system.get_total_states_count(),
                "active_tasks": len(self.get_current_tasks()),
                "current_turn": self.current_turn
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}
    
    def is_enabled(self) -> bool:
        """
        检查 WorldState 系统是否启用
        
        Returns:
            bool: 是否启用
        """
        return self.world_state_system is not None
    
    def update_current_turn(self, turn: int) -> None:
        """
        更新当前回合数
        
        Args:
            turn: 新的回合数
        """
        self.current_turn = turn
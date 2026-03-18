#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天运行器 - 从 ChatEnvironment 中分离出的运行和测试功能
"""

import os
import sys
import asyncio
from typing import Dict, Any, List, Optional, Union

# 添加项目根目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class ChatRunner:
    """聊天运行器 - 处理聊天环境的运行、测试和用户交互"""
    
    def __init__(self, chat_environment):
        """
        初始化聊天运行器
        
        Args:
            chat_environment: ChatEnvironment 实例
        """
        self.chat_env = chat_environment
    
    def player_input(self, player_prompt: str) -> str:
        """
        处理玩家输入（同步版本）
        
        Args:
            player_prompt: 玩家输入的提示
            
        Returns:
            str: 处理结果
        """
        try:
            # 调用异步版本
            return asyncio.run(self.async_player_input(player_prompt))
        except Exception as e:
            return f"处理玩家输入失败: {str(e)}"
    
    async def async_player_input(self, player_prompt: str) -> str:
        """
        处理玩家输入（异步版本）
        
        Args:
            player_prompt: 玩家输入的提示
            
        Returns:
            str: 处理结果
        """
        try:
            # 使用 ChatEnvironment 的异步方法处理输入
            result = await self.chat_env.process_message(player_prompt, "player")
            
            if result.get("success", False):
                responses = result.get("npc_responses", [])
                if responses:
                    return "\n".join([f"{r['npc_name']}: {r['response']}" for r in responses])
                else:
                    return "没有收到 NPC 响应"
            else:
                return f"处理失败: {result.get('error', '未知错误')}"
                
        except Exception as e:
            return f"异步处理玩家输入失败: {str(e)}"
    
    def run_test(self, player_inputs: List[str]) -> Dict[str, Any]:
        """
        运行测试模式
        
        Args:
            player_inputs: 玩家输入列表
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        print("=== 开始测试模式 ===")
        test_results = {
            "total_inputs": len(player_inputs),
            "successful_responses": 0,
            "failed_responses": 0,
            "responses": [],
            "errors": []
        }
        
        try:
            for i, player_input in enumerate(player_inputs):
                print(f"\n--- 测试输入 {i+1}/{len(player_inputs)} ---")
                print(f"玩家: {player_input}")
                
                try:
                    # 处理输入
                    response = self.player_input(player_input)
                    
                    if "失败" not in response and "错误" not in response:
                        test_results["successful_responses"] += 1
                        print(f"✓ 响应: {response}")
                    else:
                        test_results["failed_responses"] += 1
                        print(f"✗ 失败: {response}")
                        test_results["errors"].append(f"输入 {i+1}: {response}")
                    
                    test_results["responses"].append({
                        "input": player_input,
                        "response": response,
                        "success": "失败" not in response and "错误" not in response
                    })
                    
                except Exception as e:
                    test_results["failed_responses"] += 1
                    error_msg = f"输入 {i+1} 处理异常: {str(e)}"
                    test_results["errors"].append(error_msg)
                    print(f"✗ 异常: {error_msg}")
            
            # 输出测试总结
            print(f"\n=== 测试完成 ===")
            print(f"总输入: {test_results['total_inputs']}")
            print(f"成功响应: {test_results['successful_responses']}")
            print(f"失败响应: {test_results['failed_responses']}")
            print(f"成功率: {test_results['successful_responses']/test_results['total_inputs']*100:.1f}%")
            
            if test_results["errors"]:
                print(f"\n错误详情:")
                for error in test_results["errors"]:
                    print(f"  - {error}")
            
            return test_results
            
        except Exception as e:
            test_results["errors"].append(f"测试运行异常: {str(e)}")
            print(f"测试运行失败: {e}")
            return test_results
    
    def run(self, player_inputs: Optional[List[str]] = None) -> None:
        """
        运行聊天环境
        
        Args:
            player_inputs: 可选的玩家输入列表，如果提供则运行测试模式
        """
        if player_inputs:
            # 测试模式
            self.run_test(player_inputs)
            return
        
        # 交互模式
        print("=== 聊天环境启动 ===")
        print("输入 'quit' 或 'exit' 退出")
        print("输入 'help' 查看帮助")
        print("输入 'status' 查看状态")
        
        try:
            while True:
                try:
                    user_input = input("\n玩家: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("再见！")
                        break
                    
                    elif user_input.lower() == 'help':
                        self._show_help()
                        continue
                    
                    elif user_input.lower() == 'status':
                        self._show_status()
                        continue
                    
                    elif user_input.lower() == 'npcs':
                        self._show_available_npcs()
                        continue
                    
                    elif user_input.lower() == 'memory':
                        self._show_memory_info()
                        continue
                    
                    elif user_input.lower() == 'reset':
                        self._reset_environment()
                        continue
                    
                    elif user_input.lower() in ['npc_only', 'npc-only']:
                        self._start_npc_only_mode()
                        continue
                    
                    elif user_input.lower() in ['mode', 'switch_mode']:
                        self._switch_chat_mode()
                        continue
                    
                    # 处理正常输入
                    if self.chat_env.chat_mode == "player_involved":
                        # 在player_involved模式中，让玩家选择目标NPC
                        response = self._handle_player_involved_input(user_input)
                    else:
                        # 其他模式直接处理
                        print("处理中...")
                        response = self.player_input(user_input)
                    
                    print(f"\n{response}")
                    
                except KeyboardInterrupt:
                    print("\n\n程序被中断，正在退出...")
                    break
                except EOFError:
                    print("\n\n输入结束，正在退出...")
                    break
                except Exception as e:
                    print(f"处理输入时发生错误: {e}")
                    
        except Exception as e:
            print(f"运行聊天环境时发生错误: {e}")
    
    def run_scene(self) -> Dict[str, Any]:
        """
        运行单个场景 (Enhanced with WorldState Settlement)
        
        Workflow:
        - 玩家进入scene后，如果输入exit，scene退出并进行worldstate结算
        - 超过max_turns，worldstate自动结算
        
        Returns:
            Dict[str, Any]: 场景运行结果，包含退出原因和worldstate总结
        """
        scene_result = {
            "exit_reason": "unknown",
            "worldstate_summary": None,
            "worldstate_result": None,
            "chat_ended": False,
            "total_turns": 0
        }
        
        try:
            # 获取场景信息
            scene_data = getattr(self.chat_env, 'current_scene', {})
            max_turns = scene_data.get('max_turns', 20)
            scene_name = scene_data.get('name', 'Unknown Scene')
            scene_location = scene_data.get('location', 'Unknown Location')
            
            print(f"\n场景: {scene_name} - {scene_location}")
            print(f"最大回合数: {max_turns}")
            
            # 检查WorldState系统状态
            worldstate_enabled = (hasattr(self.chat_env, 'worldstate_manager') and 
                                self.chat_env.worldstate_manager.is_enabled())
            
            if worldstate_enabled:
                print("WorldState系统已启用")
                current_tasks = self.chat_env.worldstate_manager.get_current_tasks()
                if current_tasks:
                    print(f"场景任务 ({len(current_tasks)}个):")
                    for i, task in enumerate(current_tasks, 1):
                        deadline = task.get('deadline_turn', 'N/A')
                        print(f"  {i}. {task.get('expected_text', 'Unknown task')} (截止: 回合{deadline})")
                else:
                    print("无场景任务")
            else:
                print("WorldState系统未启用")
            
            print("\n" + "="*60)
            print("开始场景游戏")
            print("输入 'exit' 可退出当前场景并进行WorldState结算")
            print("输入 'help' 查看帮助，'status' 查看状态")
            print("="*60)
            
            turn_count = 0
            
            while turn_count < max_turns:
                turn_count += 1
                print(f"\n--- 回合 {turn_count}/{max_turns} ---")
                
                try:
                    # 修复：先让玩家选择目标 NPC
                    available_npcs = self.chat_env.get_available_npcs()
                    if not available_npcs:
                        print("错误: 没有可用的NPC")
                        break
                    
                    print(f"\n可用的NPC ({len(available_npcs)}):")
                    for i, npc in enumerate(available_npcs):
                        print(f"  {i+1}. {npc}")
                    print(f"  {len(available_npcs)+1}. 所有NPC")
                    print(f"  exit. 退出当前场景")
                    
                    choice = input(f"\n请选择目标NPC (1-{len(available_npcs)+1}, 或输入 'exit'): ").strip()
                    
                    if choice.lower() == 'exit':
                        print("\n玩家选择退出场景，开始WorldState结算...")
                        scene_result["exit_reason"] = "player_exit"
                        scene_result["chat_ended"] = True
                        break
                    
                    try:
                        choice_num = int(choice)
                        if choice_num == len(available_npcs) + 1:
                            target_npcs = available_npcs
                            print(f"已选择与所有NPC对话: {', '.join(target_npcs)}")
                        elif 1 <= choice_num <= len(available_npcs):
                            target_npcs = [available_npcs[choice_num - 1]]
                            print(f"已选择NPC: {target_npcs[0]}")
                        else:
                            print("无效的选择，请重新选择")
                            turn_count -= 1
                            continue
                    except ValueError:
                        print("无效的选择，请输入数字或 'exit'")
                        turn_count -= 1
                        continue

                    # 选择完 NPC 后再输入消息
                    user_input = input(f"请输入对 {', '.join(target_npcs)} 的消息: ").strip()
                    
                    if not user_input:
                        print("消息不能为空")
                        turn_count -= 1
                        continue
                    
                    # 处理正常游戏输入
                    print("处理中...")
                    result = asyncio.run(self.chat_env.set_player_input(user_input, target_npcs))
                    
                    # 检查处理结果
                    if isinstance(result, dict):
                        # 检查是否场景自然结束
                        if result.get("chat_ended", False):
                            scene_result["exit_reason"] = result.get("exit_reason", "scene_ended")
                            scene_result["chat_ended"] = True
                            print(f"\n🏁 场景自然结束: {scene_result['exit_reason']}")
                            break
                        
                        # 显示NPC响应和游戏状态
                        self._display_game_status(result)
                        
                        # 更新WorldState管理器的当前回合
                        if worldstate_enabled:
                            self.chat_env.worldstate_manager.update_current_turn(turn_count)
                    else:
                        print(f"\n{result}")
                    
                except KeyboardInterrupt:
                    print("\n\n场景被用户中断，开始WorldState结算...")
                    scene_result["exit_reason"] = "interrupted"
                    scene_result["chat_ended"] = True
                    break
                except EOFError:
                    print("\n\n📄 输入结束，开始WorldState结算...")
                    scene_result["exit_reason"] = "eof"
                    scene_result["chat_ended"] = True
                    break
                except Exception as e:
                    print(f"处理输入时发生错误: {e}")
                    continue
            
            # 检查是否达到最大回合数
            if turn_count >= max_turns and scene_result["exit_reason"] == "unknown":
                print(f"\n达到最大回合数 ({max_turns})，场景结束，开始WorldState结算...")
                scene_result["exit_reason"] = "max_turns_reached"
                scene_result["chat_ended"] = True
            
            scene_result["total_turns"] = turn_count
            
            # 执行WorldState结算
            print("\n" + "="*60)
            print("开始 WorldState 结算...")
            print("="*60)
            
            if worldstate_enabled:
                try:
                    # scene数据从chatstate中的scene_manager获取，不需要重复传入
                    # 使用 asyncio.run 调用异步方法
                    scene_id = self.chat_env.chat_state.get("scene_id", "unknown_scene")
                    scene_timestamp = self.chat_env.chat_state.get("scene_timestamp", "")
                    
                    worldstate_result = asyncio.run(self.chat_env.worldstate_manager.settle_scene_with_worldstate(
                        self.chat_env.chat_state.get("message_store", []),
                        turn_count,
                        scene_data=None,  # Will be fetched from scene_manager
                        scene_id=scene_id,
                        timestamp=scene_timestamp
                    ))
                    
                    if worldstate_result:
                        scene_result["worldstate_result"] = worldstate_result
                        scene_result["worldstate_summary"] = self._format_worldstate_summary(worldstate_result)
                        print("\nWorldState结算完成")
                    else:
                        print("\nWorldState结算失败：未获得结果")
                        scene_result["worldstate_summary"] = "WorldState结算失败：系统未返回结果"
                        
                except Exception as e:
                    print(f"\nWorldState结算失败: {e}")
                    import traceback
                    traceback.print_exc()
                    scene_result["worldstate_summary"] = f"WorldState结算失败: {e}"
            else:
                print("\n⚠️  WorldState系统未启用，跳过结算")
                scene_result["worldstate_summary"] = "WorldState系统未启用"
            
            print("="*60)
                    
        except Exception as e:
            print(f"运行场景时发生错误: {e}")
            scene_result["exit_reason"] = "error"
            scene_result["chat_ended"] = True
        
        return scene_result
    
    def _show_help(self) -> None:
        """显示帮助信息"""
        help_text = """
=== 帮助信息 ===
可用命令:
  quit/exit/q    - 退出程序
  help           - 显示此帮助信息
  status         - 显示当前状态
  npcs           - 显示可用的 NPC
  memory         - 显示内存系统信息
  reset          - 重置环境
  npc_only       - 启动NPC纯对话模式
  mode           - 切换聊天模式
  
聊天模式:
  - player_involved: 玩家参与模式（默认）- 输入消息前会让你选择目标NPC
  - npc_only: NPC纯对话模式 - NPC之间自由对话
  
直接输入消息与 NPC 对话。
        """
        print(help_text)
    
    def _show_scene_help(self) -> None:
        """显示场景帮助信息"""
        help_text = """
=== 场景帮助信息 (WorldState Enhanced) ===
可用命令:
  exit           - 退出当前场景并进行WorldState结算
  help           - 显示此帮助信息
  status         - 显示当前状态（包括WorldState信息）
  
游戏机制:
  🎯 每个场景都有最大回合数限制
  🎮 达到最大回合数会自动进行WorldState结算
  📋 场景中的任务会根据对话内容自动匹配完成状态
  🧠 使用Chain-of-Thought技术智能分析对话内容
  
直接输入消息与 NPC 对话。
        """
        print(help_text)
    
    def _display_game_status(self, result: Dict[str, Any]) -> None:
        """显示游戏状态信息：剩余回合数、NPC回复"""
        try:
            # 显示剩余回合数
            remaining_turns = result.get("remaining_turns", 0)
            print(f"剩余回合数: {remaining_turns}")
            
            # 显示 NPC 回复
            npc_responses = result.get("npc_responses", [])
            if npc_responses:
                for r in npc_responses:
                    npc_name = r.get("npc_name", "Unknown")
                    content = r.get("response", "")
                    print(f"{npc_name}: {content}")
            else:
                print("(无 NPC 回复)")
            
        except Exception as e:
            print(f"显示游戏状态时发生错误: {e}")
    
    def _show_status(self) -> None:
        """显示当前状态"""
        try:
            chat_state = self.chat_env.chat_state
            print("\n=== 当前状态 ===")
            print(f"聊天模式: {chat_state.get('chat_mode', 'unknown')}")
            print(f"当前回合: {chat_state.get('current_turn', 0)}")
            print(f"剩余回合: {chat_state.get('remaining_turns', 0)}")
            print(f"聊天组: {', '.join(chat_state.get('chat_group', []))}")
            print(f"活跃 NPC: {', '.join(chat_state.get('active_npcs', []))}")
            print(f"消息数量: {len(chat_state.get('message_store', []))}")
            print(f"流式输出: {'启用' if chat_state.get('streaming_enabled', False) else '禁用'}")
            
            # 显示内存系统状态
            if hasattr(self.chat_env, 'memory_manager'):
                memory_enabled = self.chat_env.memory_manager.is_memory_system_enabled()
                print(f"内存系统: {'启用' if memory_enabled else '禁用'}")
            
            # 显示 WorldState 系统状态
            if hasattr(self.chat_env, 'worldstate_manager'):
                worldstate_enabled = self.chat_env.worldstate_manager.is_enabled()
                print(f"WorldState 系统: {'启用' if worldstate_enabled else '禁用'}")
                
        except Exception as e:
            print(f"获取状态信息失败: {e}")
    
    def _show_worldstate_status(self) -> None:
        """显示WorldState系统状态"""
        try:
            if hasattr(self.chat_env, 'worldstate_manager') and self.chat_env.worldstate_manager.is_enabled():
                print("\n=== WorldState 状态 ===")
                
                # 获取当前任务
                current_tasks = self.chat_env.worldstate_manager.get_current_tasks()
                print(f"📋 当前任务数量: {len(current_tasks)}")
                
                if current_tasks:
                    for i, task in enumerate(current_tasks, 1):
                        status = task.get('status', 'UNKNOWN')
                        deadline = task.get('deadline_turn', 'N/A')
                        expected_text = task.get('expected_text', 'Unknown task')
                        
                        status_icon = {
                            'ONGOING': '🔄',
                            'SUCCESS': '[成功]',
                            'FAIL': '[失败]'
                        }.get(status, '❓')
                        
                        print(f"  {i}. {status_icon} {expected_text}")
                        print(f"     状态: {status}, 截止: 回合{deadline}")
                        
                        if task.get('matched_text'):
                            print(f"     匹配: {task['matched_text']} (置信度: {task.get('matched_score', 0):.2f})")
                
                # 获取世界状态摘要
                summary = self.chat_env.worldstate_manager.get_world_states_summary()
                print(f"🌍 总世界状态数: {summary.get('total_states', 0)}")
                print(f"🔄 当前回合: {summary.get('current_turn', 0)}")
            else:
                print("\nWorldState系统未启用")
                
        except Exception as e:
            print(f"显示WorldState状态时发生错误: {e}")
    
    def _format_worldstate_summary(self, worldstate_result: Dict[str, Any]) -> str:
        """格式化WorldState结算结果为摘要文本"""
        try:
            summary_lines = []
            summary_lines.append("=== WorldState 结算摘要 ===")
            
            # 1. 场景总结 (CoT 生成的客观描述)
            scene_summary = worldstate_result.get('scene_summary', "")
            if scene_summary:
                summary_lines.append("\n场景客观总结:")
                summary_lines.append(f"  {scene_summary}")

            # 2. 基本统计
            summary_lines.append(f"\n生成新状态: {worldstate_result.get('new_states_count', 0)}个")
            summary_lines.append(f"添加状态: {worldstate_result.get('added_states_count', 0)}个（去重后）")
            summary_lines.append(f"总状态数: {worldstate_result.get('total_states', 0)}")
            
            # 3. 上下文使用情况
            context_used = worldstate_result.get('context_used', {})
            if context_used.get('scene_context') or context_used.get('npc_context'):
                summary_lines.append("\n使用的上下文:")
                if context_used.get('scene_location'):
                    summary_lines.append(f"  📍 场景: {context_used['scene_location']}")
                if context_used.get('npc_name'):
                    summary_lines.append(f"  👤 主要NPC: {context_used['npc_name']}")
            
            # 4. 生成的状态
            generated_states = worldstate_result.get('generated_states', [])
            if generated_states:
                summary_lines.append(f"\n🧠 提取的客观事实:")
                for i, state in enumerate(generated_states, 1):
                    state_text = state.get('text', str(state))
                    summary_lines.append(f"  {i}. {state_text}")
            
            # 5. 成功的任务
            success_tasks = worldstate_result.get('success_tasks', [])
            if success_tasks:
                summary_lines.append(f"\n完成的任务 ({len(success_tasks)}个):")
                for task in success_tasks:
                    expected = task.get('expected_text', 'Unknown')
                    matched = task.get('matched_text', 'N/A')
                    score = task.get('matched_score')
                    confidence = f"{score:.2f}" if score is not None else "N/A"
                    summary_lines.append(f"  ✓ {expected}")
                    summary_lines.append(f"    证据: {matched} (置信度: {confidence})")
                    
                    # 打印 AI Judge 的理由 (如果有)
                    if 'match_reason' in task:
                        summary_lines.append(f"    理由: {task['match_reason']}")
            
            # 6. 失败的任务
            failed_tasks = worldstate_result.get('failed_tasks', [])
            if failed_tasks:
                summary_lines.append(f"\n未完成的任务 ({len(failed_tasks)}个):")
                for task in failed_tasks:
                    expected = task.get('expected_text', 'Unknown')
                    deadline = task.get('deadline_turn', 'N/A')
                    summary_lines.append(f"  ✗ {expected} (截止: 回合{deadline})")
            
            # 7. 总结
            total_tasks = len(success_tasks) + len(failed_tasks)
            if total_tasks > 0:
                success_rate = len(success_tasks) / total_tasks * 100
                summary_lines.append(f"\n任务完成率: {success_rate:.1f}% ({len(success_tasks)}/{total_tasks})")
            
            return "\n".join(summary_lines)
            
        except Exception as e:
            return f"格式化WorldState摘要失败: {e}"
    
    def _show_available_npcs(self) -> None:
        """显示可用的 NPC"""
        try:
            available_npcs = self.chat_env.get_available_npcs()
            print(f"\n=== 可用 NPC ({len(available_npcs)}) ===")
            for npc in available_npcs:
                print(f"  - {npc}")
        except Exception as e:
            print(f"获取 NPC 列表失败: {e}")
    
    def _show_memory_info(self) -> None:
        """显示内存系统信息"""
        try:
            print("\n[信息] 内存系统 (memory 模块) 已从项目中移除。")
            print("目前的 NPC 仅使用当前场景的对话历史作为上下文。")
        except Exception as e:
            print(f"获取内存信息失败: {e}")
    
    def _reset_environment(self) -> None:
        """重置环境"""
        try:
            if hasattr(self.chat_env, 'reset'):
                self.chat_env.reset()
                print("环境重置完成")
            else:
                print("环境不支持重置功能")
        except Exception as e:
            print(f"重置环境失败: {e}")
    
    def _handle_player_involved_input(self, user_input: str) -> Union[str, Dict[str, Any]]:
        """处理player_involved模式的输入，包括NPC选择"""
        try:
            # 获取可用的NPC列表
            available_npcs = self.chat_env.get_available_npcs()
            
            if not available_npcs:
                return "错误: 没有可用的NPC"
            
            # 显示可用的NPC
            print(f"\n可用的NPC ({len(available_npcs)}):")
            for i, npc in enumerate(available_npcs):
                print(f"  {i+1}. {npc}")
            
            # 添加选项：与所有NPC对话
            print(f"  {len(available_npcs)+1}. 所有NPC")
            print(f"  0. 取消")
            
            # 让用户选择目标NPC
            try:
                choice = input(f"\n请选择目标NPC (0-{len(available_npcs)+1}): ").strip()
                choice_num = int(choice)
                
                if choice_num == 0:
                    return "已取消"
                elif choice_num == len(available_npcs) + 1:
                    # 选择所有NPC
                    target_npcs = available_npcs
                    print(f"已选择与所有NPC对话: {', '.join(target_npcs)}")
                elif 1 <= choice_num <= len(available_npcs):
                    # 选择特定NPC
                    target_npcs = [available_npcs[choice_num - 1]]
                    print(f"已选择NPC: {target_npcs[0]}")
                else:
                    return "无效的选择"
                
            except (ValueError, KeyboardInterrupt):
                return "选择已取消"
            
            # 处理消息
            print("处理中...")
            result = asyncio.run(self.chat_env.set_player_input(user_input, target_npcs))
            
            if result.get("success", False):
                # 返回完整的结果字典，用于场景管理
                return result
            else:
                return f"处理失败: {result.get('error', '未知错误')}"
                
        except Exception as e:
            return f"处理输入失败: {str(e)}"
    
    def _start_npc_only_mode(self) -> None:
        """启动NPC-only模式"""
        try:
            available_npcs = self.chat_env.get_available_npcs()
            
            if len(available_npcs) < 2:
                print("错误: NPC-only模式需要至少2个NPC")
                return
            
            print(f"\n=== 进入NPC-only模式 ===")
            print(f"可用NPC: {', '.join(available_npcs)}")
            
            # 让用户选择初始发言者和消息
            print(f"\n选择初始发言者:")
            for i, npc in enumerate(available_npcs):
                print(f"  {i+1}. {npc}")
            
            try:
                choice = input(f"\n请选择初始发言者 (1-{len(available_npcs)}): ").strip()
                choice_num = int(choice)
                
                if not (1 <= choice_num <= len(available_npcs)):
                    print("无效的选择")
                    return
                
                initial_speaker = available_npcs[choice_num - 1]
                print(f"已选择初始发言者: {initial_speaker}")
                
                initial_message = input(f"\n请输入 {initial_speaker} 的初始消息: ").strip()
                
                if not initial_message:
                    print("消息不能为空")
                    return
                
                print(f"\n开始NPC自由对话...")
                print("=" * 50)
                
                # 运行NPC自由对话
                result = asyncio.run(self.chat_env.run_npc_free_chat(initial_message, initial_speaker))
                
                if result.get("success", False):
                    print(f"\nNPC对话完成！")
                    print(f"总消息数: {result.get('message_count', 0)}")
                else:
                    print(f"NPC对话失败: {result.get('error', '未知错误')}")
                
            except (ValueError, KeyboardInterrupt):
                print("\n已取消NPC-only模式")
                
        except Exception as e:
            print(f"启动NPC-only模式失败: {e}")
    
    def _switch_chat_mode(self) -> None:
        """切换聊天模式"""
        current_mode = getattr(self.chat_env, 'chat_mode', 'unknown')
        print(f"\n当前模式: {current_mode}")
        print("可用模式:")
        print("  1. player_involved - 玩家参与模式")
        print("  2. npc_only - NPC纯对话模式")
        
        try:
            choice = input("\n请选择模式 (1-2): ").strip()
            
            if choice == "1":
                self.chat_env.chat_mode = "player_involved"
                print("已切换到玩家参与模式")
            elif choice == "2":
                self.chat_env.chat_mode = "npc_only"
                print("已切换到NPC纯对话模式")
            else:
                print("无效的选择")
                
        except KeyboardInterrupt:
            print("\n已取消模式切换")
    
    def display_npc_responses(self, responses: List[Dict[str, Any]]) -> None:
        """
        显示 NPC 响应
        
        Args:
            responses: NPC 响应列表
        """
        if not responses:
            print("没有收到 NPC 响应")
            return
        
        print("\n=== NPC 响应 ===")
        for response in responses:
            npc_name = response.get('npc_name', 'Unknown')
            content = response.get('response', '')
            print(f"{npc_name}: {content}")
    
    def run_streaming_mode(self, player_inputs: Optional[List[str]] = None) -> None:
        """
        运行流式输出模式
        
        Args:
            player_inputs: 可选的玩家输入列表
        """
        def streaming_callback(chunk: str):
            """流式输出回调函数"""
            print(chunk, end='', flush=True)
        
        if player_inputs:
            # 流式测试模式
            print("=== 流式测试模式 ===")
            for i, player_input in enumerate(player_inputs):
                print(f"\n--- 输入 {i+1} ---")
                print(f"玩家: {player_input}")
                print("NPC 响应: ", end='')
                
                try:
                    result = self.chat_env.process_message_streaming(
                        player_input, "player", streaming_callback
                    )
                    print(f"\n[完成] 状态: {'成功' if result.get('success') else '失败'}")
                except Exception as e:
                    print(f"\n[错误] {e}")
        else:
            # 流式交互模式
            print("=== 流式交互模式 ===")
            print("输入 'quit' 退出")
            
            while True:
                try:
                    user_input = input("\n玩家: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    
                    if not user_input:
                        continue
                    
                    print("NPC 响应: ", end='')
                    result = self.chat_env.process_message_streaming(
                        user_input, "player", streaming_callback
                    )
                    print(f"\n[完成] 状态: {'成功' if result.get('success') else '失败'}")
                    
                except KeyboardInterrupt:
                    print("\n程序被中断")
                    break
                except Exception as e:
                    print(f"\n处理失败: {e}")


def create_chat_runner(chat_environment) -> ChatRunner:
    """
    创建聊天运行器实例
    
    Args:
        chat_environment: ChatEnvironment 实例
        
    Returns:
        ChatRunner: 聊天运行器实例
    """
    return ChatRunner(chat_environment)


if __name__ == "__main__":
    """主入口点 - 可以直接运行此文件"""
    import argparse
    
    parser = argparse.ArgumentParser(description="聊天环境运行器")
    parser.add_argument("--scene", type=str, help="场景文件路径")
    parser.add_argument("--scene-index", type=int, help="场景索引")
    parser.add_argument("--mode", type=str, default="player_involved", 
                       choices=["player_involved", "npc_only"],
                       help="聊天模式")
    parser.add_argument("--memory", action="store_true", help="启用内存系统")
    parser.add_argument("--streaming", action="store_true", help="启用流式输出")
    parser.add_argument("--test", nargs="+", help="测试模式，提供测试输入列表")
    
    args = parser.parse_args()
    
    try:
        # 导入 ChatEnvironment
        from npc.multi_npc.chat_env import ChatEnvironment
        
        print("正在初始化聊天环境...")
        
        # 创建聊天环境
        chat_env = ChatEnvironment(
            scene_path=args.scene,
            scene_index=args.scene_index,
            chat_mode=args.mode,
            enable_memory_system=args.memory,
            enable_streaming=args.streaming
        )
        
        print("聊天环境初始化完成！\n")
        
        # 创建运行器
        runner = create_chat_runner(chat_env)
        
        # 运行
        if args.test:
            # 测试模式
            runner.run_test(args.test)
        else:
            # 交互模式
            runner.run()
            
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
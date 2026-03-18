#!/usr/bin/env python3
"""
ChatEnvironment Streaming Output Example

This example demonstrates how to use streaming output for NPC responses
"""

import os
import sys
import time

# Add necessary paths to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.multi_npc.chat_env import ChatEnvironment


def simple_streaming_callback(chunk: str):
    """简单的流式输出回调函数"""
    print(chunk, end='', flush=True)


def colored_streaming_callback(chunk: str, npc_name: str = "NPC"):
    """带颜色的流式输出回调函数"""
    # 使用ANSI颜色代码
    colors = {
        "Meredith Stout": "\033[94m",  # 蓝色
        "Johnny Silverhand": "\033[91m",  # 红色
        "V": "\033[92m",  # 绿色
    }
    color = colors.get(npc_name, "\033[0m")  # 默认白色
    reset = "\033[0m"
    print(f"{color}{chunk}{reset}", end='', flush=True)


def main():
    """主函数"""
    print("=== ChatEnvironment Streaming Output Example ===")
    
    # 检查API密钥
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("错误: 未设置 OPENAI_API_KEY 环境变量")
        print("请设置环境变量: export OPENAI_API_KEY=your_api_key_here")
        return
    
    # 检查场景文件
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scene_path = os.path.join(base_dir, "..", "data", "test.json")
    
    if not os.path.exists(scene_path):
        print(f"错误: 场景文件未找到: {scene_path}")
        return
    
    print("✓ 环境检查通过")
    print("\n=== 创建ChatEnvironment（启用流式输出） ===")
    
    # 创建ChatEnvironment，启用流式输出
    chat_env = ChatEnvironment(
        scene_path=scene_path,
        characters_file="characters.json",
        chat_mode="player_involved",
        enable_player_validation=False,
        enable_memory_system=False,  # 简化示例，禁用memory系统
        enable_streaming=True,  # 启用流式输出
        streaming_callback=simple_streaming_callback  # 设置回调函数
    )
    
    print("✓ ChatEnvironment创建成功")
    print(f"可用NPC: {', '.join(chat_env.get_available_npcs())}")
    
    # 测试消息列表
    test_messages = [
        "Hello, I'd like to learn more about this place.",
        "Can you tell me more about this city?",
        "What interesting things are happening here?"
    ]
    
    print("\n=== 开始流式对话测试 ===")
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- 测试 {i} ---")
        print(f"玩家: {message}")
        
        # 选择目标NPC
        available_npcs = chat_env.get_available_npcs()
        target_npc = available_npcs[0] if available_npcs else "Meredith Stout"
        
        print(f"目标NPC: {target_npc}")
        print(f"{target_npc}的回复 (流式输出):")
        
        # 记录开始时间
        start_time = time.time()
        
        # 使用流式输出方法
        result = chat_env.set_player_input_streaming(
            message=message,
            target_npc=[target_npc],
            streaming_callback=simple_streaming_callback
        )
        
        # 记录结束时间
        end_time = time.time()
        
        print(f"\n\n=== 测试 {i} 完成 ===")
        print(f"处理时间: {end_time - start_time:.2f}秒")
        print(f"处理结果: {'成功' if result['success'] else '失败'}")
        
        if result['success'] and result['npc_responses']:
            for response in result['npc_responses']:
                print(f"完整回复: {response['response']}")
        
        print("-" * 50)
    
    print("\n=== 流式输出测试完成 ===")
    print("感谢使用ChatEnvironment Streaming Output!")


if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
ChatEnvironment Test Runner

Complete test suite for ChatEnvironment with memory storage functionality
"""

import os
import sys

# Add necessary paths to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import ChatEnvironment
from npc.multi_npc.chat_env import ChatEnvironment
from npc.multi_npc.test.test_memory import test_memory_stability


def streaming_callback(chunk: str):
    """流式输出回调函数"""
    print(chunk, end='', flush=True)


def test_player_npc_dialogue():
    """测试玩家-NPC对话模式（带记忆存储功能和场景选择）"""
    print("Initializing Player-NPC Dialogue with Scene Selection...")
    
    # 使用新的场景选择功能创建ChatEnvironment
    chat_env = ChatEnvironment.create_with_scene_selection(
        characters_file="characters.json",  # 使用相对于NPC info目录的路径
        chat_mode="player_involved",
        enable_player_validation=True,  # 启用player validation以测试casual chat功能
        enable_memory_system=True,      # 启用memory系统（使用SimpleMemoryInterface）
        enable_streaming=True,  # 启用流式输出
        streaming_callback=streaming_callback  # 设置流式输出回调
    )
    
    # 检查memory系统是否启用
    if chat_env.enable_memory_system:
        print("✓ Memory系统已启用（使用SimpleMemoryInterface）")
    else:
        print("✗ Memory系统未启用")
    
    print("✓ 流式输出功能已启用")
    
    # 运行对话（存储逻辑已集成到run方法中）
    chat_env.run()


def test_free_chat():
    """测试NPC自由对话模式（带记忆存储功能）"""
    print("Initializing NPC Free Chat...")
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        scene_path = os.path.join(base_dir, "..","..", "data", "npc_only_scene.json")
        
        if not os.path.exists(scene_path):
            print(f"Error: Scene file not found: {scene_path}")
            return
        
        # 创建ChatEnvironment，启用memory系统和流式输出
        chat_env = ChatEnvironment(
            scene_path=scene_path,
            characters_file="characters.json",  # 使用相对于NPC info目录的路径
            chat_mode="free_chat",
            enable_memory_system=True,      # 启用memory系统（使用SimpleMemoryInterface）
            enable_streaming=True,  # 启用流式输出
            streaming_callback=streaming_callback  # 设置流式输出回调
        )
        
        # 检查memory系统是否启用
        if chat_env.enable_memory_system:
            print("✓ Memory系统已启用（使用SimpleMemoryInterface）")
        else:
            print("✗ Memory系统未启用")
        
        print("✓ 流式输出功能已启用")
        
        original_message = "I just witnessed something terrible. Alice physically assaulted a poor citizen in the alley."
        available_npcs = list(chat_env.npc_behaviors.keys())
        
        original_sender = "Meredith Stout"
        
        
        print(f"Running NPC conversation with {len(available_npcs)} NPCs...")
        print("=== NPC对话流式输出 ===")
        
        # Run conversation
        final_state = chat_env.run_npc_free_chat(original_message, original_sender)
        
        # Show results
        message_store = final_state.get('message_store', [])
        print(f"\n\nGenerated {len(message_store)} messages")
        
        # Show sample messages
        if message_store:
            print("Sample messages:")
            for msg in message_store[:3]:
                if isinstance(msg, dict):
                    speaker = msg.get('speaker', 'Unknown')
                    content = msg.get('content', '')
                    preview = content[:100] + "..." if len(content) > 100 else content
                    print(f"  {speaker}: {preview}")
                else:
                    print(f"  Invalid message format: {type(msg)}")
        
        # Memory现在由每个NPC的RAGManager自动管理，不再需要手动存储
        if chat_env.enable_memory_system:
            print("\n=== Memory系统状态 ===")
            memory_status = chat_env.get_memory_status()
            print(f"Memory系统状态: {memory_status}")
        
        # 显示记忆数据（现在由NPC内部管理）
        print("\n=== 记忆数据 ===")
        print("注意: Memory现在由每个NPC的RAGManager管理（使用SimpleMemoryInterface）")
        npc_memory = chat_env.get_npc_memory()
        player_memory = chat_env.get_player_memory()
        print(f"NPC记忆数量: {len(npc_memory)}")
        print(f"Player记忆数量: {len(player_memory)}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()




def test_streaming_only():
    """测试流式输出功能（不运行对话，仅测试流式输出）"""
    print("Testing Streaming Output Interface with Scene Selection...")
    
    try:
        # 使用新的场景选择功能创建ChatEnvironment
        chat_env = ChatEnvironment.create_with_scene_selection(
            characters_file="characters.json",
            chat_mode="player_involved",
            enable_player_validation=True,  # 启用player validation以测试casual chat功能
            enable_memory_system=False,  # 禁用memory系统以简化测试
            enable_streaming=True,  # 启用流式输出
            streaming_callback=streaming_callback  # 设置流式输出回调
        )
        
        print("✓ 流式输出功能已启用")
        print(f"可用NPC: {', '.join(chat_env.get_available_npcs())}")
        
        # 测试流式输出
        test_message = "Hello, I'd like to learn more about this place."
        available_npcs = chat_env.get_available_npcs()
        target_npcs = [available_npcs[0]] if available_npcs else []
        
        if not target_npcs:
            print("错误: 没有可用的NPC")
            return
        
        print(f"\n测试消息: {test_message}")
        print(f"目标NPC: {', '.join(target_npcs)}")
        print(f"\n{target_npcs[0]}的回复 (流式输出):")
        
        # 使用流式输出方法
        result = chat_env.set_player_input_streaming(
            message=test_message,
            target_npc=target_npcs,
            streaming_callback=streaming_callback
        )
        
        print(f"\n\n=== 流式输出测试完成 ===")
        print(f"处理结果: {'成功' if result['success'] else '失败'}")
        
        if result['success'] and result['npc_responses']:
            for response in result['npc_responses']:
                print(f"完整回复: {response['response']}")
        
        print("✓ 流式输出接口测试成功")
        
    except Exception as e:
        print(f"Streaming test error: {str(e)}")
        import traceback
        traceback.print_exc()


def test_scene_selection():
    """测试场景选择功能"""
    print("Testing Scene Selection Functionality...")
    
    try:
        # 创建一个临时的ChatEnvironment来测试场景选择
        from npc.scene_control.scene_status import SceneStatus
        
        scene_status = SceneStatus()
        
        # 测试加载所有场景
        if scene_status.load_all_scenes():
            all_scenes = scene_status.get_all_scenes()
            print(f"✓ 成功加载了 {len(all_scenes)} 个场景")
            
            # 显示前几个场景的信息
            print("\n前3个场景预览:")
            for i, scene in enumerate(all_scenes[:3]):
                scene_name = scene.get("name", f"场景{i+1}")
                scene_location = scene.get("location", "未知位置")
                print(f"  {i+1}. {scene_name} - {scene_location}")
            
            # 测试按索引加载场景
            if len(all_scenes) > 0:
                test_index = 0
                if scene_status.load_scene_by_index(test_index):
                    current_scene = scene_status.current_scene
                    print(f"✓ 成功按索引加载场景: {current_scene.get('name', '未知场景')}")
                else:
                    print("✗ 按索引加载场景失败")
            
            print("✓ 场景选择功能测试成功")
        else:
            print("✗ 加载场景列表失败")
            
    except Exception as e:
        print(f"Scene selection test error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("ChatEnvironment Test Suite")
    
    while True:
        print("\n测试选项:")
        print("1. 玩家-NPC对话模式 (Player Involved Mode)")
        print("2. NPC自由对话模式 (NPC Free Chat)")
        print("3. 记忆稳定性测试 (Memory Stability Test)")
        print("4. 流式输出测试 (Streaming Output Test)")
        print("5. 场景选择功能测试 (Scene Selection Test)")
        print("6. 运行所有测试 (Run All Tests)")
        print("7. 退出 (Exit)")
        
        choice = input("请选择 (1-7): ").strip()
        
        if choice == "1":
            test_player_npc_dialogue()
        elif choice == "2":
            test_free_chat()
        elif choice == "3":
            test_memory_stability()
        elif choice == "4":
            test_streaming_only()
        elif choice == "5":
            test_scene_selection()
        elif choice == "6":
            print("运行所有测试...")
            test_scene_selection()
            test_free_chat()
            test_player_npc_dialogue()
            test_memory_stability()
            test_streaming_only()
        elif choice == "7":
            print("退出程序...")
            break
        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    main() 
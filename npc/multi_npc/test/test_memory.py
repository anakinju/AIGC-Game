#!/usr/bin/env python3
"""
ChatEnvironment Memory Stability Test

This test is designed to verify the long-term stability of the ChatEnvironment's memory storage functionality.
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

def test_memory_stability():
    """
    Tests the memory stability of ChatEnvironment over multiple rounds.
    
    This test simulates four distinct conversations to observe the effect of memory across sessions.
    """
    print("Initializing ChatEnvironment for Memory Stability Test...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scene_path = os.path.join(base_dir, "..", "..", "data", "test.json")
    
    if not os.path.exists(scene_path):
        print(f"Error: Scene file not found: {scene_path}")
        return
        
    chat_env = ChatEnvironment(
        scene_path=scene_path,
        characters_file="characters.json",
        chat_mode="player_involved",
        enable_player_validation=False,
        enable_memory_system=True  # 启用memory系统（使用SimpleMemoryInterface）
    )

    # Define the player inputs for each round
    # Round 1: Meaningless greetings with Huang Qiye
    conversation_1_greetings = [
        "Huang Qiye: 你好啊。",
        "Huang Qiye: 今天天气怎么样？",
        "Huang Qiye: 随便聊聊吧。",
        "exit"
    ]
    
    # Round 2: Off-topic questions with Huang Qiye
    conversation_2_off_topic = [
        "Huang Qiye: 你知道什么是人工智能吗?",
        "Huang Qiye: 你对这个世界之外的事情感兴趣吗?",
        "exit"
    ]

    # Round 3: Plot-related questions with Huang Qiye, checking for memory.
    conversation_3_plot_related = [
        "Huang Qiye: 我们刚才是不是聊过天？",
        "Huang Qiye: 你到底是谁？这里是哪里？",
        "Huang Qiye: 告诉我发生了什么，我觉得我好像忘了些事情。",
        "exit"
    ]
    
    # Round 4: Questions for Chou Hu
    conversation_4_chou_hu = [
        "Chou Hu: 你好，请问你是谁？",
        "Chou Hu: 你认识一个叫黄七爷的人吗？他可靠吗？",
        "Chou Hu: 这个地方看起来很奇怪，你知道些什么吗？",
        "exit"
    ]

    # --- Run Test Rounds ---
    try:
        print("--- Starting Round 1/4: Greetings with Huang Qiye ---")
        chat_env.run_test(conversation_1_greetings)
        print("--- Round 1/4 Completed Successfully ---\n")
        chat_env.reset()

        print("--- Starting Round 2/4: Off-topic with Huang Qiye ---")
        chat_env.run_test(conversation_2_off_topic)
        print("--- Round 2/4 Completed Successfully ---\n")
        chat_env.reset()

        print("--- Starting Round 3/4: Plot-related with Huang Qiye ---")
        chat_env.run_test(conversation_3_plot_related)
        print("--- Round 3/4 Completed Successfully ---\n")
        chat_env.reset()

        print("--- Starting Round 4/4: Questions for Chou Hu ---")
        chat_env.run_test(conversation_4_chou_hu)
        print("--- Round 4/4 Completed Successfully ---")
        
    except Exception as e:
        print(f"--- A test round failed: {e} ---")
        import traceback
        traceback.print_exc()
    
    print("\nMemory Stability Test Finished.")

if __name__ == "__main__":
    test_memory_stability() 
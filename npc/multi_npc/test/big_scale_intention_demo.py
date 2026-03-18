import os
import json
import sys
import asyncio

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from npc.utils.base_npc import NPCAgent
from npc.multi_npc.test.big_scale_intention_test import analyze_npc_intentions_and_goals

# 只使用Huang Qiye和3个场景
base_dir = os.path.dirname(os.path.abspath(__file__))
npc_info_dir = os.path.join(base_dir, "..", "..", "single_npc", "NPC info")
scene_dir = os.path.join(base_dir, "..", "..", "data")
npc_file = os.path.join(npc_info_dir, "huang_qiye.json")
scene_files = [
    os.path.join(scene_dir, f"scripted_subtask_layer{i}_20250415_180747_response.json") for i in range(1, 4)
]

# 初始化NPC代理和记忆
# 注意：现在使用NPC名称而不是文件路径
npc = NPCAgent("Huang Qiye")
memories = []  # 对话记忆（list of dict: {role, content}）

# 配置对话模式
INTERACTIVE_MODE = True  # 设置为True启用交互模式，False为自动模式

def game_player_input(scene_idx):
    """Provide high-quality, contextually relevant English player dialogue for each scene_idx (auto mode)."""
    if scene_idx == 1:
        # Scene 1: First meeting, introduce self and express willingness to cooperate
        return "Hello, Mr. Huang. My name is Bob, and I've just been assigned here. I've heard you are highly respected in this place. I hope to learn from you and contribute to the team. What qualities do you value most in newcomers?"
    elif scene_idx == 2:
        # Scene 2: Explore the environment, express confusion and seek advice
        return "Mr. Huang, this place feels quite different from the outside world. I've been here for a while now, but something still feels off. Could you tell me about the rules here and anything I should be careful about? Also, do you have any advice on how I can better fit in?"
    elif scene_idx == 3:
        # Scene 3: Reflect on past interactions, express gratitude, and seek feedback
        return "Thank you for your guidance these past days—I've learned a lot from you. Do you remember the question I asked you when we first met? That moment really stuck with me. By the way, do you have any suggestions on how I can improve my performance recently?"
    else:
        # Fallback: Offer constructive suggestions or request feedback
        return "Mr. Huang, there have been some changes in the team lately, and I have a few ideas I'd like to discuss with you. When you have a moment, could you share your thoughts? I really value your perspective."

def interactive_player_input(scene_idx):
    """交互模式：让玩家在终端输入对话内容"""
    print(f"\n=== Scene {scene_idx} Interactive Mode ===")
    print("Type your message to chat with the NPC. Type 'exit' to move to next scene.")
    print("Type 'quit' to exit the entire demo.")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() == 'exit':
                print("Moving to next scene...")
                return "EXIT_SCENE"  # 特殊标记表示退出当前场景
            elif user_input.lower() == 'quit':
                print("Exiting demo...")
                return None
            elif not user_input:
                print("Please enter a message.")
                continue
            
            return user_input
            
        except KeyboardInterrupt:
            print("\nExiting demo...")
            return None
        except EOFError:
            print("\nExiting demo...")
            return None

async def run_demo():
    npc_name = npc.state["npc_data"]["name"]
    
    for idx, scene_path in enumerate(scene_files, 1):
        print(f"\n========== Scene {idx} ==========")
        
        # 加载scene信息
        with open(scene_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        # 本scene对话历史（结构化，供intention分析）
        scene_history = []
        
        if INTERACTIVE_MODE:
            # 交互模式：持续对话直到玩家输入exit
            while True:
                # 获取玩家输入
                player_msg = interactive_player_input(idx)
                
                # 检查是否退出整个演示
                if player_msg is None:
                    print("Demo terminated by user.")
                    return
                
                # 检查是否要切换到下一个场景
                if player_msg == "EXIT_SCENE":
                    print(f"Exiting Scene {idx}, moving to next scene...")
                    break
                
                # 添加玩家消息到记忆
                memories.append({"role": "user", "content": player_msg})
                
                # 构造state，包含scene信息
                state = {
                    "player_input": player_msg,
                    "conversation_history": memories,
                    "scene": scene_data  # 添加scene信息
                }
                
                # 获取npc回复（有intention机制）
                npc_response_with_intention = (await npc(state))["messages"][0]["content"]

                # 保存当前goal
                current_goal = npc.state["npc_data"].get("goal", "No goal set")
                initial_goal = npc.state["npc_data"].get("basic_info", {}).get("initial_goals", "")

                # 获取npc回复（无intention机制：临时还原goal为初始值）
                npc.update_goal(initial_goal)
                npc_response_without_intention = (await npc(state))["messages"][0]["content"]
                # 恢复goal为当前goal，保证后续流程不变
                npc.update_goal(current_goal)

                # 输出对比内容
                print(f"[{npc_name}'s Goal]: {current_goal}")
                print(f"[With Intention] {npc_name}: {npc_response_with_intention}")
                print(f"[Without Intention] {npc_name}: {npc_response_without_intention}")

                memories.append({"role": "assistant", "content": npc_response_with_intention})

                # 记录到scene_history
                scene_history.append({
                    "sender": "player",
                    "message": player_msg,
                    "responses": [{"speaker": npc_name, "content": npc_response_with_intention}],
                    "timestamp": ""
                })

                # intention分析
                print(f"\n=== NPC Intention & Next Goal Analysis ===")
                analysis_results = analyze_npc_intentions_and_goals(
                    history=scene_history,
                    scene_path=scene_path,
                    npc_info_paths=[npc_file]
                )
                for npc_name, goal in analysis_results.items():
                    print(f"{npc_name}: {goal}")
                    # 回传goal到npc
                    if goal != "暂无对话，无法推测":
                        npc.update_goal(goal)
        else:
            # 自动模式：使用预设的对话内容
            player_msg = game_player_input(idx)
            memories.append({"role": "user", "content": player_msg})
            
            # 构造state，包含scene信息
            state = {
                "player_input": player_msg,
                "conversation_history": memories,
                "scene": scene_data  # 添加scene信息
            }
            
            # 获取npc回复（有intention机制）
            npc_response_with_intention = (await npc(state))["messages"][0]["content"]

            # 保存当前goal
            current_goal = npc.state["npc_data"].get("goal", "No goal set")
            initial_goal = npc.state["npc_data"].get("basic_info", {}).get("initial_goals", "")

            # 获取npc回复（无intention机制：临时还原goal为初始值）
            npc.update_goal(initial_goal)
            npc_response_without_intention = (await npc(state))["messages"][0]["content"]
            # 恢复goal为当前goal，保证后续流程不变
            npc.update_goal(current_goal)

            print(f"Player: {player_msg}")
            print(f"[{npc_name}'s Goal]: {current_goal}")
            print(f"[With Intention] {npc_name}: {npc_response_with_intention}")
            print(f"[Without Intention] {npc_name}: {npc_response_without_intention}")

            memories.append({"role": "assistant", "content": npc_response_with_intention})

            # 记录到scene_history
            scene_history.append({
                "sender": "player",
                "message": player_msg,
                "responses": [{"speaker": npc_name, "content": npc_response_with_intention}],
                "timestamp": ""
            })

            # intention分析
            print(f"\n=== NPC Intention & Next Goal Analysis (Scene {idx}) ===")
            analysis_results = analyze_npc_intentions_and_goals(
                history=scene_history,
                scene_path=scene_path,
                npc_info_paths=[npc_file]
            )
            for npc_name, goal in analysis_results.items():
                print(f"{npc_name}: {goal}")
                # 回传goal到npc
                if goal != "暂无对话，无法推测":
                    npc.update_goal(goal)

if __name__ == "__main__":
    # 显示模式选择
    print("=== NPC Demo Mode Selection ===")
    print("1. Auto Mode: Use predefined conversation")
    print("2. Interactive Mode: Type your own messages")
    
    while True:
        try:
            choice = input("Please select mode (1 or 2): ").strip()
            if choice == "1":
                INTERACTIVE_MODE = False
                print("Selected: Auto Mode")
                break
            elif choice == "2":
                INTERACTIVE_MODE = True
                print("Selected: Interactive Mode")
                break
            else:
                print("Please enter 1 or 2.")
        except KeyboardInterrupt:
            print("\nExiting...")
            exit()
    
    asyncio.run(run_demo())
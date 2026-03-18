import os
import sys
import json
from dotenv import load_dotenv

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

from npc.multi_npc.chat_env import ChatEnvironment

def test_update_npc_intention_to_goal():
    """测试update_npc_intention_to_goal功能"""
    print("=== 测试 update_npc_intention_to_goal 功能 ===")
    
    # 设置路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scene_path = os.path.join(base_dir, "..", "data", "npc_only_scene.json")
    characters_file = os.path.join(base_dir, "..", "single_npc", "NPC info", "characters.json")
    
    # 检查文件是否存在
    if not os.path.exists(scene_path):
        print(f"错误: 场景文件不存在: {scene_path}")
        return
    
    if not os.path.exists(characters_file):
        print(f"错误: 角色文件不存在: {characters_file}")
        return
    
    try:
        # 创建ChatEnvironment实例
        chat_env = ChatEnvironment(
            scene_path=scene_path,
            characters_file=characters_file,
            chat_mode="player_involved"
        )
        
        print("✓ ChatEnvironment 初始化成功")
        
        # 创建模拟的对话历史
        mock_history = [
            {
                "sender": "player",
                "message": "I just witnessed something terrible. Alice physically assaulted a poor citizen in the alley.",
                "responses": [
                    {"speaker": "Meredith Stout", "content": "That's absolutely horrifying! I can't believe Alice would do such a thing. We need to report this immediately."},
                    {"speaker": "Jackie Welles", "content": "Are you sure about what you saw? This is a serious accusation."}
                ],
                "timestamp": "2024-01-01T10:00:00"
            },
            {
                "sender": "player", 
                "message": "Yes, I'm certain. I saw it with my own eyes.",
                "responses": [
                    {"speaker": "Meredith Stout", "content": "We must take action. Alice cannot be allowed to get away with this violence."},
                    {"speaker": "Jackie Welles", "content": "I understand your concern, but we should gather more evidence before making any decisions."}
                ],
                "timestamp": "2024-01-01T10:05:00"
            }
        ]
        
        print("✓ 模拟对话历史创建成功")
        
        # 创建临时的NPC信息文件路径列表
        # 从characters.json中提取NPC信息并创建临时文件
        temp_npc_files = []
        try:
            with open(characters_file, 'r', encoding='utf-8') as f:
                characters_data = json.load(f)
            
            # 获取场景中的NPC名称
            with open(scene_path, 'r', encoding='utf-8') as f:
                scene_data = json.load(f)
            
            scene_npcs = list(scene_data.get("npc_emotion_pools", {}).keys())
            
            # 为场景中的每个NPC创建临时文件
            for npc_name in scene_npcs:
                # 在characters_data中查找对应的NPC信息
                npc_info = None
                if isinstance(characters_data, list):
                    for npc in characters_data:
                        if npc.get("name") == npc_name:
                            npc_info = npc
                            break
                elif isinstance(characters_data, dict):
                    npc_info = characters_data.get(npc_name)
                
                if npc_info:
                    temp_file = os.path.join(base_dir, f"temp_{npc_name.replace(' ', '_')}.json")
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(npc_info, f, ensure_ascii=False, indent=2)
                    temp_npc_files.append(temp_file)
                    print(f"✓ 创建临时NPC文件: {temp_file}")
        
        except Exception as e:
            print(f"创建临时NPC文件失败: {e}")
            return
        
        try:
            # 测试update_npc_intention_to_goal方法
            print("\n=== 开始测试 update_npc_intention_to_goal ===")
            updated_goals = chat_env.update_npc_intention_to_goal(
                history=mock_history,
                scene_path=scene_path,
                npc_info_paths=temp_npc_files
            )
            
            print(f"\n=== 更新结果 ===")
            for npc_name, goal in updated_goals.items():
                print(f"{npc_name}: {goal}")
            
            # 验证NPC的goal是否已更新
            print(f"\n=== 验证NPC目标更新 ===")
            for npc_name in updated_goals.keys():
                if npc_name in chat_env.npc_behaviors:
                    npc_behavior = chat_env.npc_behaviors[npc_name]
                    if hasattr(npc_behavior, 'agent') and hasattr(npc_behavior.agent, 'state'):
                        current_goal = npc_behavior.agent.state.get("npc_data", {}).get("goal", "未找到目标")
                        print(f"{npc_name} 当前目标: {current_goal}")
                    else:
                        print(f"{npc_name}: 无法访问agent状态")
                else:
                    print(f"{npc_name}: 未找到对应的behavior")
            
            print("\n✓ update_npc_intention_to_goal 测试完成")
            
        finally:
            # 清理临时文件
            for temp_file in temp_npc_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"✓ 清理临时文件: {temp_file}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_update_npc_intention_to_goal() 
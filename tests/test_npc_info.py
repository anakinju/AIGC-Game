import os
import sys
import json

# 将项目根目录添加到 sys.path，以便导入 npc 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.npc_info import NPCInfoLoader

def test_npc_info_extraction(npc_name: str):
    print(f"\n" + "="*50)
    print(f"Testing NPC: {npc_name}")
    print("="*50)
    
    loader = NPCInfoLoader(npc_name)
    
    # 1. Get info for casual chat
    print("\n[Casual Chat Info]")
    casual_info = loader.get_info_for_casual_chat()
    print(json.dumps(casual_info, indent=2, ensure_ascii=False))
    
    # 2. Get info for angry response
    print("\n[Angry Response Info]")
    angry_info = loader.get_info_for_angry_response()
    print(json.dumps(angry_info, indent=2, ensure_ascii=False))
    
    # 3. Get info for intention
    print("\n[Intention Info]")
    intention_info = loader.get_info_for_intention()
    print(json.dumps(intention_info, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    # 测试几个典型的 NPC
    test_npcs = ["Haruko", "Chouhu", "Huang Qiye"]
    
    for npc in test_npcs:
        test_npc_info_extraction(npc)

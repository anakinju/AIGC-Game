import asyncio
import sys
import os
import json
from typing import Dict, Any

# 将项目根目录添加到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.emotion_manager import EmotionManager

async def test_emotion_analysis_performance():
    """
    测试 EmotionManager 的 CoT 和 Guidance 生成性能
    """
    manager = EmotionManager(llm_model="gpt-4o-mini")
    
    # 模拟不同的测试场景
    test_cases = [
        {
            "name": "Friendly Interaction",
            "npc": "Elena",
            "personality": ["Kind", "Helpful", "Easily moved"],
            "history": [
                {"speaker": "Player", "content": "Elena, you look wonderful today. Thank you for all your help!"}
            ]
        },
        {
            "name": "Rude/Provocative Interaction",
            "npc": "Elena",
            "personality": ["Kind", "Helpful", "Easily moved"],
            "history": [
                {"speaker": "Player", "content": "Elena, why are you so slow? You're just a burden to this team."}
            ]
        },
        {
            "name": "Mysterious/Suspicious Interaction",
            "npc": "Kael",
            "personality": ["Cynical", "Sharp", "Protective"],
            "history": [
                {"speaker": "Player", "content": "I know what you're hiding in that basement, Kael. Don't try to lie to me."}
            ]
        }
    ]

    print("=== Starting Emotion Manager CoT Performance Test ===\n")

    for case in test_cases:
        print(f"--- Scenario: {case['name']} ---")
        print(f"NPC: {case['npc']} | Personality: {case['personality']}")
        print(f"Player said: \"{case['history'][-1]['content']}\"")
        
        # 构造模拟 state
        state = {
            "message_store": case['history'],
            "npc_states": {
                case['npc']: {
                    "dynamic_state": {"emotion": "Calm"}
                }
            },
            "npc_state": {} # 兼容旧结构
        }
        
        # 运行分析
        start_time = asyncio.get_event_loop().time()
        result = await manager.update_emotion_async(case['npc'], state)
        end_time = asyncio.get_event_loop().time()
        
        # 打印结果
        print(f"\n[Result]")
        print(f"Emotion: {result.get('emotion')} (Intensity: {result.get('intensity')})")
        print(f"Reasoning: {result.get('reasoning')}")
        print(f"Guidance: {result.get('guidance')}")
        
        if "thought_process" in result:
            print(f"\n[CoT Thought Process]")
            tp = result["thought_process"]
            print(f"  - Interpretation: {tp.get('interpretation')}")
            print(f"  - Trigger: {tp.get('trigger')}")
            print(f"  - Internal Reaction: {tp.get('internal_reaction')}")
            
        print(f"\nLatency: {end_time - start_time:.2f}s")
        print("-" * 50 + "\n")

if __name__ == "__main__":
    asyncio.run(test_emotion_analysis_performance())

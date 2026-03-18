import unittest
import os
from dotenv import load_dotenv
from datetime import datetime
from npc.multi_npc.player_node import PlayerNode

# 加载环境变量以获取 API KEY
load_dotenv()

class TestAngryFlowWithValidator(unittest.TestCase):
    """
    集成测试：调用真实的 PlayerValidator (LLM) 来测试愤怒逻辑流转。
    注意：运行此测试需要有效的 OPENAI_API_KEY。
    """
    
    def setUp(self):
        # 模拟真实的场景数据，以便 LLM 理解上下文
        self.scene_data = {
            "name": "The Secret Library",
            "location": "Library Archive",
            "time": "Midnight",
            "current_topic": "Finding the forbidden scroll",
            "interactive_npc": [
                {
                    "name": "Haruko", 
                    "goal": "Ensure only worthy people access the forbidden scroll",
                    "npc_background": {"role": "Guardian of the Library"}
                }
            ],
            "trigger_conditions": {"additional_conditions": "Player must show respect"},
            "scene_end_state_reference": {"success": "Player gets the scroll"},
            "worldstate_tasks": [{"expected_text": "Ask about the scroll"}]
        }
        self.player_node = PlayerNode(self.scene_data)
        
        # 基础状态
        self.base_state = {
            "sender": "player",
            "message": "",
            "current_turn": 1,
            "chat_group": ["Haruko", "player"],
            "scene_id": "secret_library_scene",
            "scene_timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "remaining_turns": 10,
            "npc_state": {
                "npc_relationships": [
                    {
                        "character1": "Haruko",
                        "character2": "player", 
                        "category": "Neutral", 
                        "emotion_modifier": "Calm",
                        "intensity": 0.5
                    }
                ],
                "angry": False,
                "angry_level": 0
            },
            "scene_context": {
                "key_questions": "Where is the scroll?",
                "npc_purposes": {"Haruko": "Protect the library"},
                "npc_background": {"Haruko": {"role": "Guardian"}},
                "npc_emotions": {"Haruko": "Neutral"}
            }
        }

    def test_real_validator_angry_flow(self):
        """
        使用真实的 LLM 验证器测试完整的愤怒流转逻辑。
        """
        print("\n--- Starting Real LLM Integration Test ---")

        # --- 步骤 1: 触发愤怒 (通过多次输入无关内容) ---
        # 我们手动设置一次 force_exit 触发，或者模拟多次调用。
        # 这里为了测试 PlayerNode 的逻辑，我们直接模拟一个会被判定为 NOT_STORY_RELEVANT 的输入
        # 并通过多次循环直到触发 force_exit (Validator 内部有计数器)
        
        current_state = self.base_state.copy()
        
        print("Step 1: Sending nonsense to trigger anger...")
        # 连续发送 3 次无关内容 (Validator 默认 2 次触发 force_exit)
        for i in range(3):
            current_state["message"] = "What is the best pizza topping in the real world?"
            current_state = self.player_node(current_state)
            validation = current_state.get("player_validation", {})
            print(f"  Turn {i+1} Category: {validation.get('category')}, Counter: {validation.get('irrelevance_count')}, Force Exit: {validation.get('force_exit')}")
            
        self.assertTrue(current_state["npc_state"]["angry"], "NPC should be angry now")
        self.assertEqual(current_state["npc_state"]["angry_level"], 3)
        print(f"Step 1 Result: Angry level is {current_state['npc_state']['angry_level']}")

        # --- 步骤 2: 仅道歉 (期待 Level 3 -> 2) ---
        print("\nStep 2: Sending a pure apology...")
        current_state["message"] = "I am very sorry for my rude behavior. Please forgive me."
        current_state = self.player_node(current_state)
        
        validation = current_state.get("player_validation", {})
        print(f"  Validation Category: {validation.get('category')}")
        print(f"  Is Apology (LLM): {validation.get('is_apology')}")
        
        self.assertEqual(current_state["npc_state"]["angry_level"], 2, "Level should drop to 2 after apology")
        print(f"Step 2 Result: Angry level is {current_state['npc_state']['angry_level']}")

        # --- 步骤 3: 道歉 + 回归正题 (期待 Level 2 -> 0) ---
        print("\nStep 3: Sending apology + story relevant message...")
        current_state["message"] = "I apologize again. I really need to know where the forbidden scroll is kept."
        current_state = self.player_node(current_state)
        
        validation = current_state.get("player_validation", {})
        print(f"  Validation Category: {validation.get('category')}")
        print(f"  Is Apology (LLM): {validation.get('is_apology')}")
        
        self.assertFalse(current_state["npc_state"]["angry"], "NPC should no longer be angry")
        self.assertEqual(current_state["npc_state"]["angry_level"], 0)
        print(f"Step 3 Result: Angry level is {current_state['npc_state']['angry_level']}, NPC is calm.")

if __name__ == '__main__':
    # 检查是否有 API KEY
    if not os.getenv("OPENAI_API_KEY"):
        print("Skipping test: OPENAI_API_KEY not found in environment.")
    else:
        unittest.main()

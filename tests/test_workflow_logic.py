import asyncio
import logging
from typing import Dict, Any, List
from npc.multi_npc.router_node import RouterNode
from npc.single_npc.npc_node import NPCNode
from npc.utils.constants import ChatMode
from npc.utils.base_npc import NPCAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockNPCAgent(NPCAgent):
    def __init__(self, name: str):
        self.name = name
        self.llm = type('MockLLM', (), {'ainvoke': self.mock_ainvoke, 'invoke': self.mock_ainvoke})
        self.state = {}
    
    async def mock_ainvoke(self, messages):
        return type('MockResponse', (), {'content': '{"action": {"id": "RESPOND"}, "utterance": "Mock response from ' + self.name + '", "real_intent": "Testing"} '})

class MockToolManager:
    def register_tool(self, tool): pass
    def get_all_tools(self): return []

async def test_workflow_logic():
    print("\n" + "="*50)
    print("STARTING WORKFLOW LOGIC TEST")
    print("="*50)

    router = RouterNode()
    
    # Setup common state
    chat_group = ["Haruko", "Chou Hu", "player"]
    scene_context = {
        "environment": "Test Room",
        "interactive_npc": [
            {"name": "Haruko", "goal": "Talk about tea"},
            {"name": "Chou Hu", "goal": "Talk about business"}
        ]
    }

    # --- TEST 1: CASUAL CHAT MODE ---
    print("\n[TEST 1] CASUAL CHAT MODE")
    print("Scenario: Player talks to Haruko about weather (Off-topic)")
    
    state_casual = {
        "msg_type": "new",
        "sender": "player",
        "message": "Nice weather today!",
        "chat_group": chat_group,
        "scene_context": scene_context,
        "responders": ["Haruko"], # Player specifically targets Haruko
        "player_validation": {"category": "NOT_STORY_RELEVANT"},
        "npc_state": {"angry_level": 0},
        "remaining_turns": 5
    }

    # 1. Route the new message
    state_casual = router(state_casual)
    print(f"Mode selected: {state_casual['chat_mode']}")
    print(f"Responders assigned: {state_casual['responders']}")
    
    # VERIFICATION: In Casual Chat, only the target (Haruko) should be a responder
    assert state_casual["chat_mode"] == ChatMode.CASUAL_CHAT
    assert state_casual["responders"] == ["Haruko"]
    print("[OK] VERIFIED: Only target NPC is assigned as responder in Casual Chat.")

    # --- TEST 2: PLAYER INVOLVED MODE ---
    print("\n[TEST 2] PLAYER INVOLVED MODE")
    print("Scenario: Player talks to Haruko about the secret ritual (Story-relevant)")
    
    state_involved = {
        "msg_type": "new",
        "sender": "player",
        "message": "Tell me about the ritual.",
        "chat_group": chat_group,
        "scene_context": scene_context,
        "responders": ["Haruko"], # Player targets Haruko
        "player_validation": {"category": "STORY_RELEVANT"},
        "npc_state": {"angry_level": 0},
        "remaining_turns": 5
    }

    # 1. Route the new message
    state_involved = router(state_involved)
    print(f"Mode selected: {state_involved['chat_mode']}")
    print(f"Responders assigned: {state_involved['responders']}")
    
    # VERIFICATION: In Player Involved, ALL NPCs should be responders for emotion analysis
    assert state_involved["chat_mode"] == ChatMode.PLAYER_INVOLVED
    assert set(state_involved["responders"]) == {"Haruko", "Chou Hu"}
    assert state_involved["primary_responders"] == ["Haruko"]
    print("[OK] VERIFIED: All NPCs assigned as responders for emotion analysis.")
    print(f"[OK] VERIFIED: Primary responder correctly identified as {state_involved['primary_responders']}.")

    # --- TEST 3: NPC NODE EXECUTION LOGIC (MOCKED) ---
    print("\n[TEST 3] NPC NODE EXECUTION (Internal Logic Check)")
    
    # We will manually check the logic we implemented in NPCNode.__call_async__
    # For Haruko (Primary)
    print("Checking Haruko (Primary) in Player Involved...")
    # Logic: Haruko is in responders AND is in primary_responders -> Should generate response
    
    # For Chou Hu (Background)
    print("Checking Chou Hu (Background) in Player Involved...")
    # Logic: Chou Hu is in responders BUT NOT in primary_responders -> Should skip response generation (return state)
    
    print("\nSummary of logic to be verified in actual runtime:")
    print("1. Casual Chat: Only Haruko node is called. Chou Hu node is never triggered.")
    print("2. Player Involved: Haruko node is called -> Generates response.")
    print("3. Player Involved: Chou Hu node is called -> Runs emotion analysis -> Skips response generation.")

    print("\n" + "="*50)
    print("WORKFLOW LOGIC TEST COMPLETED")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_workflow_logic())

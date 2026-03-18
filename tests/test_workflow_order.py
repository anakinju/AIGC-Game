import os
import sys
import asyncio
import json
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
if not os.getenv("LANGCHAIN_API_KEY"):
    print("Warning: LANGCHAIN_API_KEY not found in environment. Tracing may not work.")

from npc.multi_npc.router_strategies import PlayerInvolvedStrategy
from npc.multi_npc.managers.emotion_manager import EmotionManager
from npc.utils.constants import ChatMode

async def test_workflow_order():
    """
    Test the complete workflow: target_npc processes first with EmotionAnalyzer,
    then background NPCs process with SimpleEmotionAnalyzer.
    """
    print("\n=== Testing Complete Workflow Order ===")
    
    # Initialize managers
    strategy = PlayerInvolvedStrategy()
    emotion_manager = EmotionManager(llm_model="gpt-4o-mini")
    
    # 1. Simulate player message processing by router
    initial_state = {
        "sender": "player",
        "message": "Hey Haruko, what are you working on? Tanaka, are you listening?",
        "chat_group": ["player", "Haruko", "Tanaka"],
        "chat_mode": ChatMode.PLAYER_INVOLVED,
        "message_store": [],
        "current_turn": 1
    }
    
    print("1. Router processing player message...")
    processed_state = strategy._handle_player_message(initial_state)
    
    print(f"   - Target NPC: {processed_state.get('target_npc')}")
    print(f"   - Responders: {processed_state.get('responders')}")
    print(f"   - Chat Group: {processed_state.get('chat_group')}")
    
    # 2. Simulate target NPC processing (Haruko)
    print("\n2. Processing Target NPC (Haruko)...")
    target_result = await emotion_manager.update_emotion_async(
        "Haruko", processed_state, is_background=False
    )
    print(f"   - Emotion: {target_result.get('emotion')} (Intensity: {target_result.get('intensity')})")
    print(f"   - Has CoT thought_process: {bool(target_result.get('thought_process'))}")
    
    # 3. Simulate background NPC processing (Tanaka)
    print("\n3. Processing Background NPC (Tanaka)...")
    bg_result = await emotion_manager.update_emotion_async(
        "Tanaka", processed_state, is_background=True
    )
    print(f"   - Emotion: {bg_result.get('emotion')} (Intensity: {bg_result.get('intensity')})")
    print(f"   - Simple analyzer used: {not bg_result.get('thought_process')}")
    
    # 4. Verify state updates
    print("\n4. Verifying state updates...")
    if f"emotion_analysis_Haruko" in processed_state:
        print("   [OK] Target NPC emotion stored in state")
    else:
        print("   [FAIL] Target NPC emotion not found in state")
        
    if f"emotion_analysis_Tanaka" in processed_state:
        print("   [OK] Background NPC emotion stored in state")
    else:
        print("   [FAIL] Background NPC emotion not found in state")
    
    # 5. Test non-PLAYER_INVOLVED mode (should skip)
    print("\n5. Testing mode restriction (CASUAL_CHAT)...")
    casual_state = {**processed_state, "chat_mode": ChatMode.CASUAL_CHAT}
    
    # This would be skipped in BaseNPCNode logic
    print("   [SIMULATED] Both NPCs would skip emotion analysis in CASUAL_CHAT mode")
    
    print("\n=== Workflow Order Test Completed ===")

if __name__ == "__main__":
    asyncio.run(test_workflow_order())
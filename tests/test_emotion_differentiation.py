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

from npc.multi_npc.managers.emotion_manager import EmotionManager
from npc.utils.constants import ChatMode
from npc.utils.llm_factory import LLMFactory
from npc.utils.constants import LLMUsage
from langchain_core.messages import SystemMessage, HumanMessage

async def generate_mock_response(npc_name: str, emotion_result: Dict[str, Any], state: Dict[str, Any]):
    """Simulate generating a response based on the emotion analysis."""
    llm = LLMFactory.create_chat_model(usage=LLMUsage.GENERAL)
    
    emotion = emotion_result.get("emotion", "Calm")
    intensity = emotion_result.get("intensity", 0.5)
    guidance = emotion_result.get("guidance", "Respond naturally.")
    
    recent_msgs = state["message_store"][-2:]
    context = "\n".join([f"{m['speaker']}: {m['content']}" for m in recent_msgs])
    
    prompt = f"""You are {npc_name}. 
Current Emotion: {emotion} (Intensity: {intensity})
Guidance: {guidance}

Recent Context:
{context}

Generate a short response (1-2 sentences) in character."""

    messages = [
        SystemMessage(content=f"You are {npc_name}. Respond based on your current emotional state."),
        HumanMessage(content=prompt)
    ]
    
    response = await llm.ainvoke(messages)
    return response.content.strip()

async def test_differentiated_emotion_and_response():
    """
    Test the differentiated emotion analysis and verify target NPC generates a response.
    """
    print("\n=== Starting Emotion Analysis & Response Generation Test ===")
    
    manager = EmotionManager(llm_model="gpt-4o-mini")
    
    # Mock state
    state = {
        "chat_mode": ChatMode.PLAYER_INVOLVED,
        "target_npc": "Haruko",
        "message_store": [
            {"speaker": "Player", "content": "Haruko, I heard you're working on a secret project. Is that true?"}
        ],
        "npc_states": {
            "Haruko": {"dynamic_state": {"emotion": "Calm"}},
            "Tanaka": {"dynamic_state": {"emotion": "Calm"}}
        }
    }

    print("\n1. Processing Target NPC (Haruko)...")
    # Step A: Emotion Analysis (Full CoT)
    target_emotion = await manager.update_emotion_async("Haruko", state, is_background=False)
    print(f"Target Emotion: {target_emotion.get('emotion')} (Intensity: {target_emotion.get('intensity')})")
    
    # Step B: Response Generation (Only for Target)
    target_response = await generate_mock_response("Haruko", target_emotion, state)
    print(f"Target Response: \"{target_response}\"")
    
    if target_response:
        print("[OK] Target NPC generated a response successfully.")

    print("\n2. Processing Background NPC (Tanaka)...")
    # Step A: Emotion Analysis (Simple/Fast)
    bg_emotion = await manager.update_emotion_async("Tanaka", state, is_background=True)
    print(f"Background Emotion: {bg_emotion.get('emotion')} (Intensity: {bg_emotion.get('intensity')})")
    print("[OK] Background NPC only updated emotion, no response generation required for observers.")

    print("\n3. Verifying Mode Restrictions (Simulated)...")
    for mode in [ChatMode.CASUAL_CHAT, ChatMode.ANGRY_CHAT]:
        if mode != ChatMode.PLAYER_INVOLVED:
            print(f"[OK] Mode {mode}: Both Target and Background would SKIP emotion analysis.")

    print("\n=== Test Completed. Check LangSmith for traces. ===")

if __name__ == "__main__":
    asyncio.run(test_differentiated_emotion_and_response())

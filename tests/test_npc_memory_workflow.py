import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables before importing other modules
load_dotenv()

from npc.knowledge.npc_memory_manager import NPCMemoryManager
from npc.knowledge.memory_synthesizer import MemorySynthesizer

async def test_npc_memory_workflow():
    print("=== Starting NPC Memory Workflow Test (Corporate Mission) ===")
    
    # 1. Setup
    npc_name = "Haruko"
    scene_name = "Corporate Office - Mission Briefing"
    memory_manager = NPCMemoryManager()
    synthesizer = MemorySynthesizer()
    
    # Clear previous logs for a clean test
    memory_manager.clear_logs(npc_name)
    print(f"1. Setup complete. Testing with NPC: {npc_name} in {scene_name}")

    # 2. Simulate a conversation with emotional shifts
    # Turn 1: Haruko is professional and ready to give a mission
    turn1_emotion = {
        "emotion": "Calm",
        "intensity": 0.5,
        "thought_process": "I have the briefing ready. The player just arrived. Let's get down to business efficiently.",
        "guidance": "Present the mission details clearly and professionally."
    }
    memory_manager.append_emotion_analysis(npc_name, turn1_emotion, turn=1)
    
    # Turn 3: Player starts talking about irrelevant things (distraction)
    turn3_emotion = {
        "emotion": "Angry",
        "intensity": 0.8,
        "thought_process": "This is a high-stakes corporate mission, and they are wasting my time with nonsense about their lunch? This is incredibly unprofessional. I'm losing my patience.",
        "guidance": "Sharply remind the player that time is money and the mission is urgent."
    }
    memory_manager.append_emotion_analysis(npc_name, turn3_emotion, turn=3)
    
    # Turn 5: Player apologizes and accepts the mission
    turn5_emotion = {
        "emotion": "Calm",
        "intensity": 0.6,
        "thought_process": "They finally apologized and took the briefing seriously. At least they know when they've crossed a line. I hope their field work is better than their social skills.",
        "guidance": "Acknowledge the apology briefly and finalize the mission assignment."
    }
    memory_manager.append_emotion_analysis(npc_name, turn5_emotion, turn=5)
    
    print("2. Simulated 3 turns of emotional shifts (Professional -> Angry -> Reconciliation).")

    # 3. Define the WorldState summary (objective facts)
    world_state_summary = """
    Haruko met the player at the corporate headquarters to assign a new mission. 
    The player initially engaged in irrelevant small talk, which delayed the briefing. 
    After a stern warning from Haruko, the player apologized for the distraction. 
    The player officially accepted the mission and received the necessary clearance codes.
    """
    print("3. Defined WorldState objective summary.")

    # 4. Run the Synthesis
    print("4. Running Memory Synthesis (calling LLM)...")
    synthesized_memory = await synthesizer.synthesize_scene_knowledge(
        npc_name=npc_name,
        world_state_summary=world_state_summary,
        scene_name=scene_name
    )
    
    print("\n" + "="*50)
    print("SYNTHESIZED NPC MEMORY OUTPUT:")
    print("="*50)
    print(synthesized_memory)
    print("="*50 + "\n")

    # 5. Verification
    logs = memory_manager.get_recent_logs(npc_name)
    print(f"5. Verification: Found {len(logs)} emotional logs in {npc_name}'s file.")
    
    if len(synthesized_memory) > 50 and npc_name in synthesized_memory or "I " in synthesized_memory:
        print("Result: SUCCESS - The memory was synthesized in first person and seems rich in detail.")
    else:
        print("Result: WARNING - The memory output seems short or missing first-person perspective.")

if __name__ == "__main__":
    asyncio.run(test_npc_memory_workflow())

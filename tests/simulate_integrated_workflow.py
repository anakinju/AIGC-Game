import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from npc.utils.emotion_analyzer import EmotionAnalyzer
from npc.knowledge.npc_memory_manager import NPCMemoryManager
from npc.knowledge.memory_synthesizer import MemorySynthesizer
from npc.worldstate.system import WorldStateSystem
from npc.worldstate.generator import WorldStateGenerator

async def simulate_real_world_workflow():
    print("=== Starting Real-World Integration Test: Haruko's Office Mission ===")
    
    # 1. Initialize Components
    npc_name = "Haruko"
    scene_name = "Corporate HQ - Level 42"
    
    emotion_analyzer = EmotionAnalyzer(llm_model="gpt-4o-mini")
    memory_manager = NPCMemoryManager()
    synthesizer = MemorySynthesizer()
    
    # Simple WorldState setup for simulation
    def dummy_ai_gen(prompt):
        # Mocking the AI generator for WorldState to keep it focused on the test
        if "lunch" in prompt.lower():
            return {"scene_summary": "The player distracted Haruko with talk about lunch.", "states": [{"text": "Player was unprofessional"}]}
        elif "apologize" in prompt.lower() or "sorry" in prompt.lower():
            return {"scene_summary": "The player apologized and Haruko assigned the mission.", "states": [{"text": "Mission 'Project X' accepted"}]}
        return {"scene_summary": "Haruko and the player discussed a mission.", "states": []}

    world_state_system = WorldStateSystem(
        ai_generate_function=dummy_ai_gen,
        embedding_function=lambda x: [0.0]*1536,
        ai_judge_function=lambda x: {"matched": False}
    )

    memory_manager.clear_logs(npc_name)
    
    # 2. Simulate Dialogue and Emotion Analysis
    # We'll simulate 3 turns of actual interaction
    
    dialogue_history = []
    
    # Turn 1: Haruko starts
    print("\n[Turn 1] Haruko: Welcome. I have the briefing for Project X ready. Are you prepared?")
    dialogue_history.append({"speaker": "Haruko", "content": "Welcome. I have the briefing for Project X ready. Are you prepared?"})
    
    # Turn 2: Player distracts
    player_msg = "Wait, before that, did you see the new ramen place downstairs? I'm starving."
    print(f"[Turn 2] Player: {player_msg}")
    dialogue_history.append({"speaker": "Player", "content": player_msg})
    
    # ANALYZE EMOTION (Real call to EmotionAnalyzer)
    state = {"message_store": dialogue_history, "npc_states": {npc_name: {"dynamic_state": {"emotion": "Calm"}}}}
    emotion_result = await emotion_analyzer.analyze_interaction_async(npc_name, state)
    memory_manager.append_emotion_analysis(npc_name, emotion_result, turn=2)
    print(f"--- Haruko's Emotion: {emotion_result['emotion']} (Intensity: {emotion_result['intensity']}) ---")
    print(f"--- Internal Thought: {emotion_result['thought_process'].get('internal_reaction', '')} ---")

    # Turn 3: Haruko reacts (Simulated response based on guidance)
    haruko_react = "This is not a social club. Project X is a priority. Either focus or leave."
    print(f"[Turn 3] Haruko: {haruko_react}")
    dialogue_history.append({"speaker": "Haruko", "content": haruko_react})
    
    # Turn 4: Player apologizes
    player_msg_2 = "I'm sorry, Haruko. You're right. I'm ready for the briefing now. Let's do this."
    print(f"[Turn 4] Player: {player_msg_2}")
    dialogue_history.append({"speaker": "Player", "content": player_msg_2})
    
    # ANALYZE EMOTION AGAIN
    state["message_store"] = dialogue_history
    state["npc_states"][npc_name]["dynamic_state"]["emotion"] = emotion_result['emotion']
    emotion_result_2 = await emotion_analyzer.analyze_interaction_async(npc_name, state)
    memory_manager.append_emotion_analysis(npc_name, emotion_result_2, turn=4)
    print(f"--- Haruko's Emotion: {emotion_result_2['emotion']} (Intensity: {emotion_result_2['intensity']}) ---")
    print(f"--- Internal Thought: {emotion_result_2['thought_process'].get('internal_reaction', '')} ---")

    # Turn 5: Simulate a SYSTEM RULE trigger (Automatic Anger)
    print("\n[Turn 5] (System Rule Triggered: Player off-topic 3 times)")
    memory_manager.log_system_event(
        npc_name=npc_name,
        emotion="Angry",
        intensity=0.95,
        internal_thought="[SYSTEM] Player has ignored my warnings multiple times. My patience is zero. I am terminating this pleasantry.",
        turn=5
    )
    print("--- System Event Logged: Automatic Anger due to rule violation ---")

    # 3. WorldState Settlement
    chat_log = "\n".join([f"{m['speaker']}: {m['content']}" for m in dialogue_history])
    ws_result = world_state_system.end_turn(turn=5, chat_log=chat_log)
    world_summary = "Haruko tried to give a briefing, but the player repeatedly distracted her. After several warnings, Haruko's patience reached its limit, and she became extremely stern, forcing the player to focus on Project X."
    
    # 4. Final Synthesis
    print("\n--- Running Final Synthesis (Combining AI Emotions + System Rules + WorldState) ---")
    final_memory = await synthesizer.synthesize_scene_knowledge(
        npc_name=npc_name,
        world_state_summary=world_summary,
        scene_name=scene_name
    )
    
    print("\n" + "="*60)
    print("FINAL INTEGRATED NPC MEMORY (The 'Game-Like' Result):")
    print("="*60)
    print(final_memory)
    print("="*60)

if __name__ == "__main__":
    asyncio.run(simulate_real_world_workflow())

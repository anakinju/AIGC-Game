import os
import json
import sys
from typing import Dict

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.worldstate import WorldStateSystem
from npc.utils.llm_factory import LLMFactory
from npc.utils.constants import LLMUsage
from dotenv import load_dotenv

def test_worldstate_generation():
    # Load environment variables from project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    load_dotenv(os.path.join(project_root, ".env"))

    print("=" * 60)
    print("World State & Scene Summary CoT Test")
    print("=" * 60)

    # 1. Initialize LLM functions
    llm = LLMFactory.create_chat_model(usage=LLMUsage.GENERAL, temperature=0)
    
    def ai_generate(prompt: str) -> Dict:
        # Simple wrapper to get JSON from LLM
        response = llm.invoke(prompt)
        content = response.content
        # Clean markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)

    # Add AI Judge function for TaskMatcher
    def ai_judge(prompt: str) -> Dict:
        response = llm.invoke(prompt)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return json.loads(content)

    # 2. Initialize WorldStateSystem with AI Judge
    ws_system = WorldStateSystem(
        ai_generate_function=ai_generate,
        ai_judge_function=ai_judge
    )

    # 3. Define a test case (Library Scene)
    test_chat_log = """
player: Excuse me, Haruko. Can I eat this sandwich here? I'm really hungry.
Haruko: Absolutely not. This is a library, and rules are rules. No food allowed.
player: Oh, come on. Just a small bite? I'll be very quiet.
Haruko: I said no. If you persist, I will have to ask you to leave.
player: Fine, fine. I'll put it away. I'm sorry.
Haruko: Thank you. I appreciate your cooperation in keeping this space clean.
"""
    
    scene_context = {
        "location": "Library",
        "current_topic": "Library Rules",
        "worldstate_tasks": [
            {"expected_text": "Player followed library rules"}
        ]
    }

    # Add the task to the system
    ws_system.add_task("Player followed library rules", deadline_turn=5)

    print("\n[Input] Chat Log:")
    print(test_chat_log)

    # 4. Run the turn
    print("\n[Processing] Generating Summary and States...")
    result = ws_system.end_turn(turn=1, chat_log=test_chat_log, scene_context=scene_context)

    # 5. Show Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    print(f"\n[Scene Summary (Objective Observer)]:")
    print(result.get("scene_summary"))

    print(f"\n[Extracted Objective World States]:")
    for state in result.get("generated_states", []):
        print(f"- {state['text']}")

    print(f"\n[Task Matching Analysis]:")
    # Check all tasks in the system
    for task in ws_system.tasks:
        status_icon = "✅ SUCCESS" if task.status == "SUCCESS" else "❌ ONGOING/FAILED"
        print(f"\nTarget Task: {task.expected_text}")
        print(f"Status: {status_icon}")
        if task.status == "SUCCESS":
            print(f"Matched with State: {task.matched_state_id}")
            print(f"Match Score: {task.matched_score:.2f}")
            # Find the actual text that matched
            matched_text = next((s['text'] for s in result.get('all_states', []) if s['id'] == task.matched_state_id), "Unknown")
            print(f"Evidence Found: \"{matched_text}\"")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_worldstate_generation()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NPC Dispatch Mission Runner
Allows manual testing and execution of NPC-to-NPC dispatch missions.
"""

import sys
import os
import asyncio
import logging
import json
from dotenv import load_dotenv

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from npc.dispatch.manager import DispatchManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DispatchRunner")

# Load environment variables (LangSmith, etc.)
load_dotenv()

async def run_dispatch_mission():
    """Main function to run a dispatch mission manually."""
    print("=" * 50)
    print("NPC Dispatch Mission Runner")
    print("=" * 50)
    
    dispatch_manager = DispatchManager()
    
    # Define a callback to handle the final report
    def on_report(npc_name, report):
        print("\n" + "=" * 50)
        print(f"MISSION COMPLETE: Report from {npc_name}")
        print("-" * 50)
        print(report)
        print("=" * 50 + "\n")

    dispatch_manager.set_report_callback(on_report)

    while True:
        print("\n--- Start New Dispatch Mission ---")
        try:
            requester = input("Requester NPC Name (e.g., Haruko): ").strip()
            if not requester: break
            
            target = input("Target NPC Name (e.g., Librarian): ").strip()
            if not target: break
            
            topic = input("Inquiry Topic (What do you want to find out?): ").strip()
            if not topic: break
            
            player_req = input("Player's Request/Instruction to NPC: ").strip()
            if not player_req: player_req = f"Go talk to {target} about {topic}."
            
            rel_player = input("Relationship to Player (0.0-1.0, default 0.5): ").strip()
            rel_player = float(rel_player) if rel_player else 0.5
            
            rel_npcs = input("Relationship between NPCs (e.g., Acquaintance, Rival, default Acquaintance): ").strip()
            if not rel_npcs: rel_npcs = "Acquaintance"
            
            max_turns = input("Max Dialogue Turns (default 5): ").strip()
            max_turns = int(max_turns) if max_turns else 5

            print(f"\n[System] Dispatching {requester} to talk to {target}...")
            print(f"[System] Topic: {topic}")
            print(f"[System] Mission started in background. Waiting for results...\n")

            # Start the mission
            # Note: start_dispatch returns a mission_id and runs the workflow in a background task
            mission_id = await dispatch_manager.start_dispatch(
                requester_npc=requester,
                target_npc=target,
                player_request=player_req,
                inquiry_topic=topic,
                relationship_to_player=rel_player,
                relationship_between_npcs=rel_npcs,
                max_turns=max_turns
            )

            # Wait for the mission to complete (since this is a standalone runner)
            # In a real game, this would happen asynchronously while the player does other things.
            if mission_id in dispatch_manager.active_missions:
                await dispatch_manager.active_missions[mission_id]
            
            cont = input("Run another mission? (y/n): ").strip().lower()
            if cont != 'y':
                break

        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            break

    print("\nExiting Dispatch Runner. Goodbye!")

if __name__ == "__main__":
    try:
        asyncio.run(run_dispatch_mission())
    except KeyboardInterrupt:
        pass

#!/usr/bin/env python3
"""
Debug script to test NPC node logic and identify why target NPC isn't generating responses
"""

import os
import sys
import asyncio
from typing import Dict, Any

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.multi_npc.router_strategies import PlayerInvolvedStrategy

def debug_npc_logic():
    """Debug the NPC node decision logic"""
    print("=== Debug NPC Logic ===")
    
    # Simulate the state after router processing
    strategy = PlayerInvolvedStrategy()
    
    initial_state = {
        "sender": "player",
        "message": "Hi Chou Hu, what's up?",
        "chat_group": ["player", "Chou Hu", "Haruko"],
        "responders": ["Chou Hu"],  # Original responder
        "message_store": []
    }
    
    print("1. Initial state:")
    print(f"   - chat_group: {initial_state['chat_group']}")
    print(f"   - original responders: {initial_state['responders']}")
    
    # Process through router
    processed_state = strategy._handle_player_message(initial_state)
    
    print("\n2. After router processing:")
    print(f"   - target_npc: {processed_state.get('target_npc')}")
    print(f"   - responders: {processed_state.get('responders')}")
    print(f"   - allowed_npcs: {processed_state.get('allowed_npcs')}")
    print(f"   - background_npcs: {processed_state.get('background_npcs')}")
    
    # Test NPC logic for Chou Hu (should be target)
    npc_name = "Chou Hu"
    target_npc = processed_state.get("target_npc")
    responders = processed_state.get("responders", [])
    
    print(f"\n3. Testing logic for {npc_name}:")
    print(f"   - target_npc: '{target_npc}'")
    print(f"   - responders: {responders}")
    print(f"   - {npc_name} == target_npc: {npc_name == target_npc}")
    print(f"   - {npc_name} in responders: {npc_name in responders}")
    
    if npc_name == target_npc and npc_name in responders:
        print(f"   → {npc_name} should generate RESPONSE (target)")
    elif npc_name in responders and npc_name != target_npc:
        print(f"   → {npc_name} should do EMOTION ONLY (background)")
    else:
        print(f"   → {npc_name} should do NOTHING")
    
    # Test for Haruko (should be background)
    npc_name = "Haruko"
    print(f"\n4. Testing logic for {npc_name}:")
    print(f"   - {npc_name} == target_npc: {npc_name == target_npc}")
    print(f"   - {npc_name} in responders: {npc_name in responders}")
    
    if npc_name == target_npc and npc_name in responders:
        print(f"   → {npc_name} should generate RESPONSE (target)")
    elif npc_name in responders and npc_name != target_npc:
        print(f"   → {npc_name} should do EMOTION ONLY (background)")  
    else:
        print(f"   → {npc_name} should do NOTHING")

if __name__ == "__main__":
    debug_npc_logic()
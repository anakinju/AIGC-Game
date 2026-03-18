import random
from typing import Dict, Any, List
from .base_strategy import RouterStrategy

class NPCOnlyStrategy(RouterStrategy):
    """Strategy for NPC-to-NPC interactions without direct player involvement."""
    
    def handle_new(self, state: Dict[str, Any]) -> Dict[str, Any]:
        inactive_turns = state.get("inactive_turns", {})
        initiator = state["sender"]
        
        available_npcs = [npc for npc in state["chat_group"] if npc != initiator]
        if not available_npcs:
            return {**state}
            
        forced_speakers = [npc for npc, count in inactive_turns.items() if count >= 3 and npc in available_npcs]
        first_responder = random.choice(forced_speakers) if forced_speakers else random.choice(available_npcs)
        
        updated_inactive_turns = inactive_turns.copy()
        for npc in state["chat_group"]:
            updated_inactive_turns[npc] = 0 if npc == first_responder else updated_inactive_turns.get(npc, 0) + 1
        
        message_tags = {
            "sender": state["sender"],
            "target": "all",
            "allowed_npcs": state.get("chat_group", [])
        }
        
        message_entry = {
            "speaker": state["sender"],
            "content": state["message"],
            "allowed_npcs": state.get("chat_group", []),
            "timestamp": state.get("current_turn", 0),
            "tags": message_tags
        }
        
        message_store = state.get("message_store", [])
        if not any(m.get("content") == state["message"] and m.get("speaker") == state["sender"] for m in message_store[-1:]):
            message_store.append(message_entry)
                
        return {
            **state,
            "responders": [first_responder],
            "msg_type": "response",
            "original_sender": initiator,
            "original_message": state["message"],
            "inactive_turns": updated_inactive_turns,
            "previous_speaker": first_responder,
            "need_add_initial_message": True,
            "processed_npcs": [],
            "message_store": message_store
        }

    def handle_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        current_speaker = state["sender"]
        updated_inactive_turns = state.get("inactive_turns", {})
        
        available_npcs = [npc for npc in state["chat_group"] if npc != current_speaker]
        if not available_npcs:
            return {**state}
            
        forced_speakers = [npc for npc, count in updated_inactive_turns.items() if count >= 3 and npc in available_npcs]
        next_responder = random.choice(forced_speakers) if forced_speakers else random.choice(available_npcs)
        
        for npc in state["chat_group"]:
            updated_inactive_turns[npc] = 0 if npc == next_responder else updated_inactive_turns.get(npc, 0) + 1
        
        return {
            **state,
            "responders": [next_responder],
            "msg_type": "response",
            "current_turn": state.get("current_turn", 0) + 1,
            "sender": next_responder,
            "inactive_turns": updated_inactive_turns,
            "previous_speaker": next_responder
        }

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class RouterStrategy(ABC):
    """Abstract base class for routing strategies."""
    
    @abstractmethod
    def handle_new(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a new message entering the system."""
        pass

    @abstractmethod
    def handle_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a response from an NPC node."""
        pass

    def _setup_player_message(self, state: Dict[str, Any], responders: List[str]) -> Dict[str, Any]:
        """Common logic to store player message and setup tags."""
        allowed_npcs = [npc for npc in state.get("chat_group", []) if npc != "player"]
        
        # Determine target NPC (primary focus of the message)
        target_npc = responders[0] if responders else (allowed_npcs[0] if allowed_npcs else "unknown")
        background_npcs = [npc for npc in allowed_npcs if npc != target_npc]
        
        message_tags = {
            "sender": state["sender"],
            "target": target_npc,
            "allowed_npcs": allowed_npcs
        }
        
        message_store = state.get("message_store", [])
        # Avoid duplicate entries
        if not any(m.get("content") == state["message"] and m.get("speaker") == state["sender"] for m in message_store[-1:]):
            message_entry = {
                "speaker": state["sender"],
                "content": state["message"],
                "allowed_npcs": state.get("chat_group", []),
                "timestamp": state.get("current_turn", 0),
                "tags": message_tags
            }
            message_store.append(message_entry)
        
        return {
            **state,
            "msg_type": "response",
            "target_npc": target_npc,
            "responders": responders,
            "background_npcs": background_npcs,
            "allowed_npcs": allowed_npcs,
            "original_message": state["message"],
            "original_sender": state["sender"],
            "previous_speaker": state["sender"],
            "need_add_player_message": True,
            "processed_npcs": [],
            "message_tags": message_tags,
            "message_store": message_store
        }

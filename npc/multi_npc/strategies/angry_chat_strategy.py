from typing import Dict, Any, List
from .base_strategy import RouterStrategy

class AngryChatStrategy(RouterStrategy):
    """Strategy for interactions where the NPC is offended."""
    
    def handle_new(self, state: Dict[str, Any]) -> Dict[str, Any]:
        all_npcs = [npc for npc in state.get("chat_group", []) if npc != "player"]
        target_npcs = state.get("responders", [])
        if not target_npcs and all_npcs:
            target_npcs = [all_npcs[0]]
            
        state["primary_responder"] = target_npcs[0] if target_npcs else (all_npcs[0] if all_npcs else None)
        return self._setup_player_message(state, all_npcs)

    def handle_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # Usually ends after the angry response
        processed_npcs = state.get("processed_npcs", [])
        current_speaker = state["sender"]
        if current_speaker not in processed_npcs:
            processed_npcs.append(current_speaker)
        return {**state, "processed_npcs": processed_npcs}

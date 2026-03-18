from typing import Dict, Any, List
from .base_strategy import RouterStrategy
from .player_involved_strategy import PlayerInvolvedStrategy

class CasualChatStrategy(RouterStrategy):
    """Strategy for off-topic or casual interactions."""
    
    def handle_new(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Casual Chat mode: Only the target NPC responds. Other NPCs remain idle (halt).
        """
        all_npcs = [npc for npc in state.get("chat_group", []) if npc != "player"]
        
        target_npcs = state.get("responders", [])
        if not target_npcs and all_npcs:
            target_npcs = [all_npcs[0]]
        
        # Only the target NPCs are set as responders
        return self._setup_player_message(state, target_npcs)

    def handle_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        processed_npcs = state.get("processed_npcs", [])
        current_speaker = state["sender"]
        if current_speaker not in processed_npcs:
            processed_npcs.append(current_speaker)
        return {**state, "processed_npcs": processed_npcs}

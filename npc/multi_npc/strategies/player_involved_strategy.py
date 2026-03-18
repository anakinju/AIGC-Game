from typing import Dict, Any, List
from .base_strategy import RouterStrategy

class PlayerInvolvedStrategy(RouterStrategy):
    """Strategy for story-relevant interactions involving the player."""
    
    def handle_new(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Player Involved mode: All NPCs in the scene run emotion analysis 
        to stay updated on the story context, but only the target NPCs respond.
        """
        all_npcs = [npc for npc in state.get("chat_group", []) if npc != "player"]
        
        # Determine who the player is actually talking to
        target_npcs = state.get("responders", [])
        if not target_npcs and all_npcs:
            target_npcs = [all_npcs[0]]
            
        state["primary_responders"] = target_npcs
        
        # Set ALL NPCs as responders so they all run their NPCNode logic (for emotion analysis)
        return self._setup_player_message(state, all_npcs)

    def handle_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        processed_npcs = state.get("processed_npcs", [])
        current_speaker = state["sender"]
        if current_speaker not in processed_npcs:
            processed_npcs.append(current_speaker)
        
        all_npcs = [npc for npc in state["chat_group"] if npc != "player"]
        if set(processed_npcs) >= set(all_npcs):
            return {**state}
            
        return {
            **state,
            "previous_speaker": current_speaker,
            "processed_npcs": processed_npcs
        }

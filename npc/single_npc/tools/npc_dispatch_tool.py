import os
import sys
import logging
from typing import Dict, List, Any, Optional
from langchain_core.tools import BaseTool
from npc.dispatch.manager import dispatch_manager

logger = logging.getLogger(__name__)

class NPCDispatchTool(BaseTool):
    """
    NPC Dispatch Tool: Allows the player to send an NPC to gather information from another NPC.
    """
    name: str = "npc_dispatch"
    description: str = "Dispatch the CURRENT NPC you are talking to, to go and talk to another NPC. Params: target_npc (name of target), inquiry_topic (what to ask about)"
    
    # We need a reference to the requester (the NPC the player is currently talking to)
    requester_npc: str = ""
    relationship_to_player: float = 0.5

    def _run(self, target_npc: str, inquiry_topic: str) -> str:
        """
        Synchronous execution (not used in async flow)
        """
        return "Dispatch request received."

    async def _arun(self, target_npc: str, inquiry_topic: str) -> str:
        """
        Asynchronous execution: Triggers the DispatchManager.
        """
        if not self.requester_npc:
            return "Error: No requester NPC specified for dispatch."

        # Start the background workflow
        mission_id = await dispatch_manager.start_dispatch(
            requester_npc=self.requester_npc,
            target_npc=target_npc,
            player_request=f"Go ask {target_npc} about {inquiry_topic}",
            inquiry_topic=inquiry_topic,
            relationship_to_player=self.relationship_to_player,
            relationship_between_npcs="Acquaintance", # Default for now
            max_turns=5
        )
        
        logger.info(f"Dispatch mission {mission_id} started by {self.requester_npc}")
        
        # Immediate response to the player
        return f"Alright, I'll go find {target_npc} and see what I can find out about '{inquiry_topic}'. I'll report back to you once I'm done."

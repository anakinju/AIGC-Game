import asyncio
import logging
import os
from typing import Dict, List, Any, Optional, Callable
from langsmith import traceable
from npc.dispatch.graph import create_dispatch_graph, DispatchState

logger = logging.getLogger(__name__)

class DispatchManager:
    """
    Manages the lifecycle of NPC dispatch missions.
    Runs workflows in the background and handles results.
    """
    def __init__(self):
        self.graph = create_dispatch_graph()
        self.active_missions: Dict[str, asyncio.Task] = {}
        self._callback: Optional[Callable[[str, str], None]] = None

    def set_report_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Set a callback function to be called when a mission completes.
        Args:
            callback: A function that takes a result dictionary:
                {
                    "mission_id": str,
                    "npc_name": str,
                    "is_accepted": bool,
                    "report": str,
                    "refusal_reason": Optional[str]
                }
        """
        self._callback = callback

    async def start_dispatch(self, 
                               requester_npc: str, 
                               target_npc: str, 
                               player_request: str,
                               inquiry_topic: str,
                               relationship_to_player: float = 0.5,
                               relationship_between_npcs: str = "Acquaintance",
                               max_turns: int = 5) -> str:
        """
        Start a new dispatch mission in the background.
        """
        mission_id = f"{requester_npc}_to_{target_npc}_{asyncio.get_event_loop().time()}"
        
        initial_state: DispatchState = {
            "requester_npc": requester_npc,
            "target_npc": target_npc,
            "player_request": player_request,
            "inquiry_topic": inquiry_topic,
            "relationship_to_player": relationship_to_player,
            "relationship_between_npcs": relationship_between_npcs,
            "dialogue_history": [],
            "current_turn": 0,
            "max_turns": max_turns,
            "is_accepted": False,
            "refusal_reason": None,
            "gathered_knowledge": [],
            "final_summary": "",
            "report_to_player": ""
        }

        # Create background task
        task = asyncio.create_task(self._run_workflow_traced(mission_id, initial_state))
        self.active_missions[mission_id] = task
        
        return mission_id

    @traceable(name="NPC Dispatch Workflow")
    async def _run_workflow_traced(self, mission_id: str, initial_state: DispatchState):
        """Traced internal method to execute the graph."""
        return await self._run_workflow(mission_id, initial_state)

    async def _run_workflow(self, mission_id: str, initial_state: DispatchState):
        """Internal method to execute the graph and handle results."""
        try:
            logger.info(f"Starting dispatch mission: {mission_id}")
            
            # Execute the LangGraph workflow
            # LangGraph automatically supports tracing if LANGCHAIN_TRACING_V2 is true
            final_state = await self.graph.ainvoke(initial_state)
            
            npc_name = final_state["requester_npc"]
            is_accepted = final_state.get("is_accepted", False)
            report = final_state.get("report_to_player", "")
            refusal_reason = final_state.get("refusal_reason", None)
            
            logger.info(f"Mission {mission_id} completed. Accepted: {is_accepted}")
            
            # Notify via callback if set
            if self._callback:
                # Prepare a structured result for the callback
                result = {
                    "mission_id": mission_id,
                    "npc_name": npc_name,
                    "is_accepted": is_accepted,
                    "report": report,
                    "refusal_reason": refusal_reason
                }
                
                if asyncio.iscoroutinefunction(self._callback):
                    await self._callback(result)
                else:
                    self._callback(result)
                    
        except Exception as e:
            logger.error(f"Error in dispatch mission {mission_id}: {e}")
        finally:
            if mission_id in self.active_missions:
                del self.active_missions[mission_id]

# Global instance
dispatch_manager = DispatchManager()

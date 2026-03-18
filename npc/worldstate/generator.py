"""
Generator module for the World State system.
Handles the creation of World States and Scene Summaries from chat logs using AI.
"""

import uuid
from typing import List, Dict, Any, Optional
from npc.scene_control.scene_data import SceneRegistry
from npc.worldstate.worldstatedata import WorldState

class WorldStateGenerator:
    """
    World State Generator - Extracts world states and summaries from conversation history.
    """
    
    def __init__(self, 
                 ai_generate_function: Any,
                 embedding_service: Optional[Any] = None):
        """
        Initialize the generator.
        
        Args:
            ai_generate_function: AI function that takes a prompt and returns a JSON Dict.
                                 Expected format: {"scene_summary": "...", "states": [{"text": "..."}]}
            embedding_service: Service to generate embeddings for extracted states.
        """
        self.ai_generate_function = ai_generate_function
        self.embedding_service = embedding_service
    
    def generate_from_chat_log(self, chat_log: str, turn: int, npc_context: Dict = None, scene_context: Dict = None) -> Dict[str, Any]:
        """
        Generate World States and a Scene Summary from the provided chat log.
        
        Args:
            chat_log: The raw conversation log.
            turn: Current turn number.
            npc_context: Context about the NPC (knowledge, goals).
            scene_context: Context about the scene (location, topic).
        
        Returns:
            Dict: {"states": List[WorldState], "scene_summary": str}
        """
        try:
            # Try to get scene_context from SceneRegistry if not provided
            if scene_context is None:
                current_scene = SceneRegistry.get_current_scene()
                if current_scene:
                    scene_context = current_scene.raw_data
            
            # Build prompt and call AI
            prompt = self._build_prompt(chat_log, npc_context, scene_context)
            result = self.ai_generate_function(prompt)
            
            scene_summary = ""
            states_data = []
            
            if isinstance(result, dict):
                scene_summary = result.get("scene_summary", "")
                states_data = result.get("states", [])
            
            # Handle empty results with a default fallback
            if not states_data and not scene_summary:
                print(f"[WorldState] Warning: No states or summary generated from chat log (turn {turn})")
                default_text = "conversation happened"
                if scene_context and scene_context.get('location'):
                    default_text = f"conversation happened in {scene_context['location']}"
                states_data = [{"text": default_text}]
                scene_summary = default_text
            
            # Convert raw data to WorldState objects
            world_states = []
            for state_data in states_data:
                text = state_data.get("text", "").strip()
                if not text:
                    continue
                
                # Truncate long descriptions
                if len(text) > 80:
                    text = text[:80] + "..."
                
                # Generate embedding if service is available
                embedding = None
                if self.embedding_service:
                    embedding = self.embedding_service.get_embedding(text)
                
                world_state = WorldState(
                    id=str(uuid.uuid4()),
                    text=text,
                    turn=turn,
                    embedding=embedding
                )
                world_states.append(world_state)
            
            print(f"[WorldState] Generated {len(world_states)} states and a summary (turn {turn})")
            return {
                "states": world_states,
                "scene_summary": scene_summary
            }
            
        except Exception as e:
            print(f"[WorldState] Failed to generate World State: {e}")
            import traceback
            traceback.print_exc()
            return {
                "states": [],
                "scene_summary": "Error generating summary."
            }
    
    def _build_prompt(self, chat_log: str, npc_context: Dict = None, scene_context: Dict = None) -> str:
        """
        Build the prompt for the AI to extract world states and summarize the scene.
        Uses specialized focus areas to guide the AI without forcing hallucination.
        """
        
        # Build "Special Areas of Interest" from scene context
        special_focus = ""
        if scene_context:
            special_focus = "=== SPECIAL AREAS OF INTEREST (CRITICAL: MUST MONITOR THESE) ===\n"
            
            # 1. Expected Worldstate Changes (Tasks)
            ws_tasks = scene_context.get('worldstate_tasks', [])
            if ws_tasks:
                special_focus += "Expected Worldstate Changes:\n"
                for task in ws_tasks:
                    task_text = task.get('expected_text') if isinstance(task, dict) else str(task)
                    special_focus += f"- {task_text}\n"
            
            # 2. Scene End Conditions
            end_conditions = scene_context.get('scene_end_state_reference', {})
            if end_conditions:
                special_focus += f"Scene End Conditions: {end_conditions}\n"
            
            # 3. NPC Scene Goal
            npc_goal = npc_context.get('scene_goal') if npc_context else None
            if npc_goal:
                special_focus += f"NPC's Primary Objective: {npc_goal}\n"

        return f"""You are a high-precision game event analyst. 
Your task is to analyze the conversation log and extract concrete World States.

⚠️ EXTRACTION PROTOCOL:
1. SPECIAL FOCUS: Pay extreme attention to the 'SPECIAL AREAS OF INTEREST' listed below. If any of these events occur, they MUST be recorded.
2. NO HALLUCINATION: Do not "hallucinate" or force a match. If an event in the Special Focus area did NOT explicitly happen, DO NOT record it.
3. NO LOGICAL LEAPS: An NPC assigning a task or offering an item is NOT evidence that the player accepted it. You must see the player's explicit agreement or action.
4. LITERAL & OBJECTIVE: Record only what actually happened in the dialogue.

CONVERSATION LOG:
{chat_log}

{special_focus}

Return ONLY valid JSON format:
{{
  "scene_summary": "A neutral record of the interaction workflow...",
  "states": [
    {{"text": "Concrete fact (e.g., Player accepted the mission)"}}
  ]
}}"""

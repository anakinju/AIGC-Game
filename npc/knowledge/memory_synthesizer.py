import json
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from npc.utils.llm_factory import LLMFactory
from npc.utils.constants import LLMUsage
from npc.knowledge.npc_memory_manager import NPCMemoryManager

class MemorySynthesizer:
    """
    Synthesizes WorldState summaries and NPC emotional logs into a final Scene Knowledge.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.llm = LLMFactory.create_chat_model(
            usage=LLMUsage.GENERAL,
            model_name=model_name,
            temperature=0.3
        )
        self.memory_manager = NPCMemoryManager()

    async def synthesize_scene_knowledge(
        self, 
        npc_name: str, 
        world_state_summary: str, 
        scene_id: str,
        timestamp: str,
        scene_name: str = "Unknown Scene"
    ) -> str:
        """
        Combines WorldState summary with NPC's emotional journey into a cohesive knowledge entry.
        """
        print(f"DEBUG: [MemorySynthesizer] Synthesizing for {npc_name} in {scene_id} ({scene_name})")
        if not self.memory_manager.is_enabled():
            return f"**Scene Summary**: {world_state_summary}\n**Emotional Journey**: Memory synthesis disabled.\n**Behavioral Insights**: Analysis unavailable.\n**Memory Notes**: Knowledge system is currently disabled."

        # 1. Get emotional logs for this NPC in this specific scene session
        emotional_logs = self.memory_manager.get_recent_logs(npc_name, scene_id, timestamp)
        
        if not emotional_logs:
            print(f"DEBUG: [MemorySynthesizer] No emotional logs found for {npc_name}")
            # Still synthesize if world_state_summary exists, or return fallback
            if not world_state_summary:
                return f"**Scene Summary**: No significant events occurred.\n**Emotional Journey**: No notable emotional changes recorded.\n**Behavioral Insights**: Limited interaction data available.\n**Memory Notes**: No new information to record."

        # 2. Format emotional logs for the prompt
        emotion_history_text = ""
        if emotional_logs:
            for log in emotional_logs:
                turn_info = f"Turn {log.get('turn', '?')}"
                emotion = log.get('emotion', 'Unknown')
                thought = log.get('thought_process', 'N/A')
                emotion_history_text += f"- {turn_info}: Felt {emotion}. Internal Thought: {thought}\n"
        else:
            emotion_history_text = "No specific emotional shifts recorded during this interaction."

        # 3. Build synthesis prompt
        prompt = f"""
### TASK
You are the memory analysis engine for game NPC "{npc_name}". 
Create a structured knowledge summary that analyzes scene events and the NPC's emotional responses for future gameplay decisions.

### SCENE EVENTS (WorldState Summary):
{world_state_summary}

### NPC EMOTIONAL ANALYSIS:
{emotion_history_text}

### OUTPUT FORMAT:
Generate a structured analysis with the following components:

**Scene Summary**: [Objective summary of key events and interactions that occurred]
**Emotional Journey**: [Analysis of {npc_name}'s emotional state changes and triggers during the scene]  
**Behavioral Insights**: [Key observations about player behavior or relationship dynamics that should influence future NPC responses]
**Memory Notes**: [Important facts or character developments that {npc_name} should remember for future interactions]

### REQUIREMENTS:
- Write in third person from an analytical perspective
- Focus on actionable insights for NPC behavior guidance
- Keep each section concise (1-2 sentences)
- Maintain objective, game-development focused language
"""

        try:
            print(f"DEBUG: [MemorySynthesizer] Calling LLM for {npc_name}...")
            response = await self.llm.ainvoke([
                SystemMessage(content=f"You are an AI memory analyst for the game NPC '{npc_name}'. Provide structured analysis of scene events and emotional patterns to guide future NPC behavior."),
                HumanMessage(content=prompt)
            ])
            
            synthesized_memory = response.content.strip()
            print(f"DEBUG: [MemorySynthesizer] LLM response received for {npc_name}")
            
            # 4. Save to the NPC's persistent knowledge file (overwrites if scene_id exists)
            self.memory_manager.save_synthesized_knowledge(npc_name, scene_id, synthesized_memory)
            
            return synthesized_memory
            
        except Exception as e:
            print(f"DEBUG: [MemorySynthesizer] Error: {e}")
            return f"**Scene Summary**: {world_state_summary}\n**Emotional Journey**: Analysis unavailable due to processing error.\n**Behavioral Insights**: Unable to analyze behavioral patterns.\n**Memory Notes**: Error in memory synthesis: {str(e)}"

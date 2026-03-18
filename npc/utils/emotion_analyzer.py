from typing import Dict, Any, List, Optional
import os
import json
import asyncio
from langchain_core.messages import HumanMessage, SystemMessage
from npc.utils.llm_factory import LLMFactory
from npc.utils.constants import LLMUsage
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default emotion modifiers if import fails
try:
    from npc.single_npc.prompts.relationship_behaviors import (
        EMOTION_MODIFIERS, 
    )
except ImportError:
    EMOTION_MODIFIERS = {
        "Calm": "Steady and composed. Use guidance to determine social distance (e.g., warm/helpful vs. curt/pointed).",
        "Happy": "Energetic and positive. Guidance specifies if this is genuine warmth, professional courtesy, or even a gloating satisfaction.",
        "Uneasy": "Hesitant or anxious. Guidance clarifies if this is due to the player's behavior, a threat to your goals, or internal doubt.",
        "Angry": "Cold or sharp. Guidance defines the intensity—from a stern, professional warning to outright dismissal or cold fury.",
        "Sad": "Somber and withdrawn. Guidance suggests if you are seeking comfort, pushing others away, or simply resigned to fate.",
        "Afraid": "Wary or defensive. Guidance dictates whether you are being submissive, looking for an escape, or masking your fear with a shaky professional front.",
        "Disgusted": "Cynical or judgmental. Guidance specifies the target of your contempt and the level of mockery.",
    }

class EmotionAnalyzer:
    """
    Emotion Analyzer - Analyzes emotional shifts of an NPC based on player interactions.
    """
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        self.llm = LLMFactory.create_chat_model(usage=LLMUsage.EMOTION, model_name=llm_model)
        self.available_emotions = list(EMOTION_MODIFIERS.keys())

    def _format_emotions_for_prompt(self) -> str:
        """Format emotional states for inclusion in the LLM prompt."""
        formatted = []
        for emotion, desc in EMOTION_MODIFIERS.items():
            formatted.append(f"- **{emotion}**: {desc}")
        return "\n".join(formatted)

    async def analyze_interaction_async(self, source_npc: str, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Asynchronously analyze the impact of interaction on NPC emotion.
        
        Args:
            source_npc: Name of the NPC being analyzed.
            state: Current game state containing conversation history and NPC info.
            
        Returns:
            Dict containing the analyzed emotion, intensity, and guidance.
        """
        if not state:
            return {
                "emotion": "Calm", 
                "intensity": 0.5, 
                "thought_process": {"internal_reaction": "No state provided"}, 
                "guidance": "Keep a neutral tone."
            }

        # Extract message history from various possible state keys
        message_store = state.get("message_store", [])
        if not message_store:
            message_store = state.get("chat_history", []) or state.get("messages", []) or state.get("context", [])
        
        if not message_store:
            return {
                "emotion": "Calm", 
                "intensity": 0.5, 
                "thought_process": {"internal_reaction": "No messages to analyze"}, 
                "guidance": "Keep a neutral tone."
            }

        # Load NPC static and dynamic information
        try:
            from npc.utils.npc_info_adapter import create_npc_loader
            from npc.scene_control.scene_data import SceneRegistry
            
            npc_info_loader = create_npc_loader(source_npc)
            npc_info = npc_info_loader.get_npc_info()
            
            static_info = npc_info.get("static_info", npc_info)
            personality = static_info.get("personality_and_speech", {}).get("traits", [])
            behavioral_logic = static_info.get("behavioral_logic", {})
            motivation = static_info.get("motivation_and_drive", {})
            hidden_desire = motivation.get("hidden_desire", "None")
            
            # Social hierarchy info
            core_identity = static_info.get("core_identity", {})
            npc_role = core_identity.get("role", "Unknown")
            npc_status = core_identity.get("status", "Unknown")
            hierarchy_info = f"Role: {npc_role}, Status: {npc_status} (relative to Player)"

            # Scene context and relationship data
            current_scene = SceneRegistry.get_current_scene()
            scene_data = current_scene.raw_data if current_scene else state.get("scene_context", {})
            
            scene_relationships = scene_data.get("npc_relationships", [])
            relationship_detail = "Neutral baseline."
            for rel in scene_relationships:
                c1 = rel.get("character1", "").lower()
                c2 = rel.get("character2", "").lower()
                if (c1 == source_npc.lower() and c2 == "player") or (c2 == source_npc.lower() and c1 == "player"):
                    relationship_detail = (
                        f"Category: {rel.get('category', 'Neutral')}, "
                        f"Initial Emotion: {rel.get('emotion_modifier', 'Calm')}, "
                        f"Intensity: {rel.get('intensity', 0.5)}, "
                        f"Recent Context: {rel.get('recent_interaction', 'None')}"
                    )
                    break

            # NPC's current scene goal
            interactive_npcs = scene_data.get("interactive_npc", [])
            scene_goal = "Maintain interaction."
            for npc_item in interactive_npcs:
                if isinstance(npc_item, dict) and npc_item.get("name") == source_npc:
                    scene_goal = npc_item.get("goal", scene_goal)
                    break
            
        except Exception as e:
            personality = ["Professional"]
            behavioral_logic = {}
            hidden_desire = "None"
            scene_goal = "Continue conversation."
            hierarchy_info = "Unknown"
            relationship_detail = "Neutral"
        
        # Format recent conversation history (last 15 messages)
        recent_msgs = []
        for msg in message_store[-15:]:
            speaker = msg.get("speaker", "Unknown")
            content = msg.get("content", "")
            if isinstance(content, dict):
                content = content.get("utterance", str(content))
            recent_msgs.append(f"{speaker}: {content}")
        
        conversation_text = "\n".join(recent_msgs)
        
        # Get previous emotional state for continuity
        npc_states = state.get("npc_states", {})
        current_emotion = "Calm"
        previous_analysis = state.get(f"emotion_analysis_{source_npc}", {})
        
        if source_npc in npc_states:
            current_emotion = npc_states[source_npc]["dynamic_state"].get("emotion", "Calm")

        previous_psychology = "None"
        if previous_analysis:
            thought = previous_analysis.get("thought", {})
            previous_psychology = f"""- **Previous Emotion**: {previous_analysis.get('emotion', 'Calm')} (Intensity: {previous_analysis.get('intensity', 0.5)})
- **Previous Internal Monologue**: {thought.get('internal_reaction', 'N/A')}
- **Previous Guidance**: {previous_analysis.get('guidance', 'N/A')}"""

        # Construct the LLM Prompt
        prompt = f"""### EMOTION ANALYSIS TASK (WITH CHAIN-OF-THOUGHT)
Analyze how {source_npc}'s emotional state changes based on the LATEST interaction.

### NPC PROFILE
**Name**: {source_npc}
**Personality**: {personality}
**Behavioral Logic**: {behavioral_logic}
**Hidden Desire**: {hidden_desire}

### PREVIOUS PSYCHOLOGICAL STATE (Context for Continuity)
{previous_psychology}
*Note: Use this to track emotional momentum. Repeated similar interactions should amplify the existing state.*

### SOCIAL CONTEXT (HIERARCHY & RELATIONSHIP)
**Hierarchy Status**: {hierarchy_info}
**Relationship with Player**: {relationship_detail}

### SCENE OBJECTIVES & PLAYER ALIGNMENT
**Your Goal**: {scene_goal}
**Evaluation Framework**:
- Is the player advancing your goal? (If yes -> Positive/Happy)
- Is the player hindering your goal? (If yes -> Negative/Angry/Disgusted)
- Does the player's style align with your Hidden Desire?

### CONVERSATION CONTEXT
{conversation_text}

### AVAILABLE EMOTION STATES
{self._format_emotions_for_prompt()}

### ANALYSIS STEP-BY-STEP (CoT)
1. **Social & Goal Evaluation**: How does the player's message affect your goals and standing?
2. **Interpretation**: Analyze the player's linguistic style and intent.
3. **Emotional Trigger**: Identify if there is a specific moment that warrants a shift from {current_emotion}.
4. **Internal Reaction**: Describe your internal psychological response.
5. **Guidance for Response**: How should you behave next? (e.g., "Stay Calm but give a firm reminder").

### EMOTIONAL INERTIA & MOMENTUM
- **Default to {current_emotion}**: Maintain the current state if the interaction is minor or neutral.
- **Intensity Matters**: Use intensity (0.1-0.9) to show growth before a full category shift.

### OUTPUT FORMAT
Return ONLY a JSON object:
{{
    "thought_process": {{
        "social_goal_eval": "...",
        "interpretation": "...",
        "trigger": "...",
        "internal_reaction": "..."
    }},
    "emotion": "Chosen Emotion from the list",
    "intensity": 0.0-1.0,
    "guidance": "Direct instruction for the next dialogue"
}}"""

        messages = [
            SystemMessage(content="You are a specialized NPC Emotion Engine. You provide deep psychological analysis and actionable dialogue guidance."),
            HumanMessage(content=prompt)
        ]

        try:
            if hasattr(self.llm, 'ainvoke'):
                response = await self.llm.ainvoke(messages)
            else:
                response = self.llm.invoke(messages)
            
            content = response.content.strip()
            if content.startswith("```json"): 
                content = content[7:]
            if content.endswith("```"): 
                content = content[:-3]
            
            result = json.loads(content.strip())
            return result
        except Exception as e:
            return {
                "emotion": "Calm", 
                "intensity": 0.5, 
                "thought_process": {"internal_reaction": f"Error: {str(e)}"},
                "guidance": "Continue the conversation naturally."
            }

    def analyze_interaction(self, source_npc: str, state: Dict[str, Any] = None) -> Dict[str, Any]:
        """Synchronous wrapper for analyze_interaction_async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return {"emotion": "Calm", "intensity": 0.5, "thought_process": {"internal_reaction": "Loop running"}, "guidance": "Neutral."}
            return loop.run_until_complete(self.analyze_interaction_async(source_npc, state))
        except Exception:
            return asyncio.run(self.analyze_interaction_async(source_npc, state))

def get_emotion_description(emotion: str) -> str:
    """Get the behavioral description for a specific emotion."""
    return EMOTION_MODIFIERS.get(emotion, "Calm")

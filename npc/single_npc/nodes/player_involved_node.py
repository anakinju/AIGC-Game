import json
import logging
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, SystemMessage
from npc.single_npc.nodes.base_npc_node import BaseNPCNode
from npc.scene_control.scene_data import SceneRegistry

logger = logging.getLogger(__name__)

class PlayerInvolvedNode(BaseNPCNode):
    """
    Specialized NPC node for Player Involved mode (Player Involved).
    Uses Intention mechanism to generate responses.
    """
    
    async def generate_response_async(self, state: Dict[str, Any], context: List[Dict], cooling_down: bool = False) -> Dict[str, Any]:
        """Asynchronously generate intention-formatted responses"""
        try:
            # 1. Build base system prompt (includes identity and scene)
            base_system_prompt = self._set_system_prompt(state)
            
            # 2. Build intention guidance prompt
            intention_prompt = self._build_intention_prompt(state, context, cooling_down=cooling_down)
            
            messages = [
                SystemMessage(content=base_system_prompt),
                HumanMessage(content=intention_prompt)
            ]
            
            if hasattr(self.agent.llm, 'ainvoke'):
                response = await self.agent.llm.ainvoke(messages)
            else:
                response = self.agent.llm.invoke(messages)
            
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            try:
                result = json.loads(content)
                if not isinstance(result, dict) or "action" not in result or "utterance" not in result:
                    raise ValueError("Invalid response format")
                return result
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse intention JSON: {e}. Raw: {content[:200]}")
                return {
                    "action": {"id": "EVADE"},
                    "utterance": "I need a moment to think about that.",
                    "real_intent": "Processing error occurred during response generation"
                }
        except Exception as e:
            logger.error(f"Error in generate_response_async: {e}", exc_info=True)
            return {
                "action": {"id": "EVADE"},
                "utterance": "Something seems off... I'm not sure how to respond right now.",
                "real_intent": "System error occurred during intention generation"
            }

    def _build_intention_prompt(self, state: Dict[str, Any], conversation_history: List[Dict], cooling_down: bool = False) -> str:
        """Build intention-formatted prompt"""
        npc_state = state.get("npc_state", {})
        
        current_scene = SceneRegistry.get_current_scene()
        scene_context = current_scene.raw_data if current_scene else state.get("scene_context", {})
            
        # 1. Get emotional and relationship context (from EmotionManager pre-processed results)
        static_relationships = self.npc_info.get_relationships()
        rel_to_player = static_relationships.get("Player") or static_relationships.get("玩家") or "Neutral"
        
        current_emotion = npc_state.get("current_emotion", "Calm")
        
        # 获取完整的心理全景信息
        emotion_analysis = state.get(f"emotion_analysis_{self.name}", {})
        thought = emotion_analysis.get("thought", {})
        emotion_guidance = emotion_analysis.get("guidance") or state.get(f"emotion_guidance_{self.name}") or npc_state.get("emotion_guidance", "")
        
        # 2. Build dialogue history and scene context
        dialogue_context = self._build_dialogue_context_for_intention(conversation_history, state)
        scene_context_info = self._build_scene_context_for_intention(scene_context, state)
        
        # 3. Integrate NPC core drivers and goals
        intention_info = self.npc_info.get_info_for_intention()
        identity = intention_info.get("identity", {})
        motivation = intention_info.get("motivation", {})
        logic = intention_info.get("logic", {})

        scene_goals, scene_knowledge = self._get_scene_goal_and_knowledge_from_interactive_npc(scene_context)
        
        npc_goals = []
        if scene_goals: npc_goals.append(scene_goals)
        if motivation.get("obsession"): npc_goals.append(motivation["obsession"])
        if motivation.get("short_term_goals"): npc_goals.extend(motivation["short_term_goals"])
            
        npc_knowledge = []
        if scene_knowledge: npc_knowledge.extend(scene_knowledge if isinstance(scene_knowledge, list) else [scene_knowledge])
        if identity.get("background"): npc_knowledge.append(identity["background"])
        if logic.get("principles"): npc_knowledge.extend(logic["principles"])
        
        goals_text = "; ".join([str(g) for g in npc_goals if g]) if npc_goals else "None specified"
        knowledge_text = "; ".join([str(k) for k in npc_knowledge if k]) if npc_knowledge else "None specified"
        
        # 4. Fill template
        prompt_template = self._get_intention_prompt_template()
        
        # 格式化心理全景文本
        internal_psychology = f"""- **Goal Evaluation**: {thought.get('social_goal_eval', 'N/A')}
- **Interpretation of Player**: {thought.get('interpretation', 'N/A')}
- **Emotional Trigger**: {thought.get('trigger', 'N/A')}
- **Internal Monologue**: {thought.get('internal_reaction', 'N/A')}"""

        formatted_prompt = prompt_template.format(
            player_relationship_category=rel_to_player,
            player_emotion_modifier=current_emotion,
            internal_psychology=internal_psychology,
            emotion_guidance=emotion_guidance,
            last_player_message=dialogue_context["last_player_message"],
            dialogue_history=dialogue_context["dialogue_history"],
            current_location=scene_context_info["current_location"],
            other_npcs=scene_context_info["other_npcs"],
            your_scene_goals=goals_text,
            your_scene_knowledge=knowledge_text[:200] + "..." if len(knowledge_text) > 200 else knowledge_text
        )

        identity_desc = f"Name: {identity.get('name', self.name)}\n"
        if identity.get('nickname'): identity_desc += f"Nickname: {identity.get('nickname')}\n"
        if identity.get('identity_tags'): identity_desc += f"Tags: {', '.join(identity.get('identity_tags'))}\n"

        final_prompt = f"## NPC IDENTITY\n{identity_desc}\n" + formatted_prompt
        if cooling_down:
            final_prompt += "\n\n## COOLING DOWN (重要)\nThe player has apologized. You are softening but not fully over it. Give limited info, stay reserved."
            
        return final_prompt

    def _build_dialogue_context_for_intention(self, conversation_history: List[Dict], state: Dict[str, Any]) -> Dict[str, Any]:
        """Build dialogue context"""
        player_messages = []
        recent_messages = []
        
        # 优先使用传入的 conversation_history，如果为空则尝试从 state 获取
        history_source = conversation_history if conversation_history else state.get("message_store", [])
        
        for msg in history_source[-15:]:
            speaker = msg.get("speaker", "Unknown")
            content = self._extract_utterance_from_message(msg)
            if content:
                recent_messages.append({"speaker": speaker, "content": content})
                if speaker.lower() in ["player","Player"]:
                    player_messages.append(content)
        
        history_lines = [f"    {m['speaker']}: {m['content']}" for m in recent_messages[-5:]]
        return {
            "last_player_message": player_messages[-1] if player_messages else "No recent player input",
            "dialogue_history": "\n".join(history_lines) if history_lines else "    No recent dialogue"
        }

    def _build_scene_context_for_intention(self, scene_context: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        chat_group = state.get("chat_group", [])
        key_npcs = scene_context.get("key_npcs", [])
        other_npcs = {npc for npc in chat_group if npc != self.name and npc.lower() != "player"}
        other_npcs.update(key_npcs)
        if self.name in other_npcs: other_npcs.remove(self.name)
        
        return {
            "current_location": scene_context.get("environment", "Unknown location"),
            "other_npcs": ", ".join(other_npcs) or "None"
        }

    def _get_scene_goal_and_knowledge_from_interactive_npc(self, scene_context: Dict[str, Any]) -> tuple:
        interactive_npc = []
        current = SceneRegistry.get_current_scene()
        interactive_npc = current.interactive_npc if current else scene_context.get("interactive_npc", [])
        for item in interactive_npc:
            if (isinstance(item, dict) and item.get("name") == self.name) or item == self.name:
                if isinstance(item, dict):
                    return item.get("goal", ""), item.get("npc_background", {}).get("knowledge", [])
        return "", []

    def _get_intention_prompt_template(self) -> str:
        return """# NPC Response Generator
Generate an authentic NPC response that reflects your current emotional state and strategic goals.

## IMMEDIATE CONTEXT
**Player said**: "{last_player_message}"
**Location**: {current_location}

## RELATIONSHIP & EMOTION
**General Relationship**: {player_relationship_category}
**Current Emotional State**: {player_emotion_modifier}

## YOUR INTERNAL PSYCHOLOGY (From Emotion Analysis)
{internal_psychology}

## BEHAVIORAL GUIDANCE (From Internal Analysis)
{emotion_guidance}

## EMOTIONAL BEHAVIOR INSTRUCTION
You MUST align your dialogue style with your current emotion [{player_emotion_modifier}] while integrating the specific 'BEHAVIORAL GUIDANCE' for nuanced expression. This applies to ALL emotions:
- **Calm**: Steady and composed. Use guidance to determine social distance (e.g., warm/helpful vs. curt/pointed).
- **Happy**: Energetic and positive. Guidance specifies if this is genuine warmth, professional courtesy, or even a gloating satisfaction.
- **Uneasy**: Hesitant or anxious. Guidance clarifies if this is due to the player's behavior, a threat to your goals, or internal doubt.
- **Angry**: Cold or sharp. Guidance defines the intensity—from a stern, professional warning to outright dismissal or cold fury.
- **Sad**: Somber and withdrawn. Guidance suggests if you are seeking comfort, pushing others away, or simply resigned to fate.
- **Afraid**: Wary or defensive. Guidance dictates whether you are being submissive, looking for an escape, or masking your fear with a shaky professional front.
- **Disgusted**: Cynical or judgmental. Guidance specifies the target of your contempt and the level of mockery.

**CORE PRINCIPLE**: The 'BEHAVIORAL GUIDANCE' is your tactical roadmap. It provides the 'flavor' and 'intent' behind your current emotion. Even if your overall emotion remains the same, your 'Utterance' must reflect the specific nuance dictated by the guidance. Prioritize the guidance over generic emotional descriptions.

## CHARACTER MOTIVATION  
**Scene objectives**: {your_scene_goals}
**Scene knowledge**: {your_scene_knowledge}
**Others present**: {other_npcs}

## CONVERSATION HISTORY
{dialogue_history}


## AVAILABLE ACTIONS
- **DECEIVE**, **INTIMIDATE**, **PERSUADE**, **BARGAIN**, **CONFESS**, **EVADE**, **CHARM**

## OUTPUT INSTRUCTIONS
1. **action**: Choose the appropriate action from the 'AVAILABLE ACTIONS' list.
2. **Real Intent**: This is your TRUE strategic objective. It MUST align with your 'Goal Evaluation'. If you are lying or being manipulative, state the hidden truth here.
3. **Utterance**: This is your 'performance'. If your Real Intent is to mislead, your utterance should be a convincing lie or a strategic diversion, not a vague or ambiguous statement.

## JSON OUTPUT ONLY
{{
  "action": {{"id": "ACTION_NAME"}},
  "utterance": "Your natural dialogue response. Ensure the TONE matches your emotion and your performance aligns with your intent.",
  "real_intent": "Your true underlying strategic motivation (The truth behind the mask)."
}}"""

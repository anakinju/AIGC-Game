import os
import asyncio
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "NPC_CasualChat_Test"
# Ensure LANGCHAIN_API_KEY is in your .env file

from npc.single_npc.nodes.casual_chat_node import CasualChatNode
from npc.utils.base_npc import NPCAgent
from npc.single_npc.tools.tool_manager import ToolManager
from npc.utils.llm_factory import LLMFactory
from npc.utils.constants import LLMUsage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockNPCInfo:
    """Mock NPC Info for testing"""
    def __init__(self, name: str):
        self.name = name
    
    def get_info_for_casual_chat(self) -> Dict[str, Any]:
        return {
            "identity": {
                "name": self.name,
                "nickname": "Old Master",
                "role": "Village Elder",
                "status": "Respected Superior"
            },
            "personality": {
                "traits": ["Wise", "Strict", "Impatient with nonsense"],
                "speech_style": "Formal and concise"
            },
            "motivation": {
                "core_drive": "Maintain village order"
            },
            "logic": {
                "principles": ["Tradition above all", "Respect your elders"]
            },
            "background": "A long-time protector of the village secrets."
        }
    
    def get_relationships(self) -> Dict[str, str]:
        return {"Player": "Neutral Observer"}

async def test_casual_chat_tracing():
    """Test CasualChatNode with LangSmith tracing"""
    npc_name = "Elder_Zhang"
    
    # 1. Initialize components
    llm = LLMFactory.create_chat_model(usage=LLMUsage.GENERAL)
    # Mocking NPCAgent and ToolManager for simplicity
    class MockAgent:
        def __init__(self, llm):
            self.llm = llm
            self.state = {}
        def get_system_prompt(self):
            return "You are a helpful NPC."
    
    class MockToolManager:
        def register_tool(self, tool):
            pass
    
    agent = MockAgent(llm)
    tool_manager = MockToolManager()
    
    node = CasualChatNode(npc_name, agent, tool_manager)
    # Inject mock npc_info
    node.npc_info = MockNPCInfo(npc_name)
    
    # 2. Prepare mock state
    state = {
        "npc_state": {
            "current_emotion": "Angry",
            "emotion_guidance": "You feel the player is wasting your time with trivialities. Be firm."
        },
        "scene_context": {
            "interactive_npc": [
                {
                    "name": npc_name,
                    "goal": "Explain the ancient ritual to the player so they can save the village."
                }
            ]
        },
        "original_message": "Hey old man, do you like the weather today? It's quite sunny!",
        "message_store": [
            {"speaker": "Player", "content": "Hello Elder Zhang."},
            {"speaker": "Elder_Zhang", "content": "Greetings, traveler. We have urgent matters to discuss regarding the ritual."},
            {"speaker": "Player", "content": "Hey old man, do you like the weather today? It's quite sunny!"}
        ]
    }
    
    # 3. Build Prompt
    history = state["message_store"]
    prompt = node._build_casual_chat_prompt(state, history)
    
    print("\n=== GENERATED PROMPT ===")
    print(prompt)
    print("========================\n")
    
    # 4. Call LLM with tracing
    from langchain_core.messages import SystemMessage, HumanMessage
    
    messages = [
        SystemMessage(content="You are a specialized NPC dialogue engine. Respond in character based on the provided context."),
        HumanMessage(content=prompt)
    ]
    
    print("Calling LLM (Tracing enabled via LangSmith)...")
    response = await llm.ainvoke(messages)
    
    print("\n=== NPC RESPONSE ===")
    print(response.content)
    print("====================\n")
    
    print("Check your LangSmith dashboard at: https://smith.langchain.com/")

if __name__ == "__main__":
    asyncio.run(test_casual_chat_tracing())

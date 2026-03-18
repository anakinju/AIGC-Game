import asyncio
import logging
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置 LangSmith 相关的环境变量，确保在导入任何 langchain 库之前设置
os.environ["LANGCHAIN_TRACING_V2"] = "true"
# 如果 .env 中没有设置，可以手动在这里设置，或者确保 .env 已经被正确加载
# os.environ["LANGCHAIN_API_KEY"] = "..." 
# os.environ["LANGCHAIN_PROJECT"] = "NPC_Dispatch_Test"

import sys
# 将项目根目录添加到 python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from npc.dispatch.manager import dispatch_manager
from npc.dispatch.graph import create_dispatch_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DispatchTest")

async def mock_report_callback(npc_name: str, report_text: str):
    """Mock callback for receiving NPC reports"""
    print("\n" + "="*50)
    print(f"NOTIFICATION: NPC {npc_name} is back!")
    print(f"REPORT CONTENT:\n{report_text}")
    print("="*50 + "\n")

async def test_dispatch_flow():
    # 1. Set callback
    dispatch_manager.set_report_callback(mock_report_callback)
    
    print("Starting Test: Dispatch Haruko to ask Chief for information...")
    
    # 2. Simulate player initiating dispatch
    mission_id = await dispatch_manager.start_dispatch(
        requester_npc="Haruko",
        target_npc="Chief",
        player_request="Ask the chief about the legend of the back mountain.",
        inquiry_topic="The legend and potential dangers of the back mountain",
        relationship_to_player=0.8,
        relationship_between_npcs="Friendly",
        max_turns=3
    )
    
    print(f"Dispatch mission started, Mission ID: {mission_id}")
    print("Simulating NPC conversation in background, please wait...\n")
    
    # 3. Wait for mission completion
    while mission_id in dispatch_manager.active_missions:
        await asyncio.sleep(2)
        print("...NPCs are talking...")
    
    print("\nTest script finished.")

if __name__ == "__main__":
    try:
        asyncio.run(test_dispatch_flow())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Error during test: {e}")

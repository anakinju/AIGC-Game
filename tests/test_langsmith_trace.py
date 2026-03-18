import asyncio
import os
import json
from uuid import uuid4
from dotenv import load_dotenv
from langchain_core.tracers.context import collect_runs
from langchain_core.runnables import RunnableConfig
from langsmith import Client

from npc.utils.emotion_manager import EmotionManager
from npc.single_npc.nodes.player_involved_node import PlayerInvolvedNode
from npc.utils.npc_info_adapter import create_npc_loader
from npc.single_npc.tools.tool_manager import ToolManager

# 1. 配置 LangSmith 环境变量
load_dotenv()
os.environ["LANGCHAIN_TRACING_V2"] = "true"

async def simulate_interaction():
    npc_name = "Haruko"
    session_id = f"test-session-{uuid4().hex[:8]}"
    print(f"--- 模拟玩家与 {npc_name} 的持续交互 (Session: {session_id}) ---")
    
    # 2. 初始化组件
    emotion_manager = EmotionManager(llm_model="gpt-4o-mini")
    npc_loader = create_npc_loader(npc_name)
    tool_manager = ToolManager()

    class MockAgent:
        def __init__(self):
            from npc.utils.llm_factory import LLMFactory
            from npc.utils.constants import LLMUsage
            self.llm = LLMFactory.create_chat_model(usage=LLMUsage.GENERAL)

    mock_agent = MockAgent()
    node = PlayerInvolvedNode(name=npc_name, agent=mock_agent, tool_manager=tool_manager)

    # 3. 初始化状态
    state = {
        "npc_states": {
            npc_name: {
                "dynamic_state": {"emotion": "Calm", "emotion_intensity": 0.5},
                "last_updated": None
            }
        },
        "message_store": [],
        "chat_group": [npc_name, "Player"],
        "scene_context": {
            "environment": "A quiet library",
            "npc_relationships": [
                {"character1": npc_name, "character2": "Player", "category": "Neutral", "emotion_modifier": "Calm"}
            ],
            "interactive_npc": [
                {"name": npc_name, "goal": "Ensure the library remains quiet and books are handled with care."}
            ]
        }
    }

    # 4. 模拟连续对话序列
    test_inputs = [
        "Hi there, nice library you have here!",
        "Can I just... maybe eat my sandwich here? I'm really hungry.",
        "Oh come on, don't be so serious. It's just a sandwich!",
        "I'm sorry, I'll put it away. I didn't mean to be disrespectful."
    ]

    # 使用 LangSmith Client 来手动打标
    client = Client()

    for i, user_input in enumerate(test_inputs):
        print(f"\n[Round {i+1}] Player: {user_input}")
        
        # 将玩家输入存入消息存储
        state["message_store"].append({"speaker": "Player", "content": user_input})
        
        # 构造对话历史
        history_context = []
        for msg in state["message_store"]:
            history_context.append({"speaker": msg["speaker"], "utterance": msg["content"]})

        # 为了让 LangSmith 将多轮对话关联起来，我们使用 metadata
        # 注意：LangChain 的自动追踪会捕获这些 metadata
        metadata = {
            "session_id": session_id,
            "round": i + 1,
            "npc_name": npc_name
        }

        # A. 运行情绪分析
        print(f"[{npc_name} Thinking...]")
        # 情绪分析器内部调用了 LLM，LLM 会自动捕获全局的 tracing 状态
        analysis = await emotion_manager.update_emotion_async(npc_name, state)
        
        # B. 生成 NPC 回复
        # 我们通过 ainvoke 的 config 传递 metadata (如果 LLM 支持)
        # 这里 node 内部调用的是 self.agent.llm.ainvoke
        # 为了简单起见，我们直接运行，LangSmith 会因为在同一个进程/协程中而将其记录
        response = await node.generate_response_async(state, history_context)
        
        # 将 NPC 回复存入消息存储
        state["message_store"].append({"speaker": npc_name, "content": response["utterance"]})
        
        # C. 打印结果
        print(f"Emotion: {analysis['emotion']} (Intensity: {analysis['intensity']})")
        print(f"Guidance: {analysis['guidance']}")
        print(f"Internal Monologue: {analysis.get('thought_process', {}).get('internal_reaction', 'N/A')}")
        print(f"{npc_name}: {response['utterance']}")
        print(f"Real Intent: {response.get('real_intent', 'N/A')}")

    print(f"\n测试完成！请在 LangSmith 中搜索 metadata.session_id = '{session_id}' 来查看完整调用链。")

if __name__ == "__main__":
    asyncio.run(simulate_interaction())

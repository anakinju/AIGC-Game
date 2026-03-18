import sys
import os
from typing import Dict, Any, TypedDict, Annotated
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
# Poetry会自动处理包路径
from npc.utils.npc_info import NPCInfoLoader
import datetime
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")
langchain_key = os.getenv("LANGCHAIN_API_KEY")
langchain_project = os.getenv("LANGCHAIN_PROJECT")

# Langsmith setup
langsmith_key = os.getenv("LANGSMITH_API_KEY")
langsmith_project = os.getenv("LANGSMITH_PROJECT")
langsmith_tracing = os.getenv("LANGSMITH_TRACING", "true")
if langsmith_key:
    os.environ["LANGCHAIN_API_KEY"] = langsmith_key
if langsmith_project:
    os.environ["LANGCHAIN_PROJECT"] = langsmith_project
if langsmith_tracing:
    os.environ["LANGCHAIN_TRACING_V2"] = langsmith_tracing
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"


# 定义状态类型
class NPCState(TypedDict):
    npc_data: Dict[str, Any]  # 改名：从 npc 改为 npc_data
    scene: Dict[str, Any]  # 当前场景数据
    player_input: str  # 最新玩家输入
    conversation_history: list[str]  # 对话历史
    system_prompt: str  # LLM系统提示词
    messages: Annotated[list[Any], "messages"]  # 用于LangGraph的消息列表

from npc.utils.llm_factory import LLMFactory
from npc.utils.constants import LLMUsage

class NPCAgent:
    """
    简化的NPC代理 - 专注于LLM调用和基本NPC信息管理
    保持向后兼容的同时移除了复杂的状态管理
    """
    def __init__(self, npc_name: str, llm_model: str = "gpt-4o-mini"):
        """初始化NPC代理"""
        self.npc_loader = NPCInfoLoader(npc_name)
        self.llm = LLMFactory.create_chat_model(
            usage=LLMUsage.GENERAL,
            model_name=llm_model
        )
        
        # 缓存基本NPC信息（简化版）
        self.npc_data = self._load_npc_data()
        
        # 为了向后兼容，保留state属性但简化内容
        self.state = self._initialize_state()
        
    def _load_npc_data(self) -> Dict[str, Any]:
        """加载和缓存NPC基本信息"""
        basic_info = self.npc_loader.get_basic_info()
        npc_name = self.npc_loader.get_npc_name()
        relationships = self.npc_loader.get_relationships()
        
        return {
            "name": npc_name,
            "basic_info": basic_info,
            "relationships": relationships,
            "goal": basic_info.get("initial_goals", "")
        }
    
    def _initialize_state(self) -> NPCState:
        """初始化NPC状态（简化版，保持向后兼容）"""
        print("NPC initialized")
        return NPCState(
            npc_data=self.npc_data,  
            scene={},
            player_input="",
            conversation_history=[],
            system_prompt=self._get_default_system_prompt(),
            messages=[]
        )
    
    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        
        # 获取完整的NPC信息
        full_npc_info = self.npc_loader.get_npc_info()
        basic_info = self.npc_loader.get_basic_info()
        npc_name = self.npc_loader.get_npc_name()
        relationships = self.npc_loader.get_relationships()
        
        # 构建详细的系统提示
        prompt_parts = []
        
        # 基本身份信息
        prompt_parts.append(f"You are {npc_name}.")
        
        # 获取basic_information中的详细信息
        basic_information = full_npc_info.get('basic_information', {})
        
        # 昵称
        if 'nickname' in basic_information and basic_information['nickname']:
            prompt_parts.append(f"Nickname: {basic_information['nickname']}")
        
        # 背景
        if 'background' in basic_information and basic_information['background']:
            prompt_parts.append(f"Background: {basic_information['background']}")
        
        # 叙事线索
        if 'narrative_threads' in basic_information and basic_information['narrative_threads']:
            narrative_threads = basic_information['narrative_threads']
            if isinstance(narrative_threads, list):
                prompt_parts.append(f"Narrative Threads: {'; '.join(narrative_threads)}")
            else:
                prompt_parts.append(f"Narrative Threads: {narrative_threads}")
        
        # 当前状态
        if 'current_status' in basic_information and basic_information['current_status']:
            prompt_parts.append(f"Current Status: {basic_information['current_status']}")
        
        # 执念/目标
        goal = ''
        if 'obsession' in basic_information and basic_information['obsession']:
            goal = basic_information['obsession']
        elif 'initial_goals' in basic_information and basic_information['initial_goals']:
            goal = basic_information['initial_goals']
        elif 'initial_goal' in basic_information and basic_information['initial_goal']:
            goal = basic_information['initial_goal']
        
        if goal:
            prompt_parts.append(f"Goal/Obsession: {goal}")
        
        # 对人类妖怪的态度
        if 'attitude_toward_human_yokai' in basic_information and basic_information['attitude_toward_human_yokai']:
            prompt_parts.append(f"Attitude Toward Human-Yokai: {basic_information['attitude_toward_human_yokai']}")
        
        # 性格特征
        personality_info = ''
        if 'personality_traits' in basic_information and basic_information['personality_traits']:
            traits = basic_information['personality_traits']
            if isinstance(traits, list):
                personality_info = ', '.join(traits)
            else:
                personality_info = str(traits)
        elif 'personality' in basic_information and basic_information['personality']:
            personality_info = basic_information['personality']
        
        if personality_info:
            prompt_parts.append(f"Personality: {personality_info}")
        
        # 外貌描述
        if 'appearance' in basic_information and basic_information['appearance']:
            prompt_parts.append(f"Appearance: {basic_information['appearance']}")
        
        # 人际关系
        if relationships:
            if isinstance(relationships, dict):
                relationships_str = '; '.join([f"{k}: {v}" for k, v in relationships.items()])
            elif isinstance(relationships, str):
                relationships_str = relationships
            else:
                relationships_str = str(relationships)
            prompt_parts.append(f"Relationships: {relationships_str}")
        elif 'relationships' in basic_information and basic_information['relationships']:
            rel_info = basic_information['relationships']
            if isinstance(rel_info, str):
                prompt_parts.append(f"Relationships: {rel_info}")
        
        # 组合所有信息
        character_info = '\n'.join(prompt_parts)
        
        # 添加对话规则
        enhanced_prompt = f"""{character_info}

CONVERSATION RULES:
1. Stay in character - respond naturally based on your personality and relationships
2. Focus on the current speaker but acknowledge others if mentioned
3. Express opinions about other characters based on your relationships
4. Show warmth to friends, coldness to enemies
5. Keep responses to 2-3 sentences maximum
6. Use only direct speech - no actions, narration, or asterisks (*)
7. Embody your personality traits, background, and current status in every response
8. Remember your goals and obsessions when making decisions
"""
        
        return enhanced_prompt

    async def __call__(self, state: NPCState) -> Dict[str, Any]:
        """处理输入并生成响应（异步）"""
        # 更新状态
        if isinstance(state, dict):
            # 保存玩家输入
            self.state["player_input"] = state["player_input"]
            
            # 临时使用传入的对话历史来生成响应
            if "conversation_history" in state:
                self.state["conversation_history"] = state["conversation_history"]
            
            # 保存scene信息
            if "scene" in state:
                self.state["scene"] = state["scene"]
        
        # 生成响应（异步）
        response = await self._generate_response()
        # 构建NPC回复消息，但不存储
        npc_message = {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.datetime.now().isoformat(),
            "speaker": self.state["npc_data"]["name"],
            "target": "Player",
            "visibility": {
                "type": "private",
                "visible_to": []
            }
        }
        
        return {
            "messages": [{"role": "assistant", "content": response}],
            "goto": "player",
            "npc_message": npc_message  # 返回NPC消息，让chat_env处理存储
        }

    async def _generate_response(self) -> str:
        """生成NPC响应（异步）"""
        # 构建完整的消息列表，包含历史记录
        base_prompt = self.state["system_prompt"]
        
        # 如果有scene信息，只添加environment信息
        if "scene" in self.state and self.state["scene"]:
            scene_data = self.state["scene"]
            environment = scene_data.get('environment', 'No environment info')
            if environment and environment != 'No environment info':
                scene_info = f"""
                Current Environment: {environment}

                Please consider this environment context when responding.
                """
                base_prompt += scene_info
        
        messages = [SystemMessage(content=base_prompt)]
        
        # 使用传入的对话历史
        if "conversation_history" in self.state:
            for entry in self.state["conversation_history"]:
                if isinstance(entry, dict):
                    role = entry.get("role", "")
                    content = entry.get("content", "")
                    
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(SystemMessage(content=f"My previous response: {content}"))
        
        # 添加当前用户输入
        if self.state["player_input"]:
            # 检查输入中是否包含情绪标签
            emotion_tag = None
            if "[emotion:" in self.state["player_input"]:
                emotion_start = self.state["player_input"].find("[emotion:")
                emotion_end = self.state["player_input"].find("]", emotion_start)
                if emotion_end != -1:
                    emotion_tag = self.state["player_input"][emotion_start:emotion_end+1]
                    # 移除情绪标签，只保留实际消息内容
                    clean_input = self.state["player_input"].replace(emotion_tag, "").strip()
                    messages.append(HumanMessage(content=clean_input))
                    
                    # 添加情绪提示
                    emotion = emotion_tag.split(":")[1].strip()
                    emotion_prompt = f"\nBased on the detected emotion [{emotion}], adjust your response to match this emotional state. If the emotion is 'happy', be more cheerful and positive. If 'sad', be more somber and empathetic. If 'angry', be more assertive and intense."
                    messages.append(SystemMessage(content=emotion_prompt))
            else:
                messages.append(HumanMessage(content=self.state["player_input"]))
        
        #print(f"\n正在处理的消息历史: {messages}")  # 调试信息
        response = await self.llm.ainvoke(messages)
        
        return response.content

    def update_goal(self, new_goal: str) -> None:
        """更新NPC目标"""
        if 'npc_data' in self.state:  # 改名：从 npc 改为 npc_data
            self.state["npc_data"]["goal"] = new_goal
            self.state["system_prompt"] = self._get_default_system_prompt()
    
    def get_npc_info(self) -> Dict[str, Any]:
        """获取NPC基本信息"""
        return self.npc_data.copy()
    
    def get_npc_name(self) -> str:
        """获取NPC名称"""
        return self.npc_data.get("name", "Unknown")
    
    def get_system_prompt(self) -> str:
        """
        生成基础系统提示词
        
        Returns:
            str: 系统提示词
        """
        return self._get_default_system_prompt()
    
    
    

# 测试案例
if __name__ == "__main__":
    # import asyncio
    # import json
    
    async def test_npc_agent():
        # 创建一个临时的NPC配置文件
        test_npc_data = {
            "name": "测试NPC",
            "basic_information": {
                "nickname": "测试者",
                "background": "这是一个用于测试NPCAgent类的虚拟角色",
                "personality_traits": ["友好", "乐于助人", "聪明"],
                "appearance": "中等身高，穿着简单的衣服",
                "initial_goals": "帮助玩家完成测试",
                "current_status": "在测试环境中等待交互"
            },
            "relationships": {
                "玩家": "友好，愿意提供帮助"
            }
        }
        
        # 将测试数据写入临时文件
        temp_file_path = "temp_test_npc.json"
        with open(temp_file_path, "w", encoding="utf-8") as f:
            json.dump(test_npc_data, f, ensure_ascii=False, indent=4)
        
        try:
            # 注意：这个测试需要更新，因为新的NPCAgent只支持从characters.json加载
            # 暂时使用一个已知存在的NPC名称进行测试
            npc_agent = NPCAgent("Haruko")
            
            # 测试获取NPC信息
            npc_info = npc_agent.get_npc_info()
            print(f"NPC信息: {npc_info['name']}")
            
            # 测试更新目标
            npc_agent.update_goal("新的测试目标")
            print(f"更新后的目标: {npc_agent.state['npc_data']['goal']}")
            
            # 测试NPC响应生成
            test_state = NPCState(
                npc_data=npc_agent.npc_data,
                scene={"environment": "测试实验室"},
                player_input="你好，测试NPC！",
                conversation_history=[],
                system_prompt=npc_agent.get_system_prompt(),
                messages=[]
            )
            
            # 调用NPC代理
            response = await npc_agent(test_state)
            print(f"NPC响应: {response['npc_message']['content']}")
            
            # 测试带情绪标签的输入
            test_state["player_input"] = "你今天感觉如何？[emotion:happy]"
            response = await npc_agent(test_state)
            print(f"情绪响应: {response['npc_message']['content']}")
            
        finally:
            # 清理临时文件
            import os
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                print(f"已删除临时文件: {temp_file_path}")
    
    # 运行测试
    print("开始测试NPCAgent...")
    asyncio.run(test_npc_agent())
    print("测试完成！")





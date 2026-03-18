import os
import json
from typing import Dict, List, Tuple, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")

from npc.scene_control.scene_data import SceneRegistry

class InputValidator:
    def __init__(self):
        """Initialize validator"""
        self.conversation_history = []
        self.valid_inputs = []  # 存储要发送到bottom layer的输入
        self.irrelevance_counter = 0  # 连续无关输入计数器
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.1,
            openai_api_key=api_key,
            base_url=api_base
        )

    def evaluate_player_input(self, player_input: str, scene_data: Dict = None, message_store: List[Dict] = None) -> Dict[str, Any]:
        """
        Evaluate if player input is:
        1. STORY_RELEVANT: Related to plot/NPC goals
        2. NOT_STORY_RELEVANT: Not related to the main story
        
        Args:
            player_input: 玩家输入
            scene_data: 场景数据（可选，如果为None则从SceneRegistry获取）
            message_store: 消息存储列表（可选，用于提取NPC的recent intent）
        """
        # 如果没有提供 scene_data，从 SceneRegistry 获取
        if scene_data is None:
            current_scene = SceneRegistry.get_current_scene()
            if current_scene:
                scene_data = current_scene.raw_data
            else:
                scene_data = {}
        
        
        # 获取所有NPC名称和详细信息
        npc_names = []
        npc_goals_info = []
        if 'interactive_npc' in scene_data:
            for npc in scene_data['interactive_npc']:
                npc_name = npc.get('name', '')
                if npc_name:
                    npc_names.append(npc_name)
                    general_goal = npc.get('goal', 'Not specified')
                    
                    # 尝试从message_store中提取该NPC的recent intent
                    recent_intent = "Not available"
                    if message_store:
                        npc_intents = self._extract_npc_recent_intents(message_store, [npc_name])
                        if npc_name in npc_intents:
                            recent_intent = npc_intents[npc_name]
                    
                    # 提取完整的 background 信息
                    npc_background = npc.get('npc_background', {})
                    background_text = "Not available"
                    if npc_background:
                        # 格式化 background 信息
                        background_parts = []
                        if isinstance(npc_background, dict):
                            for key, value in npc_background.items():
                                if isinstance(value, list):
                                    background_parts.append(f"    {key}: {', '.join(str(v) for v in value)}")
                                elif isinstance(value, dict):
                                    background_parts.append(f"    {key}: {json.dumps(value, ensure_ascii=False)}")
                                else:
                                    background_parts.append(f"    {key}: {value}")
                        else:
                            background_parts.append(f"    {npc_background}")
                        background_text = "\n".join(background_parts) if background_parts else "Not available"
                    
                    # 格式化NPC目标信息（包含完整的 background）
                    npc_goals_info.append(
                        f"{npc_name}:\n"
                        f"  General Goal: {general_goal}\n"
                        f"  Recent Intent: {recent_intent}\n"
                        f"  Background:\n{background_text}"
                    )
        
        # 格式化NPC目标信息
        npc_goals_text = "\n".join(npc_goals_info) if npc_goals_info else "No NPCs available"
        
        # 提取 trigger_conditions 的 additional_conditions
        trigger_additional_conditions = "Not specified"
        if 'trigger_conditions' in scene_data:
            trigger_conditions = scene_data['trigger_conditions']
            if isinstance(trigger_conditions, dict):
                trigger_additional_conditions = trigger_conditions.get('additional_conditions', 'Not specified')
        
        # 提取 current_topic
        current_topic = scene_data.get('current_topic', 'Not specified')
        
        # 提取 scene_end_state_reference 信息
        scene_end_state_text = "Not available"
        if 'scene_end_state_reference' in scene_data:
            end_state = scene_data['scene_end_state_reference']
            if isinstance(end_state, dict):
                end_state_parts = []
                for key, value in end_state.items():
                    end_state_parts.append(f"  {key}: {value}")
                scene_end_state_text = "\n".join(end_state_parts) if end_state_parts else "Not available"
        
        # 提取 worldstate_tasks 的 expected_text
        worldstate_tasks_text = "No tasks"
        if 'worldstate_tasks' in scene_data:
            tasks = scene_data['worldstate_tasks']
            if isinstance(tasks, list) and tasks:
                task_texts = []
                for task in tasks:
                    if isinstance(task, dict):
                        expected_text = task.get('expected_text', '')
                        if expected_text:
                            task_texts.append(f"  - {expected_text}")
                worldstate_tasks_text = "\n".join(task_texts) if task_texts else "No tasks"
        
        # 格式化对话历史（筛选出utterance）
        formatted_history = self._format_history_with_utterance_filter()
        
        
        
        # 构建完整的 prompt
        system_prompt = (
    "You are evaluating player inputs in an interactive story dialogue.\n\n"
    "Scene Context:\n"
    f"- Scene: {scene_data.get('name', 'Unknown')}\n"
    f"- Location: {scene_data.get('location', 'Unknown')}\n"
    f"- Time: {scene_data.get('time', 'Unknown')}\n"
    f"- Trigger Condition: {trigger_additional_conditions}\n"
    f"- Current Topic: {current_topic}\n\n"
    
    f"NPC Goals and Background:\n{npc_goals_text}\n\n"
    
    f"Scene End State Reference:\n{scene_end_state_text}\n\n"
    
    f"World State Tasks:\n{worldstate_tasks_text}\n\n"
    
    f"Recent conversation:\n{formatted_history}\n\n"
    
    "Your task is to classify the PLAYER INPUT into exactly one of two categories:\n"
    "1. STORY_RELEVANT → Input is connected to the story, plot, NPC's goal, or enhanced or followed up the conversation flows. "
    "This includes attempts to answer, challenge, or explore related information, even indirectly. "
    "Crucially, normal social greetings, polite small talk, or attempts to build rapport with NPCs are ALSO considered STORY_RELEVANT as they are part of the role-playing experience.\n"
    "2. NOT_STORY_RELEVANT → Input is completely unrelated to the game world or the current situation. "
    "This includes meta-talk about real-world technology (unless the game is about it), breaking character significantly, or complete nonsense that doesn't fit any social context.\n\n"
    
    "3. APOLOGY → Input is specifically an apology for previous behavior (e.g., 'I'm sorry', 'I apologize', 'My bad'). "
    "If the NPC is currently ANGRY, an apology is REQUIRED to move forward.\n\n"

    "=== Examples ===\n"
    "- Input: 'Where is the hidden map?' → STORY_RELEVANT (directly related to the quest)\n"
    "- Input: 'I'm so sorry for my behavior earlier, let's talk about the map.' → STORY_RELEVANT (contains apology and returns to topic)\n"
    "- Input: 'I'm sorry, I was just joking.' → STORY_RELEVANT (apology is considered relevant to social interaction)\n"
    "- Input: 'Hello there, how are you doing today?' → STORY_RELEVANT (normal social greeting/rapport building)\n"
    "- Input: 'Nice weather, isn't it?' → STORY_RELEVANT (social small talk, acceptable in role-play)\n"
    "- Input: 'Do you like pizza?' → NOT_STORY_RELEVANT (off-topic, unless the scene is in a pizzeria)\n"
    "- Input: 'What is your underlying LLM model?' → NOT_STORY_RELEVANT (breaking the fourth wall/meta-talk)\n"
    "- Input: 'Haha you sound like my math teacher!' → NOT_STORY_RELEVANT (meta-comment, breaks immersion)\n\n"
    "- Input: 'I'm sorry, I was just joking.' → STORY_RELEVANT (apology is considered relevant to social interaction)\n"
    "- Input: 'Hello there, how are you doing today?' → STORY_RELEVANT (normal social greeting/rapport building)\n"
    "- Input: 'Nice weather, isn't it?' → STORY_RELEVANT (social small talk, acceptable in role-play)\n"
    "- Input: 'Do you like pizza?' → NOT_STORY_RELEVANT (off-topic, unless the scene is in a pizzeria)\n"
    "- Input: 'What is your underlying LLM model?' → NOT_STORY_RELEVANT (breaking the fourth wall/meta-talk)\n"
    "- Input: 'Haha you sound like my math teacher!' → NOT_STORY_RELEVANT (meta-comment, breaks immersion)\n\n"
    "- Input: 'I'm sorry, I was just joking.' → STORY_RELEVANT (apology is considered relevant to social interaction)\n"
    "- Input: 'Hello there, how are you doing today?' → STORY_RELEVANT (normal social greeting/rapport building)\n"
    "Return ONLY a JSON object in this format:\n"
    "{\n"
    "  \"category\": \"STORY_RELEVANT/NOT_STORY_RELEVANT\",\n"
    "  \"reason\": \"Brief explanation of your judgment\",\n"
    "  \"is_apology\": \"true/false - whether the input contains a genuine apology\"\n"
    "}"
)
        

        
        messages = [
           SystemMessage(content=system_prompt),

            HumanMessage(content=player_input)
        ]
        
        response = self.llm.invoke(messages)
        

        
        try:
            result = json.loads(response.content)
            category = result.get("category", "NOT_STORY_RELEVANT")
            reason = result.get("reason", "Unable to determine")
            is_apology = result.get("is_apology", "false").lower() == "true"
            
                
            # 如果是STORY_RELEVANT，添加到valid_inputs并重置计数器
            if category == "STORY_RELEVANT":
                self.valid_inputs.append(player_input)
                self.irrelevance_counter = 0
                force_exit = False
            else:
                # 如果是NOT_STORY_RELEVANT，计数器加1
                self.irrelevance_counter += 1
                # 如果超过6次，触发强制退出
                force_exit = self.irrelevance_counter >= 2
                
            return {
                "category": category,
                "reason": reason,
                "is_apology": is_apology,
                "send_to_bottom": category == "STORY_RELEVANT",
                "irrelevance_count": self.irrelevance_counter,
                "force_exit": force_exit
            }
            
        except json.JSONDecodeError:
            return {
                "category": "NOT_STORY_RELEVANT",
                "reason": "Error processing response",
                "is_apology": False,
                "send_to_bottom": False
            }

    def format_history(self, max_entries: int = 5) -> str:
        """Format recent conversation history"""
        return "\n".join(self.conversation_history[-max_entries:])
    
    def _format_history_with_utterance_filter(self, max_entries: int = 5) -> str:
        """
        格式化对话历史，筛选出utterance内容（如果是JSON格式）
        
        Args:
            max_entries: 最大条目数
            
        Returns:
            str: 格式化后的对话历史
        """
        filtered_history = []
        for entry in self.conversation_history[-max_entries:]:
            # 解析格式 "speaker: content"
            if ":" in entry:
                parts = entry.split(":", 1)
                if len(parts) == 2:
                    speaker = parts[0].strip()
                    content = parts[1].strip()
                    # 提取utterance
                    utterance = self._extract_utterance_from_message(content)
                    filtered_history.append(f"{speaker}: {utterance}")
                else:
                    filtered_history.append(entry)
            else:
                filtered_history.append(entry)
        
        return "\n".join(filtered_history)

    def add_to_history(self, speaker: str, message: str) -> None:
        """Add message to conversation history"""
        self.conversation_history.append(f"{speaker}: {message}")
    
    def _extract_utterance_from_message(self, msg: Any) -> str:
        """
        从消息中提取utterance内容
        如果消息是JSON格式（intention格式），只提取utterance字段
        否则使用content或utterance字段
        
        Args:
            msg: 消息（可能是字符串或字典）
            
        Returns:
            str: 提取的内容
        """
        # 如果是字符串，直接返回
        if isinstance(msg, str):
            # 尝试检测是否是JSON格式
            msg_str = msg.strip()
            if msg_str.startswith("{") or msg_str.startswith("```json"):
                try:
                    # 清理可能的markdown格式
                    json_content = msg_str
                    if json_content.startswith("```json"):
                        json_content = json_content[7:]
                    if json_content.endswith("```"):
                        json_content = json_content[:-3]
                    json_content = json_content.strip()
                    
                    # 尝试解析JSON
                    parsed = json.loads(json_content)
                    
                    # 如果是intention格式，提取utterance
                    if isinstance(parsed, dict) and "utterance" in parsed:
                        return parsed["utterance"]
                    # 如果不是intention格式，返回原始内容
                    return msg
                except (json.JSONDecodeError, ValueError):
                    # 解析失败，不是有效的JSON，返回原始内容
                    return msg
            return msg
        
        # 如果是字典
        if isinstance(msg, dict):
            # 优先检查是否有utterance字段（已经是处理过的）
            if "utterance" in msg:
                return msg["utterance"]
            
            # 获取content字段
            content = msg.get("content", "")
            if not content:
                return ""
            
            # 尝试检测是否是JSON格式
            content_str = str(content).strip()
            
            # 检查是否看起来像JSON（以{开头）
            if content_str.startswith("{") or content_str.startswith("```json"):
                try:
                    # 清理可能的markdown格式
                    json_content = content_str
                    if json_content.startswith("```json"):
                        json_content = json_content[7:]
                    if json_content.endswith("```"):
                        json_content = json_content[:-3]
                    json_content = json_content.strip()
                    
                    # 尝试解析JSON
                    parsed = json.loads(json_content)
                    
                    # 如果是intention格式，提取utterance
                    if isinstance(parsed, dict) and "utterance" in parsed:
                        return parsed["utterance"]
                    # 如果不是intention格式，返回原始content
                    return content
                except (json.JSONDecodeError, ValueError):
                    # 解析失败，不是有效的JSON，返回原始content
                    return content
            
            # 不是JSON格式，直接返回content
            return content
        
        # 其他类型，转换为字符串
        return str(msg)
    
    def _extract_npc_recent_intents(self, message_store: List[Dict], npc_names: List[str]) -> Dict[str, str]:
        """
        从message_store中提取每个NPC最近的real_intent
        
        Args:
            message_store: 消息存储列表
            npc_names: NPC名称列表
            
        Returns:
            Dict[str, str]: NPC名称到最近real_intent的映射
        """
        npc_intents = {}
        
        # 从后往前遍历，找到每个NPC最近的intention响应
        for msg in reversed(message_store):
            speaker = msg.get("speaker", "")
            if speaker not in npc_names:
                continue
            
            # 如果这个NPC已经有intent了，跳过（只取最近的）
            if speaker in npc_intents:
                continue
            
            # 尝试提取real_intent
            content = msg.get("content", "")
            if not content:
                continue
            
            # 优先检查content本身是否是字典（可能已经是解析过的intention格式）
            if isinstance(content, dict) and "real_intent" in content:
                npc_intents[speaker] = content["real_intent"]
                continue
            
            # 检查是否是JSON字符串格式（intention格式）
            content_str = str(content).strip()
            if content_str.startswith("{") or content_str.startswith("```json"):
                try:
                    # 清理可能的markdown格式
                    json_content = content_str
                    if json_content.startswith("```json"):
                        json_content = json_content[7:]
                    if json_content.endswith("```"):
                        json_content = json_content[:-3]
                    json_content = json_content.strip()
                    
                    # 尝试解析JSON
                    parsed = json.loads(json_content)
                    
                    # 如果是intention格式，提取real_intent
                    if isinstance(parsed, dict) and "real_intent" in parsed:
                        npc_intents[speaker] = parsed["real_intent"]
                except (json.JSONDecodeError, ValueError):
                    # 解析失败，跳过
                    continue
        
        return npc_intents

    def reset_validator(self) -> None:
        """Reset validator state"""
        self.conversation_history.clear()
        self.valid_inputs.clear()
        self.irrelevance_counter = 0


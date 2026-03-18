import os
import json
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import re 

# 添加项目根目录到系统路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")

from npc.utils.base_npc import NPCAgent
from npc.single_npc.npc_manager import NPCManager
from npc.single_npc.tools.tool_manager import ToolManager
from npc.multi_npc.chat_env import ChatEnvironment


def analyze_npc_intentions_and_goals(history, scene_path: str, npc_info_paths: list, llm_model_name="gpt-4o-mini"):
    """
    用 LLM 分析每个NPC的对话意图和下阶段goal
    Args:
        history: list of dict, 每条dict包含sender, message, responses, timestamp等
        scene_path: 当前场景json文件路径
        npc_info_paths: 所有NPC info的json文件路径列表
        llm_model_name: LLM模型名
    Returns:
        Dict[str, str]: {npc_name: predicted_goal}
    """
    import json
    from langchain_openai import ChatOpenAI
    # 1. 获取environment描述
    with open(scene_path, 'r', encoding='utf-8') as f:
        scene_data = json.load(f)
    environment = scene_data.get('environment', '')
    # 2. 获取所有npc_name
    npc_names = []
    for npc_path in npc_info_paths:
        try:
            with open(npc_path, 'r', encoding='utf-8') as f:
                npc_info = json.load(f)
            npc_name = npc_info.get('name')
            if npc_name:
                npc_names.append(npc_name)
        except Exception as e:
            continue
    # 3. 对每个npc_name，抽取相关对话片段
    npc_goals = {}
    llm = ChatOpenAI(model=llm_model_name, api_key=api_key, base_url=api_base)
    for npc_name in npc_names:
        # 格式化本npc的所有对话
        npc_dialogues = []
        for entry in history:
            # 玩家发言
            npc_dialogues.append(f"Player: {entry['message']}")
            # 本npc的回复
            for resp in entry.get("responses", []):
                if resp.get("speaker") == npc_name:
                    npc_dialogues.append(f"{npc_name}: {resp.get('content', '')}")
        if not any(f"{npc_name}:" in d for d in npc_dialogues):
            npc_goals[npc_name] = "暂无对话，无法推测"
            continue
        history_for_npc = "\n".join(npc_dialogues)
        prompt = (
            f"Environment description: {environment}\n"
            f"Dialogue history of {npc_name}:\n{history_for_npc}\n"
            f"Based on the above, please analyze the intention of {npc_name} in the most recent round of dialogue, and predict their goal for the next stage. Summarize in one sentence."
        )
        goal = llm.invoke(prompt).content
        npc_goals[npc_name] = goal
    return npc_goals


# MemorySimulator类封装
class MemorySimulator:
    def __init__(self):
        self.memory_log = []

    def add_history(self, history, scene_index, scene_title):
        """
        保存一段剧情的全部对话历史，并标记剧情段编号和标题。
        """
        for entry in history:
            entry_with_scene = entry.copy()
            entry_with_scene["scene_index"] = scene_index
            entry_with_scene["scene_title"] = scene_title
            self.memory_log.append(entry_with_scene)

    def print_history(self):
        print("\n=== Conversation History ===")
        for entry in self.memory_log:
            print(f"[Scene{entry['scene_index']}] {entry['scene_title']}")
            print(f"[{entry['timestamp']}] Player: {entry['sender']}")
            print(f"Player: {entry['message']}")
            for resp in entry.get("responses", []):
                print(f"{resp['speaker']}: {resp['content']}")
            print("-" * 50)

    def get_history_text(self):
        lines = []
        lines.append("\n=== Conversation History ===")
        for entry in self.memory_log:
            lines.append(f"[Scene{entry['scene_index']}] {entry['scene_title']}")
            lines.append(f"[{entry['timestamp']}] Player: {entry['sender']}")
            lines.append(f"Player: {entry['message']}")
            for resp in entry.get("responses", []):
                lines.append(f"{resp['speaker']}: {resp['content']}")
            lines.append("-" * 50)
        return "\n".join(lines)

    def get_segment_history(self, scene_index):
        """返回指定scene_index的结构化history（list of dict）"""
        return [entry for entry in self.memory_log if entry["scene_index"] == scene_index]


def example_usage():
    """使用示例"""
    # 设置路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 使用统一的Characters.json文件
    characters_file = os.path.join(base_dir, "..", "..", "narrative", "Generate_branches", "data", "Characters.json")
    scene_path1 = os.path.join(base_dir, "..", "data", "scripted_subtask_layer1_20250415_180747_response.json")
    scene_path2 = os.path.join(base_dir, "..", "data", "scripted_subtask_layer2_20250415_180747_response.json")
    scene_path3 = os.path.join(base_dir, "..", "data", "scripted_subtask_layer3_20250415_180747_response.json")
    
    # 为了向后兼容analyze_npc_intentions_and_goals函数，我们需要创建临时的NPC文件
    def create_temp_npc_files():
        """从Characters.json创建临时的单个NPC文件"""
        temp_files = []
        try:
            with open(characters_file, 'r', encoding='utf-8') as f:
                characters_data = json.load(f)
            
            npc_list = []
            if isinstance(characters_data, list):
                npc_list = characters_data
            elif isinstance(characters_data, dict):
                npc_list = list(characters_data.values())
            
            for npc_info in npc_list:
                if "name" in npc_info:
                    temp_file = os.path.join(base_dir, f"temp_{npc_info['name'].replace(' ', '_')}.json")
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        json.dump(npc_info, f, ensure_ascii=False, indent=2)
                    temp_files.append(temp_file)
            
            return temp_files
        except Exception as e:
            print(f"创建临时NPC文件失败: {e}")
            return []
    
    def cleanup_temp_files(temp_files):
        """清理临时文件"""
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    scene_paths = [scene_path1, scene_path2, scene_path3]
    memory_simulator = MemorySimulator()
    
    # 创建临时NPC文件
    temp_npc_files = create_temp_npc_files()
    
    try:
        for idx, scene_path in enumerate(scene_paths, 1):
            print(f"\n========== 开始第{idx}段对话 ==========")
            
            # 使用新的ChatEnvironment初始化方法
            chat_env = ChatEnvironment(
                scene_path=scene_path,
                characters_file=characters_file,
                chat_mode="player_involved"
            )
            chat_env.run()
            print(f"========== 第{idx}段对话结束 ==========")
            
            scene = json.load(open(scene_path, "r", encoding="utf-8"))
            # 保存本段对话历史
            memory_simulator.add_history(chat_env.get_history(), idx, scene["title"])

            # 立刻分析本段对话的intention
            print(f"\n=== NPC Intention & Next Goal Analysis (Scene {idx}) ===")
            segment_history = memory_simulator.get_segment_history(idx)
            analysis_results = analyze_npc_intentions_and_goals(
                history=segment_history,
                scene_path=scene_path,
                npc_info_paths=temp_npc_files  # 使用临时文件
            )
            for npc, result in analysis_results.items():
                print(f"{npc}: {result}")
    finally:
        # 清理临时文件
        cleanup_temp_files(temp_npc_files)


if __name__ == "__main__":
    example_usage()

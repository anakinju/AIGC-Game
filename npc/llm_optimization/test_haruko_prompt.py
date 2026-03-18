import os
import sys
import json
import asyncio
from typing import Dict, List, Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.getcwd()))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from npc.utils.base_npc import NPCAgent

class LLMOptimizer:
    def __init__(self, npc_name: str):
        self.npc_name = npc_name
        # 显式指定模型为 gpt-4o，避免默认的 gpt-4o-mini 可能存在的权限或额度问题
        self.agent = NPCAgent(npc_name, llm_model="gpt-4o")
        self.llm = self.agent.llm
        
    def get_default_prompt(self):
        """获取系统默认生成的 Prompt"""
        return self.agent.get_system_prompt()
    
    def get_custom_prompt(self, file_path: str):
        """从文件读取自定义 Prompt"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()

    async def run_comparison(self, custom_prompt_path: str, test_cases: List[str]):
        default_prompt = self.get_default_prompt()
        custom_prompt = self.get_custom_prompt(custom_prompt_path)
        
        results = []
        
        for i, user_input in enumerate(test_cases):
            print(f"\n[Test Case {i+1}] Input: {user_input}")
            
            # 测试默认 Prompt
            print(f"Generating response with DEFAULT prompt...")
            try:
                default_resp = await self.llm.ainvoke([
                    SystemMessage(content=default_prompt),
                    HumanMessage(content=user_input)
                ])
                default_content = default_resp.content
            except Exception as e:
                default_content = f"Error: {str(e)}"
            
            # 测试自定义 Prompt
            print(f"Generating response with CUSTOM prompt...")
            try:
                custom_resp = await self.llm.ainvoke([
                    SystemMessage(content=custom_prompt),
                    HumanMessage(content=user_input)
                ])
                custom_content = custom_resp.content
            except Exception as e:
                custom_content = f"Error: {str(e)}"
            
            results.append({
                "case_id": i + 1,
                "input": user_input,
                "default_response": default_content,
                "custom_response": custom_content
            })
            
        return results

async def main():
    optimizer = LLMOptimizer("Haruko")
    custom_prompt_path = "npc/single_npc/prompts/haruko/baseprompt.txt"
    
    test_cases = [
        # Basic Identity & Authority
        "Who are you? What are you investigating here?",
        "I don't think I need to report everything to you, Haruko.",
        
        # Scene Related (from demo.json: 01 00 00)
        "I'm here for the assignment. What is this assignment about?",
        "Why do I have to deliver this to someone named Chou Hu? Find someone else.",
        "You expect me to find Chou Hu on my own? That's not part of my job description.",
        
        # Provocation & Rule Breaking
        "I heard you're just using this investigation to build your own faction. Is that true?",
        "(Looking relaxed and leaning back) You seem awfully tense today, boss. Maybe you need a break.",
        "I lost the document. It's not a big deal, right?",
        
        # Power Dynamics & Manipulation
        "What do you think of the Dean? Is he really as objective as he seems?",
        "If I do this for you, what's in it for me? I want a seat at the table."
    ]
    
    print("Starting LLM Optimization Test for Haruko...")
    results = await optimizer.run_comparison(custom_prompt_path, test_cases)
    
    # 保存结果到文件
    output_file = "aigc_game/llm_optimization/test_results.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\nTest completed. Results saved to {output_file}")
    
    # 打印简要对比
    for res in results:
        print("\n" + "="*50)
        print(f"INPUT: {res['input']}")
        print("-" * 20)
        print(f"DEFAULT PROMPT RESPONSE:\n{res['default_response']}")
        print("-" * 20)
        print(f"CUSTOM PROMPT RESPONSE:\n{res['custom_response']}")

if __name__ == "__main__":
    asyncio.run(main())

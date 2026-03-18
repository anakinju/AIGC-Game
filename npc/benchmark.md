# NPC 交互平台技术基准文档

![workflow](images/Workflow.png)
![data](images/data.png)

## 项目概述

基于 **LangGraph** 构建的低耦合NPC交互平台，实现了双模式对话系统：玩家参与模式和NPC自主对话模式。通过工作流引擎和智能路由实现多NPC协同交互，集成完整的情绪、关系、目标管理工具链。


### 核心框架

- **LangGraph**: state machine工作流引擎，负责节点路由和状态管理
- **LangChain**: LLM工具链集成和Prompt模板管理
- **OpenAI API**: GPT-4o-mini作为推理引擎
- **Python 3.8+**: 异步编程 + 逻辑处理

### 关键库
```python
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict, Annotated
from pydantic import BaseModel, Field
```

##  核心实现

### 1. LangGraph工作流架构
```python
# 状态定义
class ChatState(TypedDict):
    sender: Annotated[str, "last"]  
    message: Annotated[str, "last"]
    chat_group: Annotated[List[str], "last"]
    game_state: Annotated[Dict[str, Any], "last"] #储存scene，relationships等信息
    npc_emotions: Annotated[Dict[str, str], "last"]
```
### 2. router算法
```python
1. Player mode: 玩家自主选择npc，被选定的npc进入responders list，只有responders list中的npc生成回复，否则只调用工具更新state/emotion
2. NPC mode： 玩家不参与，随机选择下一个发言的npc，强制3轮未发言的npc发言
```

### 3. 工具链自动编排
```python
class EnhancedNPCBehavior(BaseNPCBehavior):
    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 1. 上下文构建
        conversation_history = self._get_conversation_history(state)
        
        # 2. 工具调用 (自动)
        self._process_emotion_tools(state, conversation_history)
        self._process_relationship_tools(state, conversation_history) 
        
        # 3. 响应生成
        response = self._generate_response(full_prompt)
        
        # 4. 状态更新
        self._update_message_store(state, response)
        return state
```

##  Prompt engineer

### NPC Prompt
```python
def _build_npc_only_prompt(self, state, history):
    return f"""
    ## NPC身份
    {self.agent.get_npc_info()['basic_information']}
    
    ## 当前场景
    环境: {game_state.get('environment', '')}
    Key NPC: {game_state.get('key_npcs', [])}
    
    ## 情绪状态 
    当前情绪: {current_emotion['goal']}
    触发条件: {current_emotion.get('trigger_condition', 'None')}
    
    ## 关系网络
    {self._format_relationships(game_state)}
    
    ## 对话历史
    {self._format_conversation_history(history)}
    
    ## 指令
    基于以上信息，以{self.name}的身份回应最新消息。
    要求：符合角色性格，考虑情绪状态，维护关系动态。
    """
```

### NPC System Prompt Optimization

`system_prompt_optimization.py` 是用于自动化优化 NPC 系统提示词（System Prompt）的工具。其核心目标是通过多轮迭代评测和 LLM 自动改写，使 LLM 生成的 NPC 回应在风格、角色一致性等方面更贴合设计预期。

**主要功能：**
- 自动化 prompt 优化：结合评测反馈自动优化系统提示词。
- 风格一致性评测：集成 LLM 评测器，自动判断模型输出与参考输出在角色风格上的相似度。
- 数据驱动：支持批量读取数据集（含输入、参考输出、初始 prompt），自动完成优化流程。
- 结果回写：将最佳 prompt 及得分自动写回原数据文件。

**技术流程：**
1. 加载数据集（含初始 prompt、输入示例、参考输出）
2. 用当前 prompt 让 LLM 生成 NPC 回应
3. 用 LLM 评测器对比模型输出与参考输出，判断风格一致性
4. 统计通过率，若未达阈值则用 LLM 自动生成更优 prompt 进入下一轮
5. 达到设定分数阈值或最大轮数后，输出最佳 prompt 并写回数据文件

**典型应用场景：**
- NPC 角色风格微调与批量优化
- 新角色上线时的自动化 prompt 适配
- 长期运营下的风格一致性维护

```python
# prompt优化主循环
for iteration in range(max_iterations):
    # 1. 用当前 prompt 生成输出
    # 2. LLM 评测风格一致性
    # 3. 统计得分，若达标则终止
    # 4. 否则用 LLM 优化 prompt，进入下一轮

# LLM风格一致性评测
from openevals.llm import create_llm_as_judge

def character_evaluator(inputs, outputs, reference_outputs):
    evaluator = create_llm_as_judge(prompt=judge_prompt, ...)
    eval_result = evaluator(inputs=inputs, outputs=outputs, reference_outputs=reference_outputs)
    return eval_result

# prompt自动优化
response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...]
)
improved_prompt = response.choices[0].message.content.strip()
```

**使用方法说明：**
1. **数据准备**：在 `npc/dataset/` 目录下准备包含 `initial_prompt`、`examples` 字段的 json 文件。
2. **运行优化脚本**：
   ```bash
   cd npc/single_npc
   poetry run python system_prompt_optimization.py
   ```
3. **查看结果**：优化后的最佳 prompt 和得分会自动写回原 json 文件，可用于后续 NPC 生成。

### 工具专用Prompt
```python
# 情绪分析工具
emotion_prompt = """
分析NPC在以下对话中的情绪变化：
对话历史: {conversation_history}
情绪池: {emotion_pool}
当前情绪: {current_emotion}

输出JSON格式：
{{"emotion_id": "新情绪ID", "reasoning": "分析理由"}}
"""

# 关系管理工具  
relationship_prompt = """
分析以下交互对NPC关系的影响：
源NPC: {source_npc}
需要分析的NPC: {key_npcs}
对话历史: {interaction_content}
当前关系: {current_relationships}

输出格式：
{{"relationships": {{"npc1-npc2": {{"state": "new_state", "change": "change_direction"}}}}}}
"""


validation_prompt = f"""
分析以下玩家输入是否与当前场景相关：
        
        ## 场景信息
        场景名称: {scene_data.get('name', '')}
        环境描述: {scene_data.get('environment', '')}
        关键问题: {scene_data.get('key_questions', [])}
        NPC目标: {scene_data.get('npc_purposes', {})}
        
        ## 玩家输入
        {player_input}
        
        ## 判断标准
        - STORY_RELEVANT: 与场景/角色/剧情相关
        - NOT_STORY_RELEVANT: 无关话题、闲聊、测试性输入
        
        输出JSON格式：
        {{
            "category": "STORY_RELEVANT/NOT_STORY_RELEVANT",
            "reason": "判断理由",
            "send_to_bottom": true/false
        }}
        """
```

# Big Scale Intention

`big_scale_intention_test.py` 主要用于多NPC大规模意图与目标分析的自动化测试与流程演示，适用于剧情推进、群体NPC协作等复杂场景。该脚本集成了对话历史记录、NPC意图分析、目标预测等功能，便于开发者批量验证和调优多NPC系统的智能表现。

**主要功能：**
- 多场景对话历史自动采集与结构化存储
- 基于LLM的NPC意图与下阶段目标自动分析
- 支持从统一角色配置（Characters.json）自动生成单NPC信息文件，便于兼容分析流程
- 提供完整的测试用例与流程演示，便于开发者快速复现和扩展

**使用方法说明：**
1. **数据准备**：准备好多段场景对话的 json 文件（如 `scripted_subtask_layer1_20250415_180747_response.json` 等）和角色配置文件（Characters.json）。
2. **运行脚本**：
   ```bash
   cd npc/multi_npc/test
   poetry run python big_scale_intention_test.py
   ```
3. **查看结果**：终端将输出每段对话的历史、每个NPC的意图与下阶段目标分析，便于后续调优和验证。

### 核心能力
- **双模式交互**: Player-involved + NPC-only 
- **智能路由**: 防止NPC长期静默，动态选择发言者  
- **工具链集成**: 情绪/关系/目标工具自动调用
- **数据驱动**: 场景JSON自动生成NPC配置
- **输入验证**: 智能过滤玩家无关输入，减少bottom layer无效生成
- **系统提示词自动优化**: 支持system prompt optimization，自动提升NPC风格一致性和对话质量
- **大规模意图分析**: 支持big scale intention，批量分析多NPC意图与目标，助力复杂剧情推进

### 性能指标
- **响应时间**: 2-5秒一个NPC (GPT-4o-mini);NPC freechat 30s以内
- **Prompt优化效率**: system prompt optimization可在5轮内自动收敛至最佳prompt，提升风格一致性
- **大规模分析能力**: big scale intention可高效处理多场景、多NPC的意图与目标分析

### 解决的问题
1. **多NPC协调**: LangGraph工作流 → 避免冲突死锁
2. **状态同步**: 统一状态管理 → 跨场景连贯性
3. **输入质量**: PlayerNode验证 → 过滤无关输入  
4. **扩展性**: 低耦合设计 
5. **NPC风格一致性**: system prompt optimization自动优化提示词，保障NPC长期风格统一
6. **复杂剧情推进与分析**: big scale intention支持多场景、多NPC意图与目标的批量分析，助力剧情演化和群体智能测试


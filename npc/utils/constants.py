"""
项目常量定义，用于消除硬编码字符串。
"""

class ChatMode:
    PLAYER_INVOLVED = "player_involved"
    CASUAL_CHAT = "casual_chat"
    ANGRY_CHAT = "angry_chat"
    NPC_ONLY = "npc_only"

class LLMUsage:
    """LLM 用途分类，用于工厂模式分配不同的参数"""
    GENERAL = "general"      # 通用对话
    VALIDATION = "validation" # 逻辑验证 (low temperature)
    EMOTION = "emotion"      # 情绪分析
    STORY = "story"          # 剧情生成 (high temperature)

class ModelName:
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4O = "gpt-4o"

class Config:
    DEFAULT_MODEL = ModelName.GPT_4O_MINI
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_TIMEOUT = 100
    DEFAULT_RETRIES = 3
    MAX_HISTORY_LEN = 15

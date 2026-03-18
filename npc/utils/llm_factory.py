import os
from typing import Optional
from langchain_openai import ChatOpenAI
from npc.utils.constants import Config, LLMUsage

class LLMFactory:
    """
    LLM 工厂模式实现，统一管理 ChatOpenAI 实例的创建。
    """
    
    @staticmethod
    def create_chat_model(
        usage: str = LLMUsage.GENERAL,
        model_name: str = Config.DEFAULT_MODEL,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ChatOpenAI:
        """
        根据用途创建 LLM 实例。
        """
        # 获取环境变量
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        
        # 根据用途设置默认温度
        if temperature is None:
            if usage == LLMUsage.VALIDATION:
                temperature = 0.1
            elif usage == LLMUsage.EMOTION:
                temperature = 0.3
            elif usage == LLMUsage.STORY:
                temperature = 0.8
            else:
                temperature = Config.DEFAULT_TEMPERATURE
        
        # 默认参数
        params = {
            "model_name": model_name,
            "api_key": api_key,
            "base_url": api_base,
            "temperature": temperature,
            "request_timeout": kwargs.get("timeout", Config.DEFAULT_TIMEOUT),
            "max_retries": kwargs.get("max_retries", Config.DEFAULT_RETRIES),
        }
        
        # 允许覆盖其他参数
        params.update(kwargs)
        
        return ChatOpenAI(**params)

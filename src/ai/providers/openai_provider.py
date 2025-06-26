import os
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from openai import OpenAI, AsyncOpenAI
from ..base import LLMProvider, LLMResponse

class OpenAIProvider(LLMProvider):
    """OpenAI LLM提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        self.model = config.get("model", "gpt-4o")
        self.client = None
        self.async_client = None
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
            self.async_client = AsyncOpenAI(api_key=self.api_key)
        
        # 可用模型列表
        self._available_models = [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ]
    
    @property
    def name(self) -> str:
        return "openai"
    
    def is_available(self) -> bool:
        """检查OpenAI服务是否可用"""
        if not self.api_key:
            return False
        
        try:
            # 简单的API调用测试
            if self.client:
                models = self.client.models.list()
                return True
        except Exception:
            return False
        
        return False
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if not self.is_available():
            return []
        
        try:
            # 获取实际可用的模型
            models = self.client.models.list()
            available = []
            for model in models.data:
                if any(base in model.id for base in ["gpt-4", "gpt-3.5"]):
                    available.append(model.id)
            
            return available if available else self._available_models
        except Exception:
            return self._available_models
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """生成回复"""
        if not self.async_client:
            return LLMResponse(
                content="错误: OpenAI API密钥未配置",
                model=self.model,
                provider=self.name,
                usage={"error": "no_api_key"}
            )
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.9,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.name,
                usage=usage
            )
        
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                error_msg = "OpenAI API频率限制，请稍后重试"
            elif "insufficient_quota" in error_msg.lower():
                error_msg = "OpenAI API配额不足"
            elif "invalid_api_key" in error_msg.lower():
                error_msg = "OpenAI API密钥无效"
            
            return LLMResponse(
                content=f"OpenAI错误: {error_msg}",
                model=self.model,
                provider=self.name,
                usage={"error": str(e)}
            )
    
    def generate_sync(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """同步生成回复"""
        if not self.client:
            return LLMResponse(
                content="错误: OpenAI API密钥未配置",
                model=self.model,
                provider=self.name,
                usage={"error": "no_api_key"}
            )
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2048,
                top_p=0.9,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.name,
                usage=usage
            )
        
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                error_msg = "OpenAI API频率限制，请稍后重试"
            elif "insufficient_quota" in error_msg.lower():
                error_msg = "OpenAI API配额不足"
            elif "invalid_api_key" in error_msg.lower():
                error_msg = "OpenAI API密钥无效"
            
            return LLMResponse(
                content=f"OpenAI错误: {error_msg}",
                model=self.model,
                provider=self.name,
                usage={"error": str(e)}
            )
    
    def get_status(self) -> Dict[str, Any]:
        """获取OpenAI服务状态"""
        return {
            "available": self.is_available(),
            "model": self.model,
            "has_api_key": bool(self.api_key),
            "available_models": self.get_available_models()
        }
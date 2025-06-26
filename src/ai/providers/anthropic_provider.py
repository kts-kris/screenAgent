import os
import asyncio
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, AsyncAnthropic
from ..base import LLMProvider, LLMResponse

class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        self.model = config.get("model", "claude-3-5-sonnet-20241022")
        self.client = None
        self.async_client = None
        
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
            self.async_client = AsyncAnthropic(api_key=self.api_key)
        
        # 可用模型列表
        self._available_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307"
        ]
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    def is_available(self) -> bool:
        """检查Anthropic服务是否可用"""
        if not self.api_key:
            return False
        
        try:
            # 简单的API调用测试
            if self.client:
                # Claude API没有单独的健康检查端点，我们通过一个简单的请求来测试
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}]
                )
                return True
        except Exception:
            return False
        
        return False
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if not self.is_available():
            return []
        
        # Claude API目前没有列出模型的端点，返回已知的可用模型
        return self._available_models
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """生成回复"""
        if not self.async_client:
            return LLMResponse(
                content="错误: Anthropic API密钥未配置",
                model=self.model,
                provider=self.name,
                usage={"error": "no_api_key"}
            )
        
        try:
            # Claude的消息格式
            messages = [{"role": "user", "content": prompt}]
            
            kwargs = {
                "model": self.model,
                "max_tokens": 2048,
                "messages": messages,
                "temperature": 0.7
            }
            
            # 如果有系统提示，添加到参数中
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = await self.async_client.messages.create(**kwargs)
            
            content = response.content[0].text if response.content else ""
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
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
                error_msg = "Claude API频率限制，请稍后重试"
            elif "insufficient_quota" in error_msg.lower():
                error_msg = "Claude API配额不足"
            elif "invalid_api_key" in error_msg.lower():
                error_msg = "Claude API密钥无效"
            elif "overloaded" in error_msg.lower():
                error_msg = "Claude服务器过载，请稍后重试"
            
            return LLMResponse(
                content=f"Claude错误: {error_msg}",
                model=self.model,
                provider=self.name,
                usage={"error": str(e)}
            )
    
    def generate_sync(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """同步生成回复"""
        if not self.client:
            return LLMResponse(
                content="错误: Anthropic API密钥未配置",
                model=self.model,
                provider=self.name,
                usage={"error": "no_api_key"}
            )
        
        try:
            # Claude的消息格式
            messages = [{"role": "user", "content": prompt}]
            
            kwargs = {
                "model": self.model,
                "max_tokens": 2048,
                "messages": messages,
                "temperature": 0.7
            }
            
            # 如果有系统提示，添加到参数中
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = self.client.messages.create(**kwargs)
            
            content = response.content[0].text if response.content else ""
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
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
                error_msg = "Claude API频率限制，请稍后重试"
            elif "insufficient_quota" in error_msg.lower():
                error_msg = "Claude API配额不足"
            elif "invalid_api_key" in error_msg.lower():
                error_msg = "Claude API密钥无效"
            elif "overloaded" in error_msg.lower():
                error_msg = "Claude服务器过载，请稍后重试"
            
            return LLMResponse(
                content=f"Claude错误: {error_msg}",
                model=self.model,
                provider=self.name,
                usage={"error": str(e)}
            )
    
    def get_status(self) -> Dict[str, Any]:
        """获取Anthropic服务状态"""
        return {
            "available": self.is_available(),
            "model": self.model,
            "has_api_key": bool(self.api_key),
            "available_models": self.get_available_models()
        }
import asyncio
from typing import Dict, Any, Optional, List
from .base import LLMProvider, LLMResponse
from .providers import OllamaProvider, OpenAIProvider, AnthropicProvider

class LLMManager:
    """LLM管理器，统一管理多个LLM提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.default_provider = config.get("default_provider", "ollama")
        self.providers: Dict[str, LLMProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化LLM提供商"""
        providers_config = self.config.get("providers", {})
        
        # 初始化Ollama
        if "ollama" in providers_config:
            try:
                self.providers["ollama"] = OllamaProvider(providers_config["ollama"])
            except Exception as e:
                print(f"初始化Ollama提供商失败: {e}")
        
        # 初始化OpenAI
        if "openai" in providers_config:
            try:
                self.providers["openai"] = OpenAIProvider(providers_config["openai"])
            except Exception as e:
                print(f"初始化OpenAI提供商失败: {e}")
        
        # 初始化Anthropic
        if "anthropic" in providers_config:
            try:
                self.providers["anthropic"] = AnthropicProvider(providers_config["anthropic"])
            except Exception as e:
                print(f"初始化Anthropic提供商失败: {e}")
    
    def get_provider(self, provider_name: Optional[str] = None) -> Optional[LLMProvider]:
        """获取指定的LLM提供商"""
        if provider_name is None:
            provider_name = self.default_provider
        
        return self.providers.get(provider_name)
    
    def get_available_providers(self) -> List[str]:
        """获取所有可用的LLM提供商"""
        available = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
        return available
    
    def get_best_available_provider(self) -> Optional[str]:
        """获取最佳可用的LLM提供商"""
        # 优先级顺序：ollama -> anthropic -> openai
        priority_order = ["ollama", "anthropic", "openai"]
        
        for provider_name in priority_order:
            if provider_name in self.providers and self.providers[provider_name].is_available():
                return provider_name
        
        # 如果优先级列表中没有可用的，检查其他提供商
        for name, provider in self.providers.items():
            if provider.is_available():
                return name
        
        return None
    
    async def generate(self, 
                      prompt: str, 
                      system_prompt: Optional[str] = None,
                      provider_name: Optional[str] = None,
                      fallback: bool = True) -> LLMResponse:
        """生成回复，支持自动回退"""
        
        # 选择提供商
        if provider_name is None:
            provider_name = self.default_provider
        
        provider = self.get_provider(provider_name)
        
        if provider is None:
            if fallback:
                # 尝试使用最佳可用提供商
                provider_name = self.get_best_available_provider()
                if provider_name:
                    provider = self.get_provider(provider_name)
            
            if provider is None:
                return LLMResponse(
                    content="错误: 没有可用的LLM提供商",
                    model="none",
                    provider="none",
                    usage={"error": "no_available_providers"}
                )
        
        # 检查提供商是否可用
        if not provider.is_available():
            if fallback:
                # 尝试使用其他可用提供商
                fallback_provider_name = self.get_best_available_provider()
                if fallback_provider_name and fallback_provider_name != provider_name:
                    print(f"提供商 {provider_name} 不可用，回退到 {fallback_provider_name}")
                    provider = self.get_provider(fallback_provider_name)
                    if provider and provider.is_available():
                        return await provider.generate(prompt, system_prompt)
            
            return LLMResponse(
                content=f"错误: 提供商 {provider_name} 不可用",
                model="unknown",
                provider=provider_name,
                usage={"error": "provider_unavailable"}
            )
        
        # 生成回复
        return await provider.generate(prompt, system_prompt)
    
    def generate_sync(self, 
                     prompt: str, 
                     system_prompt: Optional[str] = None,
                     provider_name: Optional[str] = None,
                     fallback: bool = True) -> LLMResponse:
        """同步生成回复"""
        # 选择提供商
        if provider_name is None:
            provider_name = self.default_provider
        
        provider = self.get_provider(provider_name)
        
        if provider is None:
            if fallback:
                provider_name = self.get_best_available_provider()
                if provider_name:
                    provider = self.get_provider(provider_name)
            
            if provider is None:
                return LLMResponse(
                    content="错误: 没有可用的LLM提供商",
                    model="none",
                    provider="none",
                    usage={"error": "no_available_providers"}
                )
        
        # 检查提供商是否可用
        if not provider.is_available():
            if fallback:
                fallback_provider_name = self.get_best_available_provider()
                if fallback_provider_name and fallback_provider_name != provider_name:
                    print(f"提供商 {provider_name} 不可用，回退到 {fallback_provider_name}")
                    provider = self.get_provider(fallback_provider_name)
                    if provider and provider.is_available():
                        return provider.generate_sync(prompt, system_prompt)
            
            return LLMResponse(
                content=f"错误: 提供商 {provider_name} 不可用",
                model="unknown",
                provider=provider_name,
                usage={"error": "provider_unavailable"}
            )
        
        # 生成回复
        return provider.generate_sync(prompt, system_prompt)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有提供商的状态"""
        status = {}
        for name, provider in self.providers.items():
            try:
                status[name] = provider.get_status() if hasattr(provider, 'get_status') else {
                    "available": provider.is_available(),
                    "models": provider.get_available_models()
                }
            except Exception as e:
                status[name] = {
                    "available": False,
                    "error": str(e)
                }
        
        return status
    
    def set_default_provider(self, provider_name: str):
        """设置默认提供商"""
        if provider_name in self.providers:
            self.default_provider = provider_name
        else:
            raise ValueError(f"提供商 {provider_name} 不存在")
    
    def refresh_providers(self):
        """刷新所有提供商状态"""
        for provider in self.providers.values():
            if hasattr(provider, 'refresh_models'):
                provider.refresh_models()
    
    def get_provider_models(self, provider_name: str) -> List[str]:
        """获取指定提供商的可用模型"""
        provider = self.get_provider(provider_name)
        if provider:
            return provider.get_available_models()
        return []
    
    def benchmark_providers(self, test_prompt: str = "Hello, how are you?") -> Dict[str, Dict[str, Any]]:
        """对所有可用提供商进行基准测试"""
        results = {}
        
        for name, provider in self.providers.items():
            if not provider.is_available():
                results[name] = {"available": False}
                continue
            
            try:
                import time
                start_time = time.time()
                response = provider.generate_sync(test_prompt)
                end_time = time.time()
                
                results[name] = {
                    "available": True,
                    "response_time": end_time - start_time,
                    "response_length": len(response.content),
                    "model": response.model,
                    "success": "error" not in response.usage
                }
                
            except Exception as e:
                results[name] = {
                    "available": True,
                    "error": str(e),
                    "success": False
                }
        
        return results
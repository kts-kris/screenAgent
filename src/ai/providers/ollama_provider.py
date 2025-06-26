import requests
import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from ..base import LLMProvider, LLMResponse

class OllamaProvider(LLMProvider):
    """Ollama LLM提供商，支持本地模型自动检测"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.model = config.get("model", "auto")
        self.preferred_models = config.get("preferred_models", [
            "llama3.2", "qwen2.5", "gemma2", "phi3", "mistral", "codellama"
        ])
        self._selected_model = None
        self._available_models = None
    
    @property
    def name(self) -> str:
        return "ollama"
    
    def is_available(self) -> bool:
        """检查Ollama服务是否可用"""
        try:
            response = requests.get(f"{self.base_url}/api/version", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if self._available_models is not None:
            return self._available_models
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = [model["name"] for model in data.get("models", [])]
                self._available_models = models
                return models
        except Exception as e:
            print(f"获取Ollama模型列表失败: {e}")
        
        return []
    
    def _select_best_model(self) -> Optional[str]:
        """根据偏好选择最佳可用模型"""
        if self._selected_model:
            return self._selected_model
        
        if self.model != "auto":
            # 用户指定了具体模型
            available_models = self.get_available_models()
            if self.model in available_models:
                self._selected_model = self.model
                return self.model
            else:
                print(f"指定的模型 {self.model} 不可用，尝试自动选择")
        
        # 自动选择模型
        available_models = self.get_available_models()
        if not available_models:
            return None
        
        # 按偏好顺序选择
        for preferred in self.preferred_models:
            for available in available_models:
                if preferred in available.lower():
                    self._selected_model = available
                    print(f"自动选择模型: {available}")
                    return available
        
        # 如果没有匹配的偏好模型，选择第一个可用的
        self._selected_model = available_models[0]
        print(f"使用第一个可用模型: {available_models[0]}")
        return available_models[0]
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """生成回复"""
        model = self._select_best_model()
        if not model:
            return LLMResponse(
                content="错误: 没有可用的Ollama模型",
                model="none",
                provider=self.name,
                usage={"error": "no_available_models"}
            )
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get("message", {}).get("content", "")
                        
                        # 提取使用统计信息
                        usage = {
                            "prompt_tokens": data.get("prompt_eval_count", 0),
                            "completion_tokens": data.get("eval_count", 0),
                            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                            "eval_duration": data.get("eval_duration", 0),
                            "load_duration": data.get("load_duration", 0)
                        }
                        
                        return LLMResponse(
                            content=content,
                            model=model,
                            provider=self.name,
                            usage=usage
                        )
                    else:
                        error_text = await response.text()
                        return LLMResponse(
                            content=f"Ollama API错误: {error_text}",
                            model=model,
                            provider=self.name,
                            usage={"error": f"api_error_{response.status}"}
                        )
        
        except asyncio.TimeoutError:
            return LLMResponse(
                content="错误: Ollama响应超时",
                model=model,
                provider=self.name,
                usage={"error": "timeout"}
            )
        except Exception as e:
            return LLMResponse(
                content=f"Ollama连接错误: {str(e)}",
                model=model,
                provider=self.name,
                usage={"error": str(e)}
            )
    
    def generate_sync(self, prompt: str, system_prompt: Optional[str] = None) -> LLMResponse:
        """同步生成回复"""
        model = self._select_best_model()
        if not model:
            return LLMResponse(
                content="错误: 没有可用的Ollama模型",
                model="none",
                provider=self.name,
                usage={"error": "no_available_models"}
            )
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                
                usage = {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
                    "eval_duration": data.get("eval_duration", 0),
                    "load_duration": data.get("load_duration", 0)
                }
                
                return LLMResponse(
                    content=content,
                    model=model,
                    provider=self.name,
                    usage=usage
                )
            else:
                return LLMResponse(
                    content=f"Ollama API错误: {response.text}",
                    model=model,
                    provider=self.name,
                    usage={"error": f"api_error_{response.status_code}"}
                )
        
        except requests.exceptions.Timeout:
            return LLMResponse(
                content="错误: Ollama响应超时",
                model=model,
                provider=self.name,
                usage={"error": "timeout"}
            )
        except Exception as e:
            return LLMResponse(
                content=f"Ollama连接错误: {str(e)}",
                model=model,
                provider=self.name,
                usage={"error": str(e)}
            )
    
    def pull_model(self, model_name: str) -> bool:
        """拉取新模型"""
        try:
            payload = {"name": model_name}
            response = requests.post(
                f"{self.base_url}/api/pull",
                json=payload,
                timeout=300  # 5分钟超时
            )
            
            if response.status_code == 200:
                # 清空缓存，重新获取模型列表
                self._available_models = None
                print(f"模型 {model_name} 拉取成功")
                return True
            else:
                print(f"模型 {model_name} 拉取失败: {response.text}")
                return False
        
        except Exception as e:
            print(f"拉取模型时出错: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """删除模型"""
        try:
            payload = {"name": model_name}
            response = requests.delete(
                f"{self.base_url}/api/delete",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                # 清空缓存
                self._available_models = None
                if self._selected_model == model_name:
                    self._selected_model = None
                print(f"模型 {model_name} 删除成功")
                return True
            else:
                print(f"模型 {model_name} 删除失败: {response.text}")
                return False
        
        except Exception as e:
            print(f"删除模型时出错: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """获取模型详细信息"""
        try:
            payload = {"name": model_name}
            response = requests.post(
                f"{self.base_url}/api/show",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
        
        except Exception:
            return None
    
    def refresh_models(self):
        """刷新模型列表缓存"""
        self._available_models = None
        self._selected_model = None
    
    def get_status(self) -> Dict[str, Any]:
        """获取Ollama服务状态"""
        status = {
            "available": self.is_available(),
            "selected_model": self._selected_model,
            "available_models": self.get_available_models(),
            "base_url": self.base_url
        }
        
        if status["available"] and status["selected_model"]:
            model_info = self.get_model_info(status["selected_model"])
            if model_info:
                status["model_info"] = {
                    "size": model_info.get("size", "unknown"),
                    "family": model_info.get("details", {}).get("family") or "unknown",
                    "parameter_size": model_info.get("details", {}).get("parameter_size") or "unknown"
                }
        
        return status
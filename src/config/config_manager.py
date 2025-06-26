import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class LLMConfig(BaseModel):
    default_provider: str = "ollama"
    providers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class CaptureConfig(BaseModel):
    screenshot_format: str = "PNG"
    quality: int = 95

class OCRConfig(BaseModel):
    language: str = "eng+chi_sim"
    engine: str = "tesseract"

class UIConfig(BaseModel):
    theme: str = "dark"
    show_preview: bool = True

class SecurityConfig(BaseModel):
    max_execution_time: int = 30
    allowed_actions: list = Field(default_factory=lambda: ["click", "type", "scroll", "screenshot"])

class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/app.log"

class Config(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    capture: CaptureConfig = Field(default_factory=CaptureConfig)
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else Path("config.yaml")
        self._config: Optional[Config] = None
    
    def load_config(self) -> Config:
        """加载配置文件"""
        if not self.config_path.exists():
            self._config = Config()
            self.save_config()
            return self._config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            self._config = Config(**config_data)
        except Exception as e:
            print(f"配置文件加载失败，使用默认配置: {e}")
            self._config = Config()
        
        return self._config
    
    def save_config(self):
        """保存配置文件"""
        if self._config is None:
            return
        
        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config.model_dump(), f, default_flow_style=False, allow_unicode=True)
    
    @property
    def config(self) -> Config:
        """获取配置实例"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def get_env_or_config(self, env_key: str, config_value: Any) -> Any:
        """优先使用环境变量，否则使用配置值"""
        return os.getenv(env_key, config_value)
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text

class StatusDisplay:
    """状态显示器"""
    
    def __init__(self, console: Console):
        self.console = console
    
    def show_system_status(self, status: Dict[str, Any]):
        """显示完整系统状态"""
        
        # 屏幕截图状态
        screen_panel = self._create_screen_status_panel(status.get("screen_capture", {}))
        
        # OCR引擎状态
        ocr_panel = self._create_ocr_status_panel(status.get("ocr_engine", {}))
        
        # LLM状态
        llm_panel = self._create_llm_status_panel(status.get("llm_manager", {}))
        
        # 执行器状态
        executor_panel = self._create_executor_status_panel(status.get("action_executor", {}))
        
        # 组合显示
        self.console.print(Panel(
            Columns([screen_panel, ocr_panel], equal=True, expand=True),
            title="📸 截图 & 🔍 OCR 状态",
            border_style="blue"
        ))
        
        self.console.print(Panel(
            llm_panel,
            title="🤖 LLM 状态",
            border_style="green"
        ))
        
        self.console.print(Panel(
            executor_panel,
            title="⚡ 执行器状态",
            border_style="yellow"
        ))
    
    def _create_screen_status_panel(self, screen_status: Dict[str, Any]) -> Panel:
        """创建屏幕状态面板"""
        if screen_status.get("available", False):
            screen_size = screen_status.get("screen_size", (0, 0))
            content = f"""[green]✅ 可用[/green]
屏幕尺寸: {screen_size[0]}x{screen_size[1]}"""
        else:
            content = "[red]❌ 不可用[/red]"
        
        return Panel(content, title="屏幕截图", border_style="dim")
    
    def _create_ocr_status_panel(self, ocr_status: Dict[str, Any]) -> Panel:
        """创建OCR状态面板"""
        if ocr_status.get("available", False):
            languages = ocr_status.get("languages", [])
            lang_display = ", ".join(languages[:3]) if languages else "未知"
            if len(languages) > 3:
                lang_display += f" (+{len(languages)-3})"
            
            content = f"""[green]✅ 可用[/green]
支持语言: {lang_display}"""
        else:
            content = "[red]❌ 不可用[/red]\n请安装 tesseract"
        
        return Panel(content, title="OCR引擎", border_style="dim")
    
    def _create_llm_status_panel(self, llm_status: Dict[str, Any]) -> Table:
        """创建LLM状态表格"""
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("提供商", width=12)
        table.add_column("状态", width=10)
        table.add_column("模型", width=20)
        table.add_column("详情")
        
        for provider_name, info in llm_status.items():
            if isinstance(info, dict):
                # 状态
                if info.get("available", False):
                    status = "[green]✅ 可用[/green]"
                else:
                    status = "[red]❌ 不可用[/red]"
                
                # 模型
                model = info.get("model", "未知")
                if provider_name == "ollama":
                    available_models = info.get("available_models", [])
                    if available_models:
                        model = f"{model} ({len(available_models)}个可用)"
                
                # 详情
                details = []
                if "has_api_key" in info:
                    details.append("API密钥: " + ("✅" if info["has_api_key"] else "❌"))
                if provider_name == "ollama" and "base_url" in info:
                    details.append(f"URL: {info['base_url']}")
                if "selected_model" in info:
                    details.append(f"当前: {info['selected_model']}")
                
                details_text = " | ".join(details) if details else "-"
                
                table.add_row(provider_name.title(), status, model, details_text)
        
        if not llm_status:
            table.add_row("-", "[red]❌ 无配置[/red]", "-", "-")
        
        return table
    
    def _create_executor_status_panel(self, executor_status: Dict[str, Any]) -> Table:
        """创建执行器状态表格"""
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("统计项", width=15)
        table.add_column("数值", width=10)
        table.add_column("详情")
        
        total_actions = executor_status.get("total_actions", 0)
        successful_actions = executor_status.get("successful_actions", 0)
        failed_actions = executor_status.get("failed_actions", 0)
        avg_time = executor_status.get("average_time", 0)
        success_rate = executor_status.get("success_rate", 0)
        
        table.add_row("总动作数", str(total_actions), "-")
        table.add_row("成功动作", f"[green]{successful_actions}[/green]", "-")
        table.add_row("失败动作", f"[red]{failed_actions}[/red]", "-")
        table.add_row("成功率", f"{success_rate:.1%}", "-")
        table.add_row("平均用时", f"{avg_time:.2f}s", "-")
        
        return table
    
    def show_provider_details(self, provider_name: str, provider_info: Dict[str, Any]):
        """显示特定提供商的详细信息"""
        
        if provider_name == "ollama":
            self._show_ollama_details(provider_info)
        elif provider_name in ["openai", "anthropic"]:
            self._show_api_provider_details(provider_name, provider_info)
    
    def _show_ollama_details(self, info: Dict[str, Any]):
        """显示Ollama详细信息"""
        table = Table(title="Ollama 详细状态", show_header=True, header_style="bold blue")
        table.add_column("属性", width=15)
        table.add_column("值")
        
        table.add_row("服务状态", "✅ 运行中" if info.get("available") else "❌ 未运行")
        table.add_row("服务地址", info.get("base_url", "未知"))
        table.add_row("当前模型", info.get("selected_model", "未选择"))
        
        available_models = info.get("available_models", [])
        if available_models:
            models_text = "\n".join(available_models)
            table.add_row("可用模型", models_text)
        else:
            table.add_row("可用模型", "[red]无可用模型[/red]")
        
        # 模型详情
        if info.get("model_info"):
            model_info = info["model_info"]
            table.add_row("模型大小", model_info.get("size", "未知"))
            table.add_row("模型系列", model_info.get("family", "未知"))
            table.add_row("参数规模", model_info.get("parameter_size", "未知"))
        
        self.console.print(table)
    
    def _show_api_provider_details(self, provider_name: str, info: Dict[str, Any]):
        """显示API提供商详细信息"""
        table = Table(title=f"{provider_name.title()} 详细状态", show_header=True, header_style="bold green")
        table.add_column("属性", width=15)
        table.add_column("值")
        
        table.add_row("服务状态", "✅ 可用" if info.get("available") else "❌ 不可用")
        table.add_row("API密钥", "✅ 已配置" if info.get("has_api_key") else "❌ 未配置")
        table.add_row("当前模型", info.get("model", "未知"))
        
        available_models = info.get("available_models", [])
        if available_models:
            models_text = "\n".join(available_models[:10])  # 只显示前10个
            if len(available_models) > 10:
                models_text += f"\n... 及其他 {len(available_models) - 10} 个模型"
            table.add_row("可用模型", models_text)
        
        self.console.print(table)
    
    def show_performance_stats(self, stats: Dict[str, Any]):
        """显示性能统计"""
        table = Table(title="性能统计", show_header=True, header_style="bold yellow")
        table.add_column("组件", width=15)
        table.add_column("平均用时", width=12)
        table.add_column("调用次数", width=10)
        table.add_column("成功率", width=10)
        
        # 这里可以添加各组件的性能数据
        # 示例数据
        components = [
            ("屏幕截图", "0.15s", "42", "100%"),
            ("OCR识别", "1.2s", "38", "95%"),
            ("LLM分析", "3.8s", "25", "92%"),
            ("动作执行", "0.8s", "156", "88%"),
        ]
        
        for component, avg_time, count, success_rate in components:
            table.add_row(component, avg_time, count, success_rate)
        
        self.console.print(table)
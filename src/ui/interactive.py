import asyncio
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.columns import Columns
import questionary
from PIL import Image

from ..executor import InstructionProcessor

class InteractiveUI:
    """交互式用户界面"""
    
    def __init__(self, processor: InstructionProcessor, console: Console):
        self.processor = processor
        self.console = console
        self.history: List[str] = []
        self.session_stats = {
            "commands_executed": 0,
            "successful_commands": 0,
            "failed_commands": 0
        }
        
        # 设置回调
        self.processor.set_progress_callback(self._progress_callback)
        self.processor.set_screenshot_callback(self._screenshot_callback)
        
        self._current_progress_task = None
        self._progress_console = Console()
        self._screenshots: List[Image.Image] = []
    
    async def start(self):
        """启动交互界面"""
        self._show_welcome()
        await self._main_loop()
    
    def _show_welcome(self):
        """显示欢迎界面"""
        welcome_text = """
[bold blue]🤖 屏幕AI助手[/bold blue]

功能特性:
• 🖼️  智能屏幕截图和分析
• 👁️  OCR文字识别
• 🧠 多种LLM支持 (Ollama/OpenAI/Claude)
• ⚡ 自动化操作执行
• 💬 自然语言指令处理

输入指令来控制屏幕操作，或输入 'help' 查看帮助。
输入 'quit' 或 'exit' 退出程序。
        """
        
        self.console.print(Panel(
            welcome_text,
            border_style="blue",
            padding=(1, 2)
        ))
        
        # 显示系统状态
        self._show_quick_status()
    
    def _show_quick_status(self):
        """显示快速状态"""
        status = self.processor.get_system_status()
        
        # LLM状态
        llm_status = status.get("llm_manager", {})
        available_providers = [name for name, info in llm_status.items() 
                             if isinstance(info, dict) and info.get("available", False)]
        
        if available_providers:
            provider_text = ", ".join(available_providers)
            llm_display = f"[green]✅ {provider_text}[/green]"
        else:
            llm_display = "[red]❌ 无可用LLM[/red]"
        
        # OCR状态
        ocr_available = status.get("ocr_engine", {}).get("available", False)
        ocr_display = "[green]✅ 可用[/green]" if ocr_available else "[red]❌ 不可用[/red]"
        
        status_table = Table(show_header=False, box=None, padding=(0, 1))
        status_table.add_column("组件", style="bold")
        status_table.add_column("状态")
        
        status_table.add_row("LLM", llm_display)
        status_table.add_row("OCR", ocr_display)
        
        self.console.print(Panel(
            status_table,
            title="系统状态",
            border_style="dim",
            padding=(0, 1)
        ))
    
    async def _main_loop(self):
        """主循环"""
        while True:
            try:
                # 使用questionary获取用户输入
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: questionary.text(
                        "请输入指令:",
                        qmark="🎯",
                        style=questionary.Style([
                            ('qmark', 'fg:#FF6B6B bold'),
                            ('question', 'bold'),
                            ('answer', 'fg:#4ECDC4 bold'),
                            ('pointer', 'fg:#FF6B6B bold'),
                            ('highlighted', 'fg:#4ECDC4 bold'),
                        ])
                    ).ask()
                )
                
                if not user_input:
                    continue
                
                user_input = user_input.strip()
                
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    if Confirm.ask("确定要退出吗?"):
                        break
                    continue
                
                # 处理特殊命令
                if user_input.lower() == 'help':
                    self._show_help()
                    continue
                elif user_input.lower() == 'status':
                    self._show_detailed_status()
                    continue
                elif user_input.lower() == 'history':
                    self._show_history()
                    continue
                elif user_input.lower() == 'clear':
                    self.console.clear()
                    self._show_welcome()
                    continue
                elif user_input.lower() == 'stats':
                    self._show_session_stats()
                    continue
                elif user_input.lower().startswith('screenshot'):
                    await self._handle_screenshot_command(user_input)
                    continue
                elif user_input.lower().startswith('config'):
                    self._handle_config_command(user_input)
                    continue
                
                # 执行用户指令
                await self._execute_user_instruction(user_input)
                
            except KeyboardInterrupt:
                if Confirm.ask("\n检测到中断，确定要退出吗?"):
                    break
            except Exception as e:
                self.console.print(f"[red]发生错误: {e}[/red]")
        
        self._show_goodbye()
    
    async def _execute_user_instruction(self, instruction: str):
        """执行用户指令"""
        self.history.append(instruction)
        self.session_stats["commands_executed"] += 1
        
        # 询问是否使用AI分析
        use_ai = True
        if len(self.processor.llm_manager.get_available_providers()) > 1:
            use_ai = Confirm.ask("使用AI分析?", default=True)
        
        # 执行指令
        with self.console.status("[bold green]处理指令中...") as status:
            result = await self.processor.process_instruction(
                instruction, use_ai_analysis=use_ai
            )
        
        # 显示结果
        if result.success:
            self.session_stats["successful_commands"] += 1
            self.console.print(Panel(
                f"[green]✅ {result.message}[/green]",
                title="执行成功",
                border_style="green"
            ))
            
            # 显示AI分析（如果有）
            if result.ai_analysis:
                self.console.print(Panel(
                    result.ai_analysis,
                    title="🧠 AI分析",
                    border_style="blue",
                    padding=(1, 2)
                ))
            
            # 显示执行的动作
            if result.actions_executed:
                self._show_action_results(result.actions_executed)
        else:
            self.session_stats["failed_commands"] += 1
            self.console.print(Panel(
                f"[red]❌ {result.message}[/red]",
                title="执行失败",
                border_style="red"
            ))
    
    def _show_action_results(self, actions):
        """显示动作执行结果"""
        if not actions:
            return
        
        table = Table(title="执行的动作", show_header=True, header_style="bold magenta")
        table.add_column("序号", width=6)
        table.add_column("状态", width=8)
        table.add_column("描述")
        
        for i, action_result in enumerate(actions, 1):
            status_icon = "✅" if action_result.success else "❌"
            status_color = "green" if action_result.success else "red"
            
            table.add_row(
                str(i),
                f"[{status_color}]{status_icon}[/{status_color}]",
                action_result.message
            )
        
        self.console.print(table)
    
    def _show_help(self):
        """显示帮助信息"""
        help_text = """
[bold]基本指令:[/bold]
• 点击按钮名称               - 点击指定按钮
• 输入'文本'                - 输入文本
• 向下滚动                   - 滚动页面
• 截图                       - 截取屏幕
• 等待3秒                   - 等待指定时间

[bold]系统命令:[/bold]
• help                     - 显示此帮助
• status                   - 显示详细系统状态
• history                  - 显示命令历史
• stats                    - 显示会话统计
• clear                    - 清屏
• screenshot [path]        - 截图并保存
• config                   - 配置管理
• quit/exit                - 退出程序

[bold]示例指令:[/bold]
• 点击登录按钮
• 输入'用户名'
• 向下滚动3次
• 点击坐标(100, 200)
• 查找'确定'按钮
        """
        
        self.console.print(Panel(
            help_text,
            title="帮助信息",
            border_style="yellow",
            padding=(1, 2)
        ))
    
    def _show_detailed_status(self):
        """显示详细系统状态"""
        from .status_display import StatusDisplay
        status_display = StatusDisplay(self.console)
        status_display.show_system_status(self.processor.get_system_status())
    
    def _show_history(self):
        """显示命令历史"""
        if not self.history:
            self.console.print("[yellow]暂无命令历史[/yellow]")
            return
        
        table = Table(title="命令历史", show_header=True, header_style="bold cyan")
        table.add_column("序号", width=6)
        table.add_column("命令")
        
        for i, cmd in enumerate(self.history[-10:], 1):  # 只显示最近10条
            table.add_row(str(i), cmd)
        
        self.console.print(table)
    
    def _show_session_stats(self):
        """显示会话统计"""
        stats = self.session_stats
        success_rate = (stats["successful_commands"] / stats["commands_executed"] * 100) if stats["commands_executed"] > 0 else 0
        
        stats_table = Table(title="会话统计", show_header=False, box=None)
        stats_table.add_column("项目", style="bold")
        stats_table.add_column("数值")
        
        stats_table.add_row("总命令数", str(stats["commands_executed"]))
        stats_table.add_row("成功命令", f"[green]{stats['successful_commands']}[/green]")
        stats_table.add_row("失败命令", f"[red]{stats['failed_commands']}[/red]")
        stats_table.add_row("成功率", f"{success_rate:.1f}%")
        
        self.console.print(Panel(
            stats_table,
            border_style="cyan",
            padding=(1, 2)
        ))
    
    async def _handle_screenshot_command(self, command: str):
        """处理截图命令"""
        parts = command.split()
        save_path = parts[1] if len(parts) > 1 else None
        
        try:
            screenshot = self.processor.screen_capture.capture_full_screen()
            
            if save_path:
                screenshot.save(save_path)
                self.console.print(f"[green]截图已保存到: {save_path}[/green]")
            else:
                import tempfile
                import os
                temp_path = os.path.join(tempfile.gettempdir(), f"screenshot_{len(self._screenshots)}.png")
                screenshot.save(temp_path)
                self.console.print(f"[green]截图已保存到: {temp_path}[/green]")
            
            self._screenshots.append(screenshot)
            
            # 询问是否进行OCR
            if Confirm.ask("进行OCR文字识别?"):
                with self.console.status("正在进行OCR识别..."):
                    ocr_result = self.processor.ocr_engine.extract_text_smart(screenshot)
                
                if ocr_result.text.strip():
                    self.console.print(Panel(
                        ocr_result.text,
                        title=f"OCR识别结果 (置信度: {ocr_result.confidence:.1f}%)",
                        border_style="green"
                    ))
                else:
                    self.console.print("[yellow]未识别到文本内容[/yellow]")
        
        except Exception as e:
            self.console.print(f"[red]截图失败: {e}[/red]")
    
    def _handle_config_command(self, command: str):
        """处理配置命令"""
        # 显示当前LLM配置
        llm_status = self.processor.llm_manager.get_all_status()
        
        table = Table(title="LLM配置", show_header=True, header_style="bold green")
        table.add_column("提供商", width=12)
        table.add_column("状态", width=10)
        table.add_column("模型")
        table.add_column("详情")
        
        for name, info in llm_status.items():
            if isinstance(info, dict):
                status = "✅ 可用" if info.get("available", False) else "❌ 不可用"
                model = info.get("model", "未知")
                details = f"API密钥: {'✅' if info.get('has_api_key', False) else '❌'}"
                
                table.add_row(name, status, model, details)
        
        self.console.print(table)
        
        # 提供切换选项
        available_providers = [name for name, info in llm_status.items() 
                             if isinstance(info, dict) and info.get("available", False)]
        
        if len(available_providers) > 1:
            choice = questionary.select(
                "选择默认LLM提供商:",
                choices=available_providers,
                default=self.processor.llm_manager.default_provider
            ).ask()
            
            if choice and choice != self.processor.llm_manager.default_provider:
                self.processor.llm_manager.set_default_provider(choice)
                self.console.print(f"[green]默认LLM提供商已切换为: {choice}[/green]")
    
    def _progress_callback(self, message: str):
        """进度回调"""
        # 由于rich的限制，这里暂时不实现实时进度更新
        pass
    
    def _screenshot_callback(self, screenshot: Image.Image):
        """截图回调"""
        self._screenshots.append(screenshot)
    
    def _show_goodbye(self):
        """显示退出信息"""
        self.console.print(Panel(
            "[bold blue]感谢使用屏幕AI助手![/bold blue]\n\n"
            f"本次会话统计:\n"
            f"• 执行命令: {self.session_stats['commands_executed']}\n"
            f"• 成功: {self.session_stats['successful_commands']}\n"
            f"• 失败: {self.session_stats['failed_commands']}\n"
            f"• 截图: {len(self._screenshots)}",
            title="再见",
            border_style="blue",
            padding=(1, 2)
        ))
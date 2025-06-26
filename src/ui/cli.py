import asyncio
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path

from ..config import ConfigManager
from ..executor import InstructionProcessor
from .interactive import InteractiveUI
from .status_display import StatusDisplay

console = Console()
app = typer.Typer(help="屏幕AI助手 - 通过AI理解屏幕内容并执行指令")

def create_app():
    """创建CLI应用"""
    return app

@app.command()
def run(
    instruction: Optional[str] = typer.Argument(None, help="要执行的指令"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件路径"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="启动交互模式"),
    ai_analysis: bool = typer.Option(True, "--ai", help="使用AI分析"),
    no_screenshot: bool = typer.Option(False, "--no-screenshot", help="不截图"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="指定LLM提供商"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出"),
):
    """运行屏幕AI助手"""
    
    try:
        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        
        # 如果指定了提供商，更新配置
        if provider:
            config.llm.default_provider = provider
        
        # 初始化处理器
        processor = InstructionProcessor(config.model_dump())
        
        # 检查系统状态
        if verbose:
            status_display = StatusDisplay(console)
            status_display.show_system_status(processor.get_system_status())
        
        if interactive or not instruction:
            # 启动交互模式
            ui = InteractiveUI(processor, console)
            asyncio.run(ui.start())
        else:
            # 执行单个指令
            asyncio.run(_execute_single_instruction(
                processor, instruction, ai_analysis, not no_screenshot, verbose
            ))
            
    except KeyboardInterrupt:
        console.print("\n[yellow]用户中断操作[/yellow]")
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())

async def _execute_single_instruction(
    processor: InstructionProcessor,
    instruction: str,
    use_ai: bool,
    take_screenshot: bool,
    verbose: bool
):
    """执行单个指令"""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("处理指令中...", total=None)
        
        def update_progress(message: str):
            progress.update(task, description=message)
        
        processor.set_progress_callback(update_progress)
        
        result = await processor.process_instruction(
            instruction, use_ai, take_screenshot
        )
        
        progress.stop()
    
    # 显示结果
    if result.success:
        console.print(Panel(
            f"[green]✅ {result.message}[/green]",
            title="执行成功",
            border_style="green"
        ))
        
        if verbose and result.ai_analysis:
            console.print(Panel(
                result.ai_analysis,
                title="AI分析",
                border_style="blue"
            ))
        
        if verbose and result.actions_executed:
            console.print("\n[bold]执行的动作:[/bold]")
            for i, action_result in enumerate(result.actions_executed, 1):
                status = "✅" if action_result.success else "❌"
                console.print(f"{i}. {status} {action_result.message}")
    else:
        console.print(Panel(
            f"[red]❌ {result.message}[/red]",
            title="执行失败",
            border_style="red"
        ))

@app.command()
def status(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件路径"),
):
    """显示系统状态"""
    
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        processor = InstructionProcessor(config.model_dump())
        
        status_display = StatusDisplay(console)
        status_display.show_system_status(processor.get_system_status())
        
    except Exception as e:
        console.print(f"[red]获取状态失败: {e}[/red]")

@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="显示当前配置"),
    edit: bool = typer.Option(False, "--edit", help="编辑配置文件"),
    reset: bool = typer.Option(False, "--reset", help="重置为默认配置"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件路径"),
):
    """配置管理"""
    
    try:
        config_manager = ConfigManager(config_path)
        
        if reset:
            from ..config.config_manager import Config
            config_manager._config = Config()
            config_manager.save_config()
            console.print("[green]配置已重置为默认值[/green]")
            return
        
        if show:
            config = config_manager.load_config()
            console.print(Panel(
                config.model_dump_json(indent=2),
                title="当前配置",
                border_style="blue"
            ))
            return
        
        if edit:
            import subprocess
            config_path = config_manager.config_path
            if not config_path.exists():
                config_manager.load_config()  # 创建默认配置
            
            try:
                subprocess.run(["open", "-t", str(config_path)])
                console.print(f"[green]已在默认编辑器中打开配置文件: {config_path}[/green]")
            except Exception:
                console.print(f"[yellow]请手动编辑配置文件: {config_path}[/yellow]")
            return
        
        # 默认显示配置帮助
        console.print("[bold]配置管理选项:[/bold]")
        console.print("--show    显示当前配置")
        console.print("--edit    编辑配置文件")
        console.print("--reset   重置为默认配置")
        
    except Exception as e:
        console.print(f"[red]配置操作失败: {e}[/red]")

@app.command()
def screenshot(
    save_path: Optional[str] = typer.Option(None, "--save", "-s", help="保存路径"),
    show_ocr: bool = typer.Option(False, "--ocr", help="显示OCR识别结果"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件路径"),
):
    """截图并可选显示OCR结果"""
    
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        processor = InstructionProcessor(config.model_dump())
        
        # 截图
        screenshot = processor.screen_capture.capture_full_screen()
        
        # 保存截图
        if save_path:
            screenshot.save(save_path)
            console.print(f"[green]截图已保存到: {save_path}[/green]")
        else:
            import tempfile
            import os
            temp_path = os.path.join(tempfile.gettempdir(), "screen_ai_screenshot.png")
            screenshot.save(temp_path)
            console.print(f"[green]截图已保存到: {temp_path}[/green]")
        
        # OCR识别
        if show_ocr:
            with Progress(
                SpinnerColumn(),
                TextColumn("正在进行OCR识别..."),
                console=console,
            ) as progress:
                progress.add_task("OCR", total=None)
                ocr_result = processor.ocr_engine.extract_text_smart(screenshot)
            
            if ocr_result.text.strip():
                console.print(Panel(
                    ocr_result.text,
                    title=f"OCR识别结果 (置信度: {ocr_result.confidence:.1f}%)",
                    border_style="green"
                ))
            else:
                console.print("[yellow]未识别到文本内容[/yellow]")
        
    except Exception as e:
        console.print(f"[red]截图操作失败: {e}[/red]")

@app.command()
def test(
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件路径"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="测试指定提供商"),
):
    """测试系统功能"""
    
    try:
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()
        processor = InstructionProcessor(config.model_dump())
        
        console.print("[bold]正在进行系统测试...[/bold]\n")
        
        # 测试屏幕截图
        console.print("📸 测试屏幕截图...")
        try:
            screenshot = processor.screen_capture.capture_full_screen()
            console.print(f"[green]✅ 屏幕截图成功 ({screenshot.size[0]}x{screenshot.size[1]})[/green]")
        except Exception as e:
            console.print(f"[red]❌ 屏幕截图失败: {e}[/red]")
        
        # 测试OCR
        console.print("🔍 测试OCR识别...")
        try:
            ocr_result = processor.ocr_engine.extract_text_fast(screenshot)
            if ocr_result.text.strip():
                console.print(f"[green]✅ OCR识别成功 (置信度: {ocr_result.confidence:.1f}%)[/green]")
            else:
                console.print("[yellow]⚠️ OCR未识别到文本[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ OCR识别失败: {e}[/red]")
        
        # 测试LLM
        console.print("🤖 测试LLM连接...")
        if provider:
            providers_to_test = [provider]
        else:
            providers_to_test = processor.llm_manager.get_available_providers()
        
        for provider_name in providers_to_test:
            try:
                response = processor.llm_manager.generate_sync("Hello", provider_name=provider_name)
                if response.content and "error" not in response.usage:
                    console.print(f"[green]✅ {provider_name} 连接成功[/green]")
                else:
                    console.print(f"[red]❌ {provider_name} 连接失败[/red]")
            except Exception as e:
                console.print(f"[red]❌ {provider_name} 测试失败: {e}[/red]")
        
        console.print("\n[bold]测试完成![/bold]")
        
    except Exception as e:
        console.print(f"[red]测试过程中发生错误: {e}[/red]")

if __name__ == "__main__":
    app()
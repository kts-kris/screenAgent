import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from PIL import Image

from ..capture import ScreenCapture
from ..vision import OCREngine, ImageProcessor
from ..ai import LLMManager
from .command_parser import CommandParser, ParsedAction
from .action_executor import ActionExecutor, ExecutionResult

@dataclass
class ProcessingResult:
    success: bool
    message: str
    actions_executed: List[ExecutionResult]
    screenshots: List[Image.Image]
    ai_analysis: Optional[str] = None
    confidence: float = 0.0

class InstructionProcessor:
    """指令处理器 - 整合所有功能的核心类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 初始化各个组件
        self.screen_capture = ScreenCapture(
            screenshot_format=config.get("capture", {}).get("screenshot_format", "PNG"),
            quality=config.get("capture", {}).get("quality", 95)
        )
        
        self.ocr_engine = OCREngine(
            languages=config.get("ocr", {}).get("language", "eng+chi_sim")
        )
        
        self.image_processor = ImageProcessor()
        
        self.llm_manager = LLMManager(config.get("llm", {}))
        
        self.command_parser = CommandParser()
        
        self.action_executor = ActionExecutor(
            safety_mode=config.get("security", {}).get("safety_mode", True)
        )
        
        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.screenshot_callback: Optional[Callable] = None
        
        # 系统提示词
        self.system_prompt = """你是一个智能屏幕操作助手。用户会给你屏幕截图和OCR识别的文本内容，以及要执行的指令。

你的任务是：
1. 理解当前屏幕内容
2. 分析用户指令的意图
3. 提供具体的操作步骤

请按照以下JSON格式回复：
{
    "analysis": "对当前屏幕内容的分析",
    "intent": "用户指令的意图",
    "actions": [
        {
            "action": "click|type|scroll|press_key|drag|screenshot|wait|find_text",
            "parameters": {具体参数},
            "description": "动作描述",
            "confidence": 0.9
        }
    ],
    "explanation": "操作步骤的解释"
}

支持的动作类型：
- click: 点击，参数包括target(目标文本)或x,y(坐标)
- type: 输入文本，参数包括text
- scroll: 滚动，参数包括direction(up/down/left/right)和amount
- press_key: 按键，参数包括key
- drag: 拖拽，参数包括source和target或坐标
- screenshot: 截图
- wait: 等待，参数包括duration(秒)
- find_text: 查找文本，参数包括text

注意安全性，避免执行可能有害的操作。"""
    
    async def process_instruction(self, 
                                user_instruction: str,
                                use_ai_analysis: bool = True,
                                take_screenshot: bool = True) -> ProcessingResult:
        """处理用户指令的主要方法"""
        
        try:
            screenshots = []
            actions_executed = []
            ai_analysis = None
            
            if self.progress_callback:
                self.progress_callback("开始处理指令...")
            
            # 1. 截取屏幕
            if take_screenshot:
                if self.progress_callback:
                    self.progress_callback("正在截取屏幕...")
                
                screenshot = self.screen_capture.capture_full_screen()
                screenshots.append(screenshot)
                
                if self.screenshot_callback:
                    self.screenshot_callback(screenshot)
            
            # 2. 如果启用AI分析
            if use_ai_analysis and screenshots:
                if self.progress_callback:
                    self.progress_callback("正在进行AI分析...")
                
                ai_result = await self._ai_analyze_and_plan(user_instruction, screenshots[0])
                if ai_result:
                    ai_analysis = ai_result.get("explanation", "")
                    actions = ai_result.get("actions", [])
                    
                    # 将AI建议的动作转换为ParsedAction
                    parsed_actions = []
                    for action_data in actions:
                        parsed_action = self.command_parser._parse_json_action(action_data)
                        if parsed_action:
                            parsed_actions.append(parsed_action)
                else:
                    # AI分析失败，回退到传统解析
                    parsed_actions = self.command_parser.parse_instruction(user_instruction)
            else:
                # 直接使用命令解析器
                parsed_actions = self.command_parser.parse_instruction(user_instruction)
            
            # 3. 执行动作
            if parsed_actions:
                if self.progress_callback:
                    self.progress_callback(f"开始执行 {len(parsed_actions)} 个动作...")
                
                for i, action in enumerate(parsed_actions):
                    if self.progress_callback:
                        self.progress_callback(f"执行动作 {i+1}/{len(parsed_actions)}: {action.action_type.value}")
                    
                    # 在每个动作前可以选择性截图
                    if action.action_type.value != "screenshot" and i > 0:
                        current_screenshot = self.screen_capture.capture_full_screen()
                        screenshots.append(current_screenshot)
                    
                    # 执行动作
                    result = self.action_executor.execute_action(action)
                    actions_executed.append(result)
                    
                    if not result.success:
                        return ProcessingResult(
                            success=False,
                            message=f"动作执行失败: {result.message}",
                            actions_executed=actions_executed,
                            screenshots=screenshots,
                            ai_analysis=ai_analysis
                        )
                    
                    # 如果是截图动作，添加到截图列表
                    if result.screenshot:
                        screenshots.append(result.screenshot)
            
            # 4. 处理完成
            success_count = sum(1 for result in actions_executed if result.success)
            
            return ProcessingResult(
                success=True,
                message=f"成功执行了 {success_count} 个动作",
                actions_executed=actions_executed,
                screenshots=screenshots,
                ai_analysis=ai_analysis,
                confidence=0.9 if use_ai_analysis else 0.7
            )
        
        except Exception as e:
            return ProcessingResult(
                success=False,
                message=f"处理指令时发生错误: {str(e)}",
                actions_executed=actions_executed if 'actions_executed' in locals() else [],
                screenshots=screenshots if 'screenshots' in locals() else []
            )
    
    async def _ai_analyze_and_plan(self, 
                                 user_instruction: str, 
                                 screenshot: Image.Image) -> Optional[Dict[str, Any]]:
        """使用AI分析屏幕内容并规划操作"""
        
        try:
            # 1. OCR识别屏幕文本
            ocr_result = self.ocr_engine.extract_text_smart(screenshot)
            screen_text = ocr_result.text
            
            # 2. 构建AI提示
            prompt = f"""当前屏幕内容（OCR识别）：
{screen_text}

用户指令：
{user_instruction}

请分析当前屏幕内容，理解用户指令的意图，并提供具体的操作步骤。"""
            
            # 3. 调用LLM
            response = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt=self.system_prompt
            )
            
            if response.content:
                # 尝试解析JSON响应
                import json
                try:
                    ai_result = json.loads(response.content)
                    return ai_result
                except json.JSONDecodeError:
                    # 如果不是JSON格式，尝试从文本中提取操作
                    return self._extract_actions_from_text(response.content)
            
            return None
        
        except Exception as e:
            print(f"AI分析失败: {e}")
            return None
    
    def _extract_actions_from_text(self, ai_response: str) -> Dict[str, Any]:
        """从AI的文本响应中提取操作"""
        # 简单的文本解析，实际使用中可能需要更复杂的NLP处理
        actions = []
        
        # 查找动作关键词
        lines = ai_response.split('\n')
        for line in lines:
            line = line.strip()
            if '点击' in line or 'click' in line.lower():
                actions.append({
                    "action": "click",
                    "parameters": {"target": line, "use_coordinates": False},
                    "description": line,
                    "confidence": 0.7
                })
            elif '输入' in line or 'type' in line.lower():
                actions.append({
                    "action": "type",
                    "parameters": {"text": line},
                    "description": line,
                    "confidence": 0.7
                })
        
        return {
            "analysis": "从AI响应中提取的分析",
            "intent": "用户意图",
            "actions": actions,
            "explanation": ai_response
        }
    
    def process_instruction_sync(self, 
                               user_instruction: str,
                               use_ai_analysis: bool = True,
                               take_screenshot: bool = True) -> ProcessingResult:
        """同步版本的指令处理"""
        return asyncio.run(self.process_instruction(
            user_instruction, use_ai_analysis, take_screenshot
        ))
    
    def set_progress_callback(self, callback: Callable[[str], None]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def set_screenshot_callback(self, callback: Callable[[Image.Image], None]):
        """设置截图回调函数"""
        self.screenshot_callback = callback
    
    def get_screen_analysis(self) -> Dict[str, Any]:
        """获取当前屏幕分析"""
        try:
            screenshot = self.screen_capture.capture_full_screen()
            ocr_result = self.ocr_engine.extract_text_smart(screenshot)
            
            return {
                "screenshot_size": screenshot.size,
                "text_content": ocr_result.text,
                "text_confidence": ocr_result.confidence,
                "text_language": ocr_result.language
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    async def interactive_mode(self):
        """交互模式 - 持续监听用户指令"""
        print("进入交互模式。输入 'quit' 或 'exit' 退出。")
        
        while True:
            try:
                user_input = input("\n请输入指令: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("退出交互模式")
                    break
                
                if not user_input:
                    continue
                
                print("处理中...")
                result = await self.process_instruction(user_input)
                
                if result.success:
                    print(f"✅ {result.message}")
                    if result.ai_analysis:
                        print(f"AI分析: {result.ai_analysis}")
                else:
                    print(f"❌ {result.message}")
            
            except KeyboardInterrupt:
                print("\n用户中断，退出交互模式")
                break
            except Exception as e:
                print(f"发生错误: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "screen_capture": {
                "available": True,
                "screen_size": self.screen_capture.get_screen_size()
            },
            "ocr_engine": {
                "available": self.ocr_engine.check_tesseract_installation(),
                "languages": self.ocr_engine.get_available_languages()
            },
            "llm_manager": self.llm_manager.get_all_status(),
            "action_executor": self.action_executor.get_execution_stats()
        }
    
    def cleanup(self):
        """清理资源"""
        self.ocr_engine.cleanup()
        self.image_processor.clear_cache()
        self.action_executor.reset_stats()
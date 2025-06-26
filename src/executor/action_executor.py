import time
import pyautogui
import subprocess
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image
from dataclasses import dataclass
from .command_parser import ParsedAction, ActionType

@dataclass
class ExecutionResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    screenshot: Optional[Image.Image] = None

class ActionExecutor:
    """动作执行器"""
    
    def __init__(self, safety_mode: bool = True):
        self.safety_mode = safety_mode
        self.screen_size = pyautogui.size()
        
        # 设置pyautogui安全参数
        pyautogui.PAUSE = 0.1
        pyautogui.FAILSAFE = True
        
        # 执行统计
        self.execution_stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "action_times": []
        }
    
    def execute_action(self, action: ParsedAction) -> ExecutionResult:
        """执行单个动作"""
        start_time = time.time()
        
        try:
            self.execution_stats["total_actions"] += 1
            
            # 安全检查
            if not self._safety_check(action):
                return ExecutionResult(
                    success=False,
                    message=f"安全检查失败: {action.action_type.value}"
                )
            
            # 根据动作类型执行相应操作
            if action.action_type == ActionType.CLICK:
                result = self._execute_click(action)
            elif action.action_type == ActionType.TYPE:
                result = self._execute_type(action)
            elif action.action_type == ActionType.SCROLL:
                result = self._execute_scroll(action)
            elif action.action_type == ActionType.PRESS_KEY:
                result = self._execute_press_key(action)
            elif action.action_type == ActionType.DRAG:
                result = self._execute_drag(action)
            elif action.action_type == ActionType.SCREENSHOT:
                result = self._execute_screenshot(action)
            elif action.action_type == ActionType.WAIT:
                result = self._execute_wait(action)
            elif action.action_type == ActionType.FIND_TEXT:
                result = self._execute_find_text(action)
            else:
                result = ExecutionResult(
                    success=False,
                    message=f"不支持的动作类型: {action.action_type.value}"
                )
            
            # 更新统计信息
            execution_time = time.time() - start_time
            self.execution_stats["action_times"].append(execution_time)
            
            if result.success:
                self.execution_stats["successful_actions"] += 1
            else:
                self.execution_stats["failed_actions"] += 1
            
            return result
        
        except Exception as e:
            self.execution_stats["failed_actions"] += 1
            return ExecutionResult(
                success=False,
                message=f"执行动作时发生错误: {str(e)}"
            )
    
    def _safety_check(self, action: ParsedAction) -> bool:
        """安全检查"""
        if not self.safety_mode:
            return True
        
        # 检查坐标是否在屏幕范围内
        if action.action_type in [ActionType.CLICK, ActionType.DRAG]:
            if "x" in action.parameters and "y" in action.parameters:
                x, y = action.parameters["x"], action.parameters["y"]
                if not (0 <= x <= self.screen_size.width and 0 <= y <= self.screen_size.height):
                    return False
        
        # 检查等待时间是否合理
        if action.action_type == ActionType.WAIT:
            duration = action.parameters.get("duration", 0)
            if duration > 60:  # 最大等待60秒
                return False
        
        # 检查输入文本是否安全
        if action.action_type == ActionType.TYPE:
            text = action.parameters.get("text", "")
            if len(text) > 1000:  # 限制输入文本长度
                return False
        
        return True
    
    def _execute_click(self, action: ParsedAction) -> ExecutionResult:
        """执行点击动作"""
        try:
            if action.parameters.get("use_coordinates", False):
                x = action.parameters.get("x")
                y = action.parameters.get("y")
                if x is not None and y is not None:
                    pyautogui.click(x, y)
                    return ExecutionResult(
                        success=True,
                        message=f"在坐标 ({x}, {y}) 处点击成功"
                    )
            else:
                target = action.parameters.get("target", "")
                if target:
                    # 尝试通过OCR查找目标文本
                    position = self._find_text_on_screen(target)
                    if position:
                        pyautogui.click(position[0], position[1])
                        return ExecutionResult(
                            success=True,
                            message=f"找到并点击了 '{target}'"
                        )
                    else:
                        return ExecutionResult(
                            success=False,
                            message=f"未找到目标 '{target}'"
                        )
                else:
                    # 默认点击屏幕中心
                    center_x = self.screen_size.width // 2
                    center_y = self.screen_size.height // 2
                    pyautogui.click(center_x, center_y)
                    return ExecutionResult(
                        success=True,
                        message="在屏幕中心点击"
                    )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"点击操作失败: {str(e)}"
            )
    
    def _execute_type(self, action: ParsedAction) -> ExecutionResult:
        """执行输入动作"""
        try:
            text = action.parameters.get("text", "")
            if text:
                pyautogui.typewrite(text, interval=0.05)
                return ExecutionResult(
                    success=True,
                    message=f"输入文本: '{text}'"
                )
            else:
                return ExecutionResult(
                    success=False,
                    message="没有指定要输入的文本"
                )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"输入操作失败: {str(e)}"
            )
    
    def _execute_scroll(self, action: ParsedAction) -> ExecutionResult:
        """执行滚动动作"""
        try:
            direction = action.parameters.get("direction", "down")
            amount = action.parameters.get("amount", 3)
            
            if direction in ["up", "down"]:
                scroll_amount = amount if direction == "down" else -amount
                pyautogui.scroll(scroll_amount)
            elif direction in ["left", "right"]:
                # 水平滚动（某些应用支持）
                pyautogui.hscroll(amount if direction == "right" else -amount)
            
            return ExecutionResult(
                success=True,
                message=f"向{direction}滚动 {amount} 次"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"滚动操作失败: {str(e)}"
            )
    
    def _execute_press_key(self, action: ParsedAction) -> ExecutionResult:
        """执行按键动作"""
        try:
            key = action.parameters.get("key", "")
            if key:
                pyautogui.press(key)
                return ExecutionResult(
                    success=True,
                    message=f"按下了 {key} 键"
                )
            else:
                return ExecutionResult(
                    success=False,
                    message="没有指定要按下的键"
                )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"按键操作失败: {str(e)}"
            )
    
    def _execute_drag(self, action: ParsedAction) -> ExecutionResult:
        """执行拖拽动作"""
        try:
            if action.parameters.get("use_coordinates", False):
                source_x = action.parameters.get("source_x")
                source_y = action.parameters.get("source_y")
                target_x = action.parameters.get("target_x")
                target_y = action.parameters.get("target_y")
                
                if all(coord is not None for coord in [source_x, source_y, target_x, target_y]):
                    pyautogui.drag(source_x, source_y, target_x, target_y, duration=1.0)
                    return ExecutionResult(
                        success=True,
                        message=f"从 ({source_x}, {source_y}) 拖拽到 ({target_x}, {target_y})"
                    )
            else:
                source = action.parameters.get("source", "")
                target = action.parameters.get("target", "")
                
                if source and target:
                    source_pos = self._find_text_on_screen(source)
                    target_pos = self._find_text_on_screen(target)
                    
                    if source_pos and target_pos:
                        pyautogui.drag(source_pos[0], source_pos[1], 
                                     target_pos[0], target_pos[1], duration=1.0)
                        return ExecutionResult(
                            success=True,
                            message=f"从 '{source}' 拖拽到 '{target}'"
                        )
                    else:
                        return ExecutionResult(
                            success=False,
                            message=f"未找到拖拽的源或目标位置"
                        )
            
            return ExecutionResult(
                success=False,
                message="拖拽参数不完整"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"拖拽操作失败: {str(e)}"
            )
    
    def _execute_screenshot(self, action: ParsedAction) -> ExecutionResult:
        """执行截图动作"""
        try:
            screenshot = pyautogui.screenshot()
            save_path = action.parameters.get("save_path")
            
            if save_path:
                screenshot.save(save_path)
                message = f"截图已保存到: {save_path}"
            else:
                message = "截图已获取"
            
            return ExecutionResult(
                success=True,
                message=message,
                screenshot=screenshot
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"截图操作失败: {str(e)}"
            )
    
    def _execute_wait(self, action: ParsedAction) -> ExecutionResult:
        """执行等待动作"""
        try:
            duration = action.parameters.get("duration", 1)
            time.sleep(duration)
            return ExecutionResult(
                success=True,
                message=f"等待了 {duration} 秒"
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"等待操作失败: {str(e)}"
            )
    
    def _execute_find_text(self, action: ParsedAction) -> ExecutionResult:
        """执行查找文本动作"""
        try:
            text = action.parameters.get("text", "")
            if text:
                position = self._find_text_on_screen(text)
                if position:
                    return ExecutionResult(
                        success=True,
                        message=f"找到文本 '{text}' 在位置 ({position[0]}, {position[1]})",
                        data={"position": position}
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        message=f"未找到文本 '{text}'"
                    )
            else:
                return ExecutionResult(
                    success=False,
                    message="没有指定要查找的文本"
                )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"查找文本操作失败: {str(e)}"
            )
    
    def _find_text_on_screen(self, text: str) -> Optional[Tuple[int, int]]:
        """在屏幕上查找文本位置"""
        try:
            # 这里需要集成OCR功能来查找文本
            # 为了演示，我们使用pyautogui的图像识别功能
            # 实际使用时应该集成OCR引擎
            
            # 临时实现：返回None表示未找到
            # 在实际实现中，这里应该：
            # 1. 截取当前屏幕
            # 2. 使用OCR识别文本
            # 3. 返回文本的中心位置
            
            return None
        
        except Exception:
            return None
    
    def execute_batch_actions(self, actions: List[ParsedAction]) -> List[ExecutionResult]:
        """批量执行动作"""
        results = []
        
        for i, action in enumerate(actions):
            print(f"执行动作 {i+1}/{len(actions)}: {action.action_type.value}")
            
            result = self.execute_action(action)
            results.append(result)
            
            if not result.success:
                print(f"动作执行失败: {result.message}")
                # 可选择是否继续执行后续动作
                break
            else:
                print(f"动作执行成功: {result.message}")
        
        return results
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        stats = self.execution_stats.copy()
        
        if stats["action_times"]:
            stats["average_time"] = sum(stats["action_times"]) / len(stats["action_times"])
            stats["total_time"] = sum(stats["action_times"])
        else:
            stats["average_time"] = 0
            stats["total_time"] = 0
        
        if stats["total_actions"] > 0:
            stats["success_rate"] = stats["successful_actions"] / stats["total_actions"]
        else:
            stats["success_rate"] = 0
        
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.execution_stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "action_times": []
        }
    
    def set_safety_mode(self, enabled: bool):
        """设置安全模式"""
        self.safety_mode = enabled
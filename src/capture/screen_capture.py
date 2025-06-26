import io
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Union
import pyautogui
from PIL import Image, ImageGrab
import cv2
import numpy as np

class ScreenCapture:
    """屏幕截图类"""
    
    def __init__(self, screenshot_format: str = "PNG", quality: int = 95):
        self.format = screenshot_format.upper()
        self.quality = quality
        
        # 设置pyautogui安全模式
        pyautogui.PAUSE = 0.1
        pyautogui.FAILSAFE = True
    
    def capture_full_screen(self) -> Image.Image:
        """捕获全屏截图"""
        try:
            # 使用PIL的ImageGrab，在macOS上效果更好
            screenshot = ImageGrab.grab()
            return screenshot
        except Exception as e:
            # 备用方案：使用pyautogui
            print(f"ImageGrab失败，使用pyautogui备用方案: {e}")
            screenshot = pyautogui.screenshot()
            return screenshot
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """捕获指定区域截图"""
        try:
            bbox = (x, y, x + width, y + height)
            screenshot = ImageGrab.grab(bbox=bbox)
            return screenshot
        except Exception as e:
            print(f"区域截图失败，使用pyautogui备用方案: {e}")
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            return screenshot
    
    def capture_window(self, window_title: Optional[str] = None) -> Optional[Image.Image]:
        """捕获指定窗口截图（macOS需要额外权限）"""
        try:
            if window_title:
                # 在macOS上，需要使用Accessibility API
                # 这里提供基础实现，实际使用可能需要额外的权限配置
                windows = pyautogui.getWindowsWithTitle(window_title)
                if windows:
                    window = windows[0]
                    return self.capture_region(
                        window.left, window.top, 
                        window.width, window.height
                    )
            return None
        except Exception as e:
            print(f"窗口截图失败: {e}")
            return None
    
    def save_screenshot(self, image: Image.Image, filepath: Optional[str] = None) -> str:
        """保存截图到文件"""
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"screenshot_{timestamp}.{self.format.lower()}"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        save_kwargs = {}
        if self.format == "JPEG":
            save_kwargs["quality"] = self.quality
            save_kwargs["optimize"] = True
        elif self.format == "PNG":
            save_kwargs["optimize"] = True
        
        image.save(str(filepath), format=self.format, **save_kwargs)
        return str(filepath)
    
    def image_to_bytes(self, image: Image.Image) -> bytes:
        """将图像转换为字节"""
        img_buffer = io.BytesIO()
        save_kwargs = {}
        if self.format == "JPEG":
            save_kwargs["quality"] = self.quality
            save_kwargs["optimize"] = True
        elif self.format == "PNG":
            save_kwargs["optimize"] = True
        
        image.save(img_buffer, format=self.format, **save_kwargs)
        return img_buffer.getvalue()
    
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕尺寸"""
        try:
            return pyautogui.size()
        except Exception:
            # 备用方案
            screenshot = self.capture_full_screen()
            return screenshot.size
    
    def detect_screens(self) -> list:
        """检测所有显示器（macOS多显示器支持）"""
        try:
            # 在macOS上，可以通过截图不同区域来检测多显示器
            # 这是一个简化版本，实际实现可能需要使用CoreGraphics
            main_size = self.get_screen_size()
            return [{"id": 0, "size": main_size, "primary": True}]
        except Exception as e:
            print(f"检测显示器失败: {e}")
            return []
    
    def capture_with_cursor(self) -> Image.Image:
        """捕获包含鼠标指针的截图"""
        # PIL的ImageGrab在macOS上默认不包含鼠标指针
        # 如果需要包含指针，可能需要使用其他方法
        screenshot = self.capture_full_screen()
        
        try:
            # 获取鼠标位置
            cursor_pos = pyautogui.position()
            
            # 这里可以添加绘制鼠标指针的逻辑
            # 由于系统限制，这可能需要额外的实现
            
        except Exception as e:
            print(f"获取鼠标位置失败: {e}")
        
        return screenshot
    
    def compare_images(self, img1: Image.Image, img2: Image.Image) -> float:
        """比较两张图片的相似度"""
        try:
            # 转换为numpy数组
            arr1 = np.array(img1.convert('RGB'))
            arr2 = np.array(img2.convert('RGB'))
            
            # 调整尺寸使其一致
            if arr1.shape != arr2.shape:
                height, width = min(arr1.shape[0], arr2.shape[0]), min(arr1.shape[1], arr2.shape[1])
                arr1 = arr1[:height, :width]
                arr2 = arr2[:height, :width]
            
            # 计算结构相似性
            # 这里使用简单的像素差异，实际项目中可以使用更复杂的算法
            diff = np.abs(arr1.astype(float) - arr2.astype(float))
            similarity = 1.0 - (np.mean(diff) / 255.0)
            
            return similarity
        except Exception as e:
            print(f"图片比较失败: {e}")
            return 0.0
    
    def auto_capture_changes(self, interval: float = 1.0, threshold: float = 0.95) -> bool:
        """自动检测屏幕变化并截图"""
        try:
            previous_screenshot = self.capture_full_screen()
            time.sleep(interval)
            
            while True:
                current_screenshot = self.capture_full_screen()
                similarity = self.compare_images(previous_screenshot, current_screenshot)
                
                if similarity < threshold:
                    # 屏幕发生了显著变化
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = f"change_detected_{timestamp}.{self.format.lower()}"
                    self.save_screenshot(current_screenshot, filepath)
                    print(f"检测到屏幕变化，已保存截图: {filepath}")
                    return True
                
                previous_screenshot = current_screenshot
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("自动截图已停止")
            return False
        except Exception as e:
            print(f"自动截图失败: {e}")
            return False
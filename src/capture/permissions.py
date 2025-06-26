import subprocess
import sys
from typing import Optional

class PermissionManager:
    """macOS权限管理器"""
    
    @staticmethod
    def check_screen_recording_permission() -> bool:
        """检查是否有屏幕录制权限（macOS 10.15+需要）"""
        try:
            # 尝试截图来测试权限
            from PIL import ImageGrab
            test_screenshot = ImageGrab.grab(bbox=(0, 0, 1, 1))
            return test_screenshot is not None
        except Exception:
            return False
    
    @staticmethod
    def check_accessibility_permission() -> bool:
        """检查是否有辅助功能权限"""
        try:
            import pyautogui
            # 尝试获取鼠标位置来测试权限
            pyautogui.position()
            return True
        except Exception:
            return False
    
    @staticmethod
    def prompt_permissions():
        """提示用户授予必要权限"""
        print("🔐 权限检查...")
        
        if not PermissionManager.check_screen_recording_permission():
            print("❌ 缺少屏幕录制权限")
            print("请按以下步骤授予权限：")
            print("1. 打开 系统偏好设置 > 安全性与隐私 > 隐私")
            print("2. 选择 屏幕录制")
            print("3. 点击锁图标解锁，添加此应用程序")
            print("4. 重新启动应用程序")
            return False
        
        if not PermissionManager.check_accessibility_permission():
            print("❌ 缺少辅助功能权限")
            print("请按以下步骤授予权限：")
            print("1. 打开 系统偏好设置 > 安全性与隐私 > 隐私")
            print("2. 选择 辅助功能")
            print("3. 点击锁图标解锁，添加此应用程序")
            print("4. 重新启动应用程序")
            return False
        
        print("✅ 所有权限已授予")
        return True
    
    @staticmethod
    def open_privacy_settings():
        """打开macOS隐私设置"""
        try:
            subprocess.run([
                "open", 
                "x-apple.systempreferences:com.apple.preference.security?Privacy"
            ])
            print("已打开隐私设置，请手动配置权限后重新启动应用")
        except Exception as e:
            print(f"无法打开隐私设置: {e}")
    
    @staticmethod
    def get_permission_status() -> dict:
        """获取所有权限状态"""
        return {
            "screen_recording": PermissionManager.check_screen_recording_permission(),
            "accessibility": PermissionManager.check_accessibility_permission()
        }
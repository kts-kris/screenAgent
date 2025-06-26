import subprocess
import sys
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class PermissionType(Enum):
    SCREEN_RECORDING = "screen_recording"
    ACCESSIBILITY = "accessibility"
    CAMERA = "camera"
    MICROPHONE = "microphone"

@dataclass
class PermissionStatus:
    granted: bool
    required: bool
    description: str
    instructions: List[str]

class PermissionManager:
    """权限管理器 - 处理macOS系统权限"""
    
    def __init__(self):
        self.required_permissions = {
            PermissionType.SCREEN_RECORDING: PermissionStatus(
                granted=False,
                required=True,
                description="屏幕录制权限 - 用于截图和屏幕分析",
                instructions=[
                    "1. 打开 系统偏好设置 > 安全性与隐私 > 隐私",
                    "2. 选择 屏幕录制",
                    "3. 点击锁图标解锁设置",
                    "4. 勾选此应用程序或终端",
                    "5. 重新启动应用程序"
                ]
            ),
            PermissionType.ACCESSIBILITY: PermissionStatus(
                granted=False,
                required=True,
                description="辅助功能权限 - 用于控制鼠标和键盘",
                instructions=[
                    "1. 打开 系统偏好设置 > 安全性与隐私 > 隐私",
                    "2. 选择 辅助功能",
                    "3. 点击锁图标解锁设置",
                    "4. 勾选此应用程序或终端",
                    "5. 重新启动应用程序"
                ]
            )
        }
        
        self._check_all_permissions()
    
    def _check_all_permissions(self):
        """检查所有权限状态"""
        self.required_permissions[PermissionType.SCREEN_RECORDING].granted = self._check_screen_recording()
        self.required_permissions[PermissionType.ACCESSIBILITY].granted = self._check_accessibility()
    
    def _check_screen_recording(self) -> bool:
        """检查屏幕录制权限"""
        try:
            # 方法1: 尝试截图来测试权限
            from PIL import ImageGrab
            test_screenshot = ImageGrab.grab(bbox=(0, 0, 1, 1))
            return test_screenshot is not None and test_screenshot.size == (1, 1)
        except Exception:
            # 方法2: 使用系统命令检查
            try:
                result = subprocess.run([
                    "sqlite3", 
                    os.path.expanduser("~/Library/Application Support/com.apple.TCC/TCC.db"),
                    "SELECT allowed FROM access WHERE service='kTCCServiceScreenCapture';"
                ], capture_output=True, text=True, timeout=5)
                
                return "1" in result.stdout
            except Exception:
                return False
    
    def _check_accessibility(self) -> bool:
        """检查辅助功能权限"""
        try:
            # 尝试获取鼠标位置来测试权限
            import pyautogui
            pyautogui.position()
            return True
        except Exception:
            try:
                # 使用系统命令检查
                result = subprocess.run([
                    "sqlite3",
                    "/Library/Application Support/com.apple.TCC/TCC.db",
                    "SELECT allowed FROM access WHERE service='kTCCServiceAccessibility';"
                ], capture_output=True, text=True, timeout=5)
                
                return "1" in result.stdout
            except Exception:
                return False
    
    def check_permission(self, permission_type: PermissionType) -> bool:
        """检查特定权限"""
        if permission_type == PermissionType.SCREEN_RECORDING:
            granted = self._check_screen_recording()
        elif permission_type == PermissionType.ACCESSIBILITY:
            granted = self._check_accessibility()
        else:
            return False
        
        self.required_permissions[permission_type].granted = granted
        return granted
    
    def get_permission_status(self, permission_type: PermissionType) -> PermissionStatus:
        """获取权限状态"""
        return self.required_permissions.get(permission_type)
    
    def get_all_permissions_status(self) -> Dict[PermissionType, PermissionStatus]:
        """获取所有权限状态"""
        self._check_all_permissions()
        return self.required_permissions.copy()
    
    def has_required_permissions(self) -> bool:
        """检查是否拥有所有必需权限"""
        for permission_type, status in self.required_permissions.items():
            if status.required and not status.granted:
                return False
        return True
    
    def get_missing_permissions(self) -> List[PermissionType]:
        """获取缺失的权限列表"""
        missing = []
        for permission_type, status in self.required_permissions.items():
            if status.required and not status.granted:
                missing.append(permission_type)
        return missing
    
    def prompt_for_permissions(self, console=None) -> bool:
        """提示用户授予权限"""
        missing_permissions = self.get_missing_permissions()
        
        if not missing_permissions:
            if console:
                console.print("[green]✅ 所有必需权限已授予[/green]")
            else:
                print("✅ 所有必需权限已授予")
            return True
        
        if console:
            console.print("[bold red]🔐 需要系统权限[/bold red]\n")
        else:
            print("🔐 需要系统权限\n")
        
        for permission_type in missing_permissions:
            status = self.required_permissions[permission_type]
            
            if console:
                console.print(f"[bold]❌ {status.description}[/bold]")
                console.print("请按以下步骤授予权限:")
                for instruction in status.instructions:
                    console.print(f"   {instruction}")
                console.print()
            else:
                print(f"❌ {status.description}")
                print("请按以下步骤授予权限:")
                for instruction in status.instructions:
                    print(f"   {instruction}")
                print()
        
        return False
    
    def open_privacy_settings(self):
        """打开系统隐私设置"""
        try:
            # macOS Big Sur及以后版本
            subprocess.run([
                "open", 
                "x-apple.systempreferences:com.apple.preference.security?Privacy"
            ], check=False)
            return True
        except Exception:
            try:
                # 备用方法
                subprocess.run(["open", "/System/Library/PreferencePanes/Security.prefPane"], check=False)
                return True
            except Exception:
                return False
    
    def request_permission_interactive(self, permission_type: PermissionType) -> bool:
        """交互式权限请求"""
        status = self.required_permissions.get(permission_type)
        if not status:
            return False
        
        print(f"\n需要权限: {status.description}")
        print("请按以下步骤操作:")
        for instruction in status.instructions:
            print(f"  {instruction}")
        
        # 提供打开设置的选项
        try:
            response = input("\n是否打开系统设置? (y/n): ").lower().strip()
            if response in ['y', 'yes', '是']:
                self.open_privacy_settings()
                print("已打开系统设置，请手动配置权限后重新启动应用")
        except KeyboardInterrupt:
            print("\n操作被取消")
        
        return False
    
    def verify_permissions_after_grant(self) -> Tuple[bool, List[str]]:
        """验证权限授予后的状态"""
        messages = []
        self._check_all_permissions()
        
        for permission_type, status in self.required_permissions.items():
            if status.required:
                if status.granted:
                    messages.append(f"✅ {status.description} - 已授予")
                else:
                    messages.append(f"❌ {status.description} - 仍未授予")
        
        all_granted = self.has_required_permissions()
        return all_granted, messages
    
    def get_permission_instructions(self, permission_type: PermissionType) -> List[str]:
        """获取特定权限的授予说明"""
        status = self.required_permissions.get(permission_type)
        return status.instructions if status else []
    
    def create_permission_script(self, output_path: str = "grant_permissions.sh"):
        """创建权限授予脚本(仅用于提示，不能自动执行)"""
        script_content = """#!/bin/bash
# 屏幕AI助手权限授予脚本
# 注意: 此脚本仅用于提示，macOS权限必须手动授予

echo "🔐 屏幕AI助手权限配置指南"
echo "==============================="
echo ""
echo "此应用需要以下权限才能正常工作:"
echo ""
echo "1. 屏幕录制权限:"
echo "   - 打开 系统偏好设置 > 安全性与隐私 > 隐私"
echo "   - 选择 屏幕录制"
echo "   - 点击锁图标解锁"
echo "   - 勾选终端或Python"
echo ""
echo "2. 辅助功能权限:"
echo "   - 打开 系统偏好设置 > 安全性与隐私 > 隐私"
echo "   - 选择 辅助功能"
echo "   - 点击锁图标解锁"
echo "   - 勾选终端或Python"
echo ""
echo "配置完成后，请重新启动应用程序"
echo ""
echo "如需帮助，请参考应用文档或联系支持"
"""
        
        try:
            with open(output_path, 'w') as f:
                f.write(script_content)
            os.chmod(output_path, 0o755)
            return True
        except Exception:
            return False
    
    def get_system_info(self) -> Dict[str, str]:
        """获取系统信息"""
        try:
            # macOS版本
            result = subprocess.run(["sw_vers", "-productVersion"], 
                                  capture_output=True, text=True, timeout=5)
            macos_version = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # 安全策略状态
            result = subprocess.run(["csrutil", "status"], 
                                  capture_output=True, text=True, timeout=5)
            sip_status = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            return {
                "macos_version": macos_version,
                "sip_status": sip_status,
                "python_path": sys.executable,
                "working_directory": os.getcwd()
            }
        except Exception:
            return {
                "macos_version": "Unknown",
                "sip_status": "Unknown", 
                "python_path": sys.executable,
                "working_directory": os.getcwd()
            }
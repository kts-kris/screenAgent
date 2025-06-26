#!/usr/bin/env python3
"""
Screen AI Agent - 屏幕AI助手
通过图像识别技术读取屏幕内容，并使用大语言模型理解和执行用户指令
"""

import typer
from src.ui.cli import create_app

def main():
    """启动屏幕AI助手"""
    app = create_app()
    app()

if __name__ == "__main__":
    main()
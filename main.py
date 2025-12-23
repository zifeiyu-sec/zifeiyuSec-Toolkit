#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子非鱼工具箱 - 主入口
"""

import os
import sys
import signal
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QFont
from core.app import PentestToolManager

# 设置中文字体支持
def setup_fonts():
    font = QFont()
    font.setFamily("Microsoft YaHei")
    return font

# NOTE: 统一使用当前工作目录作为配置目录（config_dir = os.path.abspath('.')），
# 所有程序数据和 images 路径都存放在当前目录下的 data/ 和 images/ 中。

def main():
    # 设置高DPI支持
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建Qt应用
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 设置字体
    app.setFont(setup_fonts())
    
    # 获取可执行文件所在目录作为配置目录
    # 当作为脚本运行时，使用当前目录；当作为exe运行时，使用exe所在目录
    if hasattr(sys, 'frozen'):
        # PyInstaller打包后的exe
        config_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # 正常Python脚本运行
        config_dir = os.path.abspath(".")
    
    # 确保图片目录存在
    images_dir = os.path.join(config_dir, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    # 创建主窗口
    window = PentestToolManager(config_dir=config_dir)
    
    # 设置窗口图标
    # 优先尝试使用工作目录下的 image.png 作为图标（便于用户快速替换）
    png_icon_path = os.path.join(config_dir, "image.png")
    if os.path.exists(png_icon_path):
        icon = QIcon(png_icon_path)
        if not icon.isNull():
            # 设置应用级别与窗口级别图标，保证任务栏和标题栏均显示
            QApplication.setWindowIcon(icon)
            window.setWindowIcon(icon)
    else:
        # 回退到 resources 下的 ico 图标（保持向后兼容）
        icon_path = os.path.join(config_dir, "resources", "icons", "favicon.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                QApplication.setWindowIcon(icon)
                window.setWindowIcon(icon)
    
    # 设置信号处理程序，用于捕获Ctrl+C信号
    def signal_handler(signal, frame):
        """处理信号，确保资源被正确清理"""
        print("\n捕获到退出信号，正在清理资源...")
        try:
            # 调用窗口的closeEvent方法，确保资源被正确清理
            window.close()
        except Exception as e:
            print(f"清理资源时出错: {e}")
        finally:
            # 强制退出应用
            sys.exit(0)
    
    # 注册信号处理程序
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 显示窗口
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
子非鱼工具箱 - 主入口
"""

import os
import sys
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
    from PyQt5.QtCore import Qt
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
    icon_path = os.path.join(config_dir, "resources", "icons", "new_default_icon.svg")
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    
    # 显示窗口
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
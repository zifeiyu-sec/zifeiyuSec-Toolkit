#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试工具卡片右键菜单功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QListView
from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex, QPoint
from ui.tool_model_view import ToolCardContainer

class TestModel(QAbstractListModel):
    def __init__(self, tools):
        super().__init__()
        self.tools = tools

    def rowCount(self, parent=QModelIndex()):
        return len(self.tools)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.tools):
            return None
        return self.tools[index.row()]

    def get_tool(self, index):
        if index.isValid() and index.row() < len(self.tools):
            return self.tools[index.row()]
        return None

def test_context_menu():
    """测试右键菜单功能"""
    print("开始测试工具卡片右键菜单功能...")

    # 创建测试工具数据
    test_tools = [
        {
            'id': 1,
            'name': '测试工具1',
            'path': 'C:\\Windows\\System32\\cmd.exe',
            'description': '测试工具1描述',
            'working_directory': 'C:\\Windows\\System32',
            'is_web_tool': False
        },
        {
            'id': 2,
            'name': '测试工具2',
            'path': 'C:\\Windows\\System32\\notepad.exe',
            'description': '测试工具2描述',
            'working_directory': 'C:\\Windows\\System32',
            'is_web_tool': False
        }
    ]

    # 创建Qt应用程序
    app = QApplication(sys.argv)

    # 创建测试窗口
    window = QWidget()
    window.setWindowTitle("测试右键菜单")
    window.setGeometry(100, 100, 400, 300)

    layout = QVBoxLayout(window)

    # 创建模型和视图
    model = TestModel(test_tools)
    container = ToolCardContainer()

    # 设置模型
    container.model = model
    container.view.setModel(model)

    layout.addWidget(container)

    # 显示窗口
    window.show()

    print("✅ 测试界面已创建")
    print("请右键点击工具卡片测试新功能：")
    print("- 在此处打开命令行")
    print("- 在此处打开目录")

    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    test_context_menu()
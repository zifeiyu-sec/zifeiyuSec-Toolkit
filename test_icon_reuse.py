#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试图标复用功能
"""
import os
import tempfile
import shutil
from ui.tool_config_dialog import ToolConfigDialog

def test_icon_reuse():
    """测试图标复用功能"""
    print("开始测试图标复用功能...")

    # 创建临时图标文件
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
        # 创建一个简单的PNG文件内容（实际上我们只需要文件存在）
        temp_file.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h\xde\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x04gAMA\x00\x00\xb1\x8f\x0b\xfca\x05\x00\x00\x00\tpHYs\x00\x00\x0e\xc3\x00\x00\x0e\xc3\x01\xc7o\xa8d\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
        temp_icon_path = temp_file.name

    try:
        # 模拟工具数据
        tool_data1 = {
            "name": "TestTool1",
            "path": "C:\\Windows\\System32\\cmd.exe",
            "description": "测试工具1",
            "category_id": 1,
            "subcategory_id": 101,
            "icon": temp_icon_path,  # 使用临时图标
            "tags": [],
            "priority": 0,
            "is_favorite": False,
            "arguments": "",
            "working_directory": "",
            "run_in_terminal": False,
            "is_web_tool": False
        }

        tool_data2 = {
            "name": "TestTool2",
            "path": "C:\\Windows\\System32\\notepad.exe",
            "description": "测试工具2",
            "category_id": 1,
            "subcategory_id": 101,
            "icon": temp_icon_path,  # 使用相同的临时图标
            "tags": [],
            "priority": 0,
            "is_favorite": False,
            "arguments": "",
            "working_directory": "",
            "run_in_terminal": False,
            "is_web_tool": False
        }

        # 创建对话框实例
        categories = [{"id": 1, "name": "测试分类", "subcategories": [{"id": 101, "name": "测试子分类"}]}]

        # 测试第一个工具
        print("添加第一个工具...")
        dialog1 = ToolConfigDialog(tool_data=tool_data1, categories=categories)
        dialog1.selected_icon_name = temp_icon_path  # 设置选中的图标

        # 手动调用保存逻辑
        dialog1.on_save()
        result1 = dialog1.get_tool_data()
        icon1 = result1.get("icon")
        print(f"第一个工具图标: {icon1}")

        # 测试第二个工具（使用相同图标）
        print("添加第二个工具（使用相同图标）...")
        dialog2 = ToolConfigDialog(tool_data=tool_data2, categories=categories)
        dialog2.selected_icon_name = temp_icon_path  # 设置相同的图标

        # 手动调用保存逻辑
        dialog2.on_save()
        result2 = dialog2.get_tool_data()
        icon2 = result2.get("icon")
        print(f"第二个工具图标: {icon2}")

        # 检查结果
        if icon1 == icon2:
            print("✅ 测试成功：两个工具使用了相同的图标文件")
            return True
        else:
            print("❌ 测试失败：两个工具使用了不同的图标文件")
            return False

    finally:
        # 清理临时文件
        try:
            os.unlink(temp_icon_path)
        except:
            pass

if __name__ == "__main__":
    test_icon_reuse()
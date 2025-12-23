#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查并修复工具图标问题：
1. 确保所有工具都有图标设置
2. 对于没有图标的工具，使用favicon.ico作为默认图标
3. 确保所有引用的图标文件都存在
"""
import os
import json

def fix_default_icons():
    """检查并修复工具图标设置"""
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 工具配置文件路径
    tools_json_path = os.path.join(current_dir, 'data', 'tools.json')
    
    # 图标目录
    icons_dir = os.path.join(current_dir, 'resources', 'icons')
    
    # 默认图标路径
    default_icon = 'favicon.ico'
    
    # 检查默认图标是否存在
    default_icon_path = os.path.join(icons_dir, default_icon)
    if not os.path.exists(default_icon_path):
        print(f'错误：默认图标文件 {default_icon} 不存在于 {icons_dir} 目录中')
        return False
    
    print(f'使用 {default_icon} 作为默认工具图标')
    
    # 读取工具配置
    if not os.path.exists(tools_json_path):
        print(f'错误：工具配置文件 {tools_json_path} 不存在')
        return False
    
    with open(tools_json_path, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    
    # 检查并修复每个工具的图标
    fixed_count = 0
    for tool in tools:
        # 跳过没有id的工具（不应该有）
        if 'id' not in tool:
            continue
        
        # 获取当前工具的图标设置
        icon = tool.get('icon')
        
        # 如果没有图标，设置为默认图标
        if not icon:
            tool['icon'] = default_icon
            fixed_count += 1
            print(f'修复工具 {tool.get("name", "未知工具")} ({tool["id"]})：添加默认图标 {default_icon}')
        else:
            # 检查图标文件是否存在
            icon_path = os.path.join(icons_dir, icon)
            if not os.path.exists(icon_path):
                # 图标文件不存在，使用默认图标
                tool['icon'] = default_icon
                fixed_count += 1
                print(f'修复工具 {tool.get("name", "未知工具")} ({tool["id"]})：图标 {icon} 不存在，使用默认图标 {default_icon}')
    
    # 保存修复后的工具配置
    with open(tools_json_path, 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)
    
    print(f'\n修复完成，共修复 {fixed_count} 个工具的图标设置')
    return True

if __name__ == '__main__':
    fix_default_icons()

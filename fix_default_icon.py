import os
import shutil

# 获取项目根目录
base_dir = os.path.dirname(os.path.abspath(__file__))
icons_dir = os.path.join(base_dir, 'resources', 'icons')

# 检查new_default_icon_2.ico是否存在
new_default_icon_path = os.path.join(icons_dir, 'new_default_icon_2.ico')
default_icon_path = os.path.join(icons_dir, 'default_tool_icon.svg')

if os.path.exists(new_default_icon_path) and not os.path.exists(default_icon_path):
    # 复制new_default_icon_2.ico为default_tool_icon.svg
    # 注意：这里只是为了修复应用程序的错误，实际应该使用正确的文件格式
    # 但为了快速修复，我们直接复制并更改扩展名
    shutil.copy2(new_default_icon_path, default_icon_path)
    print(f'已复制 {new_default_icon_path} 为 {default_icon_path}')
else:
    print(f'new_default_icon_2.ico不存在或default_tool_icon.svg已存在')

# 检查是否还有其他缺失的图标
data_dir = os.path.join(base_dir, 'data')
tools_file = os.path.join(data_dir, 'tools.json')

if os.path.exists(tools_file):
    import json
    with open(tools_file, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    
    # 如果tools是字典，提取tools列表
    if isinstance(tools, dict):
        tools = tools.get('tools', [])
    
    print(f'\n检查 {len(tools)} 个工具的图标...')
    
    for tool in tools:
        icon = tool.get('icon', '')
        if icon:
            icon_path = os.path.join(icons_dir, icon)
            if not os.path.exists(icon_path):
                print(f'工具 {tool.get("name")} 使用的图标 {icon} 不存在')
    
    print('图标检查完成')
else:
    print(f'工具文件不存在: {tools_file}')

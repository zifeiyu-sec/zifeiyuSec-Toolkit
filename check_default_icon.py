import os
import json

# 获取项目根目录
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data')
icons_dir = os.path.join(base_dir, 'resources', 'icons')

# 检查图标目录内容
print('检查图标目录内容:')
for file in os.listdir(icons_dir):
    print(f'  {file}')

# 检查是否存在favicon.ico
favicon_path = os.path.join(icons_dir, 'favicon.ico')
if os.path.exists(favicon_path):
    print('\nfavicon.ico 已存在')
else:
    print('\nfavicon.ico 不存在')
    # 如果不存在，尝试从现有图标中复制一个作为favicon.ico
    available_icons = [f for f in os.listdir(icons_dir) if f.endswith(('.ico', '.png', '.svg', '.jpg', '.jpeg'))]
    if available_icons:
        # 使用第一个可用图标作为favicon.ico
        first_icon = os.path.join(icons_dir, available_icons[0])
        import shutil
        shutil.copy2(first_icon, favicon_path)
        print(f'已创建favicon.ico，从{available_icons[0]}复制')
    else:
        print('错误：resources/icons目录中没有可用图标来创建favicon.ico')
        exit(1)

# 修改默认图标设置
ui_file = os.path.join(base_dir, 'ui', 'tool_config_dialog.py')
with open(ui_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 将默认图标从default_tool.svg改为favicon.ico
new_content = content.replace('self.default_icon_name = "default_tool.svg"', 'self.default_icon_name = "favicon.ico"')

with open(ui_file, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('\n已修改tool_config_dialog.py中的默认图标为favicon.ico')

# 检查tools.json中的工具图标配置
tools_file = os.path.join(data_dir, 'tools.json')
with open(tools_file, 'r', encoding='utf-8') as f:
    tools_data = json.load(f)

# 如果tools_data是字典，提取tools列表
if isinstance(tools_data, dict):
    tools = tools_data.get('tools', [])
else:
    tools = tools_data

# 更新没有图标的工具
updated_count = 0
for tool in tools:
    # 检查图标是否为空或不存在
    icon = tool.get('icon', '')
    if not icon or not os.path.exists(os.path.join(icons_dir, icon)):
        tool['icon'] = 'favicon.ico'
        updated_count += 1
        print(f'已为工具 {tool.get("name")} 设置默认图标 favicon.ico')

# 保存更新后的工具数据
if isinstance(tools_data, dict):
    tools_data['tools'] = tools
    with open(tools_file, 'w', encoding='utf-8') as f:
        json.dump(tools_data, f, ensure_ascii=False, indent=2)
else:
    with open(tools_file, 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)

print(f'\n已保存 {updated_count} 个工具的图标设置')

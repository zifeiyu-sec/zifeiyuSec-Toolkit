import os
import json
import hashlib

# 获取项目根目录
base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, 'data')
icons_dir = os.path.join(base_dir, 'resources', 'icons')

print(f"项目根目录: {base_dir}")
print(f"数据目录: {data_dir}")
print(f"图标目录: {icons_dir}")

# 加载工具数据
tools_file = os.path.join(data_dir, 'tools.json')
if os.path.exists(tools_file):
    with open(tools_file, 'r', encoding='utf-8') as f:
        tools = json.load(f)
    
    # 如果tools是字典，提取tools列表
    if isinstance(tools, dict):
        tools = tools.get('tools', [])
    
    print(f'\n加载的工具数量: {len(tools)}')
    
    # 收集所有使用的图标
    used_icons = set()
    for tool in tools:
        icon = tool.get('icon', '')
        if icon:
            used_icons.add(icon)
    
    print(f'使用的图标数量: {len(used_icons)}')
    print('使用的图标列表:')
    for icon in sorted(used_icons):
        print(f'  {icon}')
    
    # 获取所有可用图标
    available_icons = set()
    if os.path.exists(icons_dir):
        for root, dirs, files in os.walk(icons_dir):
            for file in files:
                if file.endswith(('.ico', '.png', '.svg', '.jpg', '.jpeg')):
                    available_icons.add(file)
        
        print(f'\n可用图标数量: {len(available_icons)}')
        print('可用图标列表:')
        for icon in sorted(available_icons):
            print(f'  {icon}')
        
        # 找出没有使用的图标
        unused_icons = available_icons - used_icons
        print(f'\n未使用的图标数量: {len(unused_icons)}')
        if unused_icons:
            print('未使用的图标列表:')
            for icon in sorted(unused_icons):
                print(f'  {icon}')
        
        # 计算图标文件的哈希值，找出内容相同的图标
        icon_hashes = {}
        for icon in available_icons:
            icon_path = os.path.join(icons_dir, icon)
            try:
                with open(icon_path, 'rb') as f:
                    hash_obj = hashlib.sha256()
                    hash_obj.update(f.read())
                    icon_hash = hash_obj.hexdigest()
                    if icon_hash not in icon_hashes:
                        icon_hashes[icon_hash] = []
                    icon_hashes[icon_hash].append(icon)
            except Exception as e:
                print(f'\n计算图标{icon}哈希失败: {e}')
        
        # 找出重复的图标
        duplicate_icons = {hash_val: icons for hash_val, icons in icon_hashes.items() if len(icons) > 1} 
        print(f'\n重复图标组数量: {len(duplicate_icons)}')
        for hash_val, icons in duplicate_icons.items():
            print(f'\n哈希值 {hash_val[:8]}... 对应的重复图标:')
            for icon in icons:
                print(f'  {icon}')
                # 检查哪些被使用了
                if icon in used_icons:
                    print(f'     被使用')
                else:
                    print(f'     未被使用')
    else:
        print(f'\n图标目录不存在: {icons_dir}')
else:
    print(f'\n工具文件不存在: {tools_file}')

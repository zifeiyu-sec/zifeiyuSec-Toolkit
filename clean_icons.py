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
    
    # 获取所有可用图标
    available_icons = set()
    if os.path.exists(icons_dir):
        for root, dirs, files in os.walk(icons_dir):
            for file in files:
                if file.endswith(('.ico', '.png', '.svg', '.jpg', '.jpeg')):
                    available_icons.add(file)
        
        print(f'可用图标数量: {len(available_icons)}')
        
        # 找出没有使用的图标
        unused_icons = available_icons - used_icons
        print(f'\n未使用的图标数量: {len(unused_icons)}')
        
        # 删除未使用的图标
        if unused_icons:
            print('开始删除未使用的图标...')
            deleted_count = 0
            for icon in unused_icons:
                icon_path = os.path.join(icons_dir, icon)
                try:
                    os.remove(icon_path)
                    print(f'删除成功: {icon}')
                    deleted_count += 1
                except Exception as e:
                    print(f'删除失败 {icon}: {e}')
            print(f'\n删除完成，共删除 {deleted_count} 个未使用图标')
        
        # 重新获取可用图标列表（已删除未使用的图标）
        available_icons = set()
        for root, dirs, files in os.walk(icons_dir):
            for file in files:
                if file.endswith(('.ico', '.png', '.svg', '.jpg', '.jpeg')):
                    available_icons.add(file)
        
        print(f'\n当前可用图标数量: {len(available_icons)}')
        
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
                print(f'计算图标{icon}哈希失败: {e}')
        
        # 找出重复的图标
        duplicate_icons = {hash_val: icons for hash_val, icons in icon_hashes.items() if len(icons) > 1}
        print(f'\n重复图标组数量: {len(duplicate_icons)}')
        
        # 处理重复图标：保留一个被使用的，删除其他重复的
        if duplicate_icons:
            print('开始处理重复图标...')
            updated_tools = False
            
            for hash_val, icons in duplicate_icons.items():
                print(f'\n处理哈希值 {hash_val[:8]}... 的重复图标:')
                
                # 找出该组中被使用的图标
                used_in_group = [icon for icon in icons if icon in used_icons]
                
                if used_in_group:
                    # 选择第一个被使用的图标作为保留的图标
                    keep_icon = used_in_group[0]
                    print(f'  保留的图标: {keep_icon}')
                    
                    # 找出需要删除的重复图标
                    to_delete = [icon for icon in icons if icon != keep_icon]
                    
                    # 更新工具数据，将使用其他重复图标的工具改为使用保留的图标
                    for tool in tools:
                        icon = tool.get('icon', '')
                        if icon in to_delete:
                            tool['icon'] = keep_icon
                            updated_tools = True
                            print(f'  更新工具 {tool.get("name")} 使用图标: {icon} -> {keep_icon}')
                    
                    # 删除其他重复图标
                    for icon in to_delete:
                        icon_path = os.path.join(icons_dir, icon)
                        try:
                            os.remove(icon_path)
                            print(f'  删除重复图标: {icon}')
                        except Exception as e:
                            print(f'  删除失败 {icon}: {e}')
                else:
                    # 该组中没有被使用的图标，删除所有重复图标，只保留一个
                    keep_icon = icons[0]
                    to_delete = icons[1:]
                    print(f'  该组没有被使用的图标，保留: {keep_icon}')
                    
                    for icon in to_delete:
                        icon_path = os.path.join(icons_dir, icon)
                        try:
                            os.remove(icon_path)
                            print(f'  删除重复图标: {icon}')
                        except Exception as e:
                            print(f'  删除失败 {icon}: {e}')
            
            # 如果更新了工具数据，保存回文件
            if updated_tools:
                print(f'\n更新了 {sum(1 for tool in tools if tool.get("icon") != tool.get("icon", ""))} 个工具的图标引用')
                print('保存更新后的工具数据...')
                
                # 检查原始工具数据格式
                original_data = {}
                with open(tools_file, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                
                if isinstance(original_data, dict):
                    original_data['tools'] = tools
                    with open(tools_file, 'w', encoding='utf-8') as f:
                        json.dump(original_data, f, ensure_ascii=False, indent=2)
                else:
                    with open(tools_file, 'w', encoding='utf-8') as f:
                        json.dump(tools, f, ensure_ascii=False, indent=2)
                
                print('工具数据保存成功')
        
        print(f'\n图标清理完成！')
    else:
        print(f'图标目录不存在: {icons_dir}')
else:
    print(f'工具文件不存在: {tools_file}')

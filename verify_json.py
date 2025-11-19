import json
import os

# 获取当前脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
categories_file = os.path.join(script_dir, 'data', 'categories.json')

try:
    with open(categories_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print('JSON格式正确')
    print(f'共有 {len(data.get("categories", []))} 个分类')
    
    # 检查是否存在重复ID
    category_ids = set()
    subcategory_ids = set()
    duplicate_category_ids = []
    duplicate_subcategory_ids = []
    
    for category in data.get('categories', []):
        if category['id'] in category_ids:
            duplicate_category_ids.append(category['id'])
        else:
            category_ids.add(category['id'])
        
        for subcategory in category.get('subcategories', []):
            if subcategory['id'] in subcategory_ids:
                duplicate_subcategory_ids.append(subcategory['id'])
            else:
                subcategory_ids.add(subcategory['id'])
    
    if duplicate_category_ids:
        print(f'警告：发现重复的分类ID: {duplicate_category_ids}')
    else:
        print('没有发现重复的分类ID')
        
    if duplicate_subcategory_ids:
        print(f'警告：发现重复的子分类ID: {duplicate_subcategory_ids}')
    else:
        print('没有发现重复的子分类ID')
        
    # 检查ID是否连续
    if category_ids:
        min_id = min(category_ids)
        max_id = max(category_ids)
        expected_ids = set(range(min_id, max_id + 1))
        missing_ids = expected_ids - category_ids
        if missing_ids:
            print(f'警告：发现缺失的分类ID: {sorted(missing_ids)}')
        else:
            print('分类ID是连续的')
            
except json.JSONDecodeError as e:
    print(f'JSON格式错误: {e}')
except Exception as e:
    print(f'其他错误: {e}')
import json
import os

# 读取分类文件
categories_path = os.path.join('data', 'categories.json')
tools_path = os.path.join('data', 'tools.json')

print("=== 分类数据 ===")
try:
    with open(categories_path, 'r', encoding='utf-8') as f:
        categories_data = json.load(f)
    print(json.dumps(categories_data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"读取分类文件失败: {e}")

print("\n=== 工具数据示例 ===")
try:
    with open(tools_path, 'r', encoding='utf-8') as f:
        tools_data = json.load(f)
    if isinstance(tools_data, dict) and 'tools' in tools_data:
        tools_data = tools_data['tools']
    # 只显示前3个工具作为示例
    sample_tools = tools_data[:3] if len(tools_data) > 3 else tools_data
    print(json.dumps(sample_tools, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"读取工具文件失败: {e}")

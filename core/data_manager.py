import json
import os
from datetime import datetime

class DataManager:
    def __init__(self, config_dir=None, data_dir=None):
        """初始化数据管理器"""
        # 初始化数据目录
        if config_dir is not None:
            # 使用配置目录下的data文件夹
            self.data_dir = os.path.join(config_dir, "data")
        elif data_dir is not None:
            self.data_dir = data_dir
        else:
            # 默认数据目录为项目根目录下的data文件夹
            self.data_dir = "data"
        
        self.categories_file = os.path.join(self.data_dir, "categories.json")
        self.tools_file = os.path.join(self.data_dir, "tools.json")
        
        # 确保数据目录存在
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # 初始化默认数据文件（如果不存在）
        self._initialize_default_files()
    
    def _initialize_default_files(self):
        """初始化默认的数据文件"""
        # 如果分类文件不存在，创建默认分类
        if not os.path.exists(self.categories_file):
            # 这里可以放置默认分类数据的创建逻辑
            pass
        
        # 如果工具文件不存在，创建默认工具数据
        if not os.path.exists(self.tools_file):
            # 这里可以放置默认工具数据的创建逻辑
            pass
    
    def load_categories(self):
        """加载所有分类和子分类数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.categories_file), exist_ok=True)
            
            # 检查文件是否存在且不为空
            if os.path.exists(self.categories_file) and os.path.getsize(self.categories_file) > 0:
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        # 检查是否为嵌套结构
                        if isinstance(data, dict) and 'categories' in data:
                            categories = data['categories']
                        else:
                            categories = data
                        
                        return categories
                    except json.JSONDecodeError:
                        print("分类数据格式错误，创建默认分类")
                        return self._create_default_categories()
            else:
                # 文件不存在或为空，返回空列表
                return []
        except Exception as e:
            print(f"加载分类数据失败: {e}")
            # 创建默认分类
            return self._create_default_categories()
    
    def _create_default_categories(self):
        """创建默认分类"""
        default_categories = [
            {"id": 1, "name": "信息收集", "parent_id": None, "icon": "🔍"},
            {"id": 2, "name": "漏洞扫描", "parent_id": None, "icon": "🚨"},
            {"id": 3, "name": "Web渗透", "parent_id": None, "icon": "🌐"},
            {"id": 4, "name": "数据库工具", "parent_id": None, "icon": "💾"},
            {"id": 5, "name": "密码破解", "parent_id": None, "icon": "🔑"},
            {"id": 6, "name": "网络工具", "parent_id": None, "icon": "📡"},
            {"id": 7, "name": "开发工具", "parent_id": None, "icon": "💻"},
            {"id": 8, "name": "其他工具", "parent_id": None, "icon": "📦"}
        ]
        # 保存默认分类
        self.save_categories(default_categories)
        return default_categories
    
    def save_categories(self, categories):
        """保存分类数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.categories_file), exist_ok=True)
            
            # 检查现有文件是否使用嵌套结构
            use_nested_structure = False
            if os.path.exists(self.categories_file) and os.path.getsize(self.categories_file) > 0:
                try:
                    with open(self.categories_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, dict) and 'categories' in existing_data:
                            use_nested_structure = True
                except:
                    pass
            
            # 根据现有格式保存数据
            data_to_save = {'categories': categories} if use_nested_structure else categories
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存分类数据失败: {e}")
            return False
    
    def load_tools(self):
        """加载所有工具数据，如果文件不存在或为空则返回空列表"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tools_file), exist_ok=True)
            
            # 检查文件是否存在且不为空
            if os.path.exists(self.tools_file) and os.path.getsize(self.tools_file) > 0:
                with open(self.tools_file, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        # 检查是否为嵌套结构
                        if isinstance(data, dict) and 'tools' in data:
                            tools = data['tools']
                        else:
                            tools = data

                        # 规范化工具的 category_id / subcategory_id：
                        # 有些 tools.json 会把子分类 id 当作 category_id（例如 101），
                        # 这里尝试根据 categories.json 的结构把它们映射到父分类（一级分类）
                        try:
                            categories = self.load_categories()
                            top_level_ids = {cat.get('id') for cat in categories if isinstance(cat, dict)}
                            sub_to_parent = {}
                            for cat in categories:
                                if isinstance(cat, dict):
                                    for sub in cat.get('subcategories', []) or []:
                                        # 子分类字典应包含 id 和 parent_id
                                        sid = sub.get('id')
                                        pid = sub.get('parent_id', cat.get('id'))
                                        if sid is not None:
                                            sub_to_parent[sid] = pid

                            normalized_tools = []
                            for tool in tools:
                                # Defensive copy to avoid mutating original structures on disk
                                normalized = dict(tool)

                                cid = normalized.get('category_id')
                                sid = normalized.get('subcategory_id')

                                # 如果 category_id 指向一个子分类 id，则修正
                                if cid is not None and cid not in top_level_ids:
                                    # 如果该 id 对应子分类，则将 category_id 设为父 id，sub_id 设为原 cid（如果没有）
                                    if cid in sub_to_parent:
                                        parent = sub_to_parent[cid]
                                        normalized['subcategory_id'] = sid or cid
                                        normalized['category_id'] = parent

                                # 如果 subcategory_id 存在但 category_id 不匹配它的 parent，则修正 category_id
                                if sid is not None and sid in sub_to_parent:
                                    parent = sub_to_parent[sid]
                                    if normalized.get('category_id') != parent:
                                        normalized['category_id'] = parent

                                normalized_tools.append(normalized)

                            tools = normalized_tools
                        except Exception:
                            # 如果规范化过程出现问题，不影响基础加载，返回原始数据
                            pass

                        return tools
                    except json.JSONDecodeError:
                        print("工具数据格式错误，返回空列表")
                        return []
            else:
                # 文件不存在或为空，返回空列表
                return []
        except Exception as e:
            print(f"加载工具数据失败: {e}")
            return []
    
    def save_tools(self, tools):
        """保存工具数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tools_file), exist_ok=True)
            
            # 检查现有文件是否使用嵌套结构
            use_nested_structure = False
            if os.path.exists(self.tools_file) and os.path.getsize(self.tools_file) > 0:
                try:
                    with open(self.tools_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if isinstance(existing_data, dict) and 'tools' in existing_data:
                            use_nested_structure = True
                except json.JSONDecodeError:
                    pass
            
            with open(self.tools_file, 'w', encoding='utf-8') as f:
                if use_nested_structure:
                    json.dump({'tools': tools}, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(tools, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存工具数据失败: {e}")
            return False
    
    def get_tools_by_category(self, category_id, subcategory_id=None):
        """根据分类ID获取工具列表"""
        tools = self.load_tools()
        filtered_tools = []
        
        for tool in tools:
            # 使用get方法安全地访问category_id字段，避免KeyError
            if tool.get('category_id') == category_id:
                if subcategory_id is None or tool.get('subcategory_id') == subcategory_id:
                    filtered_tools.append(tool)
        
        return filtered_tools
    
    def get_tool_by_id(self, tool_id):
        """根据工具ID获取工具信息"""
        tools = self.load_tools()
        for tool in tools:
            if tool['id'] == tool_id:
                return tool
        return None
    
    def add_tool(self, tool_data):
        """添加新工具"""
        tools = self.load_tools()
        
        # 生成新的工具ID
        if tools:
            new_id = max(tool['id'] for tool in tools) + 1
        else:
            new_id = 1
        
        tool_data['id'] = new_id
        tool_data['usage_count'] = 0
        tool_data['last_used'] = None
        tool_data['is_favorite'] = False
        
        tools.append(tool_data)
        return self.save_tools(tools)
    
    def update_tool(self, tool_id, updated_data):
        """更新工具信息"""
        tools = self.load_tools()
        for i, tool in enumerate(tools):
            if tool['id'] == tool_id:
                # 更新工具信息，但保留ID和使用统计数据
                updated_data['id'] = tool_id
                if 'usage_count' not in updated_data:
                    updated_data['usage_count'] = tool.get('usage_count', 0)
                if 'last_used' not in updated_data:
                    updated_data['last_used'] = tool.get('last_used')
                
                tools[i] = updated_data
                return self.save_tools(tools)
        return False
    
    def delete_tool(self, tool_id):
        """删除工具"""
        tools = self.load_tools()
        filtered_tools = [tool for tool in tools if tool['id'] != tool_id]
        
        if len(filtered_tools) < len(tools):
            return self.save_tools(filtered_tools)
        return False
    
    def toggle_favorite(self, tool_id):
        """切换工具收藏状态"""
        tools = self.load_tools()
        for tool in tools:
            if tool['id'] == tool_id:
                tool['is_favorite'] = not tool.get('is_favorite', False)
                return self.save_tools(tools)
        return False
    
    def update_tool_usage(self, tool_id):
        """更新工具使用统计"""
        tools = self.load_tools()
        for tool in tools:
            if tool['id'] == tool_id:
                tool['usage_count'] = tool.get('usage_count', 0) + 1
                tool['last_used'] = datetime.now().isoformat() + 'Z'
                return self.save_tools(tools)
        return False
    
    def search_tools(self, keyword):
        """搜索工具（根据名称、描述或标签）"""
        tools = self.load_tools()
        keyword = keyword.lower()
        results = []
        
        for tool in tools:
            if (keyword in tool['name'].lower() or 
                keyword in tool.get('description', '').lower() or
                any(keyword in tag.lower() for tag in tool.get('tags', []))):
                results.append(tool)
        
        return results
    
    def add_category(self, category_data):
        """添加新的一级分类"""
        categories = self.load_categories()
        
        # 生成新的分类ID
        if categories:
            new_id = max(cat['id'] for cat in categories) + 1
        else:
            new_id = 1
        
        category_data['id'] = new_id
        if 'subcategories' not in category_data:
            category_data['subcategories'] = []
        
        categories.append(category_data)
        return self.save_categories(categories)
    
    def add_subcategory(self, parent_id, subcategory_data):
        """添加新的二级分类"""
        categories = self.load_categories()
        
        for category in categories:
            if category['id'] == parent_id:
                # 生成新的子分类ID
                if category.get('subcategories'):
                    new_id = max(sub['id'] for sub in category['subcategories']) + 1
                else:
                    new_id = parent_id * 100 + 1
                
                subcategory_data['id'] = new_id
                subcategory_data['parent_id'] = parent_id
                
                if 'subcategories' not in category:
                    category['subcategories'] = []
                
                category['subcategories'].append(subcategory_data)
                return self.save_categories(categories)
    
    def delete_category(self, category_id):
        """删除分类"""
        categories = self.load_categories()
        
        # 检查是否有工具使用该分类
        tools = self.load_tools()
        for tool in tools:
            if tool.get('category_id') == category_id:
                return False, "该分类下存在工具，无法删除！"
        
        # 移除分类
        new_categories = [cat for cat in categories if cat['id'] != category_id]
        
        if len(new_categories) < len(categories):
            return self.save_categories(new_categories), ""
        return False, "分类不存在！"
    
    def get_all_categories(self):
        """获取所有分类数据，用于工具配置对话框"""
        return self.load_categories()
    
    def get_subcategories_by_category(self, category_id):
        """根据一级分类ID获取该分类下的所有子分类"""
        categories = self.load_categories()
        
        for category in categories:
            if category['id'] == category_id:
                return category.get('subcategories', [])
        
        return []
    
    def delete_subcategory(self, subcategory_id):
        """删除子分类"""
        categories = self.load_categories()
        
        # 检查是否有工具使用该子分类
        tools = self.load_tools()
        for tool in tools:
            if tool.get('subcategory_id') == subcategory_id:
                return False, "该子分类下存在工具，无法删除！"
        
        # 移除子分类
        for category in categories:
            if 'subcategories' in category:
                original_len = len(category['subcategories'])
                category['subcategories'] = [sub for sub in category['subcategories'] if sub['id'] != subcategory_id]
                if len(category['subcategories']) < original_len:
                    return self.save_categories(categories), ""
        
        return False, "子分类不存在！"
    
    def update_tool_background(self, tool_id, background_image_path):
        """更新工具背景图片"""
        tools = self.load_tools()
        for tool in tools:
            if tool['id'] == tool_id:
                tool['background_image'] = background_image_path
                return self.save_tools(tools)
        return False

# 示例用法
if __name__ == "__main__":
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建相对于脚本的data目录路径
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    
    data_manager = DataManager(data_dir)
    
    # 示例：加载所有分类
    categories = data_manager.load_categories()
    print(f"已加载 {len(categories)} 个一级分类")
    
    # 示例：加载所有工具
    tools = data_manager.load_tools()
    print(f"已加载 {len(tools)} 个工具")
import os
from datetime import datetime
from core.logger import logger
from PyQt5.QtCore import QObject, QThread, pyqtSignal

# 使用更快的JSON解析库orjson
try:
    import orjson as json
except ImportError:
    # 回退到ujson
    try:
        import ujson as json
    except ImportError:
        # 最后回退到标准库json
        import json

# 导入多线程相关模块
from concurrent.futures import ThreadPoolExecutor, as_completed

class ToolsLoadWorker(QObject):
    """后台加载工具数据的Worker类"""
    finished = pyqtSignal(list)
    error = pyqtSignal(Exception)
    
    def __init__(self, tools_file, tools_cache, last_tools_modified):
        super().__init__()
        self.tools_file = tools_file
        self.tools_cache = tools_cache
        self.last_tools_modified = last_tools_modified
    
    def run(self):
        """执行后台加载任务"""
        try:
            # 检查文件是否存在且不为空
            if os.path.exists(self.tools_file) and os.path.getsize(self.tools_file) > 0:
                # 获取文件最后修改时间
                current_modified = os.path.getmtime(self.tools_file)
                
                # 如果缓存有效（未修改且存在），直接返回缓存
                if self.tools_cache is not None and self.last_tools_modified == current_modified:
                    self.finished.emit(self.tools_cache)
                    return
            else:
                # 文件不存在或为空，返回空列表
                self.finished.emit([])
                return
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tools_file), exist_ok=True)
            
            # 重新加载工具数据 - 使用更快的json加载方式
            tools = []
            with open(self.tools_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
                # 使用orjson.loads替代json.load，提高解析速度
                data = json.loads(file_content)
                
                # 检查是否为嵌套结构
                if isinstance(data, dict) and 'tools' in data:
                    tools = data['tools']
                else:
                    tools = data


            
            self.finished.emit(tools)
        except Exception as e:
            self.error.emit(e)

class DataManager:
    """数据管理器，负责处理工具分类和工具数据的存储与读取"""
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
        
        # 添加数据缓存，减少重复加载
        self._categories_cache = None
        self._tools_cache = None
        self._last_categories_modified = 0
        self._last_tools_modified = 0
        
        # 添加分类工具缓存，避免重复过滤
        self._category_tools_cache = {}
        
        # 添加规范化结果缓存，避免重复规范化
        self._normalization_cache = None
        self._normalization_cache_key = None
        
        # 后台加载相关
        self._tools_load_thread = None
        self._tools_load_worker = None
    
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
        """加载所有分类和子分类数据，使用缓存机制减少重复加载"""
        try:
            # 检查文件是否存在且不为空
            if os.path.exists(self.categories_file) and os.path.getsize(self.categories_file) > 0:
                # 获取文件最后修改时间
                current_modified = os.path.getmtime(self.categories_file)
                
                # 如果缓存有效（未修改且存在），直接返回缓存
                if (self._categories_cache is not None and 
                    self._last_categories_modified == current_modified):
                    return self._categories_cache
            else:
                # 文件不存在或为空，返回空列表
                self._categories_cache = []
                self._last_categories_modified = 0
                return self._categories_cache
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.categories_file), exist_ok=True)
            
            # 重新加载分类数据
            categories = []
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                try:
                    file_content = f.read()
                    data = json.loads(file_content)
                    # 检查是否为嵌套结构
                    if isinstance(data, dict) and 'categories' in data:
                        categories = data['categories']
                    else:
                        categories = data
                except json.JSONDecodeError as e:
                    logger.error("分类数据格式错误，创建默认分类: %s", str(e))
                    categories = self._create_default_categories()
            
            # 注意：不再按优先级排序分类和子分类，以保持用户拖拽设置的顺序
            # 如果需要排序，应该在拖拽排序完成后更新优先级字段
            pass
            
            # 更新缓存
            self._categories_cache = categories
            self._last_categories_modified = current_modified
            return self._categories_cache
            
        except (FileNotFoundError, PermissionError, IOError) as e:
            logger.error("加载分类数据失败: %s", str(e))
            # 创建默认分类
            categories = self._create_default_categories()
            # 更新缓存
            self._categories_cache = categories
            self._last_categories_modified = 0
            return self._categories_cache
    
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
            
            # 序列化数据（在打开文件前进行，防止序列化失败导致文件被清空）
            # 检查是否使用orjson
            is_orjson = 'orjson' in json.__name__
            
            # 准备要保存的数据结构
            # 检查现有文件是否使用嵌套结构（这里我们假设统一化，或者保留逻辑，简单起见我们直接存列表如果没特别需求）
            # 为了保持兼容性，我们先读取一下（虽然这会增加IO），或者干脆约定新版都存纯列表
            # 处于安全考虑，我们简单点，直接保存传入的 categories
            data_to_save = categories
            
            # 尝试根据之前的逻辑判断是否嵌套（略微简化逻辑以防出错）
            if os.path.exists(self.categories_file) and os.path.getsize(self.categories_file) > 0:
                try:
                    with open(self.categories_file, 'r', encoding='utf-8') as f:
                        # 只是为了通过简单的字符检查来推断结构，不完全解析以节省时间
                        first_char = f.read(10).strip()
                        if first_char.startswith('{'):
                             data_to_save = {'categories': categories}
                except Exception:
                    pass

            # 执行序列化
            if is_orjson:
                # orjson.dumps 返回 bytes，不支持 ensure_ascii
                content = json.dumps(data_to_save)
            else:
                # 标准json或ujson
                content = json.dumps(data_to_save, ensure_ascii=False)
                
            # 写入文件
            if is_orjson:
                with open(self.categories_file, 'wb') as f:
                    f.write(content)
            else:
                with open(self.categories_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 清除分类缓存，下次加载时重新读取
            self._categories_cache = None
            self._last_categories_modified = 0
            # 同时清除工具缓存，因为分类变化可能影响工具规范化
            self._tools_cache = None
            self._last_tools_modified = 0
            # 清除规范化缓存，因为分类变化可能影响规范化结果
            self._normalization_cache = None
            self._normalization_cache_key = None
            
            return True
        except (PermissionError, IOError, TypeError, ValueError) as e:
            logger.error("保存分类数据失败: %s", str(e))
            return False
    
    def load_tools(self, callback=None):
        """加载所有工具数据，如果文件不存在或为空则返回空列表，使用缓存机制减少重复加载
        
        Args:
            callback: 可选的回调函数，用于异步加载完成后处理结果
                     签名: callback(tools: list, error: Exception = None)
        
        Returns:
            如果提供了callback，返回None（异步加载）
            否则返回工具列表（同步加载）
        """
        # 如果没有提供回调，使用同步加载
        if callback is None:
            try:
                # 检查文件是否存在且不为空
                if os.path.exists(self.tools_file) and os.path.getsize(self.tools_file) > 0:
                    # 获取文件最后修改时间
                    current_modified = os.path.getmtime(self.tools_file)
                    
                    # 如果缓存有效（未修改且存在），直接返回缓存
                    if (self._tools_cache is not None and 
                        self._last_tools_modified == current_modified):
                        return self._tools_cache
                else:
                    # 文件不存在或为空，返回空列表
                    self._tools_cache = []
                    self._last_tools_modified = 0
                    return self._tools_cache
                
                # 确保目录存在
                os.makedirs(os.path.dirname(self.tools_file), exist_ok=True)
                
                # 重新加载工具数据 - 优化：使用更快的json加载方式
                tools = []
                with open(self.tools_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    data = json.loads(file_content)  # 使用loads而不是load，减少文件对象操作
                    
                    # 检查是否为嵌套结构
                    if isinstance(data, dict) and 'tools' in data:
                        tools = data['tools']
                    else:
                        tools = data



                # 更新缓存
                self._tools_cache = tools
                self._last_tools_modified = current_modified
                return self._tools_cache
                
            except json.JSONDecodeError as e:
                logger.error("工具数据格式错误，返回空列表: %s", str(e))
                self._tools_cache = []
                self._last_tools_modified = 0
                return self._tools_cache
            except (FileNotFoundError, PermissionError, IOError) as e:
                logger.error("加载工具数据失败: %s", str(e))
                return []
        # 如果提供了回调，使用异步加载
        else:
            # 停止之前可能正在运行的加载任务
            self._stop_tools_load_thread()
            
            # 创建新的线程和worker
            self._tools_load_thread = QThread()
            self._tools_load_worker = ToolsLoadWorker(
                self.tools_file, 
                self._tools_cache, 
                self._last_tools_modified
            )
            
            # 将worker移动到线程
            self._tools_load_worker.moveToThread(self._tools_load_thread)
            
            # 连接信号
            self._tools_load_thread.started.connect(self._tools_load_worker.run)
            self._tools_load_worker.finished.connect(self._on_tools_loaded)
            self._tools_load_worker.finished.connect(callback)
            self._tools_load_worker.error.connect(lambda e: callback([], e))
            self._tools_load_worker.finished.connect(self._tools_load_thread.quit)
            self._tools_load_worker.finished.connect(self._tools_load_worker.deleteLater)
            self._tools_load_thread.finished.connect(self._tools_load_thread.deleteLater)
            
            # 启动线程
            self._tools_load_thread.start()
    
    def _on_tools_loaded(self, tools):
        """处理后台加载工具完成后的回调"""
        # 更新缓存
        self._tools_cache = tools
        if os.path.exists(self.tools_file):
            self._last_tools_modified = os.path.getmtime(self.tools_file)
        else:
            self._last_tools_modified = 0
    
    def _stop_tools_load_thread(self):
        """停止正在运行的工具加载线程"""
        try:
            if self._tools_load_thread is not None:
                # 使用try-except块包装对Qt对象的访问，避免访问已删除对象
                try:
                    if self._tools_load_thread.isRunning():
                        self._tools_load_thread.quit()
                        self._tools_load_thread.wait()
                except RuntimeError as e:
                    # 捕获Qt对象已被删除的错误
                    if "wrapped C/C++ object" in str(e):
                        pass  # 对象已被删除，无需处理
                    else:
                        raise  # 其他运行时错误，重新抛出
            self._tools_load_thread = None
            self._tools_load_worker = None
        except Exception as e:
            logger.error("停止工具加载线程失败: %s", str(e))
    
    def save_tools(self, tools):
        """保存工具数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.tools_file), exist_ok=True)
            
            # 序列化数据（在打开文件前进行，防止序列化失败导致文件被清空）
            # 检查是否使用orjson
            is_orjson = 'orjson' in json.__name__
            
            # 准备数据
            data_to_save = tools
            
            # 检查是否需要嵌套结构（简化检查逻辑）
            if os.path.exists(self.tools_file) and os.path.getsize(self.tools_file) > 0:
                try:
                    with open(self.tools_file, 'r', encoding='utf-8') as f:
                        # 简单读取前几个字符判断
                        first_char = f.read(10).strip()
                        if first_char.startswith('{'):
                             data_to_save = {'tools': tools}
                except Exception:
                    pass
            
            # 执行序列化
            if is_orjson:
                # orjson 返回 bytes，不支持 ensure_ascii
                content = json.dumps(data_to_save)
            else:
                content = json.dumps(data_to_save, ensure_ascii=False)
            
            # 写入文件
            if is_orjson:
                with open(self.tools_file, 'wb') as f:
                    f.write(content)
            else:
                with open(self.tools_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 清除工具缓存和分类工具缓存，下次加载时重新读取
            self._tools_cache = None
            self._last_tools_modified = 0
            self._category_tools_cache = {}
            # 清除规范化缓存
            self._normalization_cache = None
            self._normalization_cache_key = None
            
            return True
        except Exception as e:
            logger.error("保存工具数据失败: %s", str(e))
            return False
    
    def get_common_tools(self, limit=12):
        """获取常用工具（根据使用次数排序）"""
        tools = self.load_tools()
        # 按使用次数降序排序
        sorted_tools = sorted(tools, key=lambda x: x.get('usage_count', 0), reverse=True)
        return sorted_tools[:limit]
    
    def get_favorite_tools(self):
        """获取收藏的工具列表"""
        tools = self.load_tools()
        # 过滤出收藏的工具
        favorite_tools = [tool for tool in tools if tool.get('is_favorite', False)]
        return favorite_tools

    def get_tools_by_category(self, category_id, subcategory_id=None):
        """根据分类ID获取工具列表"""
        # 创建缓存键
        cache_key = f"{category_id}_{subcategory_id}"
        
        # 检查缓存是否存在
        if cache_key in self._category_tools_cache:
            return self._category_tools_cache[cache_key]
        
        # 加载工具数据
        tools = self.load_tools()
        filtered_tools = []
        
        # 过滤工具列表
        for tool in tools:
            # 使用get方法安全地访问category_id字段，避免KeyError
            if tool.get('category_id') == category_id:
                if subcategory_id is None or tool.get('subcategory_id') == subcategory_id:
                    filtered_tools.append(tool)
        
        # 缓存过滤结果
        self._category_tools_cache[cache_key] = filtered_tools
        
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
        if 'is_favorite' not in tool_data:
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

    def rename_category(self, category_id, new_name):
        """重命名一级分类（通过 id 定位）"""
        categories = self.load_categories()
        changed = False
        for category in categories:
            if category.get('id') == category_id:
                category['name'] = new_name
                changed = True
                break

        if changed:
            return self.save_categories(categories)
        return False

    def rename_subcategory(self, subcategory_id, new_name):
        """重命名二级子分类（通过子分类 id 定位）"""
        categories = self.load_categories()
        changed = False
        for category in categories:
            subs = category.get('subcategories', [])
            for sub in subs:
                if sub.get('id') == subcategory_id:
                    sub['name'] = new_name
                    changed = True
                    break
            if changed:
                break

        if changed:
            return self.save_categories(categories)
        return False
    
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
    
    def shutdown(self):
        """清理资源，停止所有线程"""
        try:
            # 停止工具加载线程
            self._stop_tools_load_thread()
        except Exception as e:
            logger.error("清理资源失败: %s", str(e))


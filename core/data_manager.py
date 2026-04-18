import os
import re
import json as std_json
from datetime import datetime
from core.logger import logger
from core.runtime_paths import get_bundle_path, get_runtime_path, resolve_icon_path_value

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


def _load_default_data_payload(file_name, root_key, fallback_records):
    template_path = os.fspath(get_bundle_path("data", file_name))
    if os.path.exists(template_path) and os.path.getsize(template_path) > 0:
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                data = std_json.load(f)
            if isinstance(data, dict) and isinstance(data.get(root_key), list):
                return data
            if isinstance(data, list):
                return {root_key: data}
        except (OSError, ValueError, TypeError) as e:
            logger.warning("读取默认模板 %s 失败，回退内置默认值: %s", template_path, str(e))
    return {root_key: fallback_records}


def _load_json_records(file_path, root_key='tools'):
    """从 JSON 文件中读取列表记录，兼容纯列表和带根键的对象结构。"""
    with open(file_path, 'r', encoding='utf-8') as f:
        file_content = f.read()
        data = json.loads(file_content)

    if isinstance(data, dict) and root_key in data:
        records = data[root_key]
    else:
        records = data

    return records if isinstance(records, list) else []


def _get_split_tool_files(tools_split_dir):
    """返回拆分工具文件列表。"""
    if not os.path.isdir(tools_split_dir):
        return []

    split_files = []
    for name in sorted(os.listdir(tools_split_dir)):
        if not name.lower().endswith('.json'):
            continue
        file_path = os.path.join(tools_split_dir, name)
        if os.path.isfile(file_path):
            split_files.append(file_path)
    return split_files


def _get_active_split_tool_files(tools_split_dir):
    return [
        file_path for file_path in _get_split_tool_files(tools_split_dir)
        if os.path.getsize(file_path) > 0
    ]


def _get_tools_state_token(tools_file, tools_split_dir):
    """返回工具数据状态令牌，用于缓存失效判断。"""
    if os.path.isfile(tools_file) and os.path.getsize(tools_file) > 0:
        return (
            (tools_file, os.path.getmtime(tools_file), os.path.getsize(tools_file)),
        )

    active_split_files = _get_active_split_tool_files(tools_split_dir)
    if active_split_files:
        return tuple(
            (file_path, os.path.getmtime(file_path), os.path.getsize(file_path))
            for file_path in active_split_files
        )

    return ()


def _load_tools_from_storage(tools_file, tools_split_dir):
    """Load tools from disk using the aggregate file as the primary source."""
    if os.path.isfile(tools_file) and os.path.getsize(tools_file) > 0:
        return _load_json_records(tools_file)

    active_split_files = _get_active_split_tool_files(tools_split_dir)
    if active_split_files:
        tools = []
        for file_path in active_split_files:
            tools.extend(_load_json_records(file_path))
        return tools

    return []


def _serialize_json(data):
    if 'orjson' in json.__name__:
        return json.dumps(data, option=json.OPT_INDENT_2)
    return std_json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')


def _write_json_file(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'wb') as f:
        f.write(_serialize_json(data))


def _should_wrap_records(file_path, root_key='tools', default_wrap=False):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_char = f.read(10).strip()
                if first_char.startswith('{'):
                    return True
                if first_char.startswith('['):
                    return False
        except Exception:
            pass
    return default_wrap


def _slugify_file_part(value):
    text = str(value or '').strip().lower()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    text = re.sub(r'[^a-z0-9_\-]+', '', text)
    text = text.strip('_-')
    return text or 'category'


class DataManager:
    """数据管理器，负责处理工具分类和工具数据的存储与读取"""
    DEPRECATED_TOOL_FIELDS = ("tags",)
    def __init__(self, config_dir=None, data_dir=None):
        """初始化数据管理器"""
        if config_dir is not None:
            self.data_dir = os.path.join(os.path.abspath(config_dir), "data")
        elif data_dir is not None:
            self.data_dir = os.path.abspath(data_dir)
        else:
            self.data_dir = os.fspath(get_runtime_path("data"))

        self.categories_file = os.path.join(self.data_dir, "categories.json")
        self.tools_file = os.path.join(self.data_dir, "tools.json")
        self.tools_split_dir = os.path.join(self.data_dir, "tools")

        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self._initialize_default_files()

        self._categories_cache = None
        self._tools_cache = None
        self._last_categories_modified = 0
        self._last_tools_modified = ()
        self._category_tools_cache = {}
        self._normalization_cache = None
        self._normalization_cache_key = None
        self._tools_load_thread = None
        self._tools_load_worker = None
        self._pending_usage_updates = {}

    def _initialize_default_files(self):
        """初始化默认的数据文件"""
        if not os.path.exists(self.categories_file):
            _write_json_file(
                self.categories_file,
                _load_default_data_payload(
                    "categories.json",
                    "categories",
                    self._create_default_categories(),
                ),
            )
        if not os.path.exists(self.tools_file):
            _write_json_file(
                self.tools_file,
                _load_default_data_payload("tools.json", "tools", []),
            )

    def _set_categories_cache(self, categories, modified_time=0):
        self._categories_cache = categories
        self._last_categories_modified = modified_time

    def _set_tools_cache(self, tools, modified_token=()):
        self._tools_cache = tools
        self._last_tools_modified = modified_token
        self._category_tools_cache = {}

    def _invalidate_tools_cache(self):
        self._set_tools_cache(None, ())
        self._normalization_cache = None
        self._normalization_cache_key = None

    def _read_categories_from_disk(self):
        with open(self.categories_file, 'r', encoding='utf-8') as f:
            file_content = f.read()
            data = json.loads(file_content)
            if isinstance(data, dict) and 'categories' in data:
                categories = data['categories']
            else:
                categories = data
        return categories if isinstance(categories, list) else []

    def _load_tools_sync(self):
        current_modified = _get_tools_state_token(self.tools_file, self.tools_split_dir)
        if self._tools_cache is not None and self._last_tools_modified == current_modified:
            return self._tools_cache

        if not current_modified:
            self._set_tools_cache([], ())
            return self._tools_cache

        tools = self._load_tools_from_disk()
        self._set_tools_cache(tools, current_modified)
        return self._tools_cache

    def _store_pending_usage_update(self, tool_id, usage_count, last_used):
        self._pending_usage_updates[tool_id] = {
            'usage_count': int(usage_count or 0),
            'last_used': last_used,
        }

    def _apply_pending_usage_updates_to_tools(self, tools, pending_updates):
        changed = False
        for tool in tools:
            tool_id = tool.get('id')
            if tool_id not in pending_updates:
                continue
            pending = pending_updates.get(tool_id) or {}
            usage_count = pending.get('usage_count')
            if usage_count is not None:
                tool['usage_count'] = int(usage_count or 0)
            last_used = pending.get('last_used')
            if last_used:
                tool['last_used'] = last_used
            changed = True
        return changed

    def _strip_deprecated_tool_fields(self, tools):
        cleaned_tools = []
        for tool in tools or []:
            if not isinstance(tool, dict):
                cleaned_tools.append(tool)
                continue

            if not any(field_name in tool for field_name in self.DEPRECATED_TOOL_FIELDS):
                cleaned_tools.append(tool)
                continue

            cleaned_tool = dict(tool)
            tags = cleaned_tool.get("tags", []) or []
            normalized_tags = {str(tag).strip().casefold() for tag in tags if str(tag).strip()}
            if (
                "天狐导入".casefold() in normalized_tags
                and not str(cleaned_tool.get("import_source", "") or "").strip()
            ):
                cleaned_tool["import_source"] = "tianhu"
            for field_name in self.DEPRECATED_TOOL_FIELDS:
                cleaned_tool.pop(field_name, None)
            cleaned_tools.append(cleaned_tool)

        return cleaned_tools

    def _load_tools_from_disk(self):
        return _load_tools_from_storage(self.tools_file, self.tools_split_dir)

    @staticmethod
    def _invoke_tools_callback(callback, tools, error=None):
        if callback is None:
            return
        try:
            callback(tools, error)
        except TypeError:
            callback(tools)

    def _build_split_file_map(self, categories):
        file_map = {}
        ordered_categories = sorted(
            categories,
            key=lambda cat: (cat.get('priority', 9999), cat.get('id', 9999))
        )
        for category in ordered_categories:
            category_id = category.get('id')
            if category_id is None:
                continue
            priority = category.get('priority', 99)
            slug = _slugify_file_part(category.get('name'))
            file_name = f"{int(priority):02d}_{slug}_{category_id}.json"
            file_map[category_id] = os.path.join(self.tools_split_dir, file_name)
        return file_map

    def _write_tools_aggregate_file(self, tools):
        wrap = _should_wrap_records(self.tools_file, 'tools', default_wrap=True)
        payload = {'tools': tools} if wrap else tools
        _write_json_file(self.tools_file, payload)

    def _save_tools_split_files(self, tools):
        os.makedirs(self.tools_split_dir, exist_ok=True)
        categories = self.load_categories()
        file_map = self._build_split_file_map(categories)

        grouped_tools = {}
        uncategorized_tools = []
        for tool in tools:
            category_id = tool.get('category_id')
            if category_id in file_map:
                grouped_tools.setdefault(category_id, []).append(tool)
            else:
                uncategorized_tools.append(tool)

        target_files = set()
        for category_id, file_path in file_map.items():
            category_tools = grouped_tools.get(category_id, [])
            if not category_tools:
                continue
            wrap = _should_wrap_records(file_path, 'tools', default_wrap=True)
            payload = {'tools': category_tools} if wrap else category_tools
            _write_json_file(file_path, payload)
            target_files.add(os.path.abspath(file_path))

        if uncategorized_tools:
            uncategorized_path = os.path.join(self.tools_split_dir, '99_uncategorized.json')
            wrap = _should_wrap_records(uncategorized_path, 'tools', default_wrap=True)
            payload = {'tools': uncategorized_tools} if wrap else uncategorized_tools
            _write_json_file(uncategorized_path, payload)
            target_files.add(os.path.abspath(uncategorized_path))

        for existing_path in _get_split_tool_files(self.tools_split_dir):
            if os.path.abspath(existing_path) not in target_files:
                try:
                    os.remove(existing_path)
                except OSError as e:
                    logger.error("删除旧拆分工具文件失败 %s: %s", existing_path, str(e))

    def load_categories(self):
        """加载所有分类和子分类数据，使用缓存机制减少重复加载"""
        try:
            if os.path.exists(self.categories_file) and os.path.getsize(self.categories_file) > 0:
                current_modified = os.path.getmtime(self.categories_file)
                if self._categories_cache is not None and self._last_categories_modified == current_modified:
                    return self._categories_cache
            else:
                self._set_categories_cache([], 0)
                return self._categories_cache

            os.makedirs(os.path.dirname(self.categories_file), exist_ok=True)

            try:
                categories = self._read_categories_from_disk()
            except ValueError as e:
                logger.error("分类数据格式错误，创建默认分类: %s", str(e))
                categories = self._create_default_categories()

            self._set_categories_cache(categories, current_modified)
            return self._categories_cache

        except (FileNotFoundError, PermissionError, IOError) as e:
            logger.error("加载分类数据失败: %s", str(e))
            categories = self._create_default_categories()
            self._set_categories_cache(categories, 0)
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
        return default_categories

    def save_categories(self, categories):
        """保存分类数据"""
        try:
            os.makedirs(os.path.dirname(self.categories_file), exist_ok=True)
            data_to_save = categories
            if _should_wrap_records(self.categories_file, 'categories', default_wrap=False):
                data_to_save = {'categories': categories}
            _write_json_file(self.categories_file, data_to_save)

            self._categories_cache = None
            self._last_categories_modified = 0
            self._invalidate_tools_cache()
            return True
        except (PermissionError, IOError, TypeError, ValueError) as e:
            logger.error("保存分类数据失败: %s", str(e))
            return False

    def load_tools(self, callback=None):
        """加载所有工具数据，如果文件不存在或为空则返回空列表，使用缓存机制减少重复加载"""
        if callback is None:
            try:
                return self._load_tools_sync()
            except ValueError as e:
                logger.error("工具数据格式错误，返回空列表: %s", str(e))
                self._set_tools_cache([], ())
                return self._tools_cache
            except (FileNotFoundError, PermissionError, IOError) as e:
                logger.error("加载工具数据失败: %s", str(e))
                return []
        else:
            try:
                from core.data_manager_qt import QThread, ToolsLoadWorker
            except ImportError as e:
                logger.warning("PyQt5 不可用，工具异步加载回退为同步模式: %s", str(e))
                try:
                    tools = self.load_tools()
                    self._invoke_tools_callback(callback, tools, None)
                except Exception as load_error:
                    self._on_tools_load_error(callback, load_error)
                return

            self._stop_tools_load_thread()
            self._tools_load_thread = QThread()
            self._tools_load_worker = ToolsLoadWorker(
                self.tools_file,
                self.tools_split_dir,
                self._tools_cache,
                self._last_tools_modified
            )
            self._tools_load_worker.moveToThread(self._tools_load_thread)
            self._tools_load_thread.started.connect(self._tools_load_worker.run)
            self._tools_load_worker.finished.connect(self._on_tools_loaded)
            self._tools_load_worker.finished.connect(callback)
            self._tools_load_worker.error.connect(lambda e: self._on_tools_load_error(callback, e))
            self._tools_load_worker.error.connect(self._tools_load_thread.quit)
            self._tools_load_worker.error.connect(self._tools_load_worker.deleteLater)
            self._tools_load_worker.finished.connect(self._tools_load_thread.quit)
            self._tools_load_worker.finished.connect(self._tools_load_worker.deleteLater)
            self._tools_load_thread.finished.connect(self._tools_load_thread.deleteLater)
            self._tools_load_thread.finished.connect(self._on_tools_load_thread_finished)
            self._tools_load_thread.start()

    def _on_tools_loaded(self, tools):
        """处理后台加载工具完成后的回调"""
        self._set_tools_cache(tools, _get_tools_state_token(self.tools_file, self.tools_split_dir))

    def _on_tools_load_error(self, callback, error):
        """处理后台加载工具异常，确保线程能正确退出。"""
        try:
            self._invoke_tools_callback(callback, [], error)
        except Exception as e:
            logger.error("工具加载错误回调执行失败: %s", str(e))

    def _on_tools_load_thread_finished(self):
        """后台加载线程结束后清理引用。"""
        self._tools_load_thread = None
        self._tools_load_worker = None

    def _stop_tools_load_thread(self):
        """停止正在运行的工具加载线程"""
        try:
            if self._tools_load_thread is not None:
                try:
                    if self._tools_load_thread.isRunning():
                        self._tools_load_thread.quit()
                        if not self._tools_load_thread.wait(3000):  # 等待最多3秒
                            logger.warning("工具加载线程没有在规定时间内退出，尝试terminate")
                            self._tools_load_thread.terminate()
                except RuntimeError as e:
                    if "wrapped C/C++ object" not in str(e):
                        logger.error("运行时错误停止工具加载线程: %s", str(e))
                        raise
                finally:
                    self._tools_load_thread = None
                    self._tools_load_worker = None
        except Exception as e:
            logger.error("停止工具加载线程失败: %s", str(e))
            # 无论如何都清理引用
            self._tools_load_thread = None
            self._tools_load_worker = None

    def save_tools(self, tools):
        """保存工具数据"""
        try:
            tools = self._strip_deprecated_tool_fields(tools)
            os.makedirs(os.path.dirname(self.tools_file), exist_ok=True)
            split_mode = os.path.isdir(self.tools_split_dir) or bool(_get_split_tool_files(self.tools_split_dir))
            if not split_mode and tools:
                categories = self.load_categories()
                valid_category_ids = {category.get('id') for category in categories if category.get('id') is not None}
                split_mode = any(tool.get('category_id') in valid_category_ids for tool in tools)
            if split_mode:
                self._save_tools_split_files(tools)
            self._write_tools_aggregate_file(tools)
            self._invalidate_tools_cache()
            return True
        except Exception as e:
            logger.error("保存工具数据失败: %s", str(e))
            return False

    def get_favorite_tools(self):
        tools = self.load_tools()
        return [tool for tool in tools if tool.get('is_favorite', False)]

    def get_tools_by_category(self, category_id, subcategory_id=None):
        cache_key = f"{category_id}_{subcategory_id}"
        if cache_key in self._category_tools_cache:
            return self._category_tools_cache[cache_key]

        tools = self.load_tools()
        filtered_tools = []
        for tool in tools:
            if tool.get('category_id') == category_id:
                if subcategory_id is None or tool.get('subcategory_id') == subcategory_id:
                    filtered_tools.append(tool)

        self._category_tools_cache[cache_key] = filtered_tools
        return filtered_tools

    def get_tool_by_id(self, tool_id):
        tools = self.load_tools()
        for tool in tools:
            if tool.get('id') == tool_id:
                return tool
        return None

    def add_tool(self, tool_data):
        tools = self.load_tools()
        new_id = max(tool['id'] for tool in tools) + 1 if tools else 1
        tool_data['id'] = new_id
        tool_data['usage_count'] = 0
        tool_data['last_used'] = None
        if 'is_favorite' not in tool_data:
            tool_data['is_favorite'] = False
        tools.append(tool_data)
        return self.save_tools(tools)

    def update_tool(self, tool_id, updated_data):
        tools = self.load_tools()
        for i, tool in enumerate(tools):
            if tool['id'] == tool_id:
                updated_data['id'] = tool_id
                if 'usage_count' not in updated_data:
                    updated_data['usage_count'] = tool.get('usage_count', 0)
                if 'last_used' not in updated_data:
                    updated_data['last_used'] = tool.get('last_used')
                tools[i] = updated_data
                return self.save_tools(tools)
        return False

    def delete_tool(self, tool_id):
        tools = self.load_tools()
        filtered_tools = [tool for tool in tools if tool['id'] != tool_id]
        if len(filtered_tools) < len(tools):
            return self.save_tools(filtered_tools)
        return False

    def toggle_favorite(self, tool_id):
        tools = self.load_tools()
        for tool in tools:
            if tool['id'] == tool_id:
                tool['is_favorite'] = not tool.get('is_favorite', False)
                return self.save_tools(tools)
        return False

    def update_tool_usage(self, tool_id):
        if tool_id is None:
            return False

        tool = self.get_tool_by_id(tool_id)
        if tool is None:
            return False

        last_used = datetime.now().isoformat() + 'Z'
        usage_count = int(tool.get('usage_count', 0) or 0) + 1
        tool['usage_count'] = usage_count
        tool['last_used'] = last_used
        self._store_pending_usage_update(tool_id, usage_count, last_used)
        return True

    def flush_pending_usage_updates(self):
        pending_updates = dict(self._pending_usage_updates)
        if not pending_updates:
            return True

        tools = self.load_tools()
        changed = self._apply_pending_usage_updates_to_tools(tools, pending_updates)

        if not changed:
            self._pending_usage_updates = {}
            return True

        if self.save_tools(tools):
            self._pending_usage_updates = {}
            return True
        return False

    def reorder_tools(self, ordered_tool_ids):
        if not ordered_tool_ids:
            return False
        tools = self.load_tools()
        if not tools:
            return False

        tool_map = {tool.get('id'): tool for tool in tools}
        ordered_tools = []
        seen_ids = set()
        for tool_id in ordered_tool_ids:
            if tool_id in tool_map and tool_id not in seen_ids:
                ordered_tools.append(tool_map[tool_id])
                seen_ids.add(tool_id)
        for tool in tools:
            tool_id = tool.get('id')
            if tool_id not in seen_ids:
                ordered_tools.append(tool)
        if len(ordered_tools) != len(tools):
            return False
        return self.save_tools(ordered_tools)

    def search_tools(self, keyword):
        tools = self.load_tools()
        keyword = keyword.lower()
        results = []
        for tool in tools:
            if (keyword in tool['name'].lower() or
                keyword in tool.get('description', '').lower()):
                results.append(tool)
        return results

    def add_category(self, category_data):
        categories = self.load_categories()
        new_id = max(cat['id'] for cat in categories) + 1 if categories else 1
        category_data['id'] = new_id
        if 'subcategories' not in category_data:
            category_data['subcategories'] = []
        categories.append(category_data)
        return self.save_categories(categories)

    def add_subcategory(self, parent_id, subcategory_data):
        categories = self.load_categories()
        existing_sub_ids = {
            sub.get('id')
            for category in categories
            for sub in category.get('subcategories', [])
            if sub.get('id') is not None
        }
        for category in categories:
            if category['id'] == parent_id:
                new_id = max(existing_sub_ids) + 1 if existing_sub_ids else parent_id * 100 + 1
                subcategory_data['id'] = new_id
                subcategory_data['parent_id'] = parent_id
                if 'subcategories' not in category:
                    category['subcategories'] = []
                category['subcategories'].append(subcategory_data)
                return self.save_categories(categories)

    def rename_category(self, category_id, new_name):
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
        categories = self.load_categories()
        tools = self.load_tools()
        for tool in tools:
            if tool.get('category_id') == category_id:
                return False, "该分类下存在工具，无法删除！"
        new_categories = [cat for cat in categories if cat['id'] != category_id]
        if len(new_categories) < len(categories):
            return self.save_categories(new_categories), ""
        return False, "分类不存在！"

    def get_all_categories(self):
        return self.load_categories()

    def get_subcategories_by_category(self, category_id):
        categories = self.load_categories()
        for category in categories:
            if category['id'] == category_id:
                return category.get('subcategories', [])
        return []

    def delete_subcategory(self, subcategory_id):
        categories = self.load_categories()
        tools = self.load_tools()
        for tool in tools:
            if tool.get('subcategory_id') == subcategory_id:
                return False, "该子分类下存在工具，无法删除！"
        for category in categories:
            if 'subcategories' in category:
                original_len = len(category['subcategories'])
                category['subcategories'] = [sub for sub in category['subcategories'] if sub['id'] != subcategory_id]
                if len(category['subcategories']) < original_len:
                    return self.save_categories(categories), ""
        return False, "子分类不存在！"

    def update_tool_background(self, tool_id, background_image_path):
        tools = self.load_tools()
        for tool in tools:
            if tool['id'] == tool_id:
                tool['background_image'] = background_image_path
                return self.save_tools(tools)
        return False

    def audit_tools_data(self):
        tools = self.load_tools()
        categories = self.load_categories()

        category_map = {}
        subcategory_map = {}
        for category in categories:
            category_id = category.get('id')
            if category_id is None:
                continue
            category_map[category_id] = category
            for subcategory in category.get('subcategories', []) or []:
                sub_id = subcategory.get('id')
                if sub_id is None:
                    continue
                subcategory_map[sub_id] = {
                    'parent_id': category_id,
                    'name': subcategory.get('name', ''),
                }

        issues = []
        duplicate_groups = {}

        for tool in tools:
            tool_id = tool.get('id')
            name = (tool.get('name') or '').strip() or '未命名工具'
            normalized_name = self._normalize_tool_name(name)
            duplicate_groups.setdefault(normalized_name, []).append(tool)

            category_id = tool.get('category_id')
            subcategory_id = tool.get('subcategory_id')
            category_name = category_map.get(category_id, {}).get('name', '未知分类')
            subcategory_name = subcategory_map.get(subcategory_id, {}).get('name', '') if subcategory_id is not None else ''

            issue_context = {
                'tool_id': tool_id,
                'tool_name': name,
                'category_id': category_id,
                'category_name': category_name,
                'subcategory_id': subcategory_id,
                'subcategory_name': subcategory_name,
            }

            icon_value = (tool.get('icon') or '').strip()
            if not icon_value:
                issues.append({
                    **issue_context,
                    'issue_type': 'missing_icon',
                    'title': '缺失图标',
                    'message': 'icon 为空，卡片会回退到默认图标。',
                })
            elif not self._is_icon_resolvable(icon_value):
                issues.append({
                    **issue_context,
                    'issue_type': 'missing_icon',
                    'title': '图标无效',
                    'message': f'图标资源无法解析：{icon_value}',
                })

            path_value = (tool.get('path') or '').strip()
            is_web_tool = bool(tool.get('is_web_tool', False))
            if is_web_tool:
                if not path_value:
                    issues.append({
                        **issue_context,
                        'issue_type': 'invalid_path',
                        'title': '网页地址缺失',
                        'message': '网页工具没有配置 URL。',
                    })
                elif not self._is_valid_web_url(path_value):
                    issues.append({
                        **issue_context,
                        'issue_type': 'invalid_path',
                        'title': '网页地址无效',
                        'message': f'网页工具 URL 不是 http/https：{path_value}',
                    })
            else:
                if not path_value:
                    issues.append({
                        **issue_context,
                        'issue_type': 'invalid_path',
                        'title': '本地路径缺失',
                        'message': '本地工具没有配置路径。',
                    })
                else:
                    full_path = path_value if os.path.isabs(path_value) else os.path.abspath(path_value)
                    if not os.path.exists(full_path):
                        issues.append({
                            **issue_context,
                            'issue_type': 'invalid_path',
                            'title': '本地路径失效',
                            'message': f'本地工具路径不存在：{path_value}',
                        })

                    working_directory = (tool.get('working_directory') or '').strip()
                    if working_directory and not os.path.isdir(working_directory):
                        issues.append({
                            **issue_context,
                            'issue_type': 'invalid_path',
                            'title': '工作目录失效',
                            'message': f'working_directory 不存在：{working_directory}',
                        })

            if category_id not in category_map:
                issues.append({
                    **issue_context,
                    'issue_type': 'invalid_category',
                    'title': '分类无效',
                    'message': f'category_id 不存在：{category_id}',
                })
            elif subcategory_id is not None:
                subcategory_info = subcategory_map.get(subcategory_id)
                if subcategory_info is None:
                    issues.append({
                        **issue_context,
                        'issue_type': 'invalid_category',
                        'title': '子分类无效',
                        'message': f'subcategory_id 不存在：{subcategory_id}',
                    })
                elif subcategory_info.get('parent_id') != category_id:
                    issues.append({
                        **issue_context,
                        'issue_type': 'invalid_category',
                        'title': '子分类无效',
                        'message': f'subcategory_id {subcategory_id} 不属于 category_id {category_id}',
                    })

            field_messages = []
            last_used = tool.get('last_used')
            if last_used not in (None, '') and not self._is_valid_iso_datetime(last_used):
                field_messages.append(f'last_used 格式异常: {last_used}')

            for bool_field in ('is_favorite', 'is_web_tool', 'run_in_terminal'):
                if bool_field in tool and not isinstance(tool.get(bool_field), bool):
                    field_messages.append(f'{bool_field} 不是布尔值')

            if field_messages:
                issues.append({
                    **issue_context,
                    'issue_type': 'field_inconsistency',
                    'title': '字段格式不一致',
                    'message': '；'.join(field_messages),
                })

        for normalized_name, grouped_tools in duplicate_groups.items():
            if not normalized_name or len(grouped_tools) < 2:
                continue
            duplicate_ids = [item.get('id') for item in grouped_tools]
            duplicate_names = [item.get('name') or '未命名工具' for item in grouped_tools]
            for tool in grouped_tools:
                category_id = tool.get('category_id')
                subcategory_id = tool.get('subcategory_id')
                issues.append({
                    'tool_id': tool.get('id'),
                    'tool_name': tool.get('name') or '未命名工具',
                    'category_id': category_id,
                    'category_name': category_map.get(category_id, {}).get('name', '未知分类'),
                    'subcategory_id': subcategory_id,
                    'subcategory_name': subcategory_map.get(subcategory_id, {}).get('name', '') if subcategory_id is not None else '',
                    'issue_type': 'duplicate_name',
                    'title': '名称重复',
                    'message': f'与其他工具重名，重复 ID: {duplicate_ids}，名称: {duplicate_names}',
                })

        issue_priority = {
            'missing_icon': 0,
            'invalid_path': 1,
            'duplicate_name': 2,
            'invalid_category': 3,
            'field_inconsistency': 4,
        }
        issues.sort(key=lambda item: (
            issue_priority.get(item.get('issue_type'), 99),
            str(item.get('tool_name') or ''),
            item.get('tool_id') or 0,
        ))

        issue_counts = {}
        for issue in issues:
            issue_type = issue.get('issue_type', 'unknown')
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1

        return {
            'issues': issues,
            'counts': issue_counts,
            'total_tools': len(tools),
            'total_issues': len(issues),
        }

    def _normalize_tool_name(self, value):
        text = str(value or '').strip().casefold()
        text = re.sub(r'\s+', ' ', text)
        return text

    def _is_valid_web_url(self, value):
        text = str(value or '').strip()
        return text.startswith('http://') or text.startswith('https://')

    def _is_icon_resolvable(self, icon_value):
        try:
            icon_text = str(icon_value or '').strip()
            if not icon_text:
                return False
            return resolve_icon_path_value(icon_text) is not None
        except Exception:
            return False

    def _is_valid_iso_datetime(self, value):
        try:
            text = str(value or '').strip()
            if not text:
                return False
            if text.endswith('Z'):
                text = text[:-1] + '+00:00'
            datetime.fromisoformat(text)
            return True
        except Exception:
            return False

    def shutdown(self):
        try:
            self.flush_pending_usage_updates()
        except Exception as e:
            logger.error("写回工具使用统计失败: %s", str(e))
        try:
            self._stop_tools_load_thread()
        except Exception as e:
            logger.error("清理资源失败: %s", str(e))

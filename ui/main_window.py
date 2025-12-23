import difflib
import os
import sys
import webbrowser
import subprocess
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                            QToolBar, QAction, QMessageBox, QInputDialog, QApplication, 
                            QLineEdit, QActionGroup, QMenu, QToolButton, QStatusBar, 
                            QLabel)
from PyQt5.QtCore import Qt, QSize, QSettings

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

# 导入自定义模块
from core.data_manager import DataManager
from core.image_manager import ImageManager
from core.logger import logger
from core.style_manager import ThemeManager
from ui.category_view import CategoryView
from ui.subcategory_view import SubcategoryView
from ui.tool_model_view import ToolCardContainer
from ui.image_selector import ImageSelectorDialog
from ui.tool_config_dialog import ToolConfigDialog

class MainWindow(QMainWindow):
    def __init__(self, config_dir=None):
        super().__init__()
        # 设置应用程序信息
        self.app_name = "子非鱼工具箱"
        self.version = "1.0.0"
        
        # 初始化管理器
        self.data_manager = DataManager(config_dir=config_dir)
        self.image_manager = ImageManager(config_dir=config_dir)
        
        # 注意：不要在应用启动时强制创建默认背景图片（会增加启动延迟）
        # 默认背景将延迟在首次需要图片目录或列出图片时创建，以加快启动速度。
        
        # 当前选中的分类
        self.current_category = None
        
        # 是否在收藏页面
        self.is_in_favorites = False
        
        # 配置目录（用于保存 settings.ini 等）
        self.config_dir = config_dir or os.path.abspath('.')

        # 使用 config_dir 下的 settings.ini 持久化用户设置（如主题）
        settings_file = os.path.join(self.config_dir, "settings.ini")
        # QSettings 将在 settings_file 路径读写 INI 格式的文件
        self.settings = QSettings(settings_file, QSettings.IniFormat)

        # 当前主题（默认使用黑绿色主题），尝试从设置中加载
        self.current_theme = str(self.settings.value("theme", "dark_green"))
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle(f"{self.app_name} - v{self.version}")
        
        # 获取屏幕尺寸并设置窗口为屏幕的80%大小并居中显示
        screen_geometry = QApplication.desktop().screenGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # 计算窗口大小为屏幕的80%
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # 计算窗口居中的位置
        x = int((screen_width - window_width) / 2)
        y = int((screen_height - window_height) / 2)
        
        # 设置窗口几何形状
        self.setGeometry(x, y, window_width, window_height)
        
        # 设置最小窗口大小
        self.setMinimumSize(900, 600)
        
        # 创建主组件
        self.create_actions()
        self.create_menus()
        self.create_toolbars()
        self.create_statusbar()
        self.create_main_widget()
        
        # 应用样式并把主题传播给子组件（确保重启后 UI 组件使用持久化主题）
        self.apply_styles()
        # 优化：延迟主题刷新，避免启动时阻塞
        # 在初始化完成后，确保所有子组件也使用当前主题
        # 例如 CategoryView、SubcategoryView、ToolCardContainer 等
        from PyQt5.QtCore import QTimer
        def delayed_theme_refresh():
            try:
                self.refresh_ui_with_theme()
            except (ValueError, AttributeError) as e:
                # 忽略刷新失败，以避免启动时的非关键异常阻止应用
                logger.warning("主题刷新失败: %s", str(e))
        QTimer.singleShot(100, delayed_theme_refresh)
    
    def create_actions(self):
        """创建动作"""
        # 文件操作
        self.new_tool_action = QAction("新建工具", self)
        self.new_tool_action.setShortcut("Ctrl+N")
        self.new_tool_action.triggered.connect(self.on_new_tool)
        
        self.exit_action = QAction("退出", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        
        # 分类操作
        self.new_category_action = QAction("新建分类", self)
        self.new_category_action.triggered.connect(self.on_new_category)
        
        self.new_subcategory_action = QAction("新建子分类", self)
        self.new_subcategory_action.triggered.connect(self.on_new_subcategory)
        
        self.delete_category_action = QAction("删除分类", self)
        self.delete_category_action.triggered.connect(self.on_delete_category)
        
        self.delete_subcategory_action = QAction("删除子分类", self)
        self.delete_subcategory_action.triggered.connect(self.on_delete_subcategory)
        
        # 视图操作
        self.refresh_action = QAction("刷新", self)
        self.refresh_action.setShortcut("F5")
        self.refresh_action.triggered.connect(self.refresh_all)

        # 收藏操作
        self.favorites_action = QAction("收藏", self)
        self.favorites_action.triggered.connect(self.on_show_favorites)

        # 帮助
        self.about_action = QAction("关于", self)
        self.about_action.triggered.connect(self.on_about)
        
        # 主题切换动作
        self.dark_green_theme_action = QAction("黑绿色主题", self, checkable=True)
        self.dark_green_theme_action.triggered.connect(lambda: self.switch_theme("dark_green"))
        
        self.blue_white_theme_action = QAction("蓝白色主题", self, checkable=True)
        self.blue_white_theme_action.triggered.connect(lambda: self.switch_theme("blue_white"))
        
        # 创建主题动作组，确保只有一个主题被选中
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.addAction(self.dark_green_theme_action)
        self.theme_action_group.addAction(self.blue_white_theme_action)

        # 根据当前主题状态设置已选中的动作
        # 注意：在初始化 UI 时，self.current_theme 可能已经从 settings 加载
        self.dark_green_theme_action.setChecked(self.current_theme == "dark_green")
        self.blue_white_theme_action.setChecked(self.current_theme == "blue_white")
    
    def create_menus(self):
        """管理应用程序的菜单
        当前实现：隐藏顶部菜单栏，因为应用程序主要通过工具栏进行操作
        """
        # 隐藏顶部菜单栏
        self.menuBar().setVisible(False)
    
    def create_toolbars(self):
        """创建工具栏"""
        # 主工具栏
        main_toolbar = QToolBar("主工具栏", self)
        main_toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(main_toolbar)
        
        # 添加工具按钮
        main_toolbar.addAction(self.new_tool_action)
        main_toolbar.addSeparator()
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索工具...")
        self.search_input.setMaximumWidth(200)
        self.search_input.textChanged.connect(self.on_search)
        main_toolbar.addWidget(QLabel("搜索: "))
        main_toolbar.addWidget(self.search_input)

        # 右侧填充
        main_toolbar.addSeparator()
        main_toolbar.addWidget(QWidget())
        
        # 主题按钮
        main_toolbar.addSeparator()
        theme_button = QToolButton()
        theme_button.setText("主题")
        theme_button.setPopupMode(QToolButton.InstantPopup)
        
        # 创建主题菜单
        theme_menu = QMenu(theme_button)
        theme_menu.addAction(self.dark_green_theme_action)
        theme_menu.addAction(self.blue_white_theme_action)
        
        theme_button.setMenu(theme_menu)
        main_toolbar.addWidget(theme_button)
        
        # 刷新按钮
        main_toolbar.addAction(self.refresh_action)
        
        # 收藏按钮
        main_toolbar.addSeparator()
        self.favorites_button = QToolButton()
        self.favorites_button.setText("收藏")
        self.favorites_button.clicked.connect(self.on_show_favorites)
        
        main_toolbar.addWidget(self.favorites_button)
        
        # 关于按钮
        main_toolbar.addSeparator()
        about_button = QToolButton()
        about_button.setText("关于")
        about_button.clicked.connect(self.on_about)
        main_toolbar.addWidget(about_button)

    def create_statusbar(self):
        """创建状态栏"""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        # 显示工具数量
        self.tool_count_label = QLabel("工具数量: 0")
        self.statusBar.addPermanentWidget(self.tool_count_label)
        
        # 显示状态信息
        self.statusBar.showMessage("就绪")
    
    def create_main_widget(self):
        """创建主窗口组件"""
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 分割器
        self.splitter = QSplitter(Qt.Horizontal)
        
        # 左侧一级分类视图
        self.category_view = CategoryView(self.data_manager)
        self.category_view.category_selected.connect(self.on_category_selected)
        # 连接右键菜单信号
        self.category_view.new_category_requested.connect(self.on_new_category)
        self.category_view.new_subcategory_requested.connect(self.on_new_subcategory)
        self.category_view.delete_category_requested.connect(self.on_delete_category)
        self.splitter.addWidget(self.category_view)
        
        # 中间二级分类视图
        self.subcategory_view = SubcategoryView(self.data_manager)
        self.subcategory_view.subcategory_selected.connect(self.on_subcategory_selected)
        # 连接右键菜单信号
        self.subcategory_view.new_subcategory_requested.connect(self.on_new_subcategory)
        self.subcategory_view.delete_subcategory_requested.connect(self.on_delete_subcategory)
        self.splitter.addWidget(self.subcategory_view)
        
        # 右侧工具卡片容器
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 顶部信息栏
        info_bar = QWidget()
        info_layout = QHBoxLayout(info_bar)
        
        self.category_info_label = QLabel("常用工具")
        
        info_layout.addWidget(self.category_info_label)
        info_layout.addStretch()
        
        right_layout.addWidget(info_bar)
        
        # 右侧工具卡片容器
        self.tool_container = ToolCardContainer()
        self.tool_container.deleted.connect(self.on_delete_tool)
        self.tool_container.edit_requested.connect(self.on_edit_tool)
        self.tool_container.new_tool_requested.connect(self.on_new_tool)
        self.tool_container.run_tool.connect(self.on_tool_run)
        self.tool_container.toggle_favorite.connect(self.on_toggle_favorite)
        
        right_layout.addWidget(self.tool_container, 1)
        
        # 初始化时先显示空的工具容器，然后在后台加载工具
        try:
            # 先显示空的工具列表
            self.tool_container.display_tools([])
            # 更新工具数量为0
            self.refresh_tool_count()
            
            # 定义异步加载完成后的回调函数
            def on_tools_loaded(tools, error=None):
                if error:
                    logger.warning("初始加载工具失败: %s", str(error))
                    return
                try:
                    # 默认显示收藏页面
                    self.on_show_favorites()
                except Exception as e:
                    logger.warning("显示收藏页面失败: %s", str(e))
            
            # 使用异步加载工具，避免启动时阻塞
            self.data_manager.load_tools(callback=on_tools_loaded)
        except Exception as e:
            logger.warning("初始加载工具失败: %s", str(e))

        self.splitter.addWidget(right_widget)
        
        # 设置初始大小和比例
        # 三列比例：一级分类占25%，二级分类占20%，工具区占55%
        self.splitter.setSizes([300, 240, 660])
        
        # 设置拉伸因子，确保各部分按比例缩放
        self.splitter.setStretchFactor(0, 1)  # 一级分类拉伸因子1
        self.splitter.setStretchFactor(1, 1)  # 二级分类拉伸因子1
        self.splitter.setStretchFactor(2, 3)  # 工具区拉伸因子3

        # 设置最小宽度
        self.category_view.setMinimumWidth(200)
        self.subcategory_view.setMinimumWidth(180)
        right_widget.setMinimumWidth(400)
        
        main_layout.addWidget(self.splitter, 1)
    
    def apply_styles(self):
        """应用样式 - 支持多种主题"""
        theme_manager = ThemeManager()
        style = theme_manager.get_theme_style(self.current_theme)
        self.setStyleSheet(style)
        
        # 确保分类视图和子分类视图也应用当前主题
        if hasattr(self, 'category_view'):
            self.category_view.set_theme(self.current_theme)
        if hasattr(self, 'subcategory_view'):
            self.subcategory_view.set_theme(self.current_theme)
    
    def on_category_selected(self, category_id):
        """处理一级分类选择"""
        self.current_category = category_id
        
        # 重新显示分类视图
        self.category_view.show()
        self.subcategory_view.show()
        
        # 恢复分割器大小
        self.splitter.setSizes([400, 300, 640])
        
        # 加载并显示该分类下的子分类
        self.subcategory_view.load_subcategories(category_id)
        
        # 更新分类信息标签
        categories = self.data_manager.load_categories()
        category_name = "所有工具"
        for category in categories:
            if isinstance(category, dict) and category.get('id') == category_id:
                category_name = category.get('name', "未知分类")
                break
        
        self.category_info_label.setText(category_name)
        
        # 加载该分类下的所有工具（不区分子分类）
        tools = self.data_manager.get_tools_by_category(category_id)
        self.tool_container.display_tools(tools)
        self.refresh_tool_count()
    
    def on_subcategory_selected(self, category_id, subcategory_id):
        """处理二级分类选择"""
        # 重新显示分类视图
        self.category_view.show()
        self.subcategory_view.show()
        
        # 恢复分割器大小
        self.splitter.setSizes([400, 300, 640])
        
        # 更新分类信息标签
        categories = self.data_manager.load_categories()
        category_name = "所有工具"
        subcategory_name = ""
        
        # 查找当前分类和子分类
        for category in categories:
            if isinstance(category, dict) and category.get('id') == category_id:
                category_name = category.get('name', "未知分类")
                
                # 如果有子分类ID，查找子分类名称
                if subcategory_id is not None and 'subcategories' in category:
                    for subcategory in category['subcategories']:
                        if isinstance(subcategory, dict) and subcategory.get('id') == subcategory_id:
                            subcategory_name = f" - {subcategory.get('name', '未知子分类')}"
                            break
                break
        
        self.category_info_label.setText(category_name + subcategory_name)
        
        # 加载并显示该子分类下的工具
        tools = self.data_manager.get_tools_by_category(category_id, subcategory_id)
        self.tool_container.display_tools(tools)
        self.refresh_tool_count()
    
    def on_new_tool(self):
        """处理新建工具"""
        # 获取所有分类
        categories_data = self.data_manager.load_categories()
        if not categories_data:
            QMessageBox.warning(self, "警告", "请先创建分类！")
            return
        
        # 格式化分类数据
        formatted_categories = []
        for cat in categories_data:
            if isinstance(cat, dict):
                if "subcategories" not in cat:
                    cat["subcategories"] = []
                formatted_categories.append(cat)
        
        # 打开工具配置对话框
        dialog = ToolConfigDialog(categories=formatted_categories, parent=self, theme_name=self.current_theme)
        if dialog.exec_():
            # 获取工具数据
            tool_data = dialog.get_tool_data()
            
            # 保存工具
            new_tool = self.data_manager.add_tool(tool_data)
            if new_tool:
                QMessageBox.information(self, "成功", "工具创建成功！")
                # 刷新当前视图
                self.refresh_current_view()
            else:
                QMessageBox.warning(self, "失败", "工具创建失败！")
    
    def on_edit_tool(self, tool_data):
        """处理编辑工具"""
        # 获取工具ID
        tool_id = tool_data['id']
        # 获取最新工具信息
        tool = self.data_manager.get_tool_by_id(tool_id)
        if not tool:
            return
        
        # 获取所有分类
        categories = self.data_manager.get_all_categories()
        
        # 打开工具配置对话框
        dialog = ToolConfigDialog(tool_data=tool, categories=categories, parent=self, theme_name=self.current_theme)
        if dialog.exec_():
            # 获取更新后的工具数据
            updated_tool = dialog.get_tool_data()
            
            # 更新工具
            if self.data_manager.update_tool(updated_tool['id'], updated_tool):
                QMessageBox.information(self, "成功", "工具更新成功！")
                self.refresh_current_view()
            else:
                QMessageBox.warning(self, "失败", "工具更新失败！")

    def _is_windows_cui_exe(self, path: str) -> bool:
        """
        检测Windows可执行文件是否为命令行界面(CUI)应用程序
        
        Args:
            path: Windows可执行文件的路径
            
        Returns:
            bool: 如果是命令行应用程序返回True，否则返回False
        """
        try:
            if not path.lower().endswith('.exe'):
                return False
                
            with open(path, 'rb') as f:
                # 读取DOS头
                f.seek(0x3c, os.SEEK_SET)
                pe_header_offset = int.from_bytes(f.read(4), byteorder='little')
                
                # 检查PE签名
                f.seek(pe_header_offset, os.SEEK_SET)
                pe_signature = f.read(4)
                if pe_signature != b'PE\x00\x00':
                    return False
                
                # 读取文件头
                file_header_size = 20  # IMAGE_FILE_HEADER大小
                f.seek(pe_header_offset + 4, os.SEEK_SET)
                file_header = f.read(file_header_size)
                
                # 获取可选头大小
                optional_header_size = int.from_bytes(file_header[16:18], byteorder='little')
                
                # 读取可选头
                f.seek(pe_header_offset + 24, os.SEEK_SET)  # 4(PE签名) + 20(文件头) = 24
                optional_header = f.read(optional_header_size)
                
                # 检查是否为PE32或PE32+格式
                magic = int.from_bytes(optional_header[0:2], byteorder='little')
                if magic == 0x10b:  # PE32
                    subsystem_offset = 0x5c
                elif magic == 0x20b:  # PE32+
                    subsystem_offset = 0x68
                else:
                    return False
                
                # 获取子系统类型
                subsystem = int.from_bytes(optional_header[subsystem_offset:subsystem_offset+2], byteorder='little')
                
                # 0x3 = IMAGE_SUBSYSTEM_WINDOWS_CUI (命令行界面)
                return subsystem == 0x3
                
        except (IOError, OSError, IndexError, ValueError):
            # 如果解析失败，默认返回False（视为GUI应用）
            return False
        return False

    def on_tool_run(self, tool_data):
        """处理运行工具的行为"""
        tool_id = tool_data.get('id')
        tool_name = tool_data.get('name', '未知工具')
        is_web = tool_data.get('is_web_tool', False)
        path = (tool_data.get('path') or '').strip()
        working_directory = tool_data.get('working_directory', '')
        run_in_terminal = tool_data.get('run_in_terminal', False)

        started_ok = False

        if path.startswith('http://') or path.startswith('https://'):
            try:
                logger.info("启动网页工具: %s, URL: %s", tool_name, path)
                webbrowser.open(path)
                started_ok = True
            except KeyboardInterrupt as e:
                logger.warning("网页工具打开被用户中断: %s", tool_name)
                QMessageBox.warning(self, "运行中断", "网页工具打开已被用户中断")
                started_ok = False
            except webbrowser.Error as e:
                logger.error("打开网页工具失败: %s, 错误: %s", tool_name, str(e))
                QMessageBox.warning(self, "运行失败", f"打开网页工具失败: {e}")
                started_ok = False
        else:
            started_ok = self._open_local(path, working_directory, run_in_terminal, tool_name, is_web, tool_data)

        # Update usage stats
        if started_ok and tool_id:
            try:
                logger.info("更新工具使用统计: %s (ID: %s)", tool_name, tool_id)
                self.data_manager.update_tool_usage(tool_id)
            except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
                logger.warning("更新工具使用统计失败: %s", str(e))

        self.refresh_current_view()

    def _open_local(self, path: str, working_dir: str = None, run_in_terminal: bool = False, tool_name: str = '未知工具', is_web: bool = False, tool_data: dict = None) -> bool:
        try:
            if not path:
                raise ValueError("工具路径为空")

            # 确保路径是绝对路径
            if not os.path.isabs(path):
                path = os.path.abspath(path)
                logger.info("将相对路径转换为绝对路径: %s", path)
                
            # 检查路径是否存在
            if not os.path.exists(path):
                raise FileNotFoundError(f"路径不存在: {path}")

            logger.info("启动本地工具: %s, 路径: %s", tool_name, path)
            
            # 如果是目录，使用操作系统默认方式打开
            if os.path.isdir(path):
                logger.info("工具路径是目录，使用系统默认方式打开")
                if sys.platform.startswith('win'):
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])
            else:
                # 是文件，使用工作目录运行
                default_working_dir = os.path.dirname(path)
                actual_working_dir = working_dir or default_working_dir
                logger.info("工具工作目录: %s", actual_working_dir)

                if sys.platform.startswith('win'):
                    # Windows: 根据run_in_terminal属性、文件类型或自动检测决定是否在终端中运行
                    should_run_in_terminal = run_in_terminal
                    
                    # 如果用户没有明确设置，自动检测
                    if not should_run_in_terminal:
                        if path.lower().endswith('.cmd') or path.lower().endswith('.bat') or path.lower().endswith('.py'):
                            should_run_in_terminal = True
                        elif path.lower().endswith('.exe'):
                            # 自动检测EXE是否为命令行界面
                            should_run_in_terminal = self._is_windows_cui_exe(path)
                    
                    if should_run_in_terminal:
                        subprocess.Popen(
                            ['cmd.exe', '/c', 'start', path], 
                            cwd=actual_working_dir,
                            shell=True
                        )
                    else:
                        subprocess.Popen(
                            [path], 
                            cwd=actual_working_dir,
                            shell=True
                        )
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', '-a', 'Terminal', path], cwd=actual_working_dir)
                else:
                    subprocess.Popen(['x-terminal-emulator', '-e', path], cwd=actual_working_dir)

            return True
        except KeyboardInterrupt as e:
            logger.warning("工具运行被用户中断: %s", tool_name)
            QMessageBox.warning(self, "运行中断", "工具运行已被用户中断")
            return False
        except FileNotFoundError as e:
            logger.error("启动工具失败: %s, 错误: %s", tool_name, str(e))
            config_info = f"工具名称: {tool_name}\n工具路径: {path}\n工作目录: {working_dir or '默认（工具所在目录）'}\n工具类型: {'本地工具' if not is_web else '网页工具'}\n优先级: {tool_data.get('priority', 0) if tool_data else 0}"
            QMessageBox.warning(self, "工具不存在", f"无法找到工具路径:\n{path}\n\n工具配置信息:\n{config_info}")
            return False
        except (PermissionError, subprocess.SubprocessError, ValueError) as e:
            logger.error("启动工具失败: %s, 错误: %s", tool_name, str(e))
            QMessageBox.warning(self, "运行失败", f"启动工具失败: {e}")
            return False

    def on_toggle_favorite(self, tool_id):
        """切换收藏状态"""
        if tool_id:
            self.data_manager.toggle_favorite(tool_id)
            self.refresh_current_view()
    
    def on_edit_background(self, tool_data):
        """处理编辑背景图片"""
        tool_id = tool_data['id']
        tool = self.data_manager.get_tool_by_id(tool_id)
        if not tool:
            return
        
        dialog = ImageSelectorDialog(self.image_manager, tool.get("background_image", ""), self)
        if dialog.exec_():
            selected_image = dialog.get_selected_image()
            tool["background_image"] = selected_image
            if self.data_manager.update_tool(tool_id, tool):
                self.refresh_current_view()
    
    def on_delete_tool(self, tool_id):
        """处理删除工具"""
        if self.data_manager.delete_tool(tool_id):
            QMessageBox.information(self, "成功", "工具删除成功！")
            self.refresh_current_view()
        else:
            QMessageBox.warning(self, "失败", "工具删除失败！")
    
    def on_new_category(self):
        """处理新建分类"""
        dialog = QInputDialog(self)
        dialog.setWindowTitle("新建分类")
        dialog.setLabelText("请输入分类名称:")
        
        if self.current_theme == "dark_green":
            dialog.setStyleSheet(self._get_dialog_style_fragment())
        
        ok = dialog.exec_()
        category_name = dialog.textValue()
        
        if ok and category_name:
            category = {
                "name": category_name,
                "icon": "default_icon",
                "subcategories": []
            }
            if self.data_manager.add_category(category):
                QMessageBox.information(self, "成功", "分类创建成功！")
                self.category_view.refresh()
            else:
                QMessageBox.warning(self, "失败", "分类创建失败！")
    
    def on_new_subcategory(self):
        """处理新建子分类"""
        current_category = self.category_view.current_category
        if not current_category:
            QMessageBox.warning(self, "警告", "请先选择一个主分类！")
            return
        
        dialog = QInputDialog(self)
        dialog.setWindowTitle("新建子分类")
        dialog.setLabelText("请输入子分类名称:")
        
        if self.current_theme == "dark_green":
            dialog.setStyleSheet(self._get_dialog_style_fragment())
        
        ok = dialog.exec_()
        subcategory_name = dialog.textValue()
        
        if ok and subcategory_name:
            subcategory = {"name": subcategory_name}
            if self.data_manager.add_subcategory(current_category, subcategory):
                QMessageBox.information(self, "成功", "子分类创建成功！")
                self.category_view.refresh()
            else:
                QMessageBox.warning(self, "失败", "子分类创建失败！")
    
    def on_delete_category(self):
        """处理删除分类"""
        current_category = self.category_view.current_category
        current_subcategory = self.subcategory_view.current_subcategory
        
        if current_subcategory:
            QMessageBox.warning(self, "警告", "请先取消选择子分类，然后再删除主分类！")
            return
        
        if not current_category:
            QMessageBox.warning(self, "警告", "请先选择一个要删除的主分类！")
            return
        
        reply = self._themed_question('确认删除',
                                    f"确定要删除选中的分类吗？\n删除前请确保该分类下没有工具和子分类。",
                                    default=QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success, message = self.data_manager.delete_category(current_category)
            if success:
                QMessageBox.information(self, "成功", "分类删除成功！")
                self.category_view.refresh()
                self.current_category = None
                self.tool_container.display_tools([])
            else:
                QMessageBox.warning(self, "失败", message)
    
    def on_delete_subcategory(self):
        """处理删除子分类"""
        current_subcategory = self.subcategory_view.current_subcategory
        
        if not current_subcategory:
            QMessageBox.warning(self, "警告", "请先选择一个要删除的子分类！")
            return
        
        reply = self._themed_question("确认删除", 
                                    f"确定要删除选中的子分类吗？\n删除前请确保该子分类下没有工具。",
                                    default=QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            success, message = self.data_manager.delete_subcategory(current_subcategory)
            if success:
                QMessageBox.information(self, "成功", "子分类删除成功！")
                self.category_view.refresh()
                self.subcategory_view.current_subcategory = None
                self.on_category_selected(self.category_view.current_category)
            else:
                QMessageBox.warning(self, "失败", message)
    
    def on_search(self, text):
        """处理搜索"""
        tools = self.data_manager.load_tools()
        q = text.strip().lower()

        if not q:
            self.refresh_current_view()
            return

        filtered_tools = []
        FUZZY_THRESHOLD = 0.6

        for tool in tools:
            name = (tool.get('name') or '').lower()
            desc = (tool.get('description') or '').lower()
            tags = [t.lower() for t in tool.get('tags', [])]

            if q in name or q in desc or any(q in t for t in tags):
                filtered_tools.append(tool)
                continue

            if len(q) <= 2:
                continue

            score_name = difflib.SequenceMatcher(None, q, name).ratio()
            score_desc = difflib.SequenceMatcher(None, q, desc).ratio()
            score_tags = max((difflib.SequenceMatcher(None, q, t).ratio() for t in tags), default=0.0)
            max_score = max(score_name, score_desc, score_tags)

            if max_score >= FUZZY_THRESHOLD:
                filtered_tools.append(tool)

        self.tool_container.display_tools(filtered_tools)
        self.refresh_tool_count()

    def on_show_favorites(self):
        """显示收藏页面或从收藏页面返回"""
        if self.is_in_favorites:
            # 当前在收藏页面，点击返回
            self.is_in_favorites = False
            # 显示左侧分类视图
            self.category_view.show()
            self.subcategory_view.show()
            # 恢复分割器大小
            self.splitter.setSizes([300, 240, 660])
            # 更新收藏按钮文本
            self.favorites_button.setText("收藏")
            # 刷新当前视图
            self.refresh_current_view()
        else:
            # 当前不在收藏页面，点击进入收藏页面
            self.is_in_favorites = True
            self.category_info_label.setText("我的收藏")
            favorites = self.data_manager.get_favorite_tools()
            self.tool_container.display_tools(favorites)
            self.refresh_tool_count()
            
            # 隐藏左侧分类视图，增加收藏区域的显示空间
            self.category_view.hide()
            self.subcategory_view.hide()
            
            # 调整分割器大小，只显示右侧工具卡片区域
            self.splitter.setSizes([0, 0, 1200])
            # 更新收藏按钮文本
            self.favorites_button.setText("返回")
    
    def on_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于子非鱼工具箱", f"子非鱼工具箱 v{self.version}\n\n一个简单易用的本地工具管理平台")
    
    def refresh_tool_count(self):
        """刷新工具数量显示"""
        count = self.tool_container.get_tool_count()
        self.tool_count_label.setText(f"工具数量: {count}")
    
    def refresh_current_view(self):
        """刷新当前视图"""
        if self.is_in_favorites:
            self.on_show_favorites()
        else:
            current_category = self.category_view.current_category
            current_subcategory = self.subcategory_view.current_subcategory
            
            if current_subcategory:
                self.on_subcategory_selected(current_category, current_subcategory)
            elif current_category:
                self.on_category_selected(current_category)
            else:
                # 没有选择任何分类，显示常用工具
                common_tools = self.data_manager.get_common_tools()
                self.tool_container.display_tools(common_tools)
                self.category_info_label.setText("常用工具")
                self.refresh_tool_count()
    
    def refresh_all(self):
        """刷新所有视图"""
        self.category_view.refresh()
        # 刷新子分类视图，根据当前选中的分类重新加载子分类
        current_category = self.category_view.current_category
        if current_category:
            self.subcategory_view.load_subcategories(current_category)
        self.refresh_current_view()
    
    def switch_theme(self, theme_name):
        """切换主题"""
        self.current_theme = theme_name
        self.settings.setValue("theme", theme_name)
        self.apply_styles()
        # 刷新UI组件主题
        self.refresh_ui_with_theme()
    
    def refresh_ui_with_theme(self):
        """刷新UI组件主题"""
        self.tool_container.set_theme(self.current_theme)
    
    def _get_dialog_style_fragment(self):
        """获取对话框样式片段，用于QInputDialog等"""
        return ""
    
    def _themed_question(self, title, text, default=QMessageBox.No):
        """显示带主题样式的确认对话框"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(default)
        
        # 设置暗色主题样式
        if self.current_theme == "dark_green":
            dialog.setStyleSheet(
                "QMessageBox { background-color: #1a1a1a; color: #ffffff; }" +
                "QPushButton { background-color: #2d2d2d; color: #ffffff; border: 1px solid #00ff00; }" +
                "QPushButton:hover { background-color: #3d3d3d; }" +
                "QPushButton:default { background-color: #006400; }"
            )
        
        return dialog.exec_()

# 运行主窗口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
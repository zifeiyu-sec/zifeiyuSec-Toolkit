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
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.data_manager import DataManager
from core.image_manager import ImageManager
from core.logger import logger
from ui.category_view import CategoryView
from ui.subcategory_view import SubcategoryView

from ui.tool_model_view import ToolCardContainer
from ui.image_selector import ImageSelectorDialog
from ui.tool_config_dialog import ToolConfigDialog

class PentestToolManager(QMainWindow):
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
        if self.current_theme == "blue_white":
            central_widget.setStyleSheet("background-color: #f0f4f8;")
        else:
            central_widget.setStyleSheet("background-color: #1a1a1a;")
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
        if self.current_theme == "blue_white":
            right_widget.setStyleSheet("background-color: #ffffff;")
        else:
            right_widget.setStyleSheet("background-color: #1a1a1a;")
        right_layout = QVBoxLayout(right_widget)
        
        # 顶部信息栏
        info_bar = QWidget()
        if self.current_theme == "blue_white":
            info_bar.setStyleSheet("background-color: #e6f0ff; border-bottom: 2px solid #4287f5;")
        else:
            info_bar.setStyleSheet("background-color: #000000; border-bottom: 2px solid #00ff00;")
        info_layout = QHBoxLayout(info_bar)
        
        self.category_info_label = QLabel("常用工具")
        if self.current_theme == "blue_white":
            self.category_info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4287f5;")
        else:
            self.category_info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #90ee90;")
        
        info_layout.addWidget(self.category_info_label)
        info_layout.addStretch()
        
        # 添加视图切换按钮到信息栏（左侧信息栏顶部已添加）。工具切换会影响 tool_container 的 display
        
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
                    # 保存工具数据到缓存，以便其他方法可以直接使用
                    # self._all_tools_cache = tools  # 移除：不再在app层缓存，完全依赖data_manager

                    # 显示常用工具
                    common_tools = self.data_manager.get_common_tools()
                    self.tool_container.display_tools(common_tools)
                    # 更新工具数量
                    self.refresh_tool_count()
                except Exception as e:
                    logger.warning("显示工具失败: %s", str(e))
            
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

        # 设置最小宽度，避免被过度收缩导致名称截断
        self.category_view.setMinimumWidth(200)
        self.subcategory_view.setMinimumWidth(180)
        right_widget.setMinimumWidth(400)
        
        main_layout.addWidget(self.splitter, 1)
    
    def apply_styles(self):
        """应用样式 - 支持多种主题"""
        from core.style_manager import ThemeManager
        theme_manager = ThemeManager()
        style = theme_manager.get_theme_style(self.current_theme)
        self.setStyleSheet(style)
    
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
        
        # 格式化分类数据，确保每个分类都有subcategories字段
        formatted_categories = []
        for cat in categories_data:
            # 确保cat是字典格式
            if isinstance(cat, dict):
                # 添加subcategories字段（如果不存在）
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

    def on_tool_run(self, tool_data):
        """处理运行工具的行为：
        - 网页工具：使用默认浏览器打开 URL
        - 本地工具：在宿主系统上等同双击/打开操作以启动程序或脚本

        更新：只有在启动成功后才会更新使用统计和视图。
        """
        tool_id = tool_data.get('id')
        tool_name = tool_data.get('name', '未知工具')

        # 辅助函数：尝试使用平台适当的方法打开本地路径
        def _open_local(path: str, working_dir: str = None) -> bool:
            try:
                if not path:
                    raise ValueError("工具路径为空")

                # 确保路径是绝对路径
                if not os.path.isabs(path):
                    # 如果是相对路径，尝试转换为绝对路径
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
                        # Windows: 使用explorer打开目录
                        os.startfile(path)
                    elif sys.platform == 'darwin':
                        # macOS: 使用open命令打开目录
                        subprocess.Popen(['open', path])
                    else:
                        # Linux: 使用xdg-open命令打开目录
                        subprocess.Popen(['xdg-open', path])
                else:
                    # 是文件，使用工作目录运行
                    # 获取工具所在目录作为默认工作目录
                    default_working_dir = os.path.dirname(path)
                    
                    # 使用工具配置的工作目录，如果没有则使用默认工作目录
                    actual_working_dir = working_dir or default_working_dir
                    logger.info("工具工作目录: %s", actual_working_dir)

                    # 根据平台和文件类型选择运行方式
                    if sys.platform.startswith('win'):
                        # Windows: 对于所有命令行工具，使用新的终端窗口运行
                        if path.lower().endswith('.cmd') or path.lower().endswith('.bat') or path.lower().endswith('.py'):
                            # 使用cmd.exe /c start命令来打开新的终端窗口
                            logger.info("使用cmd.exe启动命令行工具")
                            subprocess.Popen(
                                ['cmd.exe', '/c', 'start', path], 
                                cwd=actual_working_dir,
                                shell=True
                            )
                        else:
                            # 对于其他可执行文件，使用默认方式运行
                            logger.info("使用默认方式启动可执行文件")
                            subprocess.Popen(
                                [path], 
                                cwd=actual_working_dir,
                                shell=True
                            )
                    elif sys.platform == 'darwin':
                        # macOS: 使用open -a Terminal命令来打开新的终端窗口
                        subprocess.Popen(['open', '-a', 'Terminal', path], cwd=actual_working_dir)
                    else:
                        # Linux: 使用x-terminal-emulator命令来打开新的终端窗口
                        subprocess.Popen(['x-terminal-emulator', '-e', path], cwd=actual_working_dir)

                return True
            except KeyboardInterrupt as e:
                # 特别处理KeyboardInterrupt异常，避免程序崩溃
                logger.warning("工具运行被用户中断: %s", tool_name)
                QMessageBox.warning(self, "运行中断", "工具运行已被用户中断")
                return False
            except FileNotFoundError as e:
                logger.error("启动工具失败: %s, 错误: %s", tool_name, str(e))
                # 显示工具不存在的详细信息，包括工具配置
                config_info = f"工具名称: {tool_name}\n"\
                              f"工具路径: {path}\n"\
                              f"工作目录: {working_dir or '默认（工具所在目录）'}\n"\
                              f"工具类型: {'本地工具' if not is_web else '网页工具'}\n"\
                              f"优先级: {tool_data.get('priority', 0)}"
                QMessageBox.warning(self, "工具不存在", f"无法找到工具路径:\n{path}\n\n工具配置信息:\n{config_info}")
                return False
            except (PermissionError, subprocess.SubprocessError, ValueError) as e:
                logger.error("启动工具失败: %s, 错误: %s", tool_name, str(e))
                QMessageBox.warning(self, "运行失败", f"启动工具失败: {e}")
                return False

        # 确定是否为Web工具
        is_web = tool_data.get('is_web_tool', False)
        path = (tool_data.get('path') or '').strip()
        working_directory = tool_data.get('working_directory', '')

        started_ok = False

        if path.startswith('http://') or path.startswith('https://'):
            # 无论工具类型如何，只有当它是URL时才在浏览器中打开
            try:
                logger.info("启动网页工具: %s, URL: %s", tool_name, path)
                webbrowser.open(path)
                started_ok = True
            except KeyboardInterrupt as e:
                # 特别处理KeyboardInterrupt异常，避免程序崩溃
                logger.warning("网页工具打开被用户中断: %s", tool_name)
                QMessageBox.warning(self, "运行中断", "网页工具打开已被用户中断")
                started_ok = False
            except webbrowser.Error as e:
                logger.error("打开网页工具失败: %s, 错误: %s", tool_name, str(e))
                QMessageBox.warning(self, "运行失败", f"打开网页工具失败: {e}")
                started_ok = False
        else:
            # If it's a path (not a URL), open as local file/directory, regardless of tool type
            started_ok = _open_local(path, working_directory)

        # If started successfully, update usage stats
        if started_ok and tool_id:
            try:
                logger.info("更新工具使用统计: %s (ID: %s)", tool_name, tool_id)
                self.data_manager.update_tool_usage(tool_id)
            except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
                # ignore data update errors but log them
                logger.warning("更新工具使用统计失败: %s", str(e))

        # Refresh UI in any case (counts may have changed)
        self.refresh_current_view()

    def on_toggle_favorite(self, tool_id):
        """切换收藏状态"""
        if tool_id:
            self.data_manager.toggle_favorite(tool_id)
            self.refresh_current_view()
    
    def on_edit_background(self, tool_data):
        """处理编辑背景图片"""
        # 获取工具ID
        tool_id = tool_data['id']
        # 获取工具信息
        tool = self.data_manager.get_tool_by_id(tool_id)
        if not tool:
            return
        
        # 打开图片选择对话框
        dialog = ImageSelectorDialog(self.image_manager, tool.get("background_image", ""), self)
        if dialog.exec_():
            selected_image = dialog.get_selected_image()
            
            # 更新工具背景
            tool["background_image"] = selected_image
            
            if self.data_manager.update_tool(tool_id, tool):
                self.refresh_current_view()
    
    def on_delete_tool(self, tool_id):
        """处理删除工具"""
        # 调用数据管理器删除工具
        if self.data_manager.delete_tool(tool_id):
            QMessageBox.information(self, "成功", "工具删除成功！")
            self.refresh_current_view()
        else:
            QMessageBox.warning(self, "失败", "工具删除失败！")
    
    def on_new_category(self):
        """处理新建分类"""
        # 创建并配置输入对话框
        dialog = QInputDialog(self)
        dialog.setWindowTitle("新建分类")
        dialog.setLabelText("请输入分类名称:")
        
        # 应用主题样式
        if self.current_theme == "dark_green":
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #16213e;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QLineEdit {
                    background-color: rgba(15, 52, 96, 0.8);
                    border: 1px solid rgba(46, 204, 113, 0.2);
                    border-radius: 8px;
                    padding: 8px;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: rgba(46, 204, 113, 0.15);
                    border: 1px solid rgba(46, 204, 113, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: rgba(46, 204, 113, 0.25);
                }
            """)
        
        # 显示对话框并获取结果
        ok = dialog.exec_()
        category_name = dialog.textValue()
        
        if ok and category_name:
            # 创建分类
            category = {
                "name": category_name,
                "icon": "default_icon",
                "subcategories": []
            }
            
            # 保存分类
            if self.data_manager.add_category(category):
                QMessageBox.information(self, "成功", "分类创建成功！")
                self.category_view.refresh()
            else:
                QMessageBox.warning(self, "失败", "分类创建失败！")
    
    def on_new_subcategory(self):
        """处理新建子分类"""
        # 获取当前选中的分类
        current_category = self.category_view.current_category
        # 检查current_category是否为整数ID或None
        if not current_category:
            QMessageBox.warning(self, "警告", "请先选择一个主分类！")
            return
        
        # 创建并配置输入对话框
        dialog = QInputDialog(self)
        dialog.setWindowTitle("新建子分类")
        dialog.setLabelText("请输入子分类名称:")
        
        # 应用主题样式
        if self.current_theme == "dark_green":
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #16213e;
                    color: #ffffff;
                }
                QLabel {
                    color: #ffffff;
                }
                QLineEdit {
                    background-color: rgba(15, 52, 96, 0.8);
                    border: 1px solid rgba(46, 204, 113, 0.2);
                    border-radius: 8px;
                    padding: 8px;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: rgba(46, 204, 113, 0.15);
                    border: 1px solid rgba(46, 204, 113, 0.3);
                    border-radius: 6px;
                    padding: 6px 12px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: rgba(46, 204, 113, 0.25);
                }
            """)
        
        # 显示对话框并获取结果
        ok = dialog.exec_()
        subcategory_name = dialog.textValue()
        
        if ok and subcategory_name:
            # 创建子分类
            subcategory = {
                "name": subcategory_name
            }
            
            # 保存子分类 - current_category已经是整数ID
            if self.data_manager.add_subcategory(current_category, subcategory):
                QMessageBox.information(self, "成功", "子分类创建成功！")
                self.category_view.refresh()
            else:
                QMessageBox.warning(self, "失败", "子分类创建失败！")
    

    
    def on_delete_category(self):
        """处理删除分类"""
        # 获取当前选中的分类
        current_category = self.category_view.current_category
        current_subcategory = self.subcategory_view.current_subcategory
        
        # 如果选中了子分类，不能直接删除主分类
        if current_subcategory:
            QMessageBox.warning(self, "警告", "请先取消选择子分类，然后再删除主分类！")
            return
        
        if not current_category:
            QMessageBox.warning(self, "警告", "请先选择一个要删除的主分类！")
            return
        
        # 弹出确认对话框
        reply = self._themed_question('确认删除',
                                    f"确定要删除选中的分类吗？\n删除前请确保该分类下没有工具和子分类。",
                                    default=QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 调用数据管理器删除分类
            success, message = self.data_manager.delete_category(current_category)
            if success:
                QMessageBox.information(self, "成功", "分类删除成功！")
                self.category_view.refresh()
                # 重置当前选中状态
                self.current_category = None
                self.tool_container.display_tools([])
            else:
                QMessageBox.warning(self, "失败", message)
    
    def on_delete_subcategory(self):
        """处理删除子分类"""
        # 获取当前选中的子分类
        current_subcategory = self.subcategory_view.current_subcategory
        
        if not current_subcategory:
            QMessageBox.warning(self, "警告", "请先选择一个要删除的子分类！")
            return
        
        # 弹出确认对话框
        reply = self._themed_question("确认删除", 
                                    f"确定要删除选中的子分类吗？\n删除前请确保该子分类下没有工具。",
                                    default=QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 调用数据管理器删除子分类
            success, message = self.data_manager.delete_subcategory(current_subcategory)
            if success:
                QMessageBox.information(self, "成功", "子分类删除成功！")
                self.category_view.refresh()
                # 重置当前选中状态
                self.subcategory_view.current_subcategory = None
                # 显示当前分类下的所有工具
                self.on_category_selected(self.category_view.current_category)
            else:
                QMessageBox.warning(self, "失败", message)
    
    # 移除视图切换功能，只保留网格视图
    
    def on_search(self, text):
        """处理搜索"""
        # 搜索应为全局搜索：无论当前是否选中某个一级分类，都在所有工具中检索
        tools = self.data_manager.load_tools()
        
        # 规范化搜索关键字并判断是否为空
        q = text.strip().lower()

        # q 为空时恢复默认视图（当前分类或全部工具），避免空查询匹配所有项
        if not q:
            self.refresh_current_view()
            return

        # 过滤工具：支持不区分大小写的模糊搜索（包含子串匹配 + 相似度匹配）
        q = text.strip().lower()

        def fuzzy_score(a: str, b: str) -> float:
            try:
                return difflib.SequenceMatcher(None, a, b).ratio()
            except (TypeError, ValueError):
                return 0.0

        filtered_tools = []
        # threshold 用于模糊匹配，0.0-1.0；较高值更严格。默认 0.6 为宽松匹配。
        FUZZY_THRESHOLD = 0.6

        for tool in tools:
            name = (tool.get('name') or '').lower()
            desc = (tool.get('description') or '').lower()
            tags = [t.lower() for t in tool.get('tags', [])]

            # 1) 直接子串匹配（忽略大小写） —— 最常见、优先级高
            if q in name or q in desc or any(q in t for t in tags):
                filtered_tools.append(tool)
                continue

            # 2) 对名称 / 描述 / 标签 做模糊相似度匹配
            # 对于较短的关键字，用子串匹配足够；如果 q 很短（<=2），跳过模糊匹配以避免误报
            if len(q) <= 2:
                continue

            score_name = fuzzy_score(q, name)
            score_desc = fuzzy_score(q, desc)
            score_tags = max((fuzzy_score(q, t) for t in tags), default=0.0)

            if max(score_name, score_desc, score_tags) >= FUZZY_THRESHOLD:
                filtered_tools.append(tool)
        
        # 如果找到了匹配项，并且不在收藏模式下，才自动在左侧定位到匹配工具所在的分类和子分类
        # 收藏模式下不应触发分类试图的显隐逻辑
        if filtered_tools and not self.is_in_favorites:
            first = filtered_tools[0]
            cat_id = first.get('category_id')
            sub_id = first.get('subcategory_id')

            # 选择一级分类（如果存在）
            if cat_id is not None:
                # 注意：select_category 会触发 signal，进而调用 on_category_selected
                # 这会导致视图重置，所以我们需要小心
                # 由于 on_search 主要是为了过滤工具列表，而 on_category_selected 会重置显示
                # 这里我们 block 信号或者接受这种行为（即搜索会跳转分类）
                # 现有逻辑中 on_category_selected 会显示分类视图，这对普通模式是好的
                # 但对收藏模式（已过滤掉）不好
                self.category_view.select_category(cat_id)
                # 以防没有自动加载子分类，显式加载
                self.subcategory_view.load_subcategories(cat_id)

            # 选择二级分类（如果存在）
            if sub_id is not None:
                self.subcategory_view.select_subcategory(sub_id)

        # 更新工具显示为搜索结果
        self.tool_container.display_tools(filtered_tools)

        # 更新工具数量为搜索结果数量
        self.tool_count_label.setText(f"工具数量: {len(filtered_tools)}")
    
    def on_show_favorites(self):
        """显示所有收藏的工具"""
        # 1. 每次都从 DataManager 加载最新数据，DataManager 内部有基于文件修改时间的缓存
        tools = self.data_manager.load_tools()
        
        # 2. 过滤出收藏的工具
        favorite_tools = [tool for tool in tools if tool.get('is_favorite', False)]
        
        # 3. 更新状态标志
        self.current_category = None
        self.is_in_favorites = True
        
        # 4. 更新UI（批量操作，减少重绘）
        # 隐藏分类视图
        self.category_view.hide()
        self.subcategory_view.hide()
        
        # 调整分割器大小
        self.splitter.setSizes([0, 0, 1200])
        
        # 显示收藏工具
        self.tool_container.display_tools(favorite_tools)
        
        # 更新标签和工具数量
        self.category_info_label.setText("收藏工具")
        self.refresh_tool_count()
        
        # 5. 更新按钮状态（最后操作，避免频繁连接断开）
        self.favorites_button.disconnect()
        self.favorites_button.setText("返回")
        self.favorites_button.clicked.connect(self.on_back_from_favorites)
    
    def on_back_from_favorites(self):
        """从收藏页面返回正常视图"""
        # 1. 更新状态标志
        self.is_in_favorites = False
        
        # 2. 重新显示分类视图和恢复分割器大小
        self.category_view.show()
        self.subcategory_view.show()
        self.splitter.setSizes([400, 300, 640])
        
        # 3. 重新加载数据
        tools = self.data_manager.load_tools()
        
        # 4. 显示所有工具
        self.tool_container.display_tools(tools)
        
        # 5. 批量更新UI（减少重绘次数）
        self.category_info_label.setText("所有工具")
        
        # 6. 优化：复用已加载的工具数据，避免重复加载
        tool_count = len(tools)
        self.tool_count_label.setText(f"工具数量: {tool_count}")
        
        # 7. 优化：减少信号连接和断开的频率
        self.favorites_button.setText("收藏")
        self.favorites_button.disconnect()
        self.favorites_button.clicked.connect(self.on_show_favorites)
        
    def on_about(self):
        """处理关于对话框"""
        # 使用自定义 QMessageBox，以便在深色主题下也能保持一致的外观
        box = QMessageBox(self)
        box.setWindowTitle("关于")
        box.setText(f"{self.app_name}\n版本: {self.version}\n\n用于管理渗透测试工具的图形化界面应用。")
        # 根据主题调整样式，仅修改此对话框的样式，避免影响全局
        if self.current_theme == 'blue_white':
            box.setStyleSheet('''
                QMessageBox { background: #f6fbff; color: #003347; }
                QLabel { color: #003347; }
                QPushButton { background: rgba(66,135,245,0.06); border-radius: 6px; padding: 6px 10px; }
            ''')
        else:
            box.setStyleSheet('''
                QMessageBox { background: #0f1113; color: #e5ffe9; }
                QLabel { color: #e5ffe9; }
                QPushButton { background: rgba(144,238,144,0.06); color: #e5ffe9; border-radius: 6px; padding: 6px 10px; }
            ''')

        box.exec_()
    
    def refresh_all(self):
        """刷新所有视图，显示加载进度"""
        from PyQt5.QtWidgets import QProgressDialog
        from PyQt5.QtCore import Qt
        
        # 创建进度对话框
        progress = QProgressDialog("正在刷新所有内容...", None, 0, 100, self)
        progress.setWindowTitle("刷新")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # 立即显示对话框
        progress.setValue(0)
        progress.show()
        
        try:
            # 刷新分类视图
            progress.setValue(30)
            progress.setLabelText("正在加载分类...")
            self.category_view.refresh()
            
            # 刷新工具视图
            progress.setValue(70)
            progress.setLabelText("正在加载工具...")
            self.refresh_current_view()
            
            # 完成
            progress.setValue(100)
            
            # 显示完成提示
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(self, "完成", "所有内容已成功刷新！")
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            from core.logger import logger
            logger.error("刷新内容失败: %s", str(e))
            QMessageBox.warning(self, "错误", f"刷新失败: {e}")
        finally:
            progress.close()
    
    def refresh_current_view(self):
        """刷新当前视图"""
        # 优先检查搜索框是否有内容
        if hasattr(self, 'search_input'):
            search_text = self.search_input.text().strip()
            if search_text:
                # 如果有搜索内容，重新执行搜索逻辑
                self.on_search(search_text)
                return

        # 如果在收藏页面，显示收藏的工具
        if self.is_in_favorites:
            tools = self.data_manager.load_tools()
            favorite_tools = [tool for tool in tools if tool.get('is_favorite', False)]
            self.tool_container.display_tools(favorite_tools)
        # 如果有选中的分类，直接加载该分类下的工具，避免重复调用on_category_selected
        elif self.current_category:
            # 直接加载该分类下的工具，避免重复操作
            tools = self.data_manager.get_tools_by_category(self.current_category)
            self.tool_container.display_tools(tools)
        else:
            # 默认视图：显示常用工具
            tools = self.data_manager.get_common_tools()
            self.tool_container.display_tools(tools)
            # 更新标题
            self.category_info_label.setText("常用工具")
        
        self.refresh_tool_count()
    
    def refresh_tool_count(self):
        """刷新工具数量显示"""
        # 优化：直接从工具容器获取当前显示的工具数量，避免重新加载
        tool_count = self.tool_container.get_tool_count()
        self.tool_count_label.setText(f"工具数量: {tool_count}")
        
    def switch_theme(self, theme_name):
        """切换应用程序主题"""
        # 设置并持久化主题
        self.current_theme = theme_name
        try:
            # 将主题保存到 settings.ini
            if hasattr(self, 'settings') and self.settings is not None:
                self.settings.setValue('theme', self.current_theme)
        except (PermissionError, IOError):
            # 忽略设置失败（例如权限问题），不过应用主题仍然生效
            pass
        
        # 更新菜单按钮状态
        self.dark_green_theme_action.setChecked(self.current_theme == "dark_green")
        self.blue_white_theme_action.setChecked(self.current_theme == "blue_white")
        
        # 应用主题样式和更新所有UI组件
        self.refresh_ui_with_theme()
        
    def refresh_ui_with_theme(self):
        """应用主题并刷新所有UI组件"""
        # 应用样式表
        self.apply_styles()
        
        # 调用各个子组件的set_theme方法，确保所有组件都能响应主题切换
        self.category_view.set_theme(self.current_theme)
        self.subcategory_view.set_theme(self.current_theme)
        self.tool_container.set_theme(self.current_theme)
        
        # 根据当前主题设置颜色变量
        if self.current_theme == "blue_white":
            main_bg_color = "#f5f7fa"
            right_bg_color = "#ffffff"
            info_bg_color = "#e6f0ff"
            category_bg_color = "#ffffff"
            subcategory_bg_color = "#f0f4f8"
            text_color = "#333333"
            label_color = "#2176ff"
            border_color = "#2176ff"
        elif self.current_theme == "dark_green":
            main_bg_color = "#1a1a2e"
            right_bg_color = "#1a1a2e"
            info_bg_color = "rgba(255, 255, 255, 0.05)"
            category_bg_color = "#16213e"
            subcategory_bg_color = "#1a1a2e"
            text_color = "#ffffff"
            label_color = "#67e8f9"
            border_color = "rgba(103, 232, 249, 0.5)"
        
        # 更新界面上的标签颜色
        self.category_info_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {label_color};")
        self.centralWidget().setStyleSheet(f"background-color: {main_bg_color};")
        
        # 更新所有分隔器中的部件
        for i in range(self.centralWidget().layout().count()):
            item = self.centralWidget().layout().itemAt(i)
            if item and item.widget():
                splitter = item.widget()
                for j in range(splitter.count()):
                    widget = splitter.widget(j)
                    if widget:
                        # 左侧分类视图 (j=0)
                        if j == 0 and hasattr(widget, "setStyleSheet"):
                            widget.setStyleSheet(f"background-color: {category_bg_color}; color: {text_color};")
                        # 中间子分类视图 (j=1)
                        elif j == 1 and hasattr(widget, "setStyleSheet"):
                            widget.setStyleSheet(f"background-color: {subcategory_bg_color}; color: {text_color};")
                        # 右侧部件 (j=2)
                        elif j == 2 and hasattr(widget, "setStyleSheet"):
                            widget.setStyleSheet(f"background-color: {right_bg_color};")
                            
                            # 更新信息栏样式
                            for k in range(widget.layout().count()):
                                info_item = widget.layout().itemAt(k)
                                if info_item and info_item.widget():
                                    info_bar = info_item.widget()
                                    if hasattr(info_bar, 'layout') and info_bar.layout():
                                        info_bar.setStyleSheet(f"background-color: {info_bg_color}; border-bottom: 2px solid {border_color};")
        
        # 刷新当前视图以应用新主题
        self.refresh_current_view()
    
    def show_status_message(self, message, timeout=2000):
        """显示状态栏消息"""
        self.statusBar.showMessage(message, timeout)

    def _themed_question(self, title: str, text: str, default=QMessageBox.No) -> QMessageBox.StandardButton:
        """显示一个与当前主题匹配的确认对话框，返回标准按钮结果。"""
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(default)

        # 在对话框本地应用主题（避免更改全局应用样式）
        if self.current_theme == 'blue_white':
            box.setStyleSheet('''
                QMessageBox { background: #f6fbff; color: #003347; }
                QLabel { color: #003347; }
                QPushButton { background-color: rgba(66,135,245,0.06); color: #003347; border-radius: 6px; padding: 6px 10px; }
                QPushButton:pressed { background-color: rgba(66,135,245,0.12); }
            ''')
        else:
            box.setStyleSheet('''
                QMessageBox { background: #0f1113; color: #e5ffe9; }
                QLabel { color: #e5ffe9; }
                QPushButton { background-color: rgba(144,238,144,0.06); color: #e5ffe9; border-radius: 6px; padding: 6px 10px; }
                QPushButton:pressed { background-color: rgba(144,238,144,0.12); }
            ''')

        return box.exec_()
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        reply = self._themed_question('确认', '确定要退出吗？', default=QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 清理资源
            try:
                # 导入AsyncIconLoader并调用shutdown方法
                from ui.tool_model_view import icon_loader
                icon_loader.shutdown()
            except Exception as e:
                logger.error("清理icon_loader资源失败: %s", str(e))
            
            try:
                # 调用数据管理器的shutdown方法，清理所有线程资源
                # 添加额外检查，确保data_manager仍然有效
                if hasattr(self, 'data_manager') and self.data_manager is not None:
                    self.data_manager.shutdown()
            except RuntimeError as e:
                # 捕获Qt对象已被删除的错误
                if "wrapped C/C++ object of type" in str(e):
                    logger.warning("部分资源已被系统自动清理，跳过手动清理")
                else:
                    logger.error("清理data_manager资源失败: %s", str(e))
            except Exception as e:
                logger.error("清理data_manager资源失败: %s", str(e))
            
            event.accept()
        else:
            event.ignore()



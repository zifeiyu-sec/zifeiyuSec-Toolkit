from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                            QToolBar, QAction, QMessageBox, QInputDialog, QApplication, 
                            QLineEdit, QActionGroup, QMenu, QToolButton, QStatusBar, 
                            QProgressBar, QLabel)
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt, QSize, QSettings
import difflib
import os
import sys
import webbrowser
import subprocess

# 导入自定义模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.data_manager import DataManager
from core.image_manager import ImageManager
from ui.category_view import CategoryView
from ui.subcategory_view import SubcategoryView
from ui.tool_card import ToolCardContainer
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
        
        # 创建默认背景图片
        self.image_manager.create_default_backgrounds()
        
        # 当前选中的分类
        self.current_category = None
        
        # 配置目录（用于保存 settings.ini 等）
        self.config_dir = config_dir or os.path.abspath('.')

        # 使用 config_dir 下的 settings.ini 持久化用户设置（如主题）
        settings_file = os.path.join(self.config_dir, "settings.ini")
        # QSettings will read/write an INI-format file at settings_file
        self.settings = QSettings(settings_file, QSettings.IniFormat)

        # 当前主题（默认使用黑绿色主题），尝试从设置中加载
        self.current_theme = str(self.settings.value("theme", "dark_green"))
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle(f"{self.app_name} - v{self.version}")
        self.setGeometry(100, 100, 1500, 900)
        # 固定窗口大小，不允许缩放
        self.setFixedSize(1200, 800)
        
        # 创建主组件
        self.create_actions()
        self.create_menus()
        self.create_toolbars()
        self.create_statusbar()
        self.create_main_widget()
        
        # 应用样式并把主题传播给子组件（确保重启后 UI 组件使用持久化主题）
        self.apply_styles()
        # 在初始化完成后，确保所有子组件也使用当前主题
        # 例如 CategoryView、SubcategoryView、ToolCardContainer 等
        try:
            self.refresh_ui_with_theme()
        except Exception:
            # 忽略刷新失败，以避免启动时的非关键异常阻止应用
            pass
    
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
        """创建菜单 - 目前不创建任何菜单"""
        # 移除顶部菜单栏
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
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧一级分类视图
        self.category_view = CategoryView(self.data_manager)
        self.category_view.category_selected.connect(self.on_category_selected)
        # 连接右键菜单信号
        self.category_view.new_category_requested.connect(self.on_new_category)
        self.category_view.new_subcategory_requested.connect(self.on_new_subcategory)
        self.category_view.delete_category_requested.connect(self.on_delete_category)
        splitter.addWidget(self.category_view)
        
        # 中间二级分类视图
        self.subcategory_view = SubcategoryView(self.data_manager)
        self.subcategory_view.subcategory_selected.connect(self.on_subcategory_selected)
        # 连接右键菜单信号
        self.subcategory_view.new_subcategory_requested.connect(self.on_new_subcategory)
        self.subcategory_view.delete_subcategory_requested.connect(self.on_delete_subcategory)
        splitter.addWidget(self.subcategory_view)
        
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
        
        self.category_info_label = QLabel("所有工具")
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

        # 调整为适配当前卡片尺寸 (260px 每张)，并考虑 spacing/margin
        # 计算：2 * 260 + grid spacing 10 + left/right margins 12*2 = 554
        # 保留小幅缓冲，设置最小宽度为 580
        right_widget.setMinimumWidth(580)
        
        splitter.addWidget(right_widget)
        
        # 设置初始大小
        # 调整三列初始宽度比例，使左侧两列足够宽以完整显示分类名称
        # 总宽度 1200，对应的三列：一级分类 260px，二级分类 300px，工具区 640px
        splitter.setSizes([400, 300, 640])

        # 强制左右两列在布局中保留最小宽度，避免被过度收缩导致名称截断
        self.category_view.setMinimumWidth(260)
        self.subcategory_view.setMinimumWidth(300)
        
        main_layout.addWidget(splitter, 1)
    
    def apply_styles(self):
        """应用样式 - 支持多种主题"""
        # 定义两种主题的样式
        themes = {
            "dark_green": """
            /* 主窗口样式 */
            QMainWindow {
                background-color: #1a1a2e;
                border: none;
            }
            
            /* 菜单栏样式 */
            QMenuBar {
                background: rgba(255, 255, 255, 0.05);
                color: #ffffff;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            QMenuBar::item {
                padding: 5px 10px;
            }
            
            QMenuBar::item:selected {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            
            /* 弹出菜单样式 */
            QMenu {
                background: rgba(26, 26, 46, 0.95);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 5px;
            }
            
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background: rgba(103, 232, 249, 0.2);
            }
            
            /* 工具栏样式 */
            QToolBar {
                background-color: #161c2a;
                border-bottom: 1px solid rgba(144, 238, 144, 0.3);
                padding: 10px 12px;
                spacing: 15px;
                border-radius: 0;
            }
            
            /* 工具栏按钮 */
            QToolButton {
                background: rgba(32, 33, 54, 0.8);
                border: 1px solid rgba(144, 238, 144, 0.2);
                padding: 9px 18px;
                border-radius: 8px;
                color: #ffffff;
                font-weight: 500;
                font-size: 13px;
                transition: all 0.2s ease;
            }
            
            QToolButton:hover {
                background: rgba(40, 42, 66, 0.9);
                border: 1px solid rgba(144, 238, 144, 0.5);
                box-shadow: 0 2px 6px rgba(144, 238, 144, 0.1);
            }
            
            QToolButton:pressed {
                background: rgba(144, 238, 144, 0.2);
                box-shadow: 0 1px 3px rgba(144, 238, 144, 0.2);
            }
            
            /* 状态栏 */
            QStatusBar {
                background: rgba(255, 255, 255, 0.05);
                border-top: 1px solid rgba(255, 255, 255, 0.1);
                color: #ffffff;
                font-size: 12px;
            }
            
            /* 分割器 */
            QSplitter {
                background-color: #1a1a2e;
            }
            
            QSplitter::handle {
                background: rgba(255, 255, 255, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            
            QSplitter::handle:hover {
                background: rgba(103, 232, 249, 0.3);
            }
            
            /* 输入框 */
            QLineEdit {
                background: rgba(32, 33, 54, 0.8);
                border: 1px solid rgba(144, 238, 144, 0.2);
                border-radius: 8px;
                padding: 9px 14px;
                color: #ffffff;
                font-size: 13px;
                transition: all 0.2s ease;
            }
            
            QLineEdit:focus {
                border: 1px solid rgba(144, 238, 144, 0.7);
                background: rgba(40, 42, 66, 0.9);
                box-shadow: 0 2px 6px rgba(144, 238, 144, 0.1);
                outline: none;
            }
            
            /* 按钮 */
            QPushButton {
                background: rgba(144, 238, 144, 0.1);
                border: 1px solid rgba(144, 238, 144, 0.3);
                border-radius: 8px;
                padding: 9px 18px;
                color: #ffffff;
                font-weight: 500;
                font-size: 13px;
                transition: all 0.2s ease;
            }
            
            QPushButton:hover {
                background: rgba(144, 238, 144, 0.2);
                border: 1px solid rgba(144, 238, 144, 0.5);
                box-shadow: 0 2px 6px rgba(144, 238, 144, 0.1);
            }
            
            QPushButton:pressed {
                background: rgba(144, 238, 144, 0.3);
                box-shadow: 0 1px 3px rgba(144, 238, 144, 0.2);
            }
            
            QPushButton:default {
                border: 1px solid rgba(144, 238, 144, 0.5);
                background: rgba(144, 238, 144, 0.15);
            }
            
            /* 分组框 */
            QGroupBox {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
            }
            
            QGroupBox::title {
                background-color: transparent;
                color: #ffffff;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }
            
            /* 标签 */
            QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            
            /* 文本编辑框 */
            QTextEdit {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
                color: #ffffff;
                font-size: 13px;
            }
            
            QTextEdit:focus {
                border: 1px solid rgba(103, 232, 249, 0.5);
                background: rgba(255, 255, 255, 0.08);
                outline: none;
            }""",
            "blue_white": """
            /* 主窗口样式 */
            QMainWindow {
                background-color: #f5f7fa;
                border: none;
            }
            
            /* 菜单栏样式 */
            QMenuBar {
                background: #ffffff;
                color: #333333;
                border-bottom: 1px solid #e0e0e0;
            }
            
            QMenuBar::item {
                padding: 5px 10px;
            }
            
            QMenuBar::item:selected {
                background: #e6f0ff;
                border-radius: 4px;
            }
            
            /* 弹出菜单样式 */
            QMenu {
                background: rgba(255, 255, 255, 0.95);
                color: #333333;
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 5px;
            }
            
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background: rgba(66, 135, 245, 0.1);
            }
            
            /* 工具栏样式 */
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #4287f5;
                padding: 8px;
                spacing: 12px;
            }
            
            /* 工具栏按钮 */
            QToolButton {
                background: rgba(66, 135, 245, 0.05);
                border: 1px solid rgba(66, 135, 245, 0.2);
                padding: 8px 16px;
                border-radius: 8px;
                color: #333333;
                font-weight: 500;
            }
            
            QToolButton:hover {
                background: rgba(66, 135, 245, 0.1);
                border: 1px solid rgba(66, 135, 245, 0.5);
            }
            
            QToolButton:pressed {
                background: rgba(66, 135, 245, 0.2);
            }
            
            /* 状态栏 */
            QStatusBar {
                background: rgba(255, 255, 255, 0.9);
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                color: #333333;
                font-size: 12px;
            }
            
            /* 分割器 */
            QSplitter {
                background-color: #f0f4f8;
            }
            
            QSplitter::handle {
                background: rgba(0, 0, 0, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            
            QSplitter::handle:hover {
                background: rgba(66, 135, 245, 0.3);
            }
            
            /* 输入框 */
            QLineEdit {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
                color: #333333;
                font-size: 13px;
            }
            
            QLineEdit:focus {
                border: 1px solid rgba(66, 135, 245, 0.5);
                background: rgba(255, 255, 255, 1);
                outline: none;
            }
            
            /* 按钮 */
            QPushButton {
                background: rgba(66, 135, 245, 0.1);
                border: 1px solid rgba(66, 135, 245, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                color: #333333;
                font-weight: 500;
                font-size: 13px;
            }
            
            QPushButton:hover {
                background: rgba(66, 135, 245, 0.2);
                border: 1px solid rgba(66, 135, 245, 0.5);
            }
            
            QPushButton:pressed {
                background: rgba(66, 135, 245, 0.3);
            }
            
            QPushButton:default {
                border: 1px solid rgba(66, 135, 245, 0.5);
            }
            
            /* 分组框 */
            QGroupBox {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
            }
            
            QGroupBox::title {
                background-color: transparent;
                color: #333333;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }
            
            /* 标签 */
            QLabel {
                color: #333333;
                font-size: 13px;
            }
            
            /* 文本编辑框 */
            QTextEdit {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 10px;
                color: #333333;
                font-size: 13px;
            }
            
            QTextEdit:focus {
                border: 1px solid rgba(66, 135, 245, 0.5);
                background: rgba(255, 255, 255, 1);
                outline: none;
            }"""
        }
        
        # 应用选中的主题样式
        self.setStyleSheet(themes[self.current_theme])
    
    def on_category_selected(self, category_id):
        """处理一级分类选择"""
        self.current_category = category_id
        
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

        # Helper: try to open local path using platform-appropriate method
        def _open_local(path: str) -> bool:
            try:
                if not path:
                    raise ValueError("工具路径为空")

                # Prefer the simplest cross-platform open semantics:
                if sys.platform.startswith('win'):
                    # Windows: os.startfile mimics double-click
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', path])
                else:
                    # Linux: use xdg-open if available
                    subprocess.Popen(['xdg-open', path])

                return True
            except Exception as e:
                QMessageBox.warning(self, "运行失败", f"启动工具失败: {e}")
                return False

        # Determine if it's a web tool
        is_web = tool_data.get('is_web_tool', False)
        path = (tool_data.get('path') or '').strip()

        started_ok = False

        if is_web or (path.startswith('http://') or path.startswith('https://')):
            # Open in default browser
            try:
                webbrowser.open(path)
                started_ok = True
            except Exception as e:
                QMessageBox.warning(self, "运行失败", f"打开网页工具失败: {e}")
                started_ok = False
        else:
            # Local tool - try to open using double-click semantics
            started_ok = _open_local(path)

        # If started successfully, update usage stats
        if started_ok and tool_id:
            try:
                self.data_manager.update_tool_usage(tool_id)
            except Exception:
                # ignore data update errors
                pass

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
        category_name, ok = QInputDialog.getText(self, "新建分类", "请输入分类名称:")
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
        
        # 获取子分类名称
        subcategory_name, ok = QInputDialog.getText(self, "新建子分类", "请输入子分类名称:")
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
            if self.current_category:
                tools = self.data_manager.get_tools_by_category(self.current_category)
            else:
                tools = self.data_manager.load_tools()

            self.tool_container.display_tools(tools)
            self.refresh_tool_count()
            return

        # 过滤工具：支持不区分大小写的模糊搜索（包含子串匹配 + 相似度匹配）
        q = text.strip().lower()

        def fuzzy_score(a: str, b: str) -> float:
            try:
                return difflib.SequenceMatcher(None, a, b).ratio()
            except Exception:
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
        
        # 如果找到了匹配项，自动在左侧定位到匹配工具所在的分类和子分类（以第一个匹配项为准）
        if filtered_tools:
            first = filtered_tools[0]
            cat_id = first.get('category_id')
            sub_id = first.get('subcategory_id')

            # 选择一级分类（如果存在）
            if cat_id is not None:
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
        """刷新所有视图"""
        self.category_view.refresh()
        self.refresh_current_view()
    
    def refresh_current_view(self):
        """刷新当前视图"""
        # 如果有选中的分类，重新加载该分类下的工具
        if self.current_category:
            # 传递正确的参数给on_category_selected
            self.on_category_selected(self.current_category)
        else:
            # 否则加载所有工具（使用load_tools方法）
            tools = self.data_manager.load_tools()
            self.tool_container.display_tools(tools)
        
        self.refresh_tool_count()
    
    def refresh_tool_count(self):
        """刷新工具数量显示"""
        # 从数据管理器获取当前显示的工具数量
        if self.current_category:
            # 如果有选中的分类，获取该分类下的工具数量
            tools = self.data_manager.get_tools_by_category(self.current_category, None)
        else:
            # 否则获取所有工具数量
            tools = self.data_manager.load_tools()
        
        tool_count = len(tools)
        self.tool_count_label.setText(f"工具数量: {tool_count}")
        
    def switch_theme(self, theme_name):
        """切换应用程序主题"""
        # 设置并持久化主题
        self.current_theme = theme_name
        try:
            # 将主题保存到 settings.ini
            if hasattr(self, 'settings') and self.settings is not None:
                self.settings.setValue('theme', self.current_theme)
        except Exception:
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

        # apply theme-locally to this dialog (avoid changing global app style)
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
            event.accept()
        else:
            event.ignore()

# 主函数
if __name__ == "__main__":
    # 确保中文显示正常
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # 获取当前脚本所在目录的父目录，即项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 创建主窗口，明确传递项目根目录作为配置目录
    window = PentestToolManager(config_dir=project_root)
    window.show()
    
    # 加载初始工具列表
    window.refresh_current_view()
    
    sys.exit(app.exec_())
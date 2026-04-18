import copy
import os
import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                            QToolBar, QAction, QMessageBox, QInputDialog, QApplication,
                            QLineEdit, QActionGroup, QMenu, QToolButton, QStatusBar, QFileDialog,
                            QLabel, QDialog, QStackedWidget, QGraphicsOpacityEffect)
from PyQt5.QtCore import Qt, QSize, QSettings, QThread, QTimer, QEasingCurve, QPropertyAnimation

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
from core.background_tasks_qt import CallableWorker
from core.image_manager import ImageManager
from core.logger import logger
from core.runtime_paths import get_runtime_state_root
from core.style_manager import ThemeManager
from core.task_control import OperationCancelledError
from core.notes_manager import NotesManager
from core.tool_config_exchange import ToolConfigExchangeService
from core.tool_launch_service import ToolLaunchService
from core.update_service import UpdateService
from core.ui_scale import metrics_for_geometry, preferred_main_window_geometry, scaled
from ui.category_view import CategoryView
from ui.subcategory_view import SubcategoryView
from ui.tool_model_view import ToolCardContainer
from ui.favorites_grid_view import FavoritesGridContainer
from ui.image_selector import ImageSelectorDialog
from ui.icon_loader import icon_loader
from ui.tool_config_dialog import ToolConfigDialog
from ui.notes_list_dialog import NotesListDialog
from ui.data_health_dialog import DataHealthDialog
from ui.main_window_navigation_mixin import MainWindowNavigationMixin
from ui.main_window_search_mixin import MainWindowSearchMixin
from ui.main_window_view_mixin import MainWindowViewMixin


class MainWindow(MainWindowViewMixin, MainWindowNavigationMixin, MainWindowSearchMixin, QMainWindow):
    BASE_MIN_CATEGORY_WIDTH = 220
    BASE_MIN_SUBCATEGORY_WIDTH = 180
    BASE_MIN_CONTENT_WIDTH = 420

    def __init__(self, config_dir=None):
        super().__init__()
        # 设置应用程序信息
        self.app_name = "子非鱼安全工具箱"
        self.version = "3.1.0"
        
        self._ui_scale = 1.0
        self.MIN_CATEGORY_WIDTH = self.BASE_MIN_CATEGORY_WIDTH
        self.MIN_SUBCATEGORY_WIDTH = self.BASE_MIN_SUBCATEGORY_WIDTH
        self.MIN_CONTENT_WIDTH = self.BASE_MIN_CONTENT_WIDTH

        # 配置目录（用于保存 settings.ini 等）
        self.config_dir = os.path.abspath(config_dir) if config_dir else os.fspath(get_runtime_state_root())

        # 初始化管理器
        self.data_manager = DataManager(config_dir=self.config_dir)
        self.image_manager = ImageManager(config_dir=self.config_dir)
        self.notes_manager = NotesManager(repo_root=self.config_dir)
        self.tool_launcher = ToolLaunchService()
        self.tool_config_exchange = ToolConfigExchangeService(self.data_manager)

        # 注意：不要在应用启动时强制创建默认背景图片（会增加启动延迟）
        # 默认背景将延迟在首次需要图片目录或列出图片时创建，以加快启动速度。

        # 当前选中的分类
        self.current_category = None

        # 是否在收藏页面
        self.is_in_favorites = False

        # 当前列表视图模式：仅保留 category（分类视图）
        self.current_view_mode = "category"
        # 进入收藏页前的视图快照，用于返回时恢复
        self._view_state_before_favorites = None
        # 标记“是否由启动流程自动进入收藏页”
        self._is_startup_favorites_entry = False

        # 使用 config_dir 下的 settings.ini 持久化用户设置（如主题）
        settings_file = os.path.join(self.config_dir, "settings.ini")
        # QSettings 将在 settings_file 路径读写 INI 格式的文件
        self.settings = QSettings(settings_file, QSettings.IniFormat)
        self.update_service = UpdateService(self.app_name, self.version, self.settings, self.config_dir)
        self._latest_update_info = None
        self._check_update_on_start = str(self.settings.value("update/check_on_start", "false")).strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        # 当前主题（默认使用亮绿色主题），尝试从设置中加载
        self.current_theme = str(self.settings.value("theme", "dark_green"))
        available_themes = ThemeManager().themes.keys()
        if self.current_theme not in available_themes:
            self.current_theme = "dark_green"
            self.settings.setValue("theme", self.current_theme)

        self.search_debounce_interval_ms = 200
        self._pending_search_text = ""
        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.timeout.connect(self._execute_pending_search)

        self.usage_flush_interval_ms = 1500
        self.usage_flush_timer = QTimer(self)
        self.usage_flush_timer.setSingleShot(True)
        self.usage_flush_timer.timeout.connect(self._flush_pending_usage_updates)
        self._background_tasks = {}
        self._background_idle_callbacks = []
        self._close_after_background_tasks = False
        self._content_fade_animation = None
        self._content_opacity_effect = None
        
        # 初始化UI
        self.init_ui()
        if self._check_update_on_start:
            QTimer.singleShot(1500, self._check_updates_on_startup)
    
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口属性
        self.setWindowTitle(f"{self.app_name} - v{self.version}")

        x, y, window_width, window_height = preferred_main_window_geometry(self)
        self._update_ui_scale_metrics(window_width, window_height)
        self.setGeometry(x, y, window_width, window_height)
        self.setMinimumSize(scaled(900, self._ui_scale), scaled(600, self._ui_scale))

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
        def delayed_theme_refresh():
            try:
                self.refresh_ui_with_theme()
            except (ValueError, AttributeError) as e:
                # 忽略刷新失败，以避免启动时的非关键异常阻止应用
                logger.warning("主题刷新失败: %s", str(e))
        QTimer.singleShot(100, delayed_theme_refresh)

    def _update_ui_scale_metrics(self, width=None, height=None):
        metrics = metrics_for_geometry(
            width or self.width() or self.BASE_MIN_CONTENT_WIDTH,
            height or self.height() or self.BASE_MIN_CONTENT_WIDTH,
        )
        self._ui_scale = metrics.scale
        self.MIN_CATEGORY_WIDTH = scaled(self.BASE_MIN_CATEGORY_WIDTH, self._ui_scale)
        self.MIN_SUBCATEGORY_WIDTH = scaled(self.BASE_MIN_SUBCATEGORY_WIDTH, self._ui_scale)
        self.MIN_CONTENT_WIDTH = scaled(self.BASE_MIN_CONTENT_WIDTH, self._ui_scale)

    def create_actions(self):
        """创建动作"""

        self.new_tool_action = QAction("新增工具", self)
        self.new_tool_action.triggered.connect(self.on_new_tool)

        self.refresh_action = QAction("刷新", self)
        self.refresh_action.triggered.connect(self.refresh_all)

        self.import_tianhu_action = QAction("导入天狐工具箱", self)
        self.import_tianhu_action.triggered.connect(self.on_import_tianhu_tools)

        self.delete_tianhu_tools_action = QAction("删除天狐导入工具", self)
        self.delete_tianhu_tools_action.triggered.connect(self.on_delete_tianhu_tools)

        self.import_native_tools_action = QAction("导入本地工具配置", self)
        self.import_native_tools_action.triggered.connect(self.on_import_native_tools)

        self.export_native_tools_action = QAction("导出配置", self)
        self.export_native_tools_action.triggered.connect(self.on_export_native_tools)

        self.sync_official_tools_action = QAction("同步官方工具库", self)
        self.sync_official_tools_action.triggered.connect(self.on_sync_official_tools)

        self.check_update_action = QAction("检查更新", self)
        self.check_update_action.triggered.connect(self.on_check_updates)

        self.one_click_update_action = QAction("一键更新", self)
        self.one_click_update_action.triggered.connect(self.on_one_click_update)

        self.about_action = QAction("关于", self)
        self.about_action.triggered.connect(self.on_about)

        self.dark_green_theme_action = QAction("亮绿色主题", self, checkable=True)
        self.dark_green_theme_action.triggered.connect(lambda: self.switch_theme("dark_green"))

        self.blue_white_theme_action = QAction("蓝白色主题", self, checkable=True)
        self.blue_white_theme_action.triggered.connect(lambda: self.switch_theme("blue_white"))

        self.purple_neon_theme_action = QAction("紫霓主题", self, checkable=True)
        self.purple_neon_theme_action.triggered.connect(lambda: self.switch_theme("purple_neon"))

        self.red_orange_theme_action = QAction("红橙主题", self, checkable=True)
        self.red_orange_theme_action.triggered.connect(lambda: self.switch_theme("red_orange"))

        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.addAction(self.dark_green_theme_action)
        self.theme_action_group.addAction(self.blue_white_theme_action)
        self.theme_action_group.addAction(self.purple_neon_theme_action)
        self.theme_action_group.addAction(self.red_orange_theme_action)

        self._sync_theme_action_state()
    
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
        self.search_input.textChanged.connect(self.schedule_search)
        main_toolbar.addWidget(QLabel("搜索: "))
        main_toolbar.addWidget(self.search_input)

        # 右侧填充
        main_toolbar.addSeparator()
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Expanding, spacer.sizePolicy().Preferred)
        main_toolbar.addWidget(spacer)
        
        # 主题按钮
        main_toolbar.addSeparator()
        theme_button = QToolButton()
        theme_button.setText("主题")
        theme_button.setPopupMode(QToolButton.InstantPopup)

        # 创建主题菜单
        theme_menu = QMenu(theme_button)
        theme_menu.addAction(self.dark_green_theme_action)
        theme_menu.addAction(self.blue_white_theme_action)
        theme_menu.addAction(self.purple_neon_theme_action)
        theme_menu.addAction(self.red_orange_theme_action)

        theme_button.setMenu(theme_menu)
        main_toolbar.addWidget(theme_button)

        config_button = QToolButton()
        config_button.setText("配置")
        config_button.setPopupMode(QToolButton.InstantPopup)

        config_menu = QMenu(config_button)
        config_menu.addAction(self.import_tianhu_action)
        config_menu.addAction(self.delete_tianhu_tools_action)
        config_menu.addSeparator()
        config_menu.addAction(self.import_native_tools_action)
        config_menu.addAction(self.export_native_tools_action)
        config_menu.addSeparator()
        config_menu.addAction(self.sync_official_tools_action)
        config_menu.addSeparator()
        config_menu.addAction(self.check_update_action)
        config_menu.addAction(self.one_click_update_action)

        config_button.setMenu(config_menu)
        main_toolbar.addWidget(config_button)
        
        # 刷新按钮
        main_toolbar.addAction(self.refresh_action)
        
        # 收藏按钮
        main_toolbar.addSeparator()
        self.favorites_button = QToolButton()
        self.favorites_button.setText("收藏")
        self.favorites_button.clicked.connect(self.on_show_favorites)
        main_toolbar.addWidget(self.favorites_button)

        self.notes_button = QToolButton()
        self.notes_button.setText("笔记")
        self.notes_button.clicked.connect(self.on_show_notes)
        main_toolbar.addWidget(self.notes_button)

        self.data_health_button = QToolButton()
        self.data_health_button.setText("体检")
        self.data_health_button.clicked.connect(self.on_show_data_health)
        main_toolbar.addWidget(self.data_health_button)

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

        self.background_task_label = QLabel("")
        self.background_task_label.setVisible(False)
        self.statusBar.addPermanentWidget(self.background_task_label, 1)

        self.cancel_background_task_button = QToolButton()
        self.cancel_background_task_button.setText("取消任务")
        self.cancel_background_task_button.setVisible(False)
        self.cancel_background_task_button.clicked.connect(self.on_cancel_background_task)
        self.statusBar.addPermanentWidget(self.cancel_background_task_button)
        
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
        right_widget.setObjectName("contentPanel")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        # 顶部信息栏
        info_bar = QWidget()
        info_bar.setObjectName("contentInfoBar")
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(14, 10, 14, 10)

        self.category_info_label = QLabel("分类工具")
        self.category_info_label.setObjectName("contentTitleLabel")
        self.view_mode_label = QLabel("视图: 分类")
        self.view_mode_label.setObjectName("contentModeLabel")

        info_layout.addWidget(self.category_info_label)
        info_layout.addWidget(self.view_mode_label)
        info_layout.addStretch()

        right_layout.addWidget(info_bar)

        # 右侧工具区：主界面与收藏页使用不同容器，避免布局逻辑互相影响
        self.tool_stack = QStackedWidget()
        self.tool_stack.setObjectName("contentStack")

        self.tool_container = ToolCardContainer()
        self._connect_tool_container_signals(self.tool_container)
        self.tool_container.set_layout_mode('main')

        self.favorites_container = FavoritesGridContainer()
        self._connect_tool_container_signals(self.favorites_container)
        self.favorites_container.set_theme(self.current_theme)

        self.tool_stack.addWidget(self.tool_container)
        self.tool_stack.addWidget(self.favorites_container)
        self.tool_stack.setCurrentWidget(self.tool_container)

        self._content_opacity_effect = QGraphicsOpacityEffect(self.tool_stack)
        self._content_opacity_effect.setOpacity(1.0)
        self.tool_stack.setGraphicsEffect(self._content_opacity_effect)
        self._content_fade_animation = QPropertyAnimation(self._content_opacity_effect, b"opacity", self)
        self._content_fade_animation.setDuration(220)
        self._content_fade_animation.setStartValue(0.78)
        self._content_fade_animation.setEndValue(1.0)
        self._content_fade_animation.setEasingCurve(QEasingCurve.OutCubic)

        right_layout.addWidget(self.tool_stack, 1)
        
        # 初始化时先显示空的工具容器，然后在后台加载工具
        try:
            # 先显示空的工具列表
            self.tool_container.display_tools([])
            self.favorites_container.display_tools([])
            # 更新工具数量为0
            self.refresh_tool_count()
            
            # 定义异步加载完成后的回调函数
            def on_tools_loaded(tools, error=None):
                if error:
                    logger.warning("初始加载工具失败: %s", str(error))
                    return
                try:
                    # 默认显示收藏页面
                    self._is_startup_favorites_entry = True
                    self.on_show_favorites()
                except Exception as e:
                    logger.warning("显示收藏页面失败: %s", str(e))
                finally:
                    self._is_startup_favorites_entry = False
            
            # 使用异步加载工具，避免启动时阻塞
            self.data_manager.load_tools(callback=on_tools_loaded)
        except Exception as e:
            logger.warning("初始加载工具失败: %s", str(e))

        self.splitter.addWidget(right_widget)
        
        # 设置初始大小和比例
        self._apply_splitter_layout('browse')

        # 设置拉伸因子，确保各部分按比例缩放
        self.splitter.setStretchFactor(0, 1)  # 一级分类拉伸因子1
        self.splitter.setStretchFactor(1, 1)  # 二级分类拉伸因子1
        self.splitter.setStretchFactor(2, 3)  # 工具区拉伸因子3

        # 设置最小宽度
        self.category_view.setMinimumWidth(200)
        self.subcategory_view.setMinimumWidth(180)
        right_widget.setMinimumWidth(400)
        
        main_layout.addWidget(self.splitter, 1)

    def _connect_tool_container_signals(self, container):
        container.deleted.connect(self.on_delete_tool)
        container.edit_requested.connect(self.on_edit_tool)
        container.new_tool_requested.connect(self.on_new_tool)
        container.run_tool.connect(self.on_tool_run)
        container.toggle_favorite.connect(self.on_toggle_favorite)
        container.tool_order_changed.connect(self.on_tool_order_changed)

    def _get_active_tool_container(self):
        if self.is_in_favorites and hasattr(self, 'favorites_container'):
            return self.favorites_container
        return getattr(self, 'tool_container', None)


    def _display_tools(self, tools):
        container = self._get_active_tool_container()
        if container is not None:
            container.display_tools(tools)
            self._restart_content_fade_animation()

    def _restart_content_fade_animation(self):
        animation = getattr(self, '_content_fade_animation', None)
        effect = getattr(self, '_content_opacity_effect', None)
        if animation is None or effect is None:
            return
        effect.setOpacity(0.78)
        animation.stop()
        animation.start()

    def _has_active_background_task(self):
        return bool(self._background_tasks)

    def _set_background_task_status(self, message, allow_cancel=True):
        text = str(message or "").strip()
        if not text:
            self.background_task_label.clear()
            self.background_task_label.setVisible(False)
            self.cancel_background_task_button.setVisible(False)
            self.cancel_background_task_button.setEnabled(False)
            return
        self.background_task_label.setText(text)
        self.background_task_label.setVisible(True)
        self.cancel_background_task_button.setVisible(True)
        self.cancel_background_task_button.setEnabled(bool(allow_cancel))
        self.statusBar.showMessage(text)

    def _set_remote_actions_enabled(self, enabled: bool):
        for action_name in (
            "sync_official_tools_action",
            "check_update_action",
            "one_click_update_action",
        ):
            action = getattr(self, action_name, None)
            if action is not None:
                action.setEnabled(enabled)

    def _run_when_background_tasks_idle(self, callback):
        if callback is None:
            return
        if self._has_active_background_task():
            self._background_idle_callbacks.append(callback)
            return
        try:
            callback()
        except Exception as error:
            logger.error("执行空闲后台回调失败: %s", error)

    def _prompt_close_with_background_task(self):
        dialog = QMessageBox(self)
        dialog.setWindowTitle("后台任务进行中")
        dialog.setText("后台任务仍在运行。你可以取消任务后退出，或隐藏窗口并在任务结束后自动退出。")
        cancel_button = dialog.addButton("取消任务并退出", QMessageBox.AcceptRole)
        hide_button = dialog.addButton("后台完成后退出", QMessageBox.DestructiveRole)
        wait_button = dialog.addButton("继续等待", QMessageBox.RejectRole)
        dialog.setDefaultButton(wait_button)

        theme_manager = ThemeManager()
        dialog.setStyleSheet(theme_manager.get_messagebox_style(self.current_theme))
        dialog.exec_()

        clicked = dialog.clickedButton()
        if clicked is cancel_button:
            return "cancel_and_close"
        if clicked is hide_button:
            return "close_after_finish"
        return "wait"

    def _start_background_task(self, task_name, func, on_success, on_error, status_message, cancel_message=None):
        if self._has_active_background_task():
            self.statusBar.showMessage("当前有后台任务正在运行，请稍候。", 5000)
            return False

        thread = QThread(self)
        worker = CallableWorker(func)
        worker.moveToThread(thread)
        self._background_tasks[task_name] = {
            "thread": thread,
            "worker": worker,
            "on_success": on_success,
            "on_error": on_error,
            "status_message": status_message,
            "cancel_message": cancel_message or "正在取消后台任务...",
            "cancel_requested": False,
        }

        self._set_remote_actions_enabled(False)
        self._set_background_task_status(status_message, allow_cancel=True)

        thread.started.connect(worker.run)
        worker.finished.connect(lambda result, name=task_name: self._on_background_task_success(name, result))
        worker.error.connect(lambda error, name=task_name: self._on_background_task_error(name, error))
        worker.progress.connect(lambda message, name=task_name: self._on_background_task_progress(name, message))
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda name=task_name: self._on_background_task_finished(name))
        thread.start()
        return True

    def _get_background_task(self, worker):
        for task_name, task in self._background_tasks.items():
            if task.get("worker") is worker:
                return task_name, task
        return None, None

    def _request_background_task_cancellation(self):
        if not self._has_active_background_task():
            return False

        requested = False
        for task in self._background_tasks.values():
            if task.get("cancel_requested"):
                continue
            task["cancel_requested"] = True
            worker = task.get("worker")
            if worker is not None:
                worker.request_cancellation()
            self._set_background_task_status(task.get("cancel_message"), allow_cancel=False)
            requested = True
        return requested

    def on_cancel_background_task(self):
        if not self._request_background_task_cancellation():
            self.statusBar.showMessage("当前没有可取消的后台任务。", 3000)

    def _on_background_task_progress(self, task_name, message):
        task = self._background_tasks.get(task_name)
        if task is None:
            return
        task["status_message"] = str(message or "").strip() or task.get("status_message", "")
        self._set_background_task_status(
            task["status_message"],
            allow_cancel=not task.get("cancel_requested"),
        )

    def _on_background_task_success(self, task_name, result):
        task = self._background_tasks.get(task_name)
        if task is None:
            return
        if task.get("cancel_requested") or self._close_after_background_tasks:
            logger.info("后台任务完成但结果已忽略(%s)。", task_name)
            return
        callback = task.get("on_success")
        if callback is None:
            return
        try:
            callback(result)
        except Exception as error:
            logger.error("后台任务成功回调失败(%s): %s", task_name, error)

    def _on_background_task_error(self, task_name, error):
        task = self._background_tasks.get(task_name)
        if task is None:
            return
        if isinstance(error, OperationCancelledError):
            logger.info("后台任务已取消(%s): %s", task_name, error)
            if not self._close_after_background_tasks:
                self.statusBar.showMessage(str(error), 5000)
            return
        if self._close_after_background_tasks:
            logger.info("后台任务在退出流程中失败(%s): %s", task_name, error)
            return
        callback = task.get("on_error")
        if callback is None:
            return
        try:
            callback(error)
        except Exception as callback_error:
            logger.error("后台任务失败回调失败(%s): %s", task_name, callback_error)

    def _on_background_task_finished(self, task_name):
        task = self._background_tasks.pop(task_name, None)
        if not self._has_active_background_task():
            self._set_remote_actions_enabled(True)
            self._set_background_task_status("", allow_cancel=False)
            while self._background_idle_callbacks and not self._has_active_background_task():
                pending_callbacks = self._background_idle_callbacks
                self._background_idle_callbacks = []
                for callback in pending_callbacks:
                    try:
                        callback()
                    except Exception as error:
                        logger.error("执行后台任务收尾回调失败: %s", error)
                    if self._has_active_background_task():
                        break
            if self._close_after_background_tasks:
                self._close_after_background_tasks = False
                QTimer.singleShot(0, self.close)
                return
            if task and task.get("cancel_requested"):
                self.statusBar.showMessage("后台任务已取消。", 5000)

    def _stop_background_tasks(self):
        for task in list(self._background_tasks.values()):
            thread = task.get("thread")
            if thread is None:
                continue
            try:
                worker = task.get("worker")
                if worker is not None:
                    worker.request_cancellation()
                if thread.isRunning():
                    thread.quit()
                    thread.wait(3000)
            except RuntimeError:
                continue
    
    def _get_splitter_sizes(self, layout_name):
        total_width = max(self.width(), self.splitter.size().width(), self.splitter.width(), 1)

        if layout_name == 'favorites':
            return [0, 0, total_width]

        if layout_name == 'category':
            category_width = max(self.MIN_CATEGORY_WIDTH, int(total_width * 0.22))
            subcategory_width = max(self.MIN_SUBCATEGORY_WIDTH, int(total_width * 0.18))
        else:
            category_width = max(self.MIN_CATEGORY_WIDTH, int(total_width * 0.20))
            subcategory_width = max(self.MIN_SUBCATEGORY_WIDTH, int(total_width * 0.16))

        max_sidebar_width = max(self.MIN_CONTENT_WIDTH, total_width - self.MIN_CONTENT_WIDTH)
        sidebar_width = min(category_width + subcategory_width, max_sidebar_width)
        if sidebar_width <= 0:
            return [category_width, subcategory_width, self.MIN_CONTENT_WIDTH]

        category_ratio = category_width / max(1, category_width + subcategory_width)
        category_width = int(sidebar_width * category_ratio)
        subcategory_width = sidebar_width - category_width
        content_width = max(self.MIN_CONTENT_WIDTH, total_width - sidebar_width)

        if content_width + sidebar_width > total_width:
            overflow = content_width + sidebar_width - total_width
            reduce_sub = min(overflow, max(0, subcategory_width - self.MIN_SUBCATEGORY_WIDTH))
            subcategory_width -= reduce_sub
            overflow -= reduce_sub
            if overflow > 0:
                reduce_cat = min(overflow, max(0, category_width - self.MIN_CATEGORY_WIDTH))
                category_width -= reduce_cat
                overflow -= reduce_cat
            content_width = max(self.MIN_CONTENT_WIDTH, total_width - category_width - subcategory_width)

        return [category_width, subcategory_width, content_width]

    def _apply_splitter_layout(self, layout_name):
        if not hasattr(self, 'splitter'):
            return
        self.splitter.setSizes(self._get_splitter_sizes(layout_name))

    def _apply_card_layout_mode(self):
        if not hasattr(self, 'tool_container'):
            return
        self.tool_container.set_layout_mode('main')

    def _get_current_layout_name(self):
        if self.is_in_favorites:
            return 'favorites'
        return 'category'

    def _apply_view_state_layout(self):
        if self.is_in_favorites:
            self.category_view.hide()
            self.subcategory_view.hide()
            self.favorites_button.setText("返回")
            if hasattr(self, 'tool_stack') and hasattr(self, 'favorites_container'):
                self.tool_stack.setCurrentWidget(self.favorites_container)
        else:
            self.category_view.show()
            self.subcategory_view.show()
            self.favorites_button.setText("收藏")
            if hasattr(self, 'tool_stack') and hasattr(self, 'tool_container'):
                self.tool_stack.setCurrentWidget(self.tool_container)

        self._apply_splitter_layout(self._get_current_layout_name())
        self._apply_card_layout_mode()
        if not self.is_in_favorites and hasattr(self, 'tool_container'):
            QTimer.singleShot(0, lambda: self.tool_container.update_card_layout(force=True))

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'tool_container') and not self.is_in_favorites:
            # 首次显示后再按最终窗口宽度重排一次，避免启动时收藏页仍沿用旧列数
            QTimer.singleShot(0, lambda: self.tool_container.update_card_layout(force=True))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_ui_scale_metrics(event.size().width(), event.size().height())
        self._apply_splitter_layout(self._get_current_layout_name())
        if hasattr(self, 'tool_container') and not self.is_in_favorites:
            QTimer.singleShot(0, lambda: self.tool_container.update_card_layout(force=True))

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
        self.handle_category_selected(category_id)

    def on_subcategory_selected(self, category_id, subcategory_id):
        """处理二级分类选择"""
        self.handle_subcategory_selected(category_id, subcategory_id)

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

    def _get_default_downloads_dir(self):
        return os.path.join(os.path.expanduser("~"), "Downloads")

    def _get_last_tianhu_import_path(self):
        stored_value = str(self.settings.value("paths/last_tianhu_import_json", "") or "").strip()
        if stored_value and os.path.exists(stored_value):
            return stored_value
        return self._get_default_downloads_dir()

    def _format_category_stats(self, category_stats, limit=6):
        if not category_stats:
            return ""

        ordered_items = sorted(
            category_stats.items(),
            key=lambda item: (-item[1], str(item[0])),
        )
        lines = ["分类分布："]
        for category_name, count in ordered_items[:limit]:
            lines.append(f"- {category_name}: {count}")

        remaining = len(ordered_items) - limit
        if remaining > 0:
            lines.append(f"- 其余分类: {remaining} 个")
        return "\n".join(lines)

    def on_import_tianhu_tools(self):
        """导入天狐 2.0 工具箱导出配置。"""
        source_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择天狐 2.0 导出配置 JSON",
            self._get_last_tianhu_import_path(),
            "JSON Files (*.json);;All Files (*)",
        )
        if not source_path:
            return

        try:
            result = self.tool_config_exchange.import_tianhu_tools(source_path)
        except (FileNotFoundError, ValueError, PermissionError, OSError) as e:
            logger.error("导入天狐 2.0 工具配置失败: %s", str(e))
            QMessageBox.warning(self, "导入失败", f"导入天狐 2.0 工具配置失败：{e}")
            return

        self.settings.setValue("paths/last_tianhu_import_json", source_path)
        self.refresh_all()
        stats_text = self._format_category_stats(result.get("category_stats") or {})
        message_parts = [
            f"检测版本: 天狐 {result.get('detected_version', '未知')}",
            f"源文件: {result.get('source_path', source_path)}",
            f"总计: {result.get('total', 0)}",
            f"新增: {result.get('imported', 0)}",
            f"跳过重复: {result.get('skipped', 0)}",
        ]
        if result.get("created_placeholder_subcategory"):
            message_parts.append("已创建临时子分类“待分类（天狐导入）”，未识别工具已暂存其中。")
        if stats_text:
            message_parts.append("")
            message_parts.append(stats_text)

        QMessageBox.information(self, "导入完成", "\n".join(message_parts))

    def on_delete_tianhu_tools(self):
        """一键删除当前工具库中所有天狐 2.0 导入工具。"""
        tianhu_tools = self.tool_config_exchange.get_tianhu_tools()
        total = len(tianhu_tools)
        if total <= 0:
            QMessageBox.information(self, "无需删除", "当前工具库中没有天狐 2.0 导入的工具。")
            return

        preview_names = [
            str(tool.get("name", "") or "").strip()
            for tool in tianhu_tools[:6]
            if str(tool.get("name", "") or "").strip()
        ]
        message_lines = [
            f"将删除 {total} 个天狐 2.0 导入工具。",
        ]
        if preview_names:
            message_lines.append("示例：")
            message_lines.extend(f"- {name}" for name in preview_names)
            remaining = total - len(preview_names)
            if remaining > 0:
                message_lines.append(f"- 以及其余 {remaining} 个工具")
        message_lines.append("")
        message_lines.append("此操作不会删除你手动添加或本地配置导入的工具。")
        message_lines.append("确定继续吗？")

        if self._themed_question("确认删除", "\n".join(message_lines)) != QMessageBox.Yes:
            return

        try:
            result = self.tool_config_exchange.remove_tianhu_tools()
        except (PermissionError, OSError, ValueError) as e:
            logger.error("删除天狐 2.0 导入工具失败: %s", str(e))
            QMessageBox.warning(self, "删除失败", f"删除天狐 2.0 导入工具失败：{e}")
            return

        self.refresh_all()
        QMessageBox.information(
            self,
            "删除完成",
            "\n".join([
                f"已删除: {result.get('removed', 0)}",
                f"剩余工具: {result.get('remaining', 0)}",
            ]),
        )

    def on_import_native_tools(self):
        """导入当前工具箱导出的本地配置。"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "导入本地工具配置",
            self._get_default_downloads_dir(),
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return

        try:
            result = self.tool_config_exchange.import_native_tools(file_path)
        except (FileNotFoundError, ValueError, PermissionError, OSError) as e:
            logger.error("导入本地工具配置失败: %s", str(e))
            QMessageBox.warning(self, "导入失败", f"导入本地工具配置失败：{e}")
            return

        self.refresh_all()
        QMessageBox.information(
            self,
            "导入完成",
            "\n".join([
                f"源文件: {file_path}",
                f"总计: {result.get('total', 0)}",
                f"新增: {result.get('imported', 0)}",
                f"跳过重复: {result.get('skipped', 0)}",
            ]),
        )

    def on_export_native_tools(self):
        """导出当前工具箱本地配置。"""
        default_file = os.path.join(self._get_default_downloads_dir(), "zifeiyu-tools-config.json")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出本地工具配置",
            default_file,
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".json"):
            file_path += ".json"

        try:
            result = self.tool_config_exchange.export_native_tools(file_path)
        except (PermissionError, OSError, TypeError, ValueError) as e:
            logger.error("导出本地工具配置失败: %s", str(e))
            QMessageBox.warning(self, "导出失败", f"导出本地工具配置失败：{e}")
            return

        QMessageBox.information(
            self,
            "导出完成",
            "\n".join([
                f"导出文件: {result.get('file_path', file_path)}",
                f"导出数量: {result.get('exported', 0)}",
                "导出模式: 仅配置，不包含使用次数和最近使用记录",
            ]),
        )

    def _get_official_sync_url(self):
        return str(self.settings.value("sync/official_tools_url", "") or "").strip()

    def _is_sync_update_existing_enabled(self):
        value = str(self.settings.value("sync/update_existing", "true") or "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    def on_sync_official_tools(self):
        sync_url = self._get_official_sync_url()
        if not sync_url:
            default_url = "https://raw.githubusercontent.com/zifeiyu-sec/zifeiyuSec-Toolkit/main/data/tools.sync.json"
            url_text, ok = QInputDialog.getText(
                self,
                "同步官方工具库",
                "请输入官方工具库 JSON 地址：",
                text=default_url,
            )
            if not ok:
                return
            sync_url = str(url_text or "").strip()
            if not sync_url:
                QMessageBox.warning(self, "同步失败", "未提供官方工具库地址。")
                return
            self.settings.setValue("sync/official_tools_url", sync_url)

        update_existing = self._is_sync_update_existing_enabled()
        self._start_background_task(
            "sync_official_tools",
            lambda cancel_requested=None, progress_callback=None: self.tool_config_exchange.sync_official_tools_from_url(
                sync_url,
                update_existing=update_existing,
                cancel_requested=cancel_requested,
                progress_callback=progress_callback,
            ),
            on_success=lambda result: self._on_sync_official_tools_success(sync_url, result),
            on_error=self._on_sync_official_tools_error,
            status_message="正在同步官方工具库...",
            cancel_message="正在取消官方工具库同步...",
        )

    def _on_sync_official_tools_success(self, sync_url, result):
        self.refresh_all()
        self.statusBar.showMessage("官方工具库同步完成。", 5000)
        QMessageBox.information(
            self,
            "同步完成",
            "\n".join([
                f"源地址: {result.get('source_url', sync_url)}",
                f"总计: {result.get('total', 0)}",
                f"新增: {result.get('imported', 0)}",
                f"更新: {result.get('updated', 0)}",
                f"跳过: {result.get('skipped', 0)}",
                f"备份: {result.get('backup_path', '')}",
            ]),
        )

    def _on_sync_official_tools_error(self, error):
        logger.error("同步官方工具库失败: %s", str(error))
        self.statusBar.showMessage("官方工具库同步失败。", 5000)
        QMessageBox.warning(self, "同步失败", f"同步官方工具库失败：{error}")

    def _truncate_update_notes(self, notes: str, limit: int = 800) -> str:
        text = str(notes or "").strip()
        if not text:
            return ""
        if len(text) <= limit:
            return text
        return f"{text[:limit]}\n..."

    def _check_update_once(self, show_latest_message: bool = True, show_available_message: bool = True, on_available=None):
        self._start_background_task(
            "check_updates",
            self.update_service.check_for_updates,
            on_success=lambda result: self._on_check_update_success(
                result,
                show_latest_message=show_latest_message,
                show_available_message=show_available_message,
                on_available=on_available,
            ),
            on_error=lambda error: self._on_check_update_error(
                error,
                show_latest_message=show_latest_message,
            ),
            status_message="正在检查更新...",
            cancel_message="正在取消更新检查...",
        )

    def _on_check_update_success(self, result, show_latest_message=True, show_available_message=True, on_available=None):
        update_info, message = result
        self._latest_update_info = update_info
        self.statusBar.showMessage(message, 5000)

        if update_info is None:
            if show_latest_message:
                QMessageBox.information(self, "检查更新", message)
            return

        if show_available_message:
            message_lines = [
                message,
                f"发布时间: {update_info.published_at or '未知'}",
            ]
            if update_info.release_url:
                message_lines.append(f"发布页: {update_info.release_url}")

            notes = self._truncate_update_notes(update_info.notes)
            if notes:
                message_lines.extend(["", "更新说明:", notes])

            QMessageBox.information(self, "发现新版本", "\n".join(message_lines))

        if on_available is not None:
            self._run_when_background_tasks_idle(lambda: on_available(update_info))

    def _on_check_update_error(self, error, show_latest_message=True):
        logger.warning("检查更新失败: %s", error)
        if show_latest_message:
            QMessageBox.warning(self, "检查更新失败", str(error))
        self.statusBar.showMessage("检查更新失败", 5000)

    def _check_updates_on_startup(self):
        self._check_update_once(show_latest_message=False, show_available_message=False)

    def on_check_updates(self):
        self._check_update_once(show_latest_message=True, show_available_message=True)

    def on_one_click_update(self):
        if not self.update_service.can_self_update():
            release_url = self.update_service.get_release_page_url()
            message = "当前运行环境不支持一键更新。\n是否打开发布页手动下载最新版本？"
            if self._themed_question("无法一键更新", message, default=QMessageBox.Yes) == QMessageBox.Yes:
                if release_url:
                    try:
                        webbrowser.open(release_url)
                    except webbrowser.Error as exc:
                        QMessageBox.warning(self, "打开链接失败", f"无法打开发布页: {exc}")
            return

        self._check_update_once(
            show_latest_message=True,
            show_available_message=False,
            on_available=self._confirm_and_start_one_click_update,
        )

    def _confirm_and_start_one_click_update(self, update_info):
        confirm_lines = [
            f"将从 v{self.version} 更新到 v{update_info.latest_version}。",
            "更新程序会在确认后关闭当前窗口并自动重启。",
        ]
        if self.update_service.get_update_mode() == "source":
            confirm_lines.append("当前为源码模式：将覆盖项目目录文件（保留 .runtime 目录）。")
        if update_info.release_url:
            confirm_lines.append(f"发布页: {update_info.release_url}")

        if self._themed_question("确认一键更新", "\n".join(confirm_lines), default=QMessageBox.No) != QMessageBox.Yes:
            return

        self._start_background_task(
            "start_one_click_update",
            lambda cancel_requested=None, progress_callback=None: self.update_service.start_one_click_update(
                update_info,
                cancel_requested=cancel_requested,
                progress_callback=progress_callback,
            ),
            on_success=self._on_one_click_update_success,
            on_error=self._on_one_click_update_error,
            status_message="正在下载并准备更新...",
            cancel_message="正在取消一键更新...",
        )

    def _on_one_click_update_success(self, result_message):
        QMessageBox.information(self, "更新流程已启动", result_message)
        self._run_when_background_tasks_idle(self.close)

    def _on_one_click_update_error(self, error):
        logger.error("一键更新失败: %s", error)
        self.statusBar.showMessage("一键更新失败", 5000)
        QMessageBox.warning(self, "一键更新失败", str(error))

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
        dialog = ToolConfigDialog(
            tool_data=copy.deepcopy(tool),
            categories=categories,
            parent=self,
            theme_name=self.current_theme,
        )
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
        """处理运行工具的行为"""
        tool_id = tool_data.get('id')
        tool_name = tool_data.get('name', '未知工具')
        path = (tool_data.get('path') or '').strip()
        working_directory = tool_data.get('working_directory', '')
        run_in_terminal = tool_data.get('run_in_terminal', False)

        logger.info("启动工具: %s, 路径: %s", tool_name, path)
        result = self.tool_launcher.launch_tool(
            tool_data=tool_data,
            path=path,
            working_dir=working_directory,
            run_in_terminal=run_in_terminal,
        )

        if result.get('success'):
            launch_mode = result.get('launch_mode') or 'default'
            command_preview = result.get('command_preview') or result.get('path') or path
            self.statusBar.showMessage(f"已启动 {tool_name}（{launch_mode}）", 5000)
            logger.info(
                "工具启动成功: %s, 模式: %s, 工作目录: %s, 命令: %s",
                tool_name,
                launch_mode,
                result.get('working_directory', ''),
                command_preview,
            )
            if tool_id:
                try:
                    logger.info("记录工具使用统计: %s (ID: %s)", tool_name, tool_id)
                    self.data_manager.update_tool_usage(tool_id)
                    self._schedule_usage_flush()
                except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
                    logger.warning("更新工具使用统计失败: %s", str(e))
            return

        error_message = result.get('error_message') or '未知错误'
        launch_mode = result.get('launch_mode') or 'unknown'
        diagnostic_lines = [
            f"工具名称: {tool_name}",
            f"工具路径: {result.get('path') or path or '未配置'}",
            f"工作目录: {result.get('working_directory') or working_directory or '默认（工具所在目录）'}",
            f"启动模式: {launch_mode}",
        ]
        command_preview = result.get('command_preview')
        if command_preview:
            diagnostic_lines.append(f"命令预览: {command_preview}")
        if result.get('requires_elevation'):
            diagnostic_lines.append("提示: 当前工具可能需要管理员权限。")

        logger.error("启动工具失败: %s, 错误: %s", tool_name, error_message)
        QMessageBox.warning(
            self,
            "运行失败",
            f"启动工具失败: {error_message}\n\n" + "\n".join(diagnostic_lines),
        )

    def _open_local(self, path: str, working_dir: str = None, run_in_terminal: bool = False, tool_name: str = '未知工具', is_web: bool = False, tool_data: dict = None) -> bool:
        result = self.tool_launcher.launch_tool(
            tool_data=tool_data,
            path=path,
            working_dir=working_dir,
            run_in_terminal=run_in_terminal,
        )
        return bool(result.get('success'))

    def on_toggle_favorite(self, tool_id):
        """切换收藏状态"""
        if tool_id:
            self.data_manager.toggle_favorite(tool_id)
            self.refresh_current_view()

    def on_tool_order_changed(self, ordered_tool_ids):
        """处理工具卡片拖拽排序后的持久化"""
        if not ordered_tool_ids:
            return

        if self.data_manager.reorder_tools(ordered_tool_ids):
            self.refresh_current_view()

    def on_edit_background(self, tool_data):
        """处理编辑背景图片"""
        tool_id = tool_data['id']
        tool = self.data_manager.get_tool_by_id(tool_id)
        if not tool:
            return
        tool = copy.deepcopy(tool)
        
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
        dialog_style = self._get_dialog_style_fragment()
        if dialog_style:
            dialog.setStyleSheet(dialog_style)
        
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
    
    def on_new_subcategory(self, *args):
        """处理新建子分类

        *args 用于兼容来自 CategoryView/SubcategoryView 带参数的信号，
        实际逻辑仍然从当前选中的分类读取。"""
        current_category = self.category_view.current_category
        if not current_category:
            QMessageBox.warning(self, "警告", "请先选择一个主分类！")
            return

        dialog = QInputDialog(self)
        dialog.setWindowTitle("新建子分类")
        dialog.setLabelText("请输入子分类名称:")
        dialog_style = self._get_dialog_style_fragment()
        if dialog_style:
            dialog.setStyleSheet(dialog_style)

        ok = dialog.exec_()
        subcategory_name = dialog.textValue()

        if ok and subcategory_name:
            subcategory = {"name": subcategory_name}
            if self.data_manager.add_subcategory(current_category, subcategory):
                QMessageBox.information(self, "成功", "子分类创建成功！")
                self.category_view.refresh()
            else:
                QMessageBox.warning(self, "失败", "子分类创建失败！")
    
    def on_delete_category(self, *args):
        """处理删除分类

        *args 用于兼容来自 CategoryView 带分类ID参数的信号，
        实际删除逻辑仍然使用当前选中的分类。"""
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
                self._display_tools([])
            else:
                QMessageBox.warning(self, "失败", message)
    
    def on_delete_subcategory(self, *args):
        """处理删除子分类

        *args 用于兼容来自 SubcategoryView 带子分类ID参数的信号，
        实际删除逻辑仍然使用当前选中的子分类。"""
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
    
    def on_show_notes(self):
        """打开笔记列表。"""
        dialog = NotesListDialog(repo_root=self.config_dir, theme_name=self.current_theme, parent=self)
        dialog.exec_()
        self.refresh_current_view()

    def on_show_data_health(self):
        """打开数据体检对话框，并在选择后定位到工具所在分类。"""
        dialog = DataHealthDialog(self.data_manager, parent=self)
        if dialog.exec_() != QDialog.Accepted:
            return

        selected_tool_id = dialog.get_selected_tool_id()
        if selected_tool_id is None:
            return

        self.navigate_to_tool(selected_tool_id)

    def navigate_to_tool(self, tool_id):
        """定位到指定工具所在的分类/子分类，并切换到对应列表。"""
        tool = self.data_manager.get_tool_by_id(tool_id)
        if not tool:
            QMessageBox.warning(self, "定位失败", f"未找到 ID 为 {tool_id} 的工具。")
            return False

        category_id = tool.get('category_id')
        subcategory_id = tool.get('subcategory_id')
        if category_id is None:
            QMessageBox.warning(self, "定位失败", f"工具“{tool.get('name', '未知工具')}”没有有效分类。")
            return False

        self.is_in_favorites = False
        self.category_view.show()
        self.subcategory_view.show()
        self.current_view_mode = "category"
        self._apply_view_state_layout()

        self.category_view.refresh()
        if not self.category_view.select_category(category_id):
            QMessageBox.warning(self, "定位失败", f"未找到 ID 为 {category_id} 的分类。")
            return False

        if subcategory_id is not None:
            self.subcategory_view.load_subcategories(category_id)
            if not self.subcategory_view.select_subcategory(subcategory_id):
                self.on_category_selected(category_id)
                QMessageBox.warning(self, "定位提示", f"未找到 ID 为 {subcategory_id} 的子分类，已定位到主分类。")
                return False
        else:
            self.on_category_selected(category_id)

        return True

    def on_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于子非鱼安全工具箱", f"子非鱼安全工具箱 v{self.version}\n\n一个简单易用的本地工具管理平台")
    
    def refresh_tool_count(self):
        """刷新工具数量显示"""
        container = self._get_active_tool_container()
        count = container.get_tool_count() if container is not None else 0
        self.tool_count_label.setText(f"工具数量: {count}")
    
    def refresh_current_view(self):
        """刷新当前视图

        注意：不要在这里切换收藏状态，只根据当前状态刷新内容，
        避免在收藏页运行工具或刷新时意外退出收藏页。"""
        self.handle_refresh_current_view()

    def refresh_all(self):
        """刷新所有视图"""
        self.handle_refresh_all()
    
    def switch_theme(self, theme_name):
        """切换主题"""
        if theme_name not in ThemeManager().themes:
            theme_name = "dark_green"
        self.current_theme = theme_name
        self.settings.setValue("theme", theme_name)
        self._sync_theme_action_state()
        self.apply_styles()
        # 刷新UI组件主题
        self.refresh_ui_with_theme()

    def _sync_theme_action_state(self):
        """同步主题菜单选中状态"""
        if hasattr(self, "dark_green_theme_action"):
            self.dark_green_theme_action.setChecked(self.current_theme == "dark_green")
        if hasattr(self, "blue_white_theme_action"):
            self.blue_white_theme_action.setChecked(self.current_theme == "blue_white")
        if hasattr(self, "purple_neon_theme_action"):
            self.purple_neon_theme_action.setChecked(self.current_theme == "purple_neon")
        if hasattr(self, "red_orange_theme_action"):
            self.red_orange_theme_action.setChecked(self.current_theme == "red_orange")

    def refresh_ui_with_theme(self):
        """刷新UI组件主题"""
        if hasattr(self, 'tool_container'):
            self.tool_container.set_theme(self.current_theme)
        if hasattr(self, 'favorites_container'):
            self.favorites_container.set_theme(self.current_theme)

    def _schedule_usage_flush(self):
        """延迟合并写回工具使用统计。"""
        if hasattr(self, "usage_flush_timer"):
            self.usage_flush_timer.start(self.usage_flush_interval_ms)

    def _flush_pending_usage_updates(self):
        """将缓存的使用统计批量写回磁盘。"""
        try:
            self.data_manager.flush_pending_usage_updates()
        except Exception as e:
            logger.warning("写回工具使用统计失败: %s", str(e))

    def closeEvent(self, event):
        """在主窗口退出前清理后台 Qt 资源。"""
        if self._has_active_background_task():
            choice = self._prompt_close_with_background_task()
            if choice == "cancel_and_close":
                self._close_after_background_tasks = True
                self._request_background_task_cancellation()
                self.hide()
            elif choice == "close_after_finish":
                self._close_after_background_tasks = True
                self.hide()
            else:
                self.statusBar.showMessage("后台任务正在运行，请稍候后再关闭。", 5000)
            event.ignore()
            return

        try:
            if hasattr(self, 'usage_flush_timer'):
                self.usage_flush_timer.stop()
            self._flush_pending_usage_updates()
        except Exception as e:
            logger.warning("关闭前写回工具使用统计失败: %s", str(e))

        try:
            if hasattr(self, 'data_manager') and self.data_manager is not None:
                self.data_manager.shutdown()
        except Exception as e:
            logger.warning("关闭数据加载线程失败: %s", str(e))

        try:
            self._stop_background_tasks()
        except Exception as e:
            logger.warning("关闭后台任务失败: %s", str(e))

        try:
            icon_loader.shutdown()
        except Exception as e:
            logger.warning("关闭图标加载线程池失败: %s", str(e))

        super().closeEvent(event)

    def _get_dialog_style_fragment(self):
        """获取对话框样式片段，用于QInputDialog等"""
        theme_manager = ThemeManager()
        return theme_manager.get_dialog_style(self.current_theme)
    
    def _themed_question(self, title, text, default=QMessageBox.No):
        """显示带主题样式的确认对话框"""
        dialog = QMessageBox(self)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dialog.setDefaultButton(default)
        
        theme_manager = ThemeManager()
        dialog.setStyleSheet(theme_manager.get_messagebox_style(self.current_theme))
        
        return dialog.exec_()

# 运行主窗口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具配置对话框模块，用于添加和编辑工具配置信息。"""
import os
import re
import shutil
import hashlib
from urllib.parse import urlparse

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget, QScrollArea
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPushButton, QComboBox
from PyQt5.QtWidgets import QCheckBox, QGroupBox, QGridLayout, QSpinBox
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication, QInputDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QFileInfo, QSize
from PyQt5.QtWidgets import QFileIconProvider
from core.logger import logger
from core.runtime_paths import ensure_runtime_dir, resolve_icon_path_value
from core.style_manager import ThemeManager
from core.ui_scale import preferred_dialog_size, scaled
from ui.favicon_downloader import FaviconDownloader

class ToolConfigDialog(QDialog):
    """工具配置对话框，用于添加或编辑工具信息"""
    def __init__(self, tool_data=None, categories=None, parent=None, theme_name=None):
        super().__init__(parent)
        # 支持主题传入，默认深色主题
        self.current_theme = theme_name or 'dark_green'
        self.tool_data = tool_data or self._create_empty_tool()
        self.categories = categories or []
        self.icon_dir = os.fspath(ensure_runtime_dir("resources", "icons"))
        self.default_icon_name = "default_icon"
        self.selected_icon_name = self._normalize_icon_name(self.tool_data.get("icon"))
        self.downloader = None  # 初始化下载器属性
        self._manual_icon_download_requested = False
        self.init_ui()
        # 在 UI 建立后应用主题样式
        try:
            self.apply_theme_styles()
        except (RuntimeError, TypeError, AttributeError) as exc:
            logger.debug("应用工具配置对话框主题失败: %s", exc)
    
    def _create_empty_tool(self):
        """创建一个空的工具数据字典"""
        return {
            "id": None,
            "name": "",
            "path": "",
            "description": "",
            "category_id": None,
            "subcategory_id": None,
            "background_image": "",
            "icon": "",  # 工具图标路径
            "is_favorite": False,
            "arguments": "",  # 命令行参数
            "working_directory": "",  # 工作目录
            "run_in_terminal": False,  # 是否在终端中运行
            "is_web_tool": False  # 是否为网页工具
        }
    
    def init_ui(self):
        """初始化对话框界面"""
        self.setWindowTitle("编辑工具配置" if self.tool_data["id"] else "新建工具")
        dialog_size = preferred_dialog_size(self, base_width=820, base_height=760)
        self.resize(dialog_size)
        self.setMinimumSize(scaled(640, 1.0), scaled(560, 1.0))

        self._dialog_scale = max(0.9, min(1.25, dialog_size.width() / 820.0))
        button_height = scaled(32, self._dialog_scale)
        icon_column_width = scaled(150, self._dialog_scale)
        icon_preview_size = scaled(72, self._dialog_scale)
        description_height = scaled(110, self._dialog_scale)
        spacing = scaled(8, self._dialog_scale)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(spacing * 2, spacing * 2, spacing * 2, spacing * 2)
        main_layout.setSpacing(spacing)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_layout.addWidget(scroll_area, 1)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(spacing)

        basic_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(spacing)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(spacing)
        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(spacing)
        form_layout.setVerticalSpacing(spacing)
        form_layout.setColumnStretch(1, 1)

        form_layout.addWidget(QLabel("工具类型:"), 0, 0)
        self.tool_type_combo = QComboBox()
        self.tool_type_combo.addItem("本地工具", False)
        self.tool_type_combo.addItem("网页工具", True)
        if self.tool_data.get("is_web_tool", False):
            self.tool_type_combo.setCurrentIndex(1)
        self.tool_type_combo.currentIndexChanged.connect(self.on_tool_type_changed)
        form_layout.addWidget(self.tool_type_combo, 0, 1)

        form_layout.addWidget(QLabel("名称:"), 1, 0)
        self.name_edit = QLineEdit(self.tool_data["name"])
        form_layout.addWidget(self.name_edit, 1, 1)

        self.path_label = QLabel("工具位置:")
        form_layout.addWidget(self.path_label, 2, 0)
        path_layout = QHBoxLayout()
        path_layout.setSpacing(spacing)
        self.path_edit = QLineEdit(self.tool_data["path"])
        self.path_edit.textChanged.connect(self.on_url_text_changed)
        self.path_edit.editingFinished.connect(self.on_url_editing_finished)
        self.favicon_timer = QTimer()
        self.favicon_timer.setSingleShot(True)
        self.favicon_timer.setInterval(500)
        self.favicon_timer.timeout.connect(self.on_favicon_timer_timeout)
        path_layout.addWidget(self.path_edit, 1)
        self.browse_button = QPushButton("浏览")
        self.browse_button.setMinimumHeight(button_height)
        self.browse_button.clicked.connect(self.on_browse_path)
        path_layout.addWidget(self.browse_button)
        form_layout.addLayout(path_layout, 2, 1)

        top_layout.addLayout(form_layout, 1)

        icon_column = QWidget()
        icon_column.setMinimumWidth(icon_column_width)
        icon_column.setMaximumWidth(icon_column_width)
        icon_container = QVBoxLayout(icon_column)
        icon_container.setAlignment(Qt.AlignTop)
        icon_container.setSpacing(spacing)
        icon_container.setContentsMargins(spacing, 0, 0, 0)
        icon_label = QLabel("工具图标:")
        icon_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(icon_preview_size, icon_preview_size)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        self.icon_preview.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.icon_preview.setStyleSheet("border: 1px solid rgba(255,255,255,0.15); border-radius: 12px;")
        self._update_icon_preview()
        self.icon_button = QPushButton("选择图标")
        self.icon_button.setMinimumHeight(button_height)
        self.icon_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.icon_button.clicked.connect(self.on_select_icon)
        self.icon_url_button = QPushButton("URL 下载")
        self.icon_url_button.setMinimumHeight(button_height)
        self.icon_url_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.icon_url_button.clicked.connect(self.on_download_icon_from_url)
        icon_container.addWidget(icon_label)
        icon_container.addWidget(self.icon_preview, alignment=Qt.AlignLeft)
        icon_container.addWidget(self.icon_button)
        icon_container.addWidget(self.icon_url_button)
        icon_container.addStretch()
        top_layout.addWidget(icon_column, 0, Qt.AlignTop)

        basic_layout.addLayout(top_layout)

        desc_label = QLabel("工具介绍:")
        self.description_edit = QTextEdit(self.tool_data["description"])
        self.description_edit.setMinimumHeight(description_height)
        self.description_edit.setMaximumHeight(description_height + scaled(36, self._dialog_scale))
        basic_layout.addWidget(desc_label)
        basic_layout.addWidget(self.description_edit)

        if self.categories:
            category_layout = QGridLayout()
            category_layout.setHorizontalSpacing(spacing)
            category_layout.setVerticalSpacing(spacing)
            category_layout.setColumnStretch(1, 1)

            category_layout.addWidget(QLabel("一级分类:"), 0, 0)
            self.category_combo = QComboBox()
            self.category_map = {}
            for category in self.categories:
                self.category_combo.addItem(category["name"], category["id"])
                self.category_map[category["id"]] = category
            if self.tool_data["category_id"] and self.tool_data["category_id"] in self.category_map:
                index = self.category_combo.findData(self.tool_data["category_id"])
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            self.category_combo.currentIndexChanged.connect(self.on_category_changed)
            category_layout.addWidget(self.category_combo, 0, 1)

            category_layout.addWidget(QLabel("二级分类:"), 1, 0)
            self.subcategory_combo = QComboBox()
            self.subcategory_combo.addItem("无", None)
            category_layout.addWidget(self.subcategory_combo, 1, 1)

            basic_layout.addLayout(category_layout)
            self.on_category_changed(self.category_combo.currentIndex())

        basic_group.setLayout(basic_layout)
        content_layout.addWidget(basic_group)

        run_group = QGroupBox("运行配置")
        run_layout = QGridLayout()
        run_layout.setHorizontalSpacing(spacing)
        run_layout.setVerticalSpacing(spacing)

        run_layout.addWidget(QLabel("运行命令/参数:"), 0, 0)
        arguments_value = self.tool_data.get("arguments", "")
        if isinstance(arguments_value, list):
            arguments_value = " ".join(str(arg) for arg in arguments_value)
        self.args_edit = QLineEdit(arguments_value)
        self.args_edit.setPlaceholderText("仅在终端工具模式下生效，例如: httpx.exe -h")
        self.args_edit.setToolTip("仅当工具类型标签为“终端”或勾选“在终端中运行”时生效；点击‘打开工具’会在工作目录打开终端并执行这里配置的命令，可用 {path} 引用工具路径。非终端工具不会使用这里的内容。")
        run_layout.addWidget(self.args_edit, 0, 1)

        self.run_in_terminal_check = QCheckBox("在终端中运行")
        self.run_in_terminal_check.setChecked(self.tool_data.get("run_in_terminal", False))
        self.run_in_terminal_check.setToolTip("启用后，‘打开工具’会按终端工具处理；‘打开命令行’只打开终端，不会执行这里配置的命令。")
        run_layout.addWidget(self.run_in_terminal_check, 1, 1, alignment=Qt.AlignLeft)

        run_group.setLayout(run_layout)
        content_layout.addWidget(run_group)

        settings_group = QGroupBox("其他设置")
        settings_layout = QGridLayout()
        settings_layout.setHorizontalSpacing(spacing)
        settings_layout.setVerticalSpacing(spacing)

        self.favorite_check = QCheckBox("添加到收藏")
        self.favorite_check.setChecked(self.tool_data.get("is_favorite", False))
        settings_layout.addWidget(self.favorite_check, 0, 1, alignment=Qt.AlignLeft)

        settings_layout.addWidget(QLabel("自定义类型标签:"), 1, 0)
        self.type_label_edit = QLineEdit(self.tool_data.get("type_label", ""))
        self.type_label_edit.setPlaceholderText("例如: 终端 / 红队综合 / 脚本工具 / 文档")
        self.type_label_edit.setToolTip("填写“终端”后，工具会按终端类处理；点击‘打开工具’时会在终端中执行运行配置命令。")
        settings_layout.addWidget(self.type_label_edit, 1, 1)

        settings_group.setLayout(settings_layout)
        content_layout.addWidget(settings_group)
        content_layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(spacing)
        button_layout.addStretch()

        cancel_button = QPushButton("取消")
        cancel_button.setMinimumHeight(button_height)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("保存")
        save_button.setMinimumHeight(button_height)
        save_button.setDefault(True)
        save_button.clicked.connect(self.on_save)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

    def on_tool_type_changed(self, index):
        """处理工具类型变更事件"""
        is_web_tool = self.tool_type_combo.itemData(index)
        if is_web_tool:
            self.path_label.setText("URL地址:")
            self.browse_button.setText("验证")
            # 如果已经输入了URL，尝试自动下载favicon
            url = self.path_edit.text().strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                # 使用延迟计时器和后台线程，避免切换时卡死
                self.favicon_timer.start()
        else:
            self.path_label.setText("工具位置:")
            self.browse_button.setText("浏览")
            # 清除可能的计时器
            self.favicon_timer.stop()
            self._stop_active_downloader()

    def set_theme(self, theme_name: str):
        """外部调用用于切换对话框主题"""
        self.current_theme = theme_name or 'dark_green'
        self.apply_theme_styles()

    def apply_theme_styles(self):
        """根据当前主题应用 QSS 样式（仅影响本对话框内控件）"""
        theme_manager = ThemeManager()
        style = theme_manager.get_dialog_style(self.current_theme)
        self.setStyleSheet(style)

        # 单独处理 Icon preview
        border_radius = max(10, self.icon_preview.width() // 5)
        if self.current_theme == 'blue_white':
            self.icon_preview.setStyleSheet(f'border: 1px solid rgba(3,105,161,0.12); border-radius: {border_radius}px;')
        else:
            self.icon_preview.setStyleSheet(f'border: 1px solid rgba(255,255,255,0.12); border-radius: {border_radius}px;')
    
    def on_url_text_changed(self, text):
        """当URL文本改变时，重置计时器"""
        is_web_tool = self.tool_type_combo.currentData()
        if is_web_tool and text.strip():
            # 重置计时器
            self.favicon_timer.start()
        else:
            # 如果不是网页工具或文本为空，停止计时器
            self.favicon_timer.stop()
            self._stop_active_downloader()
    
    def on_favicon_timer_timeout(self):
        """当计时器超时后，执行favicon下载"""
        is_web_tool = self.tool_type_combo.currentData()
        if is_web_tool:
            url = self.path_edit.text().strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                self._async_download_favicon(url)
    
    def on_favicon_download_finished(self, favicon_name):
        """处理favicon下载完成事件"""
        manual_request = self._manual_icon_download_requested
        self._manual_icon_download_requested = False
        download_succeeded = False
        try:
            if favicon_name and isinstance(favicon_name, str):
                # 验证文件名格式是否有效
                if not any(favicon_name.endswith(ext) for ext in ['.ico', '.png', '.svg', '.jpg', '.jpeg']):
                    # 无效的图标文件扩展名，不使用该图标
                    favicon_name = ""
                else:
                    # 验证文件是否真正存在
                    icon_path = os.path.join(self.icon_dir, favicon_name)
                    if os.path.exists(icon_path) and os.path.isfile(icon_path):
                        # 选中该图标名称并更新预览
                        self.selected_icon_name = favicon_name
                        self._update_icon_preview()
                        download_succeeded = True
                
        except Exception as e:
            # 捕获所有异常，防止因favicon处理问题导致崩溃
            logger.warning("处理 favicon 下载结果失败: %s", e)
        finally:
            if manual_request and not download_succeeded:
                QMessageBox.warning(self, "下载失败", "无法从该 URL 下载可用图标，请检查链接是否为可直接访问的图片地址。")
    
    def on_url_editing_finished(self):
        """当URL输入完成后自动尝试下载favicon"""
        # 不再直接调用，改为由计时器处理
        pass
    
    def _async_download_favicon(self, url):
        """异步下载favicon图标"""
        try:
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                self._manual_icon_download_requested = False
                return

            self._stop_active_downloader(wait_ms=150)

            self.downloader = FaviconDownloader(self, url, self.icon_dir)
            self.downloader.download_finished.connect(self.on_favicon_download_finished)
            self.downloader.start()
        except Exception as exc:
            self._manual_icon_download_requested = False
            logger.warning("异步下载 favicon 失败 %s: %s", url, exc)

    def _stop_active_downloader(self, wait_ms=0):
        downloader = getattr(self, 'downloader', None)
        if downloader is None:
            return

        self.downloader = None

        try:
            downloader.download_finished.disconnect(self.on_favicon_download_finished)
        except (TypeError, RuntimeError):
            pass

        try:
            downloader.requestInterruption()
        except Exception:
            pass

        is_running = False
        try:
            is_running = downloader.isRunning()
        except RuntimeError:
            return

        if is_running:
            try:
                downloader.quit()
            except RuntimeError:
                return

            if wait_ms > 0:
                try:
                    downloader.wait(wait_ms)
                    is_running = downloader.isRunning()
                except RuntimeError:
                    is_running = False

        if is_running:
            try:
                downloader.setParent(None)
            except RuntimeError:
                return
            try:
                downloader.finished.connect(downloader.deleteLater)
            except (TypeError, RuntimeError):
                pass
            return

        try:
            downloader.deleteLater()
        except RuntimeError:
            pass

    def _cleanup_async_resources(self):
        self._manual_icon_download_requested = False
        try:
            if hasattr(self, 'favicon_timer') and self.favicon_timer is not None:
                self.favicon_timer.stop()
        except RuntimeError:
            pass
        self._stop_active_downloader(wait_ms=150)

    def on_download_icon_from_url(self):
        """从指定图片 URL 下载图标到当前配置目录。"""
        url, ok = QInputDialog.getText(self, "从 URL 下载图标", "请输入图标图片 URL：")
        if not ok:
            return

        url = str(url or "").strip()
        if not url:
            return

        if not self.validate_url(url):
            QMessageBox.warning(self, "警告", "图标 URL 格式不正确，请输入完整的 http:// 或 https:// 地址。")
            return

        self._manual_icon_download_requested = True
        self._async_download_favicon(url)
    
    def validate_url(self, url):
        """验证URL格式是否正确"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
        except (ValueError, AttributeError):
            return False
    
    def on_browse_path(self):
        """浏览工具路径或验证URL"""
        try:
            is_web_tool = self.tool_type_combo.currentData()
            
            if is_web_tool:
                # 验证URL
                url = self.path_edit.text().strip()
                if not url:
                    QMessageBox.warning(self, "警告", "请输入URL地址！")
                    return
                
                # 严格验证URL格式
                if not (url.startswith("http://") or url.startswith("https://")):
                    QMessageBox.warning(self, "警告", "URL地址必须以http://或https://开头！")
                    return
                
                if not self.validate_url(url):
                    QMessageBox.warning(self, "警告", "URL格式不正确，请检查地址是否完整！")
                    return
                
                QMessageBox.information(self, "信息", "URL格式验证通过！")
                # 尝试抓取网站 favicon 并显示为图标预览
                # 使用现有的异步下载方法
                self._async_download_favicon(url)
            else:
                # 浏览本地文件或目录
                # 允许用户选择文件或目录
                path, _ = QFileDialog.getOpenFileName(
                    self, "选择工具或目录", 
                    os.path.dirname(self.path_edit.text()) or ".",
                    "常用工具文件 (*.exe *.bat *.cmd *.py *.ps1 *.vbs *.jar *.html *.htm);;所有文件 (*.*)"
                )
                
                # 如果没有选择文件，尝试选择目录
                if not path:
                    path = QFileDialog.getExistingDirectory(
                        self, "选择目录", 
                        os.path.dirname(self.path_edit.text()) or "."
                    )
                
                if path:
                    self.path_edit.setText(path)
        except Exception as e:
            # 捕获所有异常，防止因浏览路径或验证URL过程中的问题导致崩溃
            QMessageBox.warning(self, "错误", f"操作失败: {e}")

    def on_select_icon(self):
        """选择工具图标"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图标",
            self.icon_dir,
            "图标文件 (*.png *.jpg *.jpeg *.svg *.ico);;所有文件 (*.*)",
        )
        if file_path:
            # 允许选择任意目录下的图标文件
            self.selected_icon_name = file_path
            self._update_icon_preview()

    def on_category_changed(self, index):
        """处理分类变更事件"""
        # 清空子分类列表
        self.subcategory_combo.clear()
        self.subcategory_combo.addItem("无", None)
        
        # 获取当前分类
        if index >= 0:
            category_id = self.category_combo.itemData(index)
            if category_id and category_id in self.category_map:
                category = self.category_map[category_id]
                # 添加子分类
                for subcategory in category.get("subcategories", []):
                    self.subcategory_combo.addItem(subcategory["name"], subcategory["id"])
                
                # 设置当前子分类
                if self.tool_data["subcategory_id"]:
                    sub_index = self.subcategory_combo.findData(self.tool_data["subcategory_id"])
                    if sub_index >= 0:
                        self.subcategory_combo.setCurrentIndex(sub_index)
    
    def _path_looks_like_directory(self, path):
        normalized = (path or "").strip()
        if not normalized:
            return False
        if normalized.endswith(("/", "\\")):
            return True
        return not os.path.splitext(os.path.basename(normalized))[1]

    def _derive_working_directory(self, path):
        abs_path = os.path.abspath(path)
        if os.path.isdir(abs_path):
            return abs_path
        if self._path_looks_like_directory(path):
            return abs_path
        parent_dir = os.path.dirname(abs_path)
        return parent_dir or abs_path

    def on_save(self):
        """保存工具配置"""
        # 验证必填字段
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "警告", "请输入工具名称！")
            return
        
        if not path:
            QMessageBox.warning(self, "警告", "请输入工具路径或URL！")
            return
        
        is_web_tool = self.tool_type_combo.currentData()
        working_directory = ""
        
        if not is_web_tool:
            # 路径不存在时也允许保存，方便为占位工具单独维护基础信息
            path_exists = os.path.exists(path)
            if not path_exists:
                reply = QMessageBox.question(
                    self,
                    "路径不存在",
                    "当前工具路径不存在，仍然保存吗？\n这不会影响你单独设置工具类型等信息，但工具会保持异常状态，直到路径修正。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.No:
                    return
            
            # 检查文件是否可执行（对于Windows可执行文件）
            if False:  # Allow arbitrary files such as .txt/.md/.lnk to be configured as tools.
                reply = QMessageBox.question(self, "询问", 
                                           f"所选文件 '{os.path.basename(path)}' 可能不是可执行文件，是否继续？",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            
            # 自动设置工作目录，不依赖路径当前是否存在
            working_directory = self._derive_working_directory(path)
        else:
            # 验证网页工具URL格式
            if not (path.startswith("http://") or path.startswith("https://")):
                QMessageBox.warning(self, "警告", "URL地址必须以http://或https://开头！")
                return
                
            if not self.validate_url(path):
                QMessageBox.warning(self, "警告", "URL格式不正确，请检查地址是否完整！")
                return
        
        # 若为网页工具且未选择图标，优先使用分类图标兜底，不等待favicon下载
        # 保存后若favicon异步成功，可覆盖该兜底图标
        if is_web_tool and not self.selected_icon_name:
            self.selected_icon_name = self._get_selected_category_icon_name()
        # 若为本地工具且未选择图标，尝试使用工具根目录的favicon.ico
        elif not is_web_tool and not self.selected_icon_name:
            try:
                # 获取工具根目录
                tool_dir = os.path.dirname(os.path.abspath(path))
                # 检查工具根目录是否存在favicon.ico
                favicon_path = os.path.join(tool_dir, "favicon.ico")
                if os.path.exists(favicon_path):
                    # 使用工具根目录的favicon.ico
                    self.selected_icon_name = favicon_path
            except (FileNotFoundError, PermissionError, OSError):
                # 忽略错误，使用默认图标
                pass
            
            # 如果仍然没有图标，且是本地可执行文件，尝试提取系统图标
            if not self.selected_icon_name and os.path.isfile(path):
                try:
                    # 使用 QFileIconProvider 提取图标
                    file_info = QFileInfo(path)
                    provider = QFileIconProvider()
                    icon = provider.icon(file_info)
                    
                    if not icon.isNull():
                        # 获取最大可用尺寸
                        sizes = icon.availableSizes()
                        if sizes:
                            # 找最大的尺寸，或者至少 48x48
                            max_size = sizes[-1] # 通常最后一个是最大的
                            if max_size.width() < 48:
                                max_size = QSize(48, 48)
                        else:
                            max_size = QSize(48, 48)
                            
                        # 转换为 Pixmap
                        pixmap = icon.pixmap(max_size)
                        
                        # 生成保存路径
                        tool_name_safe = re.sub(r'[\\/:*?"<>|]', '_', name)
                        icon_filename = f"{tool_name_safe}_icon.png"
                        target_path = os.path.join(self.icon_dir, icon_filename)
                        
                        # 确保不覆盖现有文件
                        counter = 1
                        base_name, ext = os.path.splitext(icon_filename)
                        while os.path.exists(target_path):
                            icon_filename = f"{base_name}_{counter}{ext}"
                            target_path = os.path.join(self.icon_dir, icon_filename)
                            counter += 1
                        
                        # 确保目录存在
                        os.makedirs(self.icon_dir, exist_ok=True)
                        
                        # 保存图标
                        if pixmap.save(target_path, "PNG"):
                            self.selected_icon_name = target_path
                except Exception as e:
                    logger.warning("提取图标失败: %s", e)

        # 处理图标文件路径，统一保存到resources/icons目录
        final_icon_name = None
        try:
            if self.selected_icon_name:
                if os.path.isabs(self.selected_icon_name):
                    # 如果是绝对路径，复制到resources/icons目录
                    # 先检查文件是否存在且是有效文件
                    if not os.path.exists(self.selected_icon_name) or not os.path.isfile(self.selected_icon_name):
                        # 文件不存在或无效，使用默认图标
                        final_icon_name = self.default_icon_name
                    else:
                        try:
                            # 首先检查是否已存在相同内容的图标
                            existing_icon = self._find_existing_icon_by_hash(self.selected_icon_name)
                            if existing_icon:
                                # 找到相同图标，直接使用现有的
                                final_icon_name = existing_icon
                            else:
                                # 没有找到相同图标，需要复制新文件
                                icon_name = os.path.basename(self.selected_icon_name)
                                # 确保文件名唯一（仅当文件名冲突时）
                                base_name, ext = os.path.splitext(icon_name)
                                counter = 1
                                target_path = os.path.join(self.icon_dir, icon_name)
                                while os.path.exists(target_path):
                                    icon_name = f"{base_name}_{counter}{ext}"
                                    target_path = os.path.join(self.icon_dir, icon_name)
                                    counter += 1
                                # 复制文件
                                shutil.copy2(self.selected_icon_name, target_path)
                                final_icon_name = icon_name
                        except (FileNotFoundError, PermissionError, IOError, shutil.Error, OSError):
                            # 复制失败，使用默认图标
                            final_icon_name = self.default_icon_name
                else:
                    # 相对路径，检查文件是否存在
                    icon_path = resolve_icon_path_value(self.selected_icon_name)
                    if icon_path is not None and os.path.isfile(icon_path):
                        final_icon_name = self.selected_icon_name
                    else:
                        # 文件不存在，使用默认图标
                        final_icon_name = self.default_icon_name
            else:
                final_icon_name = self.default_icon_name
        except Exception as e:
            # 捕获所有异常，确保工具添加操作能继续完成
            final_icon_name = self.default_icon_name

        type_label = self.type_label_edit.text().strip()
        run_in_terminal = self.run_in_terminal_check.isChecked()
        if not is_web_tool and type_label == "终端":
            run_in_terminal = True

        # 更新工具数据
        self.tool_data.update({
            "name": name,
            "path": path,
            "description": self.description_edit.toPlainText(),
            "category_id": self.category_combo.currentData() if self.categories else None,
            "subcategory_id": self.subcategory_combo.currentData() if self.categories else None,
            "is_favorite": self.favorite_check.isChecked(),
            "icon": final_icon_name,
            "arguments": self.args_edit.text(),
            "working_directory": working_directory,  # 自动设置工作目录
            "run_in_terminal": run_in_terminal,  # 保存是否在终端中运行的设置
            "is_web_tool": is_web_tool,  # 设置工具类型
            "type_label": type_label  # 自定义工具类型标签
        })
        self.tool_data.pop("tags", None)
        
        self.accept()
    
    def get_tool_data(self):
        """获取工具数据"""
        return self.tool_data

    def _normalize_icon_name(self, value):
        if not value:
            return ""
        if os.path.isabs(value):
            resolved = resolve_icon_path_value(value)
            return os.fspath(resolved) if resolved else ""
        resolved = resolve_icon_path_value(value)
        if resolved is None:
            return ""
        if os.path.splitext(value)[1]:
            return value
        return resolved.name

    def _get_selected_category_icon_name(self):
        """获取当前选中分类可用的图标名称，用作网页工具兜底图标"""
        if not self.categories or not hasattr(self, 'category_combo'):
            return ""

        category_id = self.category_combo.currentData()
        if not category_id:
            return ""

        category = self.category_map.get(category_id)
        if not isinstance(category, dict):
            return ""

        return self._normalize_icon_name(category.get('icon'))

    def _calculate_file_hash(self, file_path):
        """计算文件的SHA256哈希值"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning("计算文件哈希失败: %s", e)
            return None

    def _find_existing_icon_by_hash(self, source_path):
        """根据文件哈希值查找已存在的相同图标"""
        try:
            source_hash = self._calculate_file_hash(source_path)
            if not source_hash:
                return None

            # 遍历图标目录，查找相同哈希值的文件
            if os.path.exists(self.icon_dir):
                for filename in os.listdir(self.icon_dir):
                    file_path = os.path.join(self.icon_dir, filename)
                    if os.path.isfile(file_path):
                        file_hash = self._calculate_file_hash(file_path)
                        if file_hash == source_hash:
                            return filename
            return None
        except Exception as e:
            logger.warning("查找重复图标失败: %s", e)
            return None

    def closeEvent(self, event):
        """当对话框关闭时，清理资源"""
        try:
            self._cleanup_async_resources()
        except Exception as e:
            # 捕获所有异常，防止清理过程中出错
            logger.warning("关闭工具配置对话框时清理资源失败: %s", e)
        
        # 调用父类的closeEvent
        super().closeEvent(event)

    def done(self, result):
        try:
            self._cleanup_async_resources()
        except Exception as e:
            logger.warning("关闭工具配置对话框前清理资源失败: %s", e)
        super().done(result)
    
    def _update_icon_preview(self):
        try:
            # 处理图标文件路径
            icon_name = self.selected_icon_name or self.default_icon_name
            
            # 处理绝对路径和相对路径
            if os.path.isabs(icon_name):
                icon_path = icon_name
            else:
                icon_path = os.path.join(self.icon_dir, icon_name)
            
            # 检查文件是否存在
            if not os.path.exists(icon_path) or not os.path.isfile(icon_path):
                # 如果文件不存在或不是文件，使用默认图标
                icon_path = os.path.join(self.icon_dir, self.default_icon_name)
            
            # 确保默认图标路径有效
            if not os.path.exists(icon_path) or not os.path.isfile(icon_path):
                # 如果默认图标也不存在，直接返回
                return
            
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                preview_size = max(48, min(self.icon_preview.width() - 12, self.icon_preview.height() - 12))
                self.icon_preview.setPixmap(pixmap.scaled(preview_size, preview_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                # 如果图标文件损坏，也使用默认图标
                default_icon_path = os.path.join(self.icon_dir, self.default_icon_name)
                if os.path.exists(default_icon_path) and os.path.isfile(default_icon_path):
                    pixmap = QPixmap(default_icon_path)
                    if not pixmap.isNull():
                        preview_size = max(48, min(self.icon_preview.width() - 12, self.icon_preview.height() - 12))
                self.icon_preview.setPixmap(pixmap.scaled(preview_size, preview_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            # 捕获所有异常，防止因图标问题导致崩溃
            logger.warning("刷新图标预览失败: %s", e)

# 示例用法
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    # 示例工具数据
    sample_tool = {
        "id": 1,
        "name": "Nmap",
        "path": "tools/nmap.exe",
        "description": "网络扫描和安全评估工具",
        "category_id": 1,
        "subcategory_id": 101,
        "background_image": "",
        "priority": 3,
        "is_favorite": True
    }
    
    # 示例分类数据
    sample_categories = [
        {
            "id": 1,
            "name": "网络扫描工具",
            "icon": "network_scan.png",
            "subcategories": [
                {"id": 101, "name": "端口扫描"},
                {"id": 102, "name": "服务探测"}
            ]
        },
        {
            "id": 2,
            "name": "Web安全工具",
            "icon": "web_security.png",
            "subcategories": [
                {"id": 201, "name": "代理工具"},
                {"id": 202, "name": "漏洞扫描"}
            ]
        }
    ]
    
    dialog = ToolConfigDialog(sample_tool, sample_categories)
    if dialog.exec_():
        updated_tool = dialog.get_tool_data()
        logger.info("更新后的工具数据: %s", updated_tool)
    
    sys.exit(app.exec_())

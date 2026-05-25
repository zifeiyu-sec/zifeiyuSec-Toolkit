#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tool configuration dialog."""
import os
import re
import shutil
import hashlib
from pathlib import Path
from urllib.parse import urlparse

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QWidget, QScrollArea
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPushButton, QComboBox
from PyQt5.QtWidgets import QCheckBox, QGroupBox, QGridLayout, QSpinBox
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication, QInputDialog
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap, QPen
from PyQt5.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, QFileInfo, QSize
from PyQt5.QtWidgets import QFileIconProvider
from core.logger import logger
from core.runtime_paths import (
    ensure_runtime_dir,
    get_runtime_state_root,
    looks_like_command_name,
    resolve_accessible_path_value,
    resolve_configured_path_value,
    resolve_icon_path_value,
)
from core.style_manager import ThemeManager
from core.ui_scale import scaled
from ui.favicon_downloader import FaviconDownloader
from ui.icon_loader import get_icon_cache_key

class ToolConfigDialog(QDialog):
    """Documentation."""
    def __init__(self, tool_data=None, categories=None, parent=None, theme_name=None, base_dir=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("toolConfigDialog")
        # 支持主题传入，默认深色主题
        self.current_theme = theme_name or 'dark_green'
        self.tool_data = tool_data or self._create_empty_tool()
        self.categories = categories or []
        self.base_dir = os.fspath(
            base_dir
            or getattr(parent, "config_dir", None)
            or getattr(parent, "base_dir", None)
            or get_runtime_state_root()
        )
        self.icon_dir = os.fspath(ensure_runtime_dir("resources", "icons"))
        self.default_icon_name = "default_icon"
        self.selected_icon_name = self._normalize_icon_name(self.tool_data.get("icon"))
        self.downloader = None  # 初始化下载器属性
        self._manual_icon_download_requested = False
        self._dialog_background_path = None
        self._dialog_background_pixmap = QPixmap()
        self._drag_position = None
        self.init_ui()
        # 在 UI 建立后应用主题样式
        try:
            self.apply_theme_styles()
        except (RuntimeError, TypeError, AttributeError) as exc:
            logger.debug("应用工具配置对话框主题失败: %s", exc)
    
    def _create_empty_tool(self):
        """Documentation."""
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
    
    def _create_section_title_label(self, text):
        label = QLabel(text)
        label.setObjectName("toolConfigSectionTitle")
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return label

    def _create_field_label(self, text):
        label = QLabel(text)
        label.setObjectName("toolConfigFieldLabel")
        label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        return label

    def _resolve_theme_background_path(self):
        names = {
            "dark_green": ("\u9ed1\u5ba2.png", "dark_green.png"),
            "blue_white": ("blue_white.png", "blue_write.png"),
            "celadon_mist": ("\u56fd\u98ce.png",),
            "purple_neon": ("\u7d2b\u91d1.png", "purple_neon.png"),
            "red_orange": ("\u7ea2\u8272.png", "red_orange.png"),
        }
        candidates = names.get(self.current_theme)
        if not candidates:
            return None
        background_dir = Path(__file__).resolve().parents[1] / "images" / "background"
        for name in candidates:
            path = background_dir / name
            if path.exists():
                return path
        return None

    def _load_dialog_background_pixmap(self):
        path = self._resolve_theme_background_path()
        if path is None:
            self._dialog_background_path = None
            self._dialog_background_pixmap = QPixmap()
            return self._dialog_background_pixmap
        if self._dialog_background_path != path:
            self._dialog_background_path = path
            self._dialog_background_pixmap = QPixmap(os.fspath(path))
        return self._dialog_background_pixmap

    def _paint_cropped_theme_background(self, painter, pixmap):
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0 or pixmap.isNull():
            return

        scale = max(width / pixmap.width(), height / pixmap.height())
        source_width = width / scale
        source_height = height / scale
        source_x = max(0, (pixmap.width() - source_width) * 0.5)
        source_y = max(0, (pixmap.height() - source_height) * 0.42)
        painter.drawPixmap(
            QRectF(0, 0, width, height),
            pixmap,
            QRectF(source_x, source_y, source_width, source_height),
        )

    def _paint_theme_background_tint(self, painter):
        width = self.width()
        height = self.height()
        if width <= 0 or height <= 0:
            return

        tints = {
            "dark_green": (
                QColor(0, 8, 6, 178),
                QColor(0, 255, 65, 24),
                QColor(0, 229, 255, 92),
            ),
            "blue_white": (
                QColor(235, 248, 252, 118),
                QColor(108, 197, 238, 54),
                QColor(108, 197, 238, 116),
            ),
            "celadon_mist": (
                QColor(231, 246, 245, 126),
                QColor(36, 154, 158, 48),
                QColor(36, 154, 158, 96),
            ),
            "purple_neon": (
                QColor(8, 2, 13, 184),
                QColor(189, 58, 255, 24),
                QColor(255, 207, 92, 124),
            ),
            "red_orange": (
                QColor(42, 0, 0, 174),
                QColor(255, 210, 96, 24),
                QColor(255, 220, 112, 132),
            ),
        }
        base, accent, border = tints.get(
            self.current_theme,
            (QColor(16, 39, 29, 150), QColor(111, 231, 135, 26), QColor(111, 231, 135, 82)),
        )

        painter.fillRect(QRectF(0, 0, width, height), base)
        glow = QLinearGradient(QPointF(0, 0), QPointF(width, height))
        glow.setColorAt(0.0, accent)
        glow.setColorAt(0.52, QColor(accent.red(), accent.green(), accent.blue(), max(0, accent.alpha() // 2)))
        glow.setColorAt(1.0, QColor(0, 0, 0, 24))
        painter.fillRect(QRectF(0, 0, width, height), glow)
        painter.setPen(border)
        painter.drawRoundedRect(QRectF(0.5, 0.5, width - 1, height - 1), 16, 16)
        painter.setPen(QPen(QColor(border.red(), border.green(), border.blue(), max(18, border.alpha() // 2)), 1))
        painter.drawLine(22, 18, width - 22, 18)
        painter.drawLine(22, height - 18, width - 22, height - 18)
        painter.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), max(14, accent.alpha() // 2)), 1))
        painter.drawLine(width - 168, 36, width - 28, 36)
        painter.drawLine(28, height - 40, 164, height - 40)

    def _theme_base_color(self):
        colors = {
            "dark_green": QColor(3, 7, 7, 255),
            "blue_white": QColor(237, 248, 252, 255),
            "celadon_mist": QColor(231, 246, 245, 255),
            "purple_neon": QColor(8, 2, 13, 255),
            "red_orange": QColor(42, 0, 0, 255),
        }
        return colors.get(self.current_theme, QColor(16, 39, 29, 255))

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        bounds = QRectF(0, 0, self.width(), self.height())
        clip_path = QPainterPath()
        clip_path.addRoundedRect(bounds.adjusted(0.5, 0.5, -0.5, -0.5), 14, 14)
        painter.setClipPath(clip_path)
        painter.fillPath(clip_path, self._theme_base_color())
        pixmap = self._load_dialog_background_pixmap()
        if not pixmap.isNull():
            self._paint_cropped_theme_background(painter, pixmap)
        else:
            painter.fillRect(QRectF(0, 0, self.width(), self.height()), self._theme_base_color())
        self._paint_theme_background_tint(painter)
        painter.end()

    def _resolve_dialog_size(self):
        parent_window = None
        parent = self.parentWidget()
        if parent is not None:
            parent_window = parent.window()

        parent_size = QSize()
        if parent_window is not None:
            parent_size = parent_window.size()

        app = QApplication.instance()
        screen = self.screen() if hasattr(self, "screen") else None
        if screen is None and parent_window is not None and hasattr(parent_window, "screen"):
            screen = parent_window.screen()
        if screen is None and app is not None:
            screen = app.primaryScreen()

        available_geometry = screen.availableGeometry() if screen is not None else None
        if parent_size.isValid() and parent_size.width() > 0 and parent_size.height() > 0:
            width = int(parent_size.width() * 0.62)
            height = int(parent_size.height() * 0.90)
        elif available_geometry is not None:
            width = int(available_geometry.width() * 0.58)
            height = int(available_geometry.height() * 0.88)
        else:
            width = 680
            height = 720

        min_width = 560
        min_height = 600
        max_width = 820
        max_height = 900
        if available_geometry is not None:
            max_width = min(max_width, int(available_geometry.width() * 0.82))
            max_height = min(max_height, int(available_geometry.height() * 0.96))
            min_width = min(min_width, max_width)
            min_height = min(min_height, max_height)

        width = max(min_width, min(width, max_width))
        height = max(min_height, min(height, max_height))
        return QSize(width, height)

    def _create_title_bar(self, title_height, spacing):
        title_bar = QWidget()
        title_bar.setObjectName("toolConfigTitleBar")
        title_bar.setFixedHeight(title_height)
        title_bar.installEventFilter(self)

        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(spacing + 5, 0, spacing + 2, 0)
        title_layout.setSpacing(spacing)

        self.title_accent = QLabel()
        self.title_accent.setObjectName("toolConfigTitleAccent")
        self.title_accent.setFixedSize(max(10, scaled(12, self._dialog_scale)), max(10, scaled(12, self._dialog_scale)))
        self.title_accent.installEventFilter(self)

        self.title_label = QLabel(self.windowTitle())
        self.title_label.setObjectName("toolConfigWindowTitle")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.title_label.installEventFilter(self)

        self.close_button = QPushButton("x")
        self.close_button.setObjectName("toolConfigCloseButton")
        self.close_button.setFixedSize(title_height - 6, title_height - 6)
        self.close_button.clicked.connect(self.reject)

        title_layout.addWidget(self.title_accent, 0, Qt.AlignVCenter)
        title_layout.addWidget(self.title_label, 1, Qt.AlignVCenter)
        title_layout.addWidget(self.close_button, 0, Qt.AlignVCenter)
        return title_bar

    def eventFilter(self, watched, event):
        drag_widgets = (
            getattr(self, "title_bar", None),
            getattr(self, "title_label", None),
            getattr(self, "title_accent", None),
        )
        if any(watched is widget for widget in drag_widgets):
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return True
            if event.type() == QEvent.MouseMove and self._drag_position is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPos() - self._drag_position)
                event.accept()
                return True
            if event.type() == QEvent.MouseButtonRelease:
                self._drag_position = None
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def _max_dialog_height(self):
        screen = self.screen() if hasattr(self, "screen") else None
        if screen is None:
            app = QApplication.instance()
            screen = app.primaryScreen() if app is not None else None
        if screen is None:
            return 900
        return min(900, int(screen.availableGeometry().height() * 0.96))

    def _expand_height_for_content(self, content_widget, button_layout):
        layout = self.layout()
        if layout is None:
            return

        layout.activate()
        margins = layout.contentsMargins()
        spacing = layout.spacing()
        title_height = self.title_bar.height() if hasattr(self, "title_bar") else 0
        content_height = content_widget.sizeHint().height()
        button_height = button_layout.sizeHint().height()
        desired_height = (
            margins.top()
            + margins.bottom()
            + title_height
            + content_height
            + button_height
            + max(0, spacing) * 2
            + 12
        )
        target_height = min(max(self.height(), desired_height), self._max_dialog_height())
        if target_height > self.height():
            self.resize(self.width(), target_height)

    def init_ui(self):
        """初始化对话框界面"""
        self.setWindowTitle("编辑工具配置" if self.tool_data["id"] else "新建工具")
        dialog_size = self._resolve_dialog_size()
        self.resize(dialog_size)
        self.setMinimumSize(min(540, dialog_size.width()), min(520, dialog_size.height()))

        self._dialog_scale = max(0.72, min(0.98, dialog_size.width() / 760.0))
        button_height = max(24, scaled(28, self._dialog_scale))
        icon_column_width = max(112, scaled(124, self._dialog_scale))
        icon_preview_size = max(52, scaled(60, self._dialog_scale))
        description_height = max(78, scaled(96, self._dialog_scale))
        spacing = max(5, scaled(6, self._dialog_scale))
        section_margin = max(7, scaled(9, self._dialog_scale))
        title_height = max(34, scaled(38, self._dialog_scale))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(spacing + 1, spacing + 1, spacing + 1, spacing + 1)
        main_layout.setSpacing(spacing)

        self.title_bar = self._create_title_bar(title_height, spacing)
        main_layout.addWidget(self.title_bar)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("toolConfigScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area = scroll_area
        main_layout.addWidget(scroll_area, 1)

        content_widget = QWidget()
        content_widget.setObjectName("toolConfigContent")
        scroll_area.setWidget(content_widget)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(spacing)

        basic_group = QGroupBox()
        basic_layout = QVBoxLayout()
        basic_layout.setSpacing(spacing)
        basic_layout.setContentsMargins(section_margin, section_margin, section_margin, section_margin)
        basic_layout.addWidget(self._create_section_title_label("基本信息"), 0, Qt.AlignLeft)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(spacing)
        top_layout.setContentsMargins(0, 0, 0, 0)
        form_layout = QGridLayout()
        form_layout.setHorizontalSpacing(spacing)
        form_layout.setVerticalSpacing(spacing)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setColumnStretch(1, 1)

        form_layout.addWidget(self._create_field_label("工具类型:"), 0, 0)
        self.tool_type_combo = QComboBox()
        self.tool_type_combo.addItem("本地工具", False)
        self.tool_type_combo.addItem("网页工具", True)
        if self.tool_data.get("is_web_tool", False):
            self.tool_type_combo.setCurrentIndex(1)
        self.tool_type_combo.currentIndexChanged.connect(self.on_tool_type_changed)
        form_layout.addWidget(self.tool_type_combo, 0, 1)

        form_layout.addWidget(self._create_field_label("名称:"), 1, 0)
        self.name_edit = QLineEdit(self.tool_data["name"])
        form_layout.addWidget(self.name_edit, 1, 1)

        self.path_label = self._create_field_label("工具位置:")
        form_layout.addWidget(self.path_label, 2, 0)
        path_layout = QHBoxLayout()
        path_layout.setSpacing(spacing)
        path_layout.setContentsMargins(0, 0, 0, 0)
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
        icon_container.setContentsMargins(0, 0, 0, 0)
        icon_label = self._create_field_label("工具图标:")
        icon_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(icon_preview_size, icon_preview_size)
        self.icon_preview.setAlignment(Qt.AlignCenter)
        self.icon_preview.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.icon_preview.setStyleSheet("border: 1px solid rgba(0,229,255,0.22); border-radius: 12px;")
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

        desc_label = self._create_field_label("工具介绍:")
        self.description_edit = QTextEdit(self.tool_data["description"])
        self.description_edit.setMinimumHeight(description_height)
        self.description_edit.setMaximumHeight(description_height + scaled(36, self._dialog_scale))
        basic_layout.addWidget(desc_label)
        basic_layout.addWidget(self.description_edit)

        if self.categories:
            category_layout = QGridLayout()
            category_layout.setHorizontalSpacing(spacing)
            category_layout.setVerticalSpacing(spacing)
            category_layout.setContentsMargins(0, 0, 0, 0)
            category_layout.setColumnStretch(1, 1)

            category_layout.addWidget(self._create_field_label("Primary category:"), 0, 0)
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

            category_layout.addWidget(self._create_field_label("二级分类:"), 1, 0)
            self.subcategory_combo = QComboBox()
            self.subcategory_combo.addItem("", None)
            category_layout.addWidget(self.subcategory_combo, 1, 1)

            basic_layout.addLayout(category_layout)
            self.on_category_changed(self.category_combo.currentIndex())

        basic_group.setLayout(basic_layout)
        content_layout.addWidget(basic_group)

        run_group = QGroupBox()
        run_group_layout = QVBoxLayout()
        run_group_layout.setSpacing(spacing)
        run_group_layout.setContentsMargins(section_margin, section_margin, section_margin, section_margin)
        run_group_layout.addWidget(self._create_section_title_label("运行配置"), 0, Qt.AlignLeft)
        run_layout = QGridLayout()
        run_layout.setHorizontalSpacing(spacing)
        run_layout.setVerticalSpacing(spacing)
        run_layout.setContentsMargins(0, 0, 0, 0)

        run_layout.addWidget(self._create_field_label("运行命令/参数:"), 0, 0)
        arguments_value = self.tool_data.get("arguments", "")
        if isinstance(arguments_value, list):
            arguments_value = " ".join(str(arg) for arg in arguments_value)
        self.args_edit = QLineEdit(arguments_value)
        self.args_edit.setPlaceholderText("仅在终端工具模式下生效，例如: httpx.exe -h")
        self.args_edit.setToolTip("\u4ec5\u7ec8\u7aef\u5de5\u5177\u4f1a\u4f7f\u7528\u8fd9\u91cc\u7684\u5185\u5bb9\uff1b\u975e\u7ec8\u7aef\u5de5\u5177\u4e0d\u4f1a\u4f7f\u7528\u8fd9\u91cc\u7684\u5185\u5bb9\u3002\u53ef\u4f7f\u7528 {path} \u5f15\u7528\u5de5\u5177\u8def\u5f84\uff0c\u6216\u76f4\u63a5\u70b9\u51fb\u6253\u5f00\u5de5\u5177\u3002")
        run_layout.addWidget(self.args_edit, 0, 1)

        self.run_in_terminal_check = QCheckBox("在终端中运行")
        self.run_in_terminal_check.setChecked(self.tool_data.get("run_in_terminal", False))
        self.run_in_terminal_check.setToolTip("Run this tool through a terminal command.")
        run_layout.addWidget(self.run_in_terminal_check, 1, 1, alignment=Qt.AlignLeft)

        run_group_layout.addLayout(run_layout)
        run_group.setLayout(run_group_layout)
        content_layout.addWidget(run_group)

        settings_group = QGroupBox()
        settings_group_layout = QVBoxLayout()
        settings_group_layout.setSpacing(spacing)
        settings_group_layout.setContentsMargins(section_margin, section_margin, section_margin, section_margin)
        settings_group_layout.addWidget(self._create_section_title_label("其他设置"), 0, Qt.AlignLeft)
        settings_layout = QGridLayout()
        settings_layout.setHorizontalSpacing(spacing)
        settings_layout.setVerticalSpacing(spacing)
        settings_layout.setContentsMargins(0, 0, 0, 0)

        self.favorite_check = QCheckBox("Add to favorites")
        self.favorite_check.setChecked(self.tool_data.get("is_favorite", False))
        settings_layout.addWidget(self.favorite_check, 0, 1, alignment=Qt.AlignLeft)

        settings_layout.addWidget(self._create_field_label("Custom type label:"), 1, 0)
        self.type_label_edit = QLineEdit(self.tool_data.get("type_label", ""))
        self.type_label_edit.setPlaceholderText("例如: 终端 / 红队综合 / 脚本工具 / 文档")
        self.type_label_edit.setToolTip("Set to terminal to treat this tool as a terminal tool.")
        settings_layout.addWidget(self.type_label_edit, 1, 1)

        settings_group_layout.addLayout(settings_layout)
        settings_group.setLayout(settings_group_layout)
        content_layout.addWidget(settings_group)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(spacing)
        button_layout.setContentsMargins(0, 0, 0, 0)
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
        self._expand_height_for_content(content_widget, button_layout)

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
        """Documentation."""
        self.current_theme = theme_name or 'dark_green'
        self.apply_theme_styles()
        self.update()

    def apply_theme_styles(self):
        """Apply the selected theme to controls inside this dialog."""
        theme_manager = ThemeManager()
        base_style = theme_manager.get_dialog_style(self.current_theme)
        palettes = {
            "blue_white": {
                "surface": "#edf8fc",
                "content_bg": "rgba(237,248,252,0.48)",
                "group_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(206,239,252,0.62), stop:0.58 rgba(151,213,244,0.46), stop:1 rgba(84,171,224,0.30))",
                "group_border": "rgba(151,213,244,0.62)",
                "title_bg": "rgba(207,239,252,0.72)",
                "title_border": "rgba(151,213,244,0.68)",
                "text": "#31506c",
                "input_bg": "rgba(220,244,253,0.66)",
                "input_border": "rgba(151,213,244,0.70)",
                "hover_bg": "rgba(196,234,250,0.82)",
                "accent": "rgba(108,197,238,0.82)",
                "scroll_track": "rgba(198,228,242,0.58)",
                "scroll_handle": "rgba(108,197,238,0.62)",
            },
            "celadon_mist": {
                "surface": "#e7f6f5",
                "content_bg": "rgba(231,246,245,0.46)",
                "group_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(204,242,239,0.60), stop:0.58 rgba(137,220,223,0.42), stop:1 rgba(68,175,180,0.30))",
                "group_border": "rgba(137,220,223,0.62)",
                "title_bg": "rgba(197,237,235,0.66)",
                "title_border": "rgba(137,220,223,0.58)",
                "text": "#244d50",
                "input_bg": "rgba(214,243,241,0.66)",
                "input_border": "rgba(137,220,223,0.62)",
                "hover_bg": "rgba(190,235,233,0.82)",
                "accent": "rgba(36,154,158,0.56)",
                "scroll_track": "rgba(191,227,226,0.54)",
                "scroll_handle": "rgba(36,154,158,0.46)",
            },
            "dark_green": {
                "surface": "rgba(5,12,11,0.98)",
                "content_bg": "rgba(5,12,11,0.30)",
                "group_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(5,20,22,0.42), stop:0.58 rgba(0,24,22,0.34), stop:1 rgba(0,6,8,0.48))",
                "group_border": "rgba(0,229,255,0.46)",
                "title_bg": "rgba(0,46,30,0.58)",
                "title_border": "rgba(0,255,65,0.46)",
                "text": "#00e676",
                "input_bg": "rgba(5,18,18,0.56)",
                "input_border": "rgba(13,115,119,0.72)",
                "hover_bg": "rgba(5,22,18,0.68)",
                "accent": "rgba(0,255,65,0.72)",
                "scroll_track": "rgba(26,46,51,0.50)",
                "scroll_handle": "rgba(0,255,65,0.42)",
            },
            "purple_neon": {
                "surface": "rgba(8,2,13,0.98)",
                "content_bg": "rgba(13,2,22,0.34)",
                "group_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(45,25,86,0.58), stop:0.42 rgba(18,8,42,0.78), stop:1 rgba(9,4,24,0.88))",
                "group_border": "rgba(255,207,92,0.56)",
                "title_bg": "rgba(23,10,50,0.18)",
                "title_border": "rgba(255,207,92,0.18)",
                "text": "#fff0b8",
                "input_bg": "rgba(8,4,22,0.76)",
                "input_border": "rgba(255,207,92,0.40)",
                "hover_bg": "rgba(28,12,58,0.78)",
                "accent": "rgba(255,232,147,0.88)",
                "scroll_track": "rgba(24,9,48,0.66)",
                "scroll_handle": "rgba(255,207,92,0.58)",
            },
            "red_orange": {
                "surface": "rgba(42,0,0,0.98)",
                "content_bg": "rgba(58,0,0,0.34)",
                "group_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(112,0,0,0.68), stop:0.48 rgba(180,18,8,0.38), stop:1 rgba(58,0,0,0.70))",
                "group_border": "rgba(255,205,92,0.76)",
                "title_bg": "rgba(112,0,0,0.62)",
                "title_border": "rgba(255,220,112,0.78)",
                "text": "#ffdc70",
                "input_bg": "rgba(74,0,0,0.54)",
                "input_border": "rgba(255,224,140,0.70)",
                "hover_bg": "rgba(126,0,0,0.62)",
                "accent": "rgba(255,220,112,0.84)",
                "scroll_track": "rgba(106,0,0,0.48)",
                "scroll_handle": "rgba(255,205,92,0.62)",
            },
        }
        palette = palettes.get(
            self.current_theme,
            {
                "surface": "#10271d",
                "content_bg": "rgba(16,39,29,0.42)",
                "group_bg": "rgba(24,58,39,0.58)",
                "group_border": "rgba(111,231,135,0.18)",
                "title_bg": "rgba(24,58,39,0.82)",
                "title_border": "rgba(111,231,135,0.22)",
                "text": "#f3fff5",
                "input_bg": "rgba(22,49,35,0.82)",
                "input_border": "rgba(111,231,135,0.18)",
                "hover_bg": "rgba(111,231,135,0.16)",
                "accent": "rgba(152,246,176,0.34)",
                "scroll_track": "rgba(20,42,31,0.72)",
                "scroll_handle": "rgba(111,231,135,0.34)",
            },
        )
        theme_effects = {
            "blue_white": {
                "panel_bg": "transparent",
                "group_top": "rgba(151,213,244,0.74)",
                "button_bg": "rgba(213,242,253,0.72)",
                "button_border": "rgba(151,213,244,0.58)",
                "button_hover": "rgba(191,232,250,0.86)",
                "button_text": "#2d4764",
                "group_radius": "16px",
                "pressed_bg": "rgba(166,216,246,0.84)",
            },
            "celadon_mist": {
                "panel_bg": "transparent",
                "group_top": "rgba(137,220,223,0.70)",
                "button_bg": "rgba(207,242,240,0.68)",
                "button_border": "rgba(139,220,223,0.58)",
                "button_hover": "rgba(184,232,230,0.82)",
                "button_text": "#164d52",
                "group_radius": "12px",
                "pressed_bg": "rgba(17,142,150,0.28)",
            },
            "dark_green": {
                "panel_bg": "transparent",
                "group_top": "rgba(0,229,255,0.46)",
                "button_bg": "rgba(5,18,18,0.50)",
                "button_border": "rgba(0,229,255,0.38)",
                "button_hover": "rgba(0,45,27,0.62)",
                "button_text": "#9fcbb2",
                "group_radius": "16px",
                "pressed_bg": "rgba(0,255,65,0.16)",
            },
            "purple_neon": {
                "panel_bg": "transparent",
                "group_top": "rgba(255,232,147,0.72)",
                "button_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(66,26,104,0.78), stop:1 rgba(32,12,66,0.78))",
                "button_border": "rgba(255,207,92,0.52)",
                "button_hover": "rgba(84,32,132,0.82)",
                "button_text": "#ffe6a3",
                "group_radius": "10px",
                "pressed_bg": "rgba(255,207,92,0.24)",
                "label_bg": "qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(88,42,130,0.82), stop:1 rgba(42,18,80,0.76))",
                "label_border": "rgba(255,207,92,0.34)",
                "label_text": "#ffe6a3",
            },
            "red_orange": {
                "panel_bg": "transparent",
                "group_top": "rgba(255,240,170,0.62)",
                "button_bg": "rgba(96,0,0,0.54)",
                "button_border": "rgba(255,205,92,0.64)",
                "button_hover": "rgba(150,16,8,0.58)",
                "button_text": "#ffe6b0",
                "group_radius": "16px",
                "pressed_bg": "rgba(255,198,72,0.24)",
            },
        }
        palette.update(theme_effects.get(self.current_theme, {
            "panel_bg": "transparent",
            "group_top": palette["accent"],
            "button_bg": palette["input_bg"],
            "button_border": palette["input_border"],
            "button_hover": palette["hover_bg"],
            "button_text": palette["text"],
            "group_radius": "16px",
            "pressed_bg": palette["accent"],
            "label_bg": palette["input_bg"],
            "label_border": palette["input_border"],
            "label_text": palette["text"],
        }))
        palette.setdefault("label_bg", palette["input_bg"])
        palette.setdefault("label_border", palette["input_border"])
        palette.setdefault("label_text", palette["text"])
        palette.setdefault("titlebar_bg", palette["content_bg"])
        palette.setdefault("titlebar_border", palette["group_border"])
        palette.setdefault("titlebar_text", palette["text"])
        palette.setdefault("titlebar_accent", palette["accent"])

        control_radius = max(5, scaled(6, self._dialog_scale))
        control_padding_v = max(3, scaled(4, self._dialog_scale))
        control_padding_h = max(7, scaled(8, self._dialog_scale))
        button_padding_v = max(3, scaled(4, self._dialog_scale))
        button_padding_h = max(8, scaled(9, self._dialog_scale))
        label_padding_v = max(3, scaled(4, self._dialog_scale))
        label_padding_h = max(7, scaled(8, self._dialog_scale))
        section_padding_top = max(2, scaled(3, self._dialog_scale))
        section_padding_h = max(7, scaled(8, self._dialog_scale))
        section_padding_bottom = max(2, scaled(3, self._dialog_scale))
        scrollbar_size = max(6, scaled(7, self._dialog_scale))
        scrollbar_margin = max(1, scaled(2, self._dialog_scale))

        supplemental_style = f"""
            QDialog#toolConfigDialog {{
                background: transparent;
            }}
            QWidget#toolConfigTitleBar {{
                background: {palette['titlebar_bg']};
                border: 1px solid {palette['titlebar_border']};
                border-radius: {max(7, scaled(9, self._dialog_scale))}px;
            }}
            QLabel#toolConfigTitleAccent {{
                background: {palette['titlebar_accent']};
                border: 1px solid {palette['titlebar_border']};
                border-radius: {max(4, scaled(5, self._dialog_scale))}px;
            }}
            QLabel#toolConfigWindowTitle {{
                color: {palette['titlebar_text']};
                background: transparent;
                border: none;
                font-weight: 700;
            }}
            QPushButton#toolConfigCloseButton {{
                background: {palette['button_bg']};
                color: {palette['button_text']};
                border: 1px solid {palette['button_border']};
                border-radius: {max(6, scaled(8, self._dialog_scale))}px;
                padding: 0px;
                font-weight: 700;
            }}
            QPushButton#toolConfigCloseButton:hover {{
                background: {palette['button_hover']};
                color: {palette['titlebar_text']};
                border-color: {palette['titlebar_accent']};
            }}
            QScrollArea#toolConfigScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea#toolConfigScrollArea > QWidget {{
                background: transparent;
            }}
            QScrollArea#toolConfigScrollArea > QWidget > QWidget {{
                background: {palette['panel_bg']};
                border-radius: {max(8, scaled(10, self._dialog_scale))}px;
            }}
            QWidget#toolConfigContent {{
                background: transparent;
            }}
            QLineEdit, QTextEdit, QComboBox, QSpinBox {{
                background: {palette['input_bg']};
                color: {palette['text']};
                border: 1px solid {palette['input_border']};
                border-radius: {control_radius}px;
                padding: {control_padding_v}px {control_padding_h}px;
                selection-background-color: {palette['hover_bg']};
                selection-color: {palette['text']};
            }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border: 1px solid {palette['accent']};
                background: {palette['hover_bg']};
            }}
            QPushButton {{
                background: {palette['button_bg']};
                color: {palette['button_text']};
                border: 1px solid {palette['button_border']};
                border-radius: {control_radius}px;
                padding: {button_padding_v}px {button_padding_h}px;
                font-weight: 600;
            }}
            QLabel#toolConfigFieldLabel {{
                background: {palette['label_bg']};
                color: {palette['label_text']};
                border: 1px solid {palette['label_border']};
                border-radius: {control_radius}px;
                padding: {label_padding_v}px {label_padding_h}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {palette['button_hover']};
                border: 1px solid {palette['accent']};
            }}
            QPushButton:pressed {{
                background: {palette['pressed_bg']};
                border-color: {palette['accent']};
            }}
            QPushButton:default {{
                border: 1px solid {palette['accent']};
            }}
            QCheckBox {{
                color: {palette['text']};
                spacing: {control_radius}px;
            }}
            QCheckBox::indicator {{
                width: {max(10, scaled(11, self._dialog_scale))}px;
                height: {max(10, scaled(11, self._dialog_scale))}px;
                border-radius: {max(3, scaled(4, self._dialog_scale))}px;
                background: {palette['input_bg']};
                border: 1px solid {palette['input_border']};
            }}
            QCheckBox::indicator:checked {{
                background: {palette['accent']};
                border: 1px solid {palette['accent']};
            }}
            QComboBox QAbstractItemView {{
                background: {palette['surface']};
                color: {palette['text']};
                border: 1px solid {palette['input_border']};
                selection-background-color: {palette['hover_bg']};
                selection-color: {palette['text']};
            }}
            QScrollBar:vertical {{
                background: {palette['scroll_track']};
                width: {scrollbar_size}px;
                margin: {scrollbar_margin}px 0 {scrollbar_margin}px 0;
                border-radius: {scrollbar_size // 2}px;
            }}
            QScrollBar::handle:vertical {{
                background: {palette['scroll_handle']};
                min-height: {max(16, scaled(20, self._dialog_scale))}px;
                border-radius: {scrollbar_size // 2}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {palette['accent']};
            }}
            QScrollBar:horizontal {{
                background: {palette['scroll_track']};
                height: {scrollbar_size}px;
                margin: 0 {scrollbar_margin}px 0 {scrollbar_margin}px;
                border-radius: {scrollbar_size // 2}px;
            }}
            QScrollBar::handle:horizontal {{
                background: {palette['scroll_handle']};
                min-width: {max(16, scaled(20, self._dialog_scale))}px;
                border-radius: {scrollbar_size // 2}px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {palette['accent']};
            }}
            QScrollBar::add-line,
            QScrollBar::sub-line,
            QScrollBar::add-page,
            QScrollBar::sub-page {{
                border: none;
                background: transparent;
            }}
        """
        group_style = f"""
            QGroupBox {{
                background: {palette['group_bg']};
                border: 1px solid {palette['group_border']};
                border-top: 1px solid {palette['group_top']};
                border-radius: {palette['group_radius']};
                margin-top: 0px;
                padding-top: 0px;
            }}
        """
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet("")
        self.setStyleSheet(base_style + supplemental_style + group_style)

        title_style = (
            "QLabel#toolConfigSectionTitle {"
            f"background-color: {palette['title_bg']};"
            f"border: 1px solid {palette['title_border']};"
            f"border-radius: {max(4, scaled(5, self._dialog_scale))}px;"
            f"color: {palette['text']};"
            "font-weight: 700;"
            f"padding: {section_padding_top}px {section_padding_h}px {section_padding_bottom}px {section_padding_h}px;"
            "}"
        )

        for label in self.findChildren(QLabel, "toolConfigSectionTitle"):
            label.setStyleSheet(title_style)

        border_radius = max(10, self.icon_preview.width() // 5)
        self.icon_preview.setStyleSheet(
            f"background: {palette['input_bg']}; "
            f"border: 1px solid {palette['input_border']}; "
            f"border-radius: {border_radius}px;"
        )

    def on_url_text_changed(self, text):
        """Documentation."""
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
                QMessageBox.warning(self, "Download failed", "Unable to download a usable icon from this URL.")
    
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
        """Documentation."""
        url, ok = QInputDialog.getText(self, "Download icon from URL", "Enter icon image URL:")
        if not ok:
            return

        url = str(url or "").strip()
        if not url:
            return

        if not self.validate_url(url):
            QMessageBox.warning(self, "Warning", "Icon URL must start with http:// or https://.")
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
                    QMessageBox.warning(self, "Warning", "Please enter a URL.")
                    return
                
                # 严格验证URL格式
                if not (url.startswith("http://") or url.startswith("https://")):
                    QMessageBox.warning(self, "警告", "URL地址必须以http://或https://开头！")
                    return
                
                if not self.validate_url(url):
                    QMessageBox.warning(self, "Warning", "Invalid URL format.")
                    return
                
                self.browse_button.setToolTip("URL format validated.")
                # 尝试抓取网站 favicon 并显示为图标预览
                # 使用现有的异步下载方式
                self._async_download_favicon(url)
            else:
                # 浏览本地文件或目录
                # 允许用户选择文件或目录
                path, _ = QFileDialog.getOpenFileName(
                    self, "Select tool or directory",
                    os.path.dirname(self.path_edit.text()) or self.base_dir or ".",
                    "Common tool files (*.exe *.bat *.cmd *.py *.ps1 *.vbs *.jar *.html *.htm);;All files (*.*)"
                )
                
                # 如果没有选择文件，尝试选择目录
                if not path:
                    path = QFileDialog.getExistingDirectory(
                        self, "选择目录", 
                        os.path.dirname(self.path_edit.text()) or self.base_dir or "."
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
            "Icon files (*.png *.jpg *.jpeg *.svg *.ico);;All files (*.*)",
        )
        if file_path:
            # 允许选择任意目录下的图标文件
            self.selected_icon_name = file_path
            self._update_icon_preview()

    def on_category_changed(self, index):
        """处理分类变更事件"""
        # 清空子分类列表
        self.subcategory_combo.clear()
        self.subcategory_combo.addItem("", None)
        
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

    def _path_looks_like_command_name(self, path):
        normalized = (path or "").strip()
        return looks_like_command_name(normalized)

    def _resolve_accessible_tool_path(self, path):
        try:
            return resolve_accessible_path_value(path, base_dir=self.base_dir)
        except (OSError, ValueError):
            return None

    def _resolve_configured_tool_path(self, path, allow_command_name=False):
        try:
            return resolve_configured_path_value(
                path,
                base_dir=self.base_dir,
                allow_command_name=allow_command_name,
            )
        except (OSError, ValueError):
            return None

    def _derive_working_directory(self, path):
        normalized = (path or "").strip()
        if not normalized:
            return self.base_dir

        if self._path_looks_like_command_name(normalized):
            return self.base_dir

        resolved_path = self._resolve_accessible_tool_path(normalized)
        if resolved_path is not None:
            resolved_text = os.fspath(resolved_path)
            if os.path.isdir(resolved_text):
                return resolved_text
            parent_dir = os.path.dirname(resolved_text)
            return parent_dir or resolved_text

        configured_path = self._resolve_configured_tool_path(normalized)
        if configured_path is not None:
            configured_text = os.fspath(configured_path)
            if os.path.isdir(configured_text) or self._path_looks_like_directory(normalized):
                return configured_text
            parent_dir = os.path.dirname(configured_text)
            return parent_dir or configured_text

        if os.path.isabs(normalized):
            resolved_text = os.path.normpath(normalized)
            if os.path.isdir(resolved_text) or self._path_looks_like_directory(normalized):
                return resolved_text
            parent_dir = os.path.dirname(resolved_text)
            return parent_dir or resolved_text

        if self._path_looks_like_directory(normalized):
            return os.path.normpath(normalized)
        return self.base_dir

    def _should_extract_local_file_icon(self, path):
        normalized = (path or '').strip()
        if not normalized:
            return False

        resolved_path = self._resolve_accessible_tool_path(normalized)
        if resolved_path is None or not resolved_path.is_file():
            return False

        return resolved_path.suffix.casefold() == '.exe'

    def on_save(self):
        """保存工具配置"""
        # 验证必填字段
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "警告", "请输入工具名称！")
            return
        
        if not path:
            QMessageBox.warning(self, "Warning", "Please enter a tool path or URL.")
            return
        
        is_web_tool = self.tool_type_combo.currentData()
        working_directory = ""
        
        if not is_web_tool:
            # 路径不存在时也允许保存，方便为占位工具单独维护基础信息
            resolved_path = self._resolve_accessible_tool_path(path)
            path_exists = resolved_path is not None and resolved_path.exists()
            if not path_exists:
                reply = QMessageBox.question(
                    self,
                    "Path does not exist",
                    "The current tool path does not exist. Save anyway?\nThe tool will remain in an abnormal state until the path is fixed.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if reply == QMessageBox.No:
                    return
            
            # 检查文件是否可执行（对于Windows可执行文件）
            if False:  # Allow arbitrary files such as .txt/.md/.lnk to be configured as tools.
                reply = QMessageBox.question(self, "询问", 
                                           f"Selected file {os.path.basename(path)!r} may not be executable. Continue?",
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
                QMessageBox.warning(self, "Warning", "Invalid URL format.")
                return
        
        # 若为网页工具且未选择图标，优先使用分类图标兜底，不等待favicon下载
        # 保存后若 favicon 异步成功，可覆盖该兜底图标
        if is_web_tool and not self.selected_icon_name:
            self.selected_icon_name = self._get_selected_category_icon_name()
        # 若为本地工具且未选择图标，尝试使用工具根目录的favicon.ico
        elif not is_web_tool and not self.selected_icon_name:
            try:
                if resolved_path is not None and resolved_path.exists():
                    tool_path = os.fspath(resolved_path)
                    tool_dir = tool_path if os.path.isdir(tool_path) else os.path.dirname(tool_path)
                    favicon_path = os.path.join(tool_dir, "favicon.ico")
                    if os.path.exists(favicon_path):
                        self.selected_icon_name = favicon_path
            except (FileNotFoundError, PermissionError, OSError):
                # 忽略错误，使用默认图标
                pass
            
            # 如果仍然没有图标，且是本地 .exe 文件，尝试提取系统图标
            if not self.selected_icon_name and self._should_extract_local_file_icon(path):
                try:
                    # 使用 QFileIconProvider 提取图标
                    icon_source_path = self._resolve_accessible_tool_path(path)
                    if icon_source_path is None:
                        raise FileNotFoundError(path)
                    file_info = QFileInfo(os.fspath(icon_source_path))
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
                except (FileNotFoundError, PermissionError, OSError, ValueError) as e:
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
        except (FileNotFoundError, PermissionError, IOError, shutil.Error, OSError, ValueError) as e:
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
        """Documentation."""
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
        """Documentation."""
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
            icon_name = self.selected_icon_name or self.default_icon_name
            icon_path = get_icon_cache_key(icon_name, theme_name=self.current_theme)

            if not icon_path or not os.path.exists(icon_path) or not os.path.isfile(icon_path):
                icon_path = get_icon_cache_key(self.default_icon_name, theme_name=self.current_theme)

            if not icon_path or not os.path.exists(icon_path) or not os.path.isfile(icon_path):
                return

            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                preview_size = max(48, min(self.icon_preview.width() - 12, self.icon_preview.height() - 12))
                self.icon_preview.setPixmap(pixmap.scaled(preview_size, preview_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                default_icon_path = get_icon_cache_key(self.default_icon_name, theme_name=self.current_theme)
                if default_icon_path and os.path.exists(default_icon_path) and os.path.isfile(default_icon_path):
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
        "description": "Network scanning and security assessment tool",
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

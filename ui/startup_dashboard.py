#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Startup dashboard with recent, favorite, and path attention sections."""

from datetime import datetime
from math import ceil

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget, QAbstractItemView, QScrollArea, QSizePolicy

from core.style_manager import ThemeManager
from ui.tool_model_view import ToolCardContainer


class DashboardSection(QWidget):
    def __init__(self, title, empty_text, parent=None):
        super().__init__(parent)
        self.empty_text = empty_text
        self._displayed_tool_count = 0
        self._height_sync_timer = QTimer(self)
        self._height_sync_timer.setSingleShot(True)
        self._height_sync_timer.setInterval(0)
        self._height_sync_timer.timeout.connect(self._sync_container_height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("dashboardSectionTitle")
        layout.addWidget(self.title_label)

        self.empty_label = QLabel(empty_text, self)
        self.empty_label.setObjectName("dashboardEmptyLabel")
        layout.addWidget(self.empty_label)

        self.container = ToolCardContainer(self)
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.container.view.setDragEnabled(False)
        self.container.view.setAcceptDrops(False)
        self.container.view.setDropIndicatorShown(False)
        self.container.view.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.container.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.container.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.container)

    def set_theme(self, theme_name):
        self.container.set_theme(theme_name)

    def display_tools(self, tools):
        tools = list(tools or [])
        self._displayed_tool_count = len(tools)
        self.empty_label.setVisible(not tools)
        self.container.setVisible(bool(tools))
        self.container.display_tools(tools)
        self._request_container_height_sync()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._displayed_tool_count:
            self._request_container_height_sync()

    def _request_container_height_sync(self):
        if not self._displayed_tool_count:
            self._height_sync_timer.stop()
            self._sync_container_height()
            return
        if not self._height_sync_timer.isActive():
            self._height_sync_timer.start()

    def _sync_container_height(self):
        if not self._displayed_tool_count:
            self.container.setMinimumHeight(0)
            self.container.setMaximumHeight(0)
            return

        self.container.update_card_layout()
        grid_size = self.container.view.gridSize()
        spacing = max(0, self.container.view.spacing())
        row_height = max(self.container.card_height + spacing, grid_size.height())
        grid_width = max(1, grid_size.width())
        viewport_width = max(self.container.view.viewport().width(), self.container.width(), grid_width)
        columns = max(1, min(self._displayed_tool_count, viewport_width // grid_width))
        rows = max(1, ceil(self._displayed_tool_count / columns))
        height = rows * row_height + 2

        if self.container.minimumHeight() != height:
            self.container.setMinimumHeight(height)
            self.container.setMaximumHeight(height)


class DashboardContainer(QWidget):
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    tool_order_changed = pyqtSignal(list)
    new_tool_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "dark_green"
        self._tools = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("dashboardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        root_layout.addWidget(self.scroll_area)

        self.page = QWidget(self.scroll_area)
        self.page.setObjectName("dashboardPage")
        layout = QVBoxLayout(self.page)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(14)

        self.recent_section = DashboardSection("最近使用", "还没有最近使用记录，运行一次工具后会出现在这里。", self.page)
        self.favorite_section = DashboardSection("收藏工具", "还没有收藏工具，可以在工具卡片上点击星标收藏。", self.page)
        self.path_section = DashboardSection("路径提醒", "没有发现明显路径配置问题。", self.page)

        for section in (self.recent_section, self.favorite_section, self.path_section):
            layout.addWidget(section)
            self._connect_section(section)
        layout.addStretch(1)
        self.scroll_area.setWidget(self.page)

        self.apply_theme_styles()

    def _connect_section(self, section):
        container = section.container
        container.run_tool.connect(self.run_tool.emit)
        container.edit_requested.connect(self.edit_requested.emit)
        container.deleted.connect(self.deleted.emit)
        container.toggle_favorite.connect(self.toggle_favorite.emit)
        container.new_tool_requested.connect(self.new_tool_requested.emit)

    def set_theme(self, theme_name):
        self.current_theme = theme_name or "dark_green"
        self.apply_theme_styles()
        for section in (self.recent_section, self.favorite_section, self.path_section):
            section.set_theme(self.current_theme)

    def apply_theme_styles(self):
        self.setStyleSheet(ThemeManager().get_dashboard_style(self.current_theme))

    def display_tools(self, tools_data):
        self._tools = [tool for tool in (tools_data or []) if isinstance(tool, dict)]
        self.recent_section.display_tools(self._recent_tools(self._tools))
        self.favorite_section.display_tools(self._favorite_tools(self._tools))
        self.path_section.display_tools(self._path_attention_tools(self._tools))

    def get_tool_count(self):
        return len(self._tools)

    def _recent_tools(self, tools, limit=4):
        candidates = [tool for tool in tools if tool.get("last_used") or int(tool.get("usage_count", 0) or 0) > 0]
        candidates.sort(key=lambda tool: str(tool.get("name") or "").casefold())
        candidates.sort(key=lambda tool: self._last_used_sort_key(tool.get("last_used")), reverse=True)
        candidates.sort(key=lambda tool: int(tool.get("usage_count", 0) or 0), reverse=True)
        return [self._copy_with_description(tool, self._recent_description(tool)) for tool in candidates[:limit]]

    def _favorite_tools(self, tools, limit=8):
        favorites = [tool for tool in tools if tool.get("is_favorite", False)]
        favorites.sort(
            key=lambda tool: (
                -int(tool.get("usage_count", 0) or 0),
                str(tool.get("name") or "").casefold(),
                tool.get("id") or 0,
            )
        )
        return [self._copy_with_description(tool, tool.get("description") or "收藏工具") for tool in favorites[:limit]]

    def _path_attention_tools(self, tools, limit=8):
        results = []
        for tool in tools:
            reason = self._path_attention_reason(tool)
            if not reason:
                continue
            results.append(self._copy_with_description(tool, reason))
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def _copy_with_description(tool, description):
        copied = dict(tool)
        copied["_display_description"] = str(description or "").strip()
        return copied

    @staticmethod
    def _last_used_sort_key(value):
        text = str(value or "").strip()
        if not text:
            return datetime.min
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return datetime.min

    @staticmethod
    def _recent_description(tool):
        count = int(tool.get("usage_count", 0) or 0)
        if count > 0:
            return f"已使用 {count} 次"
        return "最近使用"

    @staticmethod
    def _path_attention_reason(tool):
        path = str(tool.get("path") or "").strip()
        if not path:
            return "未配置路径或 URL"
        if bool(tool.get("is_web_tool", False)) and not path.lower().startswith(("http://", "https://")):
            return "网页工具 URL 不是 http/https"
        if tool.get("_is_path_available") is False:
            return "本地路径不可用"
        if "CHANGE_ME" in path or "TODO" in path.upper():
            return "路径仍是占位值"
        return ""

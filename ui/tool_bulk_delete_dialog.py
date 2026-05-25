#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bulk tool deletion dialog."""

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.style_manager import ThemeManager
from ui.record_list_model import RecordListDelegate, RecordListModel


class ToolBulkDeleteDialog(QDialog):
    """Select multiple tool records for deletion."""

    def __init__(self, tools, categories=None, theme_name=None, parent=None):
        super().__init__(parent)
        self.tools = [tool for tool in (tools or []) if isinstance(tool, dict)]
        self.category_labels = self._build_category_labels(categories or [])
        self.theme_name = theme_name or (
            getattr(parent, "current_theme", "dark_green") if parent is not None else "dark_green"
        )
        self.checked_tool_ids = set()
        self.selected_tool_ids = []
        self.visible_tool_ids = []

        self.setWindowTitle("批量删除工具")
        self.setMinimumSize(760, 560)
        self._init_ui()
        self._apply_theme_styles()
        self.refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 16)
        layout.setSpacing(10)

        title = QLabel("选择要从工具箱配置中删除的工具", self)
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        hint = QLabel("此操作只删除工具箱配置，不会删除本地工具文件、笔记或附件。", self)
        hint.setObjectName("hintLabel")
        layout.addWidget(hint)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:", self))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("按名称、路径、描述或分类搜索...")
        self.search_input.textChanged.connect(self.refresh_list)
        search_layout.addWidget(self.search_input, 1)
        layout.addLayout(search_layout)

        self.summary_label = QLabel(self)
        self.summary_label.setObjectName("summaryLabel")
        layout.addWidget(self.summary_label)

        self.list_model = RecordListModel(
            text_func=self._format_tool_item_text,
            key_func=lambda tool: tool.get("id"),
            checkable=True,
            parent=self,
        )
        self.list_model.checked_keys_changed.connect(self._on_checked_keys_changed)
        self.list_view = QListView(self)
        self.list_view.setModel(self.list_model)
        self.list_view.setItemDelegate(RecordListDelegate(row_height=78, parent=self.list_view))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setWordWrap(True)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.setLayoutMode(QListView.Batched)
        self.list_view.setBatchSize(80)
        layout.addWidget(self.list_view, 1)

        buttons = QHBoxLayout()
        self.select_visible_button = QPushButton("全选可见", self)
        self.select_visible_button.clicked.connect(self.select_visible_tools)
        self.clear_button = QPushButton("取消选择", self)
        self.clear_button.clicked.connect(self.clear_selection)
        buttons.addWidget(self.select_visible_button)
        buttons.addWidget(self.clear_button)
        buttons.addStretch()

        self.delete_button = QPushButton("删除选中", self)
        self.delete_button.setObjectName("dangerButton")
        self.delete_button.clicked.connect(self.accept_selected_tools)
        self.close_button = QPushButton("关闭", self)
        self.close_button.clicked.connect(self.reject)
        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    @staticmethod
    def _build_category_labels(categories):
        labels = {}
        for category in categories:
            if not isinstance(category, dict):
                continue
            category_id = category.get("id")
            category_name = str(category.get("name") or "未命名分类").strip()
            if category_id is not None:
                labels[(category_id, None)] = category_name
            for subcategory in category.get("subcategories", []) or []:
                if not isinstance(subcategory, dict):
                    continue
                subcategory_id = subcategory.get("id")
                subcategory_name = str(subcategory.get("name") or "未命名子分类").strip()
                if category_id is not None and subcategory_id is not None:
                    labels[(category_id, subcategory_id)] = f"{category_name} / {subcategory_name}"
        return labels

    def _tool_category_label(self, tool):
        category_id = tool.get("category_id")
        subcategory_id = tool.get("subcategory_id")
        return (
            self.category_labels.get((category_id, subcategory_id))
            or self.category_labels.get((category_id, None))
            or "未分类"
        )

    def _format_tool_item_text(self, tool):
        if tool.get("_placeholder"):
            return tool.get("text", "")
        tool_id = tool.get("id", "")
        name = str(tool.get("name") or "未命名工具").strip()
        path = str(tool.get("path") or "未配置路径").strip()
        category = self._tool_category_label(tool)
        return f"{name}  [ID {tool_id}]\n{category}\n{path}"

    def _matches_tool(self, tool, query):
        if not query:
            return True
        haystack = " ".join(
            str(value or "")
            for value in (
                tool.get("id"),
                tool.get("name"),
                tool.get("path"),
                tool.get("description"),
                tool.get("type_label"),
                self._tool_category_label(tool),
            )
        ).casefold()
        return query in haystack

    def refresh_list(self):
        query = (self.search_input.text() or "").strip().casefold()
        self.visible_tool_ids = []
        visible_tools = []

        for tool in self.tools:
            tool_id = tool.get("id")
            if tool_id is None or not self._matches_tool(tool, query):
                continue
            visible_tools.append(tool)
            self.visible_tool_ids.append(tool_id)

        if not self.visible_tool_ids:
            visible_tools.append({"_placeholder": True, "text": "没有匹配的工具"})

        self.list_model.set_checked_keys(self.checked_tool_ids, emit=False)
        self.list_model.set_records(visible_tools)
        self._refresh_summary()

    def _refresh_summary(self):
        visible_count = len(self.visible_tool_ids)
        checked_count = len(self.checked_tool_ids)
        self.summary_label.setText(
            f"共 {len(self.tools)} 个工具，当前显示 {visible_count} 个，已选择 {checked_count} 个"
        )
        self.delete_button.setEnabled(checked_count > 0)
        self.select_visible_button.setEnabled(visible_count > 0)
        self.clear_button.setEnabled(checked_count > 0)

    def _on_checked_keys_changed(self):
        self.checked_tool_ids = self.list_model.checked_keys()
        self._refresh_summary()

    def select_visible_tools(self):
        self.checked_tool_ids.update(self.visible_tool_ids)
        self.refresh_list()

    def clear_selection(self):
        self.checked_tool_ids.clear()
        self.refresh_list()

    def accept_selected_tools(self):
        if not self.checked_tool_ids:
            QMessageBox.information(self, "未选择", "请先勾选要删除的工具。")
            return

        ordered_ids = []
        seen_ids = set()
        for tool in self.tools:
            tool_id = tool.get("id")
            if tool_id in self.checked_tool_ids and tool_id not in seen_ids:
                ordered_ids.append(tool_id)
                seen_ids.add(tool_id)
        self.selected_tool_ids = ordered_ids
        self.accept()

    def get_selected_tool_ids(self):
        return list(self.selected_tool_ids)

    def _apply_theme_styles(self):
        self.setStyleSheet(ThemeManager().get_dialog_list_style(self.theme_name))

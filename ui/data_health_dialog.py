#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据体检结果对话框。"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)


class DataHealthDialog(QDialog):
    ISSUE_LABELS = {
        'all': '全部问题',
        'missing_icon': '缺失图标',
        'invalid_path': '路径异常',
        'duplicate_name': '名称重复',
        'invalid_category': '分类异常',
        'field_inconsistency': '字段异常',
    }

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.audit_result = {'issues': [], 'counts': {}, 'total_tools': 0, 'total_issues': 0}
        self.selected_tool_id = None
        self.setWindowTitle('工具数据体检')
        self.setMinimumSize(780, 560)
        self._init_ui()
        self.refresh_results()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.summary_label = QLabel('正在检查...')
        top.addWidget(self.summary_label, 1)

        top.addWidget(QLabel('问题类型:'))
        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem(self.ISSUE_LABELS['all'], 'all')
        for key in ('missing_icon', 'invalid_path', 'duplicate_name', 'invalid_category', 'field_inconsistency'):
            self.filter_combo.addItem(self.ISSUE_LABELS[key], key)
        self.filter_combo.currentIndexChanged.connect(self.refresh_list)
        top.addWidget(self.filter_combo)
        layout.addLayout(top)

        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self._open_selected_issue)
        layout.addWidget(self.list_widget, 1)

        btns = QHBoxLayout()
        btns.addStretch()
        self.locate_btn = QPushButton('定位工具')
        self.locate_btn.clicked.connect(self._open_selected_issue)
        self.close_btn = QPushButton('关闭')
        self.close_btn.clicked.connect(self.reject)
        btns.addWidget(self.locate_btn)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

    def refresh_results(self):
        self.audit_result = self.data_manager.audit_tools_data() or {'issues': [], 'counts': {}, 'total_tools': 0, 'total_issues': 0}
        total_tools = self.audit_result.get('total_tools', 0)
        total_issues = self.audit_result.get('total_issues', 0)
        if total_issues:
            self.summary_label.setText(f'已检查 {total_tools} 个工具，发现 {total_issues} 个问题。')
        else:
            self.summary_label.setText(f'已检查 {total_tools} 个工具，未发现问题。')
        self.refresh_list()

    def refresh_list(self):
        selected_type = self.filter_combo.currentData() or 'all'
        issues = self.audit_result.get('issues', []) or []
        if selected_type != 'all':
            issues = [issue for issue in issues if issue.get('issue_type') == selected_type]

        self.list_widget.clear()
        if not issues:
            item = QListWidgetItem('未发现符合条件的问题。')
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
            self.list_widget.addItem(item)
            return

        for issue in issues:
            tool_name = issue.get('tool_name') or '未命名工具'
            title = issue.get('title') or issue.get('issue_type') or '未知问题'
            category_name = issue.get('category_name') or '未知分类'
            message = issue.get('message') or ''
            tool_id = issue.get('tool_id')
            text = f"{tool_name}  [ID {tool_id}]\n{title} | {category_name}\n{message}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, issue)
            self.list_widget.addItem(item)

    def _open_selected_issue(self, item=None):
        item = item or self.list_widget.currentItem()
        if item is None:
            return
        issue = item.data(Qt.UserRole)
        if not issue:
            return
        self.selected_tool_id = issue.get('tool_id')
        if self.selected_tool_id is None:
            return
        self.accept()

    def get_selected_tool_id(self):
        return self.selected_tool_id

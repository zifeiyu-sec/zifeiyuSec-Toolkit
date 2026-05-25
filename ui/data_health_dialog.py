#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data health result dialog."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.style_manager import ThemeManager
from ui.record_list_model import RECORD_ROLE, RecordListDelegate, RecordListModel


class DataHealthDialog(QDialog):
    ISSUE_LABELS = {
        'all': '全部问题',
        'split_mismatch': '数据镜像',
        'invalid_category': '分类异常',
        'invalid_path': '路径异常',
        'placeholder_path': '未配置路径',
        'missing_icon': '缺失图标',
        'invalid_icon': '无效图标',
        'duplicate_name': '名称重复',
        'field_inconsistency': '字段异常',
    }

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.theme_name = getattr(parent, 'current_theme', 'dark_green') if parent is not None else 'dark_green'
        self.audit_result = {'issues': [], 'counts': {}, 'total_tools': 0, 'total_issues': 0}
        self.selected_tool_id = None
        self.setWindowTitle('工具数据体检')
        self.setMinimumSize(780, 560)
        self._init_ui()
        self._apply_theme_styles()
        self.refresh_results()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.data_dir_label = QLabel('')
        self.data_dir_label.setObjectName("dataHealthPathLabel")
        self.data_dir_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.data_dir_label)

        top = QHBoxLayout()
        self.summary_label = QLabel('正在检查...')
        top.addWidget(self.summary_label, 1)

        top.addWidget(QLabel('问题类型:'))
        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem(self.ISSUE_LABELS['all'], 'all')
        for key in (
            'split_mismatch',
            'invalid_category',
            'invalid_path',
            'placeholder_path',
            'missing_icon',
            'invalid_icon',
            'duplicate_name',
            'field_inconsistency',
        ):
            self.filter_combo.addItem(self.ISSUE_LABELS[key], key)
        self.filter_combo.currentIndexChanged.connect(self.refresh_list)
        top.addWidget(self.filter_combo)
        layout.addLayout(top)

        self.list_model = RecordListModel(text_func=self._format_issue_text, parent=self)
        self.list_view = QListView(self)
        self.list_view.setModel(self.list_model)
        self.list_view.setItemDelegate(RecordListDelegate(row_height=78, parent=self.list_view))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setWordWrap(True)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.setLayoutMode(QListView.Batched)
        self.list_view.setBatchSize(80)
        self.list_view.doubleClicked.connect(self._open_selected_issue)
        layout.addWidget(self.list_view, 1)

        btns = QHBoxLayout()
        self.rebuild_split_btn = QPushButton('重建拆分镜像')
        self.rebuild_split_btn.clicked.connect(self.rebuild_split_mirror)
        btns.addWidget(self.rebuild_split_btn)
        btns.addStretch()
        self.locate_btn = QPushButton('定位工具')
        self.locate_btn.clicked.connect(self._open_selected_issue)
        self.close_btn = QPushButton('关闭')
        self.close_btn.clicked.connect(self.reject)
        btns.addWidget(self.locate_btn)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

    def _apply_theme_styles(self):
        self.setStyleSheet(ThemeManager().get_dialog_list_style(self.theme_name))

    @staticmethod
    def _format_issue_text(issue):
        if issue.get("_placeholder"):
            return issue.get("text", "")
        tool_name = issue.get('tool_name') or 'Unnamed tool'
        title = issue.get('title') or issue.get('issue_type') or 'Unknown issue'
        category_name = issue.get('category_name') or 'Unknown category'
        message = issue.get('message') or ''
        tool_id = issue.get('tool_id')
        return f"{tool_name}  [ID {tool_id}]\n{title} | {category_name}\n{message}"

    def refresh_results(self):
        self.audit_result = self.data_manager.audit_tools_data() or {'issues': [], 'counts': {}, 'total_tools': 0, 'total_issues': 0}
        total_tools = self.audit_result.get('total_tools', 0)
        total_issues = self.audit_result.get('total_issues', 0)
        data_dir = self.audit_result.get('data_dir') or getattr(self.data_manager, 'data_dir', '')
        self.data_dir_label.setText(f'当前生效数据目录: {data_dir}')
        if total_issues:
            counts = self.audit_result.get('counts', {}) or {}
            count_text = '，'.join(
                f"{self.ISSUE_LABELS.get(key, key)} {value}"
                for key, value in counts.items()
                if value
            )
            self.summary_label.setText(f'已检查 {total_tools} 个工具，发现 {total_issues} 个问题。{count_text}')
        else:
            self.summary_label.setText(f'已检查 {total_tools} 个工具，未发现问题')
        self._refresh_rebuild_button_state()
        self.refresh_list()

    def _refresh_rebuild_button_state(self):
        split_consistency = self.audit_result.get('split_consistency') or {}
        self.rebuild_split_btn.setEnabled(not bool(split_consistency.get('consistent', False)))
        if split_consistency.get('consistent', False):
            self.rebuild_split_btn.setToolTip('聚合 tools.json 与拆分镜像一致')
        else:
            self.rebuild_split_btn.setToolTip(split_consistency.get('message') or '重建 .runtime/data/tools/*.json 镜像')

    def refresh_list(self):
        selected_type = self.filter_combo.currentData() or 'all'
        issues = self.audit_result.get('issues', []) or []
        if selected_type != 'all':
            issues = [issue for issue in issues if issue.get('issue_type') == selected_type]

        if not issues:
            self.list_model.set_records([{"_placeholder": True, "text": "没有匹配的问题"}])
            return

        self.list_model.set_records(issues)

    def rebuild_split_mirror(self):
        split_consistency = self.audit_result.get('split_consistency') or {}
        if split_consistency.get('consistent', False):
            QMessageBox.information(self, '无需重建', '聚合 tools.json 与拆分镜像已经一致。')
            return

        result = QMessageBox.question(
            self,
            '重建拆分镜像',
            '将以当前聚合 tools.json 为准重建 .runtime/data/tools/*.json。\n'
            '旧拆分镜像会先复制为 backup 目录，不会删除工具主数据。\n\n'
            '是否继续？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return

        try:
            rebuild_result = self.data_manager.rebuild_tools_split_mirror(backup=True)
        except Exception as exc:
            QMessageBox.warning(self, '重建失败', f'重建拆分镜像失败：{exc}')
            self.refresh_results()
            return

        backup_path = rebuild_result.get('backup_path') or '未创建备份（原拆分镜像为空）'
        if rebuild_result.get('success'):
            QMessageBox.information(
                self,
                '重建完成',
                f"已重建 {rebuild_result.get('tools', 0)} 个工具的拆分镜像。\n备份目录: {backup_path}",
            )
        else:
            QMessageBox.warning(
                self,
                '重建后仍不一致',
                f"已尝试重建拆分镜像，但一致性检查仍未通过。\n备份目录: {backup_path}",
            )
        self.refresh_results()

    def _open_selected_issue(self, index=None):
        if index is None or not index.isValid():
            index = self.list_view.currentIndex()
        if not index.isValid():
            return
        issue = self.list_model.data(index, RECORD_ROLE)
        if not issue:
            return
        if issue.get('issue_type') == 'split_mismatch':
            self.filter_combo.setCurrentIndex(max(0, self.filter_combo.findData('split_mismatch')))
            return
        self.selected_tool_id = issue.get('tool_id')
        if self.selected_tool_id is None:
            return
        self.accept()

    def get_selected_tool_id(self):
        return self.selected_tool_id

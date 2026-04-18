#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""笔记列表对话框。"""
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QListWidgetItem, QPushButton, QVBoxLayout)

from core.notes_manager import NotesManager
from ui.markdown_note_dialog import MarkdownNoteDialog


class NotesListDialog(QDialog):
    def __init__(self, repo_root=None, theme_name=None, parent=None):
        super().__init__(parent)
        self.notes = NotesManager(repo_root=repo_root)
        self.theme_name = theme_name or getattr(parent, 'current_theme', 'dark_green') if parent is not None else 'dark_green'
        self.note_records = []

        self.setWindowTitle('笔记列表')
        self.setMinimumSize(720, 520)

        self._init_ui()
        self.refresh_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel('搜索:'))
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText('按工具名、摘要或正文搜索笔记...')
        self.search_input.textChanged.connect(self.refresh_list)
        top.addWidget(self.search_input, 1)
        layout.addLayout(top)

        self.list_widget = QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self._open_selected_note)
        layout.addWidget(self.list_widget, 1)

        btns = QHBoxLayout()
        btns.addStretch()
        self.open_btn = QPushButton('打开笔记')
        self.open_btn.clicked.connect(self._open_selected_note)
        self.close_btn = QPushButton('关闭')
        self.close_btn.clicked.connect(self.accept)
        btns.addWidget(self.open_btn)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

    def refresh_list(self):
        query = (self.search_input.text() or '').strip()
        if query:
            records = self.notes.search_notes(query)
            records = sorted(records, key=lambda item: item.get('updated_at', 0), reverse=True)
        else:
            records = self.notes.list_notes()

        self.note_records = records
        self.list_widget.clear()

        for record in records:
            updated = record.get('updated_at', 0)
            updated_text = datetime.fromtimestamp(updated).strftime('%Y-%m-%d %H:%M') if updated else '未知时间'
            summary = record.get('excerpt') or record.get('summary') or '无内容'
            title = record.get('tool_name') or 'untitled'
            attachments = record.get('attachment_count', 0)
            text = f"{title}\n{updated_text} | 附件 {attachments}\n{summary}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, {
                'tool_id': record.get('tool_id'),
                'tool_name': title,
            })
            self.list_widget.addItem(item)

    def _open_selected_note(self, item=None):
        item = item or self.list_widget.currentItem()
        if item is None:
            return
        tool_ref = item.data(Qt.UserRole) or {}
        dialog = MarkdownNoteDialog(
            tool_id=tool_ref.get('tool_id'),
            tool_name=tool_ref.get('tool_name', 'untitled'),
            repo_root=self.notes.repo_root,
            parent=self,
            theme_name=self.theme_name,
        )
        dialog.exec_()
        self.refresh_list()

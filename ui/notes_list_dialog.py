#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Notes list dialog."""
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QListView, QPushButton, QVBoxLayout)

from core.notes_manager import NotesManager
from core.style_manager import ThemeManager
from ui.markdown_note_dialog import MarkdownNoteDialog
from ui.record_list_model import RECORD_ROLE, RecordListDelegate, RecordListModel


class NotesListDialog(QDialog):
    def __init__(self, repo_root=None, theme_name=None, parent=None):
        super().__init__(parent)
        self.notes = NotesManager(repo_root=repo_root)
        self.theme_name = theme_name or getattr(parent, 'current_theme', 'dark_green') if parent is not None else 'dark_green'
        self.note_records = []

        self.setWindowTitle('笔记列表')
        self.setMinimumSize(720, 520)

        self._init_ui()
        self._apply_theme_styles()
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

        self.list_model = RecordListModel(text_func=self._format_record_text, parent=self)
        self.list_view = QListView(self)
        self.list_view.setModel(self.list_model)
        self.list_view.setItemDelegate(RecordListDelegate(row_height=76, parent=self.list_view))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setWordWrap(True)
        self.list_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_view.setLayoutMode(QListView.Batched)
        self.list_view.setBatchSize(80)
        self.list_view.doubleClicked.connect(self._open_selected_note)
        layout.addWidget(self.list_view, 1)

        btns = QHBoxLayout()
        btns.addStretch()
        self.open_btn = QPushButton('打开笔记')
        self.open_btn.clicked.connect(self._open_selected_note)
        self.close_btn = QPushButton('关闭')
        self.close_btn.clicked.connect(self.accept)
        btns.addWidget(self.open_btn)
        btns.addWidget(self.close_btn)
        layout.addLayout(btns)

    def _apply_theme_styles(self):
        self.setStyleSheet(ThemeManager().get_dialog_list_style(self.theme_name))

    @staticmethod
    def _format_record_text(record):
        updated = record.get('updated_at', 0)
        updated_text = datetime.fromtimestamp(updated).strftime('%Y-%m-%d %H:%M') if updated else 'Unknown time'
        summary = record.get('excerpt') or record.get('summary') or 'No content'
        title = record.get('tool_name') or 'untitled'
        attachments = record.get('attachment_count', 0)
        return f"{title}\n{updated_text} | 附件 {attachments}\n{summary}"

    def refresh_list(self):
        query = (self.search_input.text() or '').strip()
        if query:
            records = self.notes.search_notes(query)
            records = sorted(records, key=lambda item: item.get('updated_at', 0), reverse=True)
        else:
            records = self.notes.list_notes()

        self.note_records = records
        self.list_model.set_records(records)

    def _open_selected_note(self, index=None):
        if index is None or not index.isValid():
            index = self.list_view.currentIndex()
        if not index.isValid():
            return
        tool_ref = self.list_model.data(index, RECORD_ROLE) or {}
        dialog = MarkdownNoteDialog(
            tool_id=tool_ref.get('tool_id'),
            tool_name=tool_ref.get('tool_name', 'untitled'),
            repo_root=self.notes.repo_root,
            parent=self,
            theme_name=self.theme_name,
        )
        dialog.exec_()
        self.refresh_list()

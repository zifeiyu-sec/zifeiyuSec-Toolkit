#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Note Dialog

Provides a simple split editor: left raw Markdown (QTextEdit), right preview (QTextBrowser).
Uses `markdown` package to convert markdown -> html. Saves via `NotesManager`.
"""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QTextBrowser,
                             QPushButton, QLabel, QToolButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer

try:
    import markdown as _markdown
except Exception:
    _markdown = None

from core.notes_manager import NotesManager


class MarkdownNoteDialog(QDialog):
    def __init__(self, tool_name: str, repo_root: str = None, parent=None, theme_name: str = None):
        super().__init__(parent)
        self.tool_name = tool_name or 'untitled'
        self.setWindowTitle(f"笔记 — {self.tool_name}")
        self.setMinimumSize(700, 480)

        # 主题优先级：参数 > 父级（如果有 current_theme） > dark_green
        if theme_name:
            self.theme = theme_name
        else:
            self.theme = getattr(parent, 'current_theme', 'dark_green') if parent is not None else 'dark_green'

        self.notes = NotesManager(repo_root=repo_root)

        self._init_ui()

        # 加载现有内容
        content = self.notes.load_note(self.tool_name)
        self.editor.setPlainText(content)
        # 立即更新预览
        self._update_preview()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 顶部 header + 切换按钮
        top_bar = QHBoxLayout()
        header = QLabel(f"工具: {self.tool_name}")
        header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        top_bar.addWidget(header)

        top_bar.addStretch()
        # 切换编辑/只看预览按钮
        self.toggle_preview_btn = QToolButton()
        self.toggle_preview_btn.setText("只看预览")
        self.toggle_preview_btn.setCheckable(True)
        self.toggle_preview_btn.toggled.connect(self.set_preview_only)
        top_bar.addWidget(self.toggle_preview_btn)

        layout.addLayout(top_bar)

        split = QHBoxLayout()

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(False)
        self.editor.textChanged.connect(self._on_text_changed)

        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)

        split.addWidget(self.editor, 1)
        split.addWidget(self.preview, 1)

        layout.addLayout(split)

        # 按钮栏
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("保存")
        self.save_btn.clicked.connect(self.on_save)
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        # 预览防抖
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(300)
        self._preview_timer.timeout.connect(self._update_preview)

    def _on_text_changed(self):
        # 延迟更新预览，减小频繁渲染开销
        self._preview_timer.start()

    def set_preview_only(self, preview_only: bool):
        """切换到只看预览模式（隐藏左侧编辑器）或恢复分屏编辑模式。"""
        if preview_only:
            # 隐藏编辑器，让预览占据全部空间
            self.editor.hide()
            # 将 preview 拉为主控件
            self.preview.setParent(None)
            # 把 preview 重新加入布局以填满
            self.layout().itemAt(1).addWidget(self.preview, 1)
            self.toggle_preview_btn.setText("编辑")
        else:
            # 恢复编辑器
            self.editor.show()
            # 确保 preview 在右侧
            self.preview.setParent(None)
            self.layout().itemAt(1).addWidget(self.editor, 1)
            self.layout().itemAt(1).addWidget(self.preview, 1)
            self.toggle_preview_btn.setText("只看预览")
        # 强制更新预览样式以匹配当前主题
        self._update_preview()

    def _update_preview(self):
        text = self.editor.toPlainText()
        if _markdown:
            try:
                html = _markdown.markdown(text, extensions=['fenced_code', 'tables', 'toc'])
            except Exception:
                html = '<pre>' + self._escape(text) + '</pre>'
        else:
            # 退回到简单的预览
            html = '<pre>' + self._escape(text) + '</pre>'

        # 基本样式保证可读性，并根据主题调整预览背景/文字
        if self.theme == 'blue_white':
            body_style = 'body{font-family:Segoe UI,Arial, sans-serif; padding:10px; background:#ffffff; color:#0b2540;} '
            pre_style = 'pre{background:#f6f8fa;padding:10px;border-radius:6px;overflow:auto;}'
        else:
            # 深绿主题
            body_style = 'body{font-family:Segoe UI,Arial, sans-serif; padding:10px; background:#1a1a2e; color:#e6ffe8;} '
            pre_style = 'pre{background:rgba(15,52,96,0.6);padding:10px;border-radius:6px;overflow:auto;color:#e6ffe8;}'

        styled = ('<html><head><meta charset="utf-8">'
                  '<style>' + body_style + pre_style + '</style></head>'
                  '<body>' + html + '</body></html>')

        self.preview.setHtml(styled)

    def _escape(self, s: str) -> str:
        return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                .replace('\n', '<br/>'))

    def on_save(self):
        content = self.editor.toPlainText()
        ok = self.notes.save_note(self.tool_name, content)
        if ok:
            QMessageBox.information(self, '保存', '笔记已保存。')
        else:
            QMessageBox.warning(self, '保存失败', '保存笔记时发生错误。')

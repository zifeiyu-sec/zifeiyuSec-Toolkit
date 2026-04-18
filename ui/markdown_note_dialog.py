#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown Note Dialog

单窗口 Markdown 编辑器，支持工具栏、基础语法高亮、自动保存与附件插入。
"""
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QRegularExpression, QTimer
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QPixmap, QTextBlock
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.notes_manager import NotesManager


class MarkdownHighlighter(QSyntaxHighlighter):
    def __init__(self, editor: QTextEdit, theme: str = 'dark_green'):
        super().__init__(editor.document())
        self.editor = editor
        self.theme = theme or 'dark_green'
        self.rules = []
        self._fence_pattern = QRegularExpression(r'^\s*```.*$')
        self._heading_pattern = QRegularExpression(r'^(\s*)(#{1,6})\s+(.*)$')
        self._quote_pattern = QRegularExpression(r'^(\s*)(>)\s?(.*)$')
        self._list_pattern = QRegularExpression(r'^(\s*)((?:[-*+])|(?:\d+\.))\s+(.*)$')
        self._build_rules()

    def _color(self, dark: str, light: str) -> QColor:
        return QColor(light if self.theme == 'blue_white' else dark)

    def _format(self, color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _build_rules(self):
        heading_color = self._color('#7dd3fc', '#1d4ed8').name()
        emphasis_color = self._color('#f9a8d4', '#be185d').name()
        code_color = self._color('#86efac', '#166534').name()
        quote_color = self._color('#fcd34d', '#b45309').name()
        list_color = self._color('#fdba74', '#c2410c').name()
        link_color = self._color('#c4b5fd', '#6d28d9').name()
        rule_color = self._color('#94a3b8', '#64748b').name()
        marker_color = self._color('#475569', '#cbd5e1').name()

        self.rules = [
            (QRegularExpression(r'`[^`]+`'), self._format(code_color)),
            (QRegularExpression(r'!\[[^\]]*\]\([^\)]+\)'), self._format(link_color)),
            (QRegularExpression(r'\[[^\]]+\]\([^\)]+\)'), self._format(link_color)),
            (QRegularExpression(r'^\s*(?:---|\*\*\*|___)\s*$'), self._format(rule_color)),
            (QRegularExpression(r'\*\*[^*]+\*\*'), self._format(emphasis_color, bold=True)),
            (QRegularExpression(r'__[^_]+__'), self._format(emphasis_color, bold=True)),
            (QRegularExpression(r'~~[^~]+~~'), self._format(emphasis_color)),
            (QRegularExpression(r'(?<!\*)\*[^*]+\*(?!\*)'), self._format(emphasis_color, italic=True)),
            (QRegularExpression(r'(?<!_)_[^_]+_(?!_)'), self._format(emphasis_color, italic=True)),
        ]

        self.fence_format = self._format(code_color)
        self.fence_format.setBackground(self._color('#111827', '#eff6ff'))
        self.fence_format.setFontFamily('Consolas')

        self.hidden_marker_format = QTextCharFormat()
        self.hidden_marker_format.setForeground(self._color('#0f172a', '#ffffff'))
        self.hidden_marker_format.setFontPointSize(1)

        self.heading_body_formats = {
            1: self._format(heading_color, bold=True),
            2: self._format(heading_color, bold=True),
            3: self._format(heading_color, bold=True),
            4: self._format(heading_color, bold=True),
            5: self._format(heading_color, bold=True),
            6: self._format(heading_color, bold=True),
        }
        self.heading_body_formats[1].setFontPointSize(18)
        self.heading_body_formats[2].setFontPointSize(16)
        self.heading_body_formats[3].setFontPointSize(14)
        self.heading_body_formats[4].setFontPointSize(13)
        self.heading_body_formats[5].setFontPointSize(12)
        self.heading_body_formats[6].setFontPointSize(11)

        self.quote_content_format = self._format(quote_color, italic=True)
        self.quote_content_format.setBackground(self._color('#1f2937', '#fff7ed'))

        self.list_content_format = self._format(list_color)
        self.list_content_format.setFontWeight(QFont.Medium)

        self.marker_format = self._format(marker_color)

    def _is_current_block(self, block: QTextBlock) -> bool:
        cursor = self.editor.textCursor()
        return block.blockNumber() == cursor.blockNumber()

    def _apply_heading_display(self, text: str):
        match = self._heading_pattern.match(text)
        if not match.hasMatch():
            return False

        if self._is_current_block(self.currentBlock()):
            return False

        indent = match.capturedLength(1)
        marker = match.captured(2)
        level = len(marker)
        marker_length = len(marker) + 1
        title_start = indent + marker_length
        title_length = len(text) - title_start

        if title_length <= 0:
            return False

        self.setFormat(indent, marker_length, self.hidden_marker_format)
        self.setFormat(title_start, title_length, self.heading_body_formats.get(level, self.heading_body_formats[6]))
        return True

    def _apply_quote_display(self, text: str):
        match = self._quote_pattern.match(text)
        if not match.hasMatch() or self._is_current_block(self.currentBlock()):
            return False

        marker_start = len(match.captured(1))
        marker_length = len(match.captured(2))
        content_start = match.capturedStart(3)
        content_length = len(match.captured(3))
        self.setFormat(marker_start, marker_length, self.hidden_marker_format)
        if content_length > 0:
            self.setFormat(content_start, content_length, self.quote_content_format)
        return True

    def _apply_list_display(self, text: str):
        match = self._list_pattern.match(text)
        if not match.hasMatch() or self._is_current_block(self.currentBlock()):
            return False

        marker_start = len(match.captured(1))
        marker_length = len(match.captured(2))
        content_start = match.capturedStart(3)
        content_length = len(match.captured(3))
        self.setFormat(marker_start, marker_length, self.hidden_marker_format)
        if content_length > 0:
            self.setFormat(content_start, content_length, self.list_content_format)
        return True

    def _apply_inline_marker_hiding(self, text: str):
        if self._is_current_block(self.currentBlock()):
            return

        patterns = [
            QRegularExpression(r'(\*\*)([^*\n]+)(\*\*)'),
            QRegularExpression(r'(__)([^_\n]+)(__)'),
            QRegularExpression(r'(?<!\*)(\*)([^*\n]+)(\*)(?!\*)'),
            QRegularExpression(r'(?<!_)(_)([^_\n]+)(_)(?!_)'),
            QRegularExpression(r'(~~)([^~\n]+)(~~)'),
            QRegularExpression(r'(`)([^`\n]+)(`)'),
        ]

        for pattern in patterns:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(1), match.capturedLength(1), self.hidden_marker_format)
                self.setFormat(match.capturedStart(3), match.capturedLength(3), self.hidden_marker_format)

    def highlightBlock(self, text: str):
        in_fence = self.previousBlockState() == 1
        if self._fence_pattern.match(text).hasMatch():
            if not self._is_current_block(self.currentBlock()):
                self.setFormat(0, len(text), self.fence_format)
            self.setCurrentBlockState(0 if in_fence else 1)
            return

        if in_fence:
            if not self._is_current_block(self.currentBlock()):
                self.setFormat(0, len(text), self.fence_format)
            self.setCurrentBlockState(1)
            return

        heading_applied = self._apply_heading_display(text)
        quote_applied = self._apply_quote_display(text)
        list_applied = self._apply_list_display(text)

        for pattern, fmt in self.rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        if not heading_applied and not quote_applied and not list_applied:
            self._apply_inline_marker_hiding(text)

        self.setCurrentBlockState(0)


class MarkdownNoteDialog(QDialog):
    IMAGE_PATTERN = QRegularExpression(r'!\[[^\]]*\]\(([^\)]+)\)')

    def __init__(self, tool_id=None, tool_name: str = '', repo_root: str = None, parent=None, theme_name: str = None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.tool_name = tool_name or 'untitled'
        self.theme = theme_name or getattr(parent, 'current_theme', 'dark_green')
        self.notes = NotesManager(repo_root=repo_root)

        self._dirty = False
        self._last_saved_content = ''
        self._last_saved_at = None

        self.setWindowTitle(f"笔记 - {self.tool_name}")
        self.setMinimumSize(900, 680)

        self._init_ui()

        content = self.notes.load_note(tool_id=self.tool_id, tool_name=self.tool_name)
        self.editor.setPlainText(content)
        self._last_saved_content = content
        self._dirty = False
        self._update_status('已加载')
        self._update_stats()
        self._refresh_image_previews()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"工具: {self.tool_name}")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.toolbar = QToolBar('Markdown 工具栏', self)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        layout.addWidget(self.toolbar)
        self._build_toolbar()

        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText('在这里直接编写 Markdown 笔记...')
        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._on_cursor_position_changed)
        self.highlighter = MarkdownHighlighter(self.editor, self.theme)
        layout.addWidget(self.editor, 1)

        self.preview_title = QLabel('图片预览')
        layout.addWidget(self.preview_title)

        self.preview_scroll = QScrollArea(self)
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.preview_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.preview_scroll.setMinimumHeight(126)
        self.preview_scroll.setMaximumHeight(164)
        self.preview_scroll.setFrameShape(QFrame.NoFrame)
        self.preview_container = QWidget(self.preview_scroll)
        self.preview_layout = QHBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_layout.setSpacing(8)
        self.preview_scroll.setWidget(self.preview_container)
        layout.addWidget(self.preview_scroll)

        footer_layout = QHBoxLayout()
        self.status_label = QLabel('未修改')
        self.meta_label = QLabel('0 行 · 0 字')
        footer_layout.addWidget(self.status_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.meta_label)
        layout.addLayout(footer_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton('保存')
        self.save_btn.clicked.connect(self.on_save)
        self.close_btn = QPushButton('关闭')
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(1200)
        self._autosave_timer.timeout.connect(self._auto_save)

        self._rehighlight_timer = QTimer(self)
        self._rehighlight_timer.setSingleShot(True)
        self._rehighlight_timer.setInterval(0)
        self._rehighlight_timer.timeout.connect(self.highlighter.rehighlight)

        self._apply_theme_styles()

    def _build_toolbar(self):
        def add_action(text, callback):
            action = QAction(text, self)
            action.triggered.connect(callback)
            self.toolbar.addAction(action)
            return action

        add_action('H1', lambda: self._prefix_current_lines('# '))
        add_action('H2', lambda: self._prefix_current_lines('## '))
        add_action('H3', lambda: self._prefix_current_lines('### '))
        self.toolbar.addSeparator()

        add_action('加粗', lambda: self._wrap_selection('**', '**', '文本'))
        add_action('斜体', lambda: self._wrap_selection('*', '*', '文本'))
        add_action('删除线', lambda: self._wrap_selection('~~', '~~', '文本'))
        add_action('行内代码', lambda: self._wrap_selection('`', '`', 'code'))
        add_action('代码块', self._insert_code_block)
        self.toolbar.addSeparator()

        add_action('引用', lambda: self._prefix_current_lines('> '))
        add_action('无序列表', lambda: self._prefix_current_lines('- '))
        add_action('有序列表', self._insert_ordered_list)
        add_action('分割线', lambda: self._insert_block('\n---\n'))
        self.toolbar.addSeparator()

        add_action('链接', self._insert_link)
        add_action('图片', self._insert_image_markdown)
        add_action('附件', self._insert_attachment)
        self.toolbar.addSeparator()

        add_action('保存', self.on_save)

    def _apply_theme_styles(self):
        if self.theme == 'blue_white':
            self.setStyleSheet(
                "QDialog { background: #f8fbff; color: #0f172a; }"
                "QTextEdit { background: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; selection-background-color: #bfdbfe; }"
                "QToolBar { background: #eaf4ff; border: 1px solid #cbd5e1; spacing: 4px; padding: 6px; border-radius: 8px; }"
                "QToolButton, QPushButton { background: #ffffff; border: 1px solid #cbd5e1; padding: 6px 10px; border-radius: 6px; }"
                "QToolButton:hover, QPushButton:hover { background: #eff6ff; }"
                "QLabel { color: #0f172a; }"
                "QScrollArea { background: transparent; }"
            )
        else:
            self.setStyleSheet(
                "QDialog { background: #101827; color: #e5f7e7; }"
                "QTextEdit { background: #0f172a; color: #e5f7e7; border: 1px solid #334155; border-radius: 8px; padding: 10px; selection-background-color: #14532d; }"
                "QToolBar { background: #162033; border: 1px solid #334155; spacing: 4px; padding: 6px; border-radius: 8px; }"
                "QToolButton, QPushButton { background: #1e293b; color: #e5f7e7; border: 1px solid #475569; padding: 6px 10px; border-radius: 6px; }"
                "QToolButton:hover, QPushButton:hover { background: #334155; }"
                "QLabel { color: #e5f7e7; }"
                "QScrollArea { background: transparent; }"
            )

    def _on_text_changed(self):
        self._dirty = True
        self._update_status('编辑中...')
        self._update_stats()
        self._refresh_image_previews()
        self._rehighlight_timer.start()
        self._autosave_timer.start()

    def _on_cursor_position_changed(self):
        self._rehighlight_timer.start()

    def _resolve_note_asset_path(self, raw_path: str) -> str:
        note_path = self.notes.get_note_path(tool_id=self.tool_id, tool_name=self.tool_name)
        candidate = (raw_path or '').strip().strip('"').strip("'")
        if not candidate:
            return ''
        if os.path.isabs(candidate):
            return candidate
        return os.path.normpath(os.path.join(str(note_path.parent), candidate))

    def _clear_image_previews(self):
        while self.preview_layout.count():
            item = self.preview_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _create_preview_card(self, title: str, image_path: str) -> QWidget:
        card = QWidget(self.preview_container)
        card.setFixedWidth(170)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(6)

        image_label = QLabel(card)
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setFixedHeight(88)

        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            image_label.setPixmap(pixmap.scaled(150, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            image_label.setText('图片不可预览')

        title_label = QLabel(title or os.path.basename(image_path), card)
        title_label.setWordWrap(True)
        path_label = QLabel(os.path.basename(image_path), card)
        path_label.setWordWrap(True)
        path_label.setStyleSheet('font-size: 11px; color: #64748b;' if self.theme == 'blue_white' else 'font-size: 11px; color: #94a3b8;')

        card_layout.addWidget(image_label)
        card_layout.addWidget(title_label)
        card_layout.addWidget(path_label)

        if self.theme == 'blue_white':
            card.setStyleSheet('QWidget { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; }')
        else:
            card.setStyleSheet('QWidget { background: #111827; border: 1px solid #334155; border-radius: 8px; }')
        return card

    def _refresh_image_previews(self):
        self._clear_image_previews()
        text = self._current_text()
        iterator = self.IMAGE_PATTERN.globalMatch(text)
        shown = 0

        while iterator.hasNext() and shown < 6:
            match = iterator.next()
            raw_path = match.captured(1)
            resolved_path = self._resolve_note_asset_path(raw_path)
            if not resolved_path or not os.path.exists(resolved_path):
                continue

            full_match = match.captured(0)
            title_match = QRegularExpression(r'!\[([^\]]*)\]').match(full_match)
            title = title_match.captured(1) if title_match.hasMatch() else ''
            self.preview_layout.addWidget(self._create_preview_card(title, resolved_path))
            shown += 1

        if shown == 0:
            self.preview_title.hide()
            self.preview_scroll.hide()
            return

        self.preview_title.show()
        self.preview_scroll.show()
        self.preview_layout.addStretch()

    def _current_text(self) -> str:
        return self.editor.toPlainText()

    def _update_stats(self):
        text = self._current_text()
        lines = text.count('\n') + 1 if text else 0
        chars = len(text)
        self.meta_label.setText(f'{lines} 行 · {chars} 字')

    def _update_status(self, text: str):
        if self._last_saved_at and text in {'已保存', '已自动保存'}:
            stamp = self._last_saved_at.strftime('%H:%M:%S')
            self.status_label.setText(f'{text} · {stamp}')
        else:
            self.status_label.setText(text)

    def _insert_text_at_cursor(self, text: str):
        cursor = self.editor.textCursor()
        cursor.insertText(text)
        self.editor.setFocus()

    def _insert_block(self, text: str):
        cursor = self.editor.textCursor()
        if cursor.position() > 0:
            cursor.insertText(text)
        else:
            cursor.insertText(text.lstrip('\n'))
        self.editor.setFocus()

    def _wrap_selection(self, prefix: str, suffix: str, placeholder: str = '文本'):
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().replace('\u2029', '\n')
        has_selection = bool(selected)
        if not selected:
            selected = placeholder
        cursor.insertText(f'{prefix}{selected}{suffix}')
        if not has_selection:
            for _ in range(len(suffix)):
                cursor.movePosition(QTextCursor.Left)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(selected))
            self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _prefix_current_lines(self, prefix: str):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.StartOfLine)
            start = cursor.position()
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            selected = cursor.selectedText().replace('\u2029', '\n')
            lines = selected.split('\n')
            updated = '\n'.join(f'{prefix}{line}' if line else prefix.rstrip() for line in lines)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.insertText(updated)
        else:
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.insertText(prefix)
        self.editor.setFocus()

    def _insert_code_block(self):
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().replace('\u2029', '\n').strip('\n')
        if selected:
            cursor.insertText(f'```\n{selected}\n```')
        else:
            cursor.insertText('```\ncode\n```')
            for _ in range(len('\n```')):
                cursor.movePosition(QTextCursor.Left)
            cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len('code'))
            self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _insert_ordered_list(self):
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().replace('\u2029', '\n')
        if selected:
            lines = [line for line in selected.split('\n') if line]
            if not lines:
                lines = ['条目']
            cursor.insertText('\n'.join(f'{index}. {line}' for index, line in enumerate(lines, start=1)))
        else:
            cursor.insertText('1. 条目')
        self.editor.setFocus()

    def _insert_link(self):
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().replace('\u2029', '\n').strip()
        label = selected or '链接文本'
        cursor.insertText(f'[{label}](https://)')
        self.editor.setFocus()

    def _insert_image_markdown(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            '选择图片',
            '',
            '图片文件 (*.png *.jpg *.jpeg *.gif *.webp *.svg *.bmp);;所有文件 (*.*)'
        )
        if not file_path:
            return

        attachment = self.notes.copy_attachment(file_path, tool_id=self.tool_id, tool_name=self.tool_name)
        if not attachment:
            QMessageBox.warning(self, '插入失败', '保存图片附件失败。')
            return

        alt_text = os.path.splitext(os.path.basename(file_path))[0]
        self._insert_text_at_cursor(f'![{alt_text}]({attachment.get("relative_path", "")})')

    def _insert_attachment(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '选择附件', '', '所有文件 (*.*)')
        if not file_path:
            return

        attachment = self.notes.copy_attachment(file_path, tool_id=self.tool_id, tool_name=self.tool_name)
        if not attachment:
            QMessageBox.warning(self, '插入失败', '保存附件失败。')
            return

        label = os.path.basename(file_path)
        self._insert_text_at_cursor(f'[{label}]({attachment.get("relative_path", "")})')

    def _save_content(self, *, auto: bool) -> bool:
        content = self._current_text()
        if content == self._last_saved_content:
            self._dirty = False
            self._update_status('已保存')
            return True

        if self.notes.save_note(content, tool_id=self.tool_id, tool_name=self.tool_name):
            self._last_saved_content = content
            self._dirty = False
            self._last_saved_at = datetime.now()
            self._update_status('已自动保存' if auto else '已保存')
            return True

        self._update_status('自动保存失败' if auto else '保存失败')
        return False

    def _auto_save(self):
        if self._dirty:
            self._save_content(auto=True)

    def on_save(self):
        if self._save_content(auto=False):
            QMessageBox.information(self, '保存', '笔记已保存。')
        else:
            QMessageBox.warning(self, '保存失败', '保存笔记时发生错误。')

    def closeEvent(self, event):
        self._autosave_timer.stop()
        self._rehighlight_timer.stop()
        if self._dirty and not self._save_content(auto=True):
            QMessageBox.warning(self, '保存失败', '关闭前自动保存失败，请手动重试。')
            event.ignore()
            return
        super().closeEvent(event)

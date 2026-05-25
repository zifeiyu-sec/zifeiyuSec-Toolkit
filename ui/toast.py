#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small non-blocking toast notification for the main window."""

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout

from core.style_manager import ThemeManager


class ToastWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("toastFrame")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setMaximumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self.title_label = QLabel(self)
        self.title_label.setObjectName("toastTitle")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.message_label = QLabel(self)
        self.message_label.setObjectName("toastMessage")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self.hide()

    def show_message(self, title, message="", theme_name="dark_green", kind="info", timeout_ms=3200):
        title = str(title or "").strip()
        message = str(message or "").strip()
        if not title and message:
            title, message = message, ""

        self.title_label.setText(title)
        self.message_label.setText(message)
        self.message_label.setVisible(bool(message))
        self.setStyleSheet(ThemeManager().get_toast_style(theme_name, kind=kind))
        self.adjustSize()
        self._position_to_parent()
        self.show()
        self.raise_()
        self._hide_timer.start(max(800, int(timeout_ms)))

    def _position_to_parent(self):
        parent = self.parentWidget()
        if parent is None:
            return
        margin = 22
        status_offset = 34
        width = min(self.sizeHint().width(), max(260, parent.width() - margin * 2))
        self.setFixedWidth(width)
        self.adjustSize()
        x = max(margin, parent.width() - self.width() - margin)
        y = max(margin, parent.height() - self.height() - status_offset - margin)
        self.move(x, y)

    def reposition(self):
        if self.isVisible():
            self._position_to_parent()

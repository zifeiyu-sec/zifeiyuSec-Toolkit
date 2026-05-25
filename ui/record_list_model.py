#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reusable virtual list model for dialog-sized record lists."""

from PyQt5.QtCore import QAbstractListModel, QModelIndex, QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QStyledItemDelegate


RECORD_ROLE = Qt.UserRole
KEY_ROLE = Qt.UserRole + 1


class RecordListModel(QAbstractListModel):
    checked_keys_changed = pyqtSignal()

    def __init__(self, text_func=None, key_func=None, checkable=False, parent=None):
        super().__init__(parent)
        self._records = []
        self._text_func = text_func or self._default_text
        self._key_func = key_func or self._default_key
        self._checkable = bool(checkable)
        self._checked_keys = set()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._records)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()
        if row < 0 or row >= len(self._records):
            return None
        record = self._records[row]

        if role == Qt.DisplayRole:
            return self._text_func(record)
        if role == RECORD_ROLE:
            return record
        if role == KEY_ROLE:
            return self._key_func(record)
        if role == Qt.CheckStateRole and self._checkable and not record.get("_placeholder"):
            return Qt.Checked if self._key_func(record) in self._checked_keys else Qt.Unchecked
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        record = self._records[index.row()]
        if record.get("_placeholder"):
            return Qt.ItemIsEnabled

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if self._checkable:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.CheckStateRole or not self._checkable or not index.isValid():
            return False
        record = self._records[index.row()]
        if record.get("_placeholder"):
            return False

        key = self._key_func(record)
        if value == Qt.Checked:
            self._checked_keys.add(key)
        else:
            self._checked_keys.discard(key)

        self.dataChanged.emit(index, index, [Qt.CheckStateRole])
        self.checked_keys_changed.emit()
        return True

    def set_records(self, records):
        self.beginResetModel()
        self._records = [record for record in (records or []) if isinstance(record, dict)]
        self.endResetModel()

    def records(self):
        return list(self._records)

    def record_at(self, index):
        if isinstance(index, QModelIndex):
            row = index.row()
        else:
            row = int(index)
        if row < 0 or row >= len(self._records):
            return None
        record = self._records[row]
        return None if record.get("_placeholder") else record

    def checked_keys(self):
        return set(self._checked_keys)

    def set_checked_keys(self, keys, emit=True):
        self._checked_keys = set(keys or [])
        if self._records:
            first = self.index(0, 0)
            last = self.index(len(self._records) - 1, 0)
            self.dataChanged.emit(first, last, [Qt.CheckStateRole])
        if emit:
            self.checked_keys_changed.emit()

    @staticmethod
    def _default_text(record):
        return str(record.get("text") or "")

    @staticmethod
    def _default_key(record):
        return record.get("id")


class RecordListDelegate(QStyledItemDelegate):
    def __init__(self, row_height=74, parent=None):
        super().__init__(parent)
        self.row_height = int(row_height)

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width(), max(self.row_height, size.height()))

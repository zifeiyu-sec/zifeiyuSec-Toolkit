#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notes manager - 管理基于工具名称的 Markdown 笔记文件。

Notes are stored under: <repo_root>/resources/notes/<sanitized_tool_name>.md
"""
import os
import re
from pathlib import Path


class NotesManager:
    def __init__(self, repo_root=None):
        # repo_root 若为 None，则推断为项目根（core 的父级）
        if repo_root:
            self.repo_root = Path(repo_root)
        else:
            self.repo_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self.notes_dir = self.repo_root / 'resources' / 'notes'
        self.notes_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        # 只保留安全的字符，替换其他字符为下划线
        if not name:
            return 'untitled'
        # 去掉两端空白
        name = name.strip()
        # 替换路径分隔符与非法字符
        safe = re.sub(r"[\\/:*?\"<>|]+", "_", name)
        # 限制长度，防止过长的文件名
        return safe[:200]

    def get_note_path(self, tool_name: str) -> Path:
        name = self._sanitize_name(tool_name)
        return self.notes_dir / f"{name}.md"

    def load_note(self, tool_name: str) -> str:
        path = self.get_note_path(tool_name)
        if path.exists():
            try:
                return path.read_text(encoding='utf-8')
            except Exception:
                try:
                    return path.read_text(encoding='utf-8', errors='ignore')
                except Exception:
                    return ''
        return ''

    def save_note(self, tool_name: str, content: str) -> bool:
        try:
            path = self.get_note_path(tool_name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content or '', encoding='utf-8')
            return True
        except Exception:
            return False

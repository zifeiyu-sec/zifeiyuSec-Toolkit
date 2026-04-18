#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notes manager - 管理基于工具稳定标识的 Markdown 笔记文件。

Notes are stored under: <repo_root>/resources/notes/tool_<id>.md
Legacy notes may still exist as: <repo_root>/resources/notes/<sanitized_tool_name>.md
Attachments are stored under: <repo_root>/resources/notes/_attachments/tool_<id>/
"""
import os
import re
import shutil
from pathlib import Path

from core.logger import logger
from core.runtime_paths import get_runtime_state_root


class NotesManager:
    def __init__(self, repo_root=None):
        if repo_root:
            self.repo_root = Path(repo_root)
        else:
            self.repo_root = get_runtime_state_root()

        self.notes_dir = self.repo_root / 'resources' / 'notes'
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.attachments_root = self.notes_dir / '_attachments'
        self.attachments_root.mkdir(parents=True, exist_ok=True)
        self._search_index = []
        self._search_index_token = None
        self._data_manager = None
        self._tool_name_cache = {}

    def _invalidate_search_index(self):
        self._search_index = []
        self._search_index_token = None
        self._tool_name_cache = {}

    def _get_search_index_token(self):
        note_files = sorted(self.notes_dir.glob('*.md'))
        return tuple(
            (
                str(note_path),
                note_path.stat().st_mtime if note_path.exists() else 0,
                note_path.stat().st_size if note_path.exists() else 0,
            )
            for note_path in note_files
        )

    def _get_data_manager(self):
        if self._data_manager is not None:
            return self._data_manager
        try:
            from core.data_manager import DataManager
            self._data_manager = DataManager(config_dir=os.fspath(self.repo_root))
        except Exception as e:
            logger.debug("初始化 NotesManager 的 DataManager 失败: %s", e)
            self._data_manager = False
        return self._data_manager if self._data_manager is not False else None

    def _resolve_tool_name(self, tool_id=None, fallback_name: str = '') -> str:
        if tool_id in (None, ''):
            return fallback_name or ''

        cache_key = int(tool_id) if isinstance(tool_id, int) or str(tool_id).isdigit() else tool_id
        if cache_key in self._tool_name_cache:
            return self._tool_name_cache[cache_key] or fallback_name or ''

        resolved_name = ''
        data_manager = self._get_data_manager()
        if data_manager is not None:
            try:
                tool = data_manager.get_tool_by_id(int(tool_id))
                if isinstance(tool, dict):
                    resolved_name = str(tool.get('name', '') or '').strip()
            except Exception as e:
                logger.debug("根据 tool_id 解析工具名失败 %s: %s", tool_id, e)

        self._tool_name_cache[cache_key] = resolved_name
        return resolved_name or fallback_name or ''

    def _build_search_index(self):
        token = self._get_search_index_token()
        if token == self._search_index_token and self._search_index:
            return self._search_index

        index = []
        for note_path in sorted(self.notes_dir.glob('*.md')):
            content = self._read_text(note_path)
            if not content:
                continue

            note_key, tool_id = self._parse_note_identity(note_path.stem)
            display_name = self._resolve_tool_name(tool_id=tool_id, fallback_name=note_key)
            summary = self._make_summary(content)
            record = self._build_note_record(note_path, content)
            record['note_key'] = note_key
            record['tool_id'] = tool_id
            index.append({
                'note_key': note_key,
                'tool_id': tool_id,
                'summary': summary,
                'content': content,
                'searchable_text': ' '.join(
                    filter(None, [note_key.lower(), display_name.lower(), summary.lower(), content.lower()])
                ),
                'record': record,
            })

        self._search_index = index
        self._search_index_token = token
        return self._search_index

    def _sanitize_name(self, name: str) -> str:
        if not name:
            return 'untitled'
        name = name.strip()
        safe = re.sub(r"[\\/:*?\"<>|]+", "_", name)
        return safe[:200]

    def _normalize_tool_key(self, tool_id=None, tool_name: str = '') -> str:
        if tool_id not in (None, ''):
            try:
                return f"tool_{int(tool_id)}"
            except (TypeError, ValueError):
                pass
        return self._sanitize_name(tool_name).lower()

    def _parse_note_identity(self, stem: str):
        text = str(stem or '').strip()
        match = re.fullmatch(r'tool_(\d+)', text)
        if match:
            return text, int(match.group(1))
        return text, None

    def _get_legacy_note_path(self, tool_name: str) -> Path:
        name = self._sanitize_name(tool_name)
        return self.notes_dir / f"{name}.md"

    def _get_legacy_attachment_dir(self, tool_name: str) -> Path:
        return self.attachments_root / self._sanitize_name(tool_name)

    def _maybe_migrate_legacy_note(self, tool_id=None, tool_name: str = '') -> Path | None:
        if tool_id in (None, '') or not tool_name:
            return None

        canonical_path = self.get_note_path(tool_id=tool_id, tool_name=tool_name, create=False)
        legacy_path = self._get_legacy_note_path(tool_name)
        if canonical_path.exists() or not legacy_path.exists():
            return canonical_path if canonical_path.exists() else None

        try:
            canonical_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(legacy_path), str(canonical_path))

            legacy_attachment_dir = self._get_legacy_attachment_dir(tool_name)
            canonical_attachment_dir = self.get_attachment_dir(tool_id=tool_id, tool_name=tool_name, create=True)
            if legacy_attachment_dir.exists() and legacy_attachment_dir.is_dir():
                for source in legacy_attachment_dir.iterdir():
                    if not source.is_file():
                        continue
                    target = canonical_attachment_dir / source.name
                    if not target.exists():
                        shutil.copy2(str(source), str(target))

            self._invalidate_search_index()
            return canonical_path
        except Exception as e:
            logger.warning("迁移旧版笔记失败 %s -> %s: %s", legacy_path, canonical_path, e)
            return legacy_path if legacy_path.exists() else None

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            logger.warning("读取笔记失败，尝试忽略错误继续读取: %s", e)
            try:
                return path.read_text(encoding='utf-8', errors='ignore')
            except Exception as fallback_error:
                logger.warning("读取笔记失败: %s", fallback_error)
                return ''

    def _strip_markdown(self, content: str) -> str:
        if not content:
            return ''

        text = content.replace('\r', '\n')
        text = re.sub(r'```[\s\S]*?```', ' ', text)
        text = re.sub(r'`([^`]*)`', r'\1', text)
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', text)
        text = re.sub(r'(^|\n)#{1,6}\s*', ' ', text)
        text = re.sub(r'(^|\n)[>*-]\s*', ' ', text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _make_summary(self, content: str, max_length: int = 120) -> str:
        text = self._strip_markdown(content)
        if len(text) <= max_length:
            return text
        return text[:max_length].rstrip() + '...'

    def _make_excerpt(self, content: str, query: str, radius: int = 30) -> str:
        if not content:
            return ''

        content_lower = content.lower()
        match_index = content_lower.find(query)
        if match_index < 0:
            return self._make_summary(content, max_length=radius * 2)

        start = max(0, match_index - radius)
        end = min(len(content), match_index + len(query) + radius)
        excerpt = content[start:end].replace('\n', ' ').strip()
        if start > 0:
            excerpt = f"...{excerpt}"
        if end < len(content):
            excerpt = f"{excerpt}..."
        return excerpt

    def _iter_attachment_files(self, tool_id=None, tool_name: str = ''):
        attachment_dir = self.get_attachment_dir(tool_id=tool_id, tool_name=tool_name, create=False)
        if not attachment_dir.exists() and tool_name:
            legacy_dir = self._get_legacy_attachment_dir(tool_name)
            if legacy_dir.exists():
                attachment_dir = legacy_dir
        if not attachment_dir.exists():
            return []
        return sorted(path for path in attachment_dir.iterdir() if path.is_file())

    def _build_note_record(self, note_path: Path, content: str = None) -> dict:
        if content is None:
            content = self._read_text(note_path)

        note_key, tool_id = self._parse_note_identity(note_path.stem)
        display_name = self._resolve_tool_name(tool_id=tool_id, fallback_name=note_key)
        attachments = self._iter_attachment_files(tool_id=tool_id, tool_name=note_key)
        try:
            stat = note_path.stat()
            updated_at = stat.st_mtime
            size = stat.st_size
        except Exception:
            updated_at = 0
            size = 0

        return {
            'tool_name': display_name,
            'note_key': note_key,
            'tool_id': tool_id,
            'path': str(note_path),
            'note_path': str(note_path),
            'summary': self._make_summary(content),
            'content_length': len(content or ''),
            'size': size,
            'updated_at': updated_at,
            'attachment_dir': str(self.get_attachment_dir(tool_id=tool_id, tool_name=note_key, create=False)),
            'attachment_count': len(attachments),
            'attachments': [
                {
                    'name': attachment.name,
                    'path': str(attachment),
                    'suffix': attachment.suffix.lower(),
                    'size': attachment.stat().st_size if attachment.exists() else 0,
                }
                for attachment in attachments
            ],
        }

    def get_note_path(self, tool_id=None, tool_name: str = '', create: bool = True) -> Path:
        note_key = self._normalize_tool_key(tool_id=tool_id, tool_name=tool_name)
        path = self.notes_dir / f"{note_key}.md"
        if create and tool_id not in (None, '') and tool_name:
            self._maybe_migrate_legacy_note(tool_id=tool_id, tool_name=tool_name)
        return path

    def get_attachment_dir(self, tool_id=None, tool_name: str = '', create: bool = True) -> Path:
        attachment_dir = self.attachments_root / self._normalize_tool_key(tool_id=tool_id, tool_name=tool_name)
        if create:
            attachment_dir.mkdir(parents=True, exist_ok=True)
            if tool_id not in (None, '') and tool_name:
                legacy_dir = self._get_legacy_attachment_dir(tool_name)
                if legacy_dir.exists() and legacy_dir.is_dir():
                    for source in legacy_dir.iterdir():
                        if not source.is_file():
                            continue
                        target = attachment_dir / source.name
                        if not target.exists():
                            try:
                                shutil.copy2(str(source), str(target))
                            except Exception as e:
                                logger.warning("迁移旧版附件失败 %s -> %s: %s", source, target, e)
        return attachment_dir

    def get_attachment_relative_path(self, tool_id=None, tool_name: str = '', file_name: str = '') -> str:
        safe_name = Path(file_name or '').name
        if not safe_name:
            return ''
        return f"_attachments/{self._normalize_tool_key(tool_id=tool_id, tool_name=tool_name)}/{safe_name}"

    def get_note_key(self, tool_id=None, tool_name: str = '') -> str:
        return self._normalize_tool_key(tool_id=tool_id, tool_name=tool_name)

    def load_note(self, tool_id=None, tool_name: str = '') -> str:
        path = self.get_note_path(tool_id=tool_id, tool_name=tool_name)
        if path.exists():
            return self._read_text(path)
        if tool_name:
            legacy_path = self._get_legacy_note_path(tool_name)
            if legacy_path.exists():
                return self._read_text(legacy_path)
        return ''

    def save_note(self, content: str, tool_id=None, tool_name: str = '') -> bool:
        try:
            path = self.get_note_path(tool_id=tool_id, tool_name=tool_name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content or '', encoding='utf-8')
            self._invalidate_search_index()
            return True
        except Exception as e:
            logger.warning("保存笔记失败 %s/%s: %s", tool_id, tool_name, e)
            return False

    def list_notes(self):
        results = []
        for note_path in sorted(
            self.notes_dir.glob('*.md'),
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        ):
            results.append(self._build_note_record(note_path))
        return results

    def get_note_summary(self, tool_id=None, tool_name: str = '', max_length: int = 120) -> dict:
        path = self.get_note_path(tool_id=tool_id, tool_name=tool_name, create=False)
        if not path.exists() and tool_name:
            path = self._get_legacy_note_path(tool_name)
        if not path.exists():
            return {
                'tool_name': tool_name or self._normalize_tool_key(tool_id=tool_id, tool_name=tool_name),
                'tool_id': tool_id,
                'path': str(path),
                'note_path': str(path),
                'summary': '',
                'content_length': 0,
                'size': 0,
                'updated_at': 0,
                'attachment_dir': str(self.get_attachment_dir(tool_id=tool_id, tool_name=tool_name, create=False)),
                'attachment_count': 0,
                'attachments': [],
            }

        record = self._build_note_record(path)
        record['summary'] = self._make_summary(self.load_note(tool_id=tool_id, tool_name=tool_name), max_length=max_length)
        if tool_name:
            record['tool_name'] = tool_name
        if tool_id not in (None, ''):
            record['tool_id'] = tool_id
        return record

    def copy_attachment(self, source_path: str, tool_id=None, tool_name: str = '') -> dict:
        source = Path(source_path or '')
        if not source.exists() or not source.is_file():
            return {}

        attachment_dir = self.get_attachment_dir(tool_id=tool_id, tool_name=tool_name, create=True)
        base_name = self._sanitize_name(source.stem) or 'attachment'
        suffix = source.suffix
        target = attachment_dir / f"{base_name}{suffix}"

        counter = 1
        while target.exists():
            target = attachment_dir / f"{base_name}_{counter}{suffix}"
            counter += 1

        try:
            shutil.copy2(str(source), str(target))
        except Exception as e:
            logger.warning("复制笔记附件失败 %s -> %s: %s", source, target, e)
            return {}

        return {
            'name': target.name,
            'path': str(target),
            'relative_path': self.get_attachment_relative_path(tool_id=tool_id, tool_name=tool_name, file_name=target.name),
            'suffix': target.suffix.lower(),
            'size': target.stat().st_size if target.exists() else 0,
        }

    def search_notes(self, keyword: str):
        query = (keyword or '').strip().lower()
        if not query:
            return []

        results = []
        for entry in self._build_search_index():
            content = entry.get('content') or ''
            note_key = entry.get('note_key') or ''
            summary = entry.get('summary') or ''
            searchable_text = entry.get('searchable_text') or ''
            if query not in searchable_text:
                continue

            record = dict(entry.get('record') or {})
            record.update({
                'excerpt': self._make_excerpt(content, query),
                'matched_in_title': query in note_key.lower() or query in str(record.get('tool_name', '')).lower(),
                'matched_in_summary': query in summary.lower(),
                'matched_in_content': query in content.lower(),
                'query': keyword,
            })
            results.append(record)

        return results

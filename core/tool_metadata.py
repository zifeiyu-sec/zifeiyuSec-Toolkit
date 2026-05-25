from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from core.runtime_paths import looks_like_command_name, resolve_accessible_path_value, resolve_configured_path_value


WEB_TOOL_LABEL = "网页"
TERMINAL_TOOL_LABEL = "终端"
DIRECTORY_TOOL_LABEL = "目录"
DOCUMENT_TOOL_LABEL = "文档"
APPLICATION_TOOL_LABEL = "应用"
FILE_TOOL_LABEL = "文件"
OTHER_TOOL_LABEL = "其他"

DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".csv",
    ".json",
    ".yaml",
    ".yml",
}
DISPLAY_DOCUMENT_EXTENSIONS = {
    ".txt",
    ".md",
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
}
TERMINAL_EXTENSIONS = {".bat", ".cmd", ".ps1", ".sh", ".py", ".vbs"}
APPLICATION_EXTENSIONS = {".exe", ".lnk", ".jar", ".app"}
TERMINAL_SOURCE_TYPES = {"命令行", "python", "批处理"}
TERMINAL_SOURCE_TYPE_KEYS = frozenset(item.casefold() for item in TERMINAL_SOURCE_TYPES)


def _text(value) -> str:
    return str(value or "").strip()


def _casefolded_values(values) -> frozenset[str]:
    normalized = set()
    for value in values:
        text = _text(value)
        if text:
            normalized.add(text.casefold())
    return frozenset(normalized)


def _is_web_path(path: str) -> bool:
    return path.startswith(("http://", "https://"))


def _path_looks_like_directory(path: str) -> bool:
    if not path:
        return False
    if path.endswith(("/", "\\")):
        return True
    return not os.path.splitext(os.path.basename(path))[1]


def infer_display_tool_type_label(tool: Mapping | None, base_dir=None) -> str:
    """Infer the type label used by tool cards."""
    tool = tool or {}
    custom_label = _text(tool.get("type_label"))
    if custom_label:
        return custom_label

    path = _text(tool.get("path"))
    if bool(tool.get("is_web_tool", False)) or _is_web_path(path):
        return WEB_TOOL_LABEL
    if not path:
        return OTHER_TOOL_LABEL
    if path.endswith(("/", "\\")):
        return DIRECTORY_TOOL_LABEL

    run_in_terminal = bool(tool.get("run_in_terminal", False))
    ext = os.path.splitext(path)[1].lower()
    if not ext and base_dir is not None:
        try:
            resolved_path = resolve_accessible_path_value(path, base_dir=base_dir)
        except (OSError, ValueError):
            resolved_path = None
        if resolved_path is not None:
            resolved_text = os.fspath(resolved_path)
            if os.path.isdir(resolved_text):
                return DIRECTORY_TOOL_LABEL

            resolved_ext = os.path.splitext(resolved_text)[1].lower()
            if resolved_ext in DISPLAY_DOCUMENT_EXTENSIONS:
                return DOCUMENT_TOOL_LABEL
            if run_in_terminal or resolved_ext in TERMINAL_EXTENSIONS:
                return TERMINAL_TOOL_LABEL
            if resolved_ext in APPLICATION_EXTENSIONS:
                return APPLICATION_TOOL_LABEL

    if ext in DISPLAY_DOCUMENT_EXTENSIONS:
        return DOCUMENT_TOOL_LABEL
    if run_in_terminal or ext in TERMINAL_EXTENSIONS:
        return TERMINAL_TOOL_LABEL
    if ext in APPLICATION_EXTENSIONS:
        return APPLICATION_TOOL_LABEL
    if not ext and looks_like_command_name(path):
        return TERMINAL_TOOL_LABEL
    return FILE_TOOL_LABEL


def infer_import_tool_type_label(
    path,
    source_type="",
    is_web_tool=False,
    terminal_source_types=None,
    document_extensions=None,
) -> str:
    """Infer a persisted type label while importing external tool configs."""
    if is_web_tool:
        return WEB_TOOL_LABEL

    source_type_key = _text(source_type).casefold()
    terminal_source_keys = (
        TERMINAL_SOURCE_TYPE_KEYS
        if terminal_source_types is None
        else _casefolded_values(terminal_source_types)
    )
    if source_type_key in terminal_source_keys:
        return TERMINAL_TOOL_LABEL

    path_text = _text(path)
    if path_text and not os.path.splitext(path_text)[1] and looks_like_command_name(path_text):
        return TERMINAL_TOOL_LABEL

    try:
        path_is_dir = Path(path_text).is_dir()
    except OSError:
        path_is_dir = False
    if path_text and (path_is_dir or _path_looks_like_directory(path_text)):
        return DIRECTORY_TOOL_LABEL

    ext = os.path.splitext(path_text)[1].lower()
    resolved_document_extensions = (
        DOCUMENT_EXTENSIONS
        if document_extensions is None
        else {str(extension).lower() for extension in document_extensions}
    )
    if ext in resolved_document_extensions:
        return DOCUMENT_TOOL_LABEL
    return APPLICATION_TOOL_LABEL


def is_tool_path_available(tool: Mapping | None, base_dir=None) -> bool:
    """Return True when a tool points at a URL, existing local path, or PATH command."""
    tool = tool or {}
    path = _text(tool.get("path"))
    if bool(tool.get("is_web_tool", False)) or _is_web_path(path):
        return bool(path)
    if not path:
        return False

    try:
        resolved = resolve_accessible_path_value(path, base_dir=base_dir)
    except (OSError, ValueError):
        return False
    return bool(resolved is not None and Path(resolved).exists())


def resolve_tool_target_directory(tool: Mapping | None, base_dir=None) -> str | None:
    """Resolve the directory used by card actions such as open terminal/open folder."""
    tool = tool or {}
    if bool(tool.get("is_web_tool", False)):
        return None

    working_dir = _text(tool.get("working_directory"))
    if working_dir:
        try:
            resolved_working_dir = resolve_configured_path_value(
                working_dir,
                base_dir=base_dir,
                allow_command_name=False,
            )
        except (OSError, ValueError):
            resolved_working_dir = None
        if resolved_working_dir is not None:
            return os.fspath(resolved_working_dir)

    tool_path = _text(tool.get("path"))
    if not tool_path or _is_web_path(tool_path):
        return None

    try:
        resolved_path = resolve_accessible_path_value(tool_path, base_dir=base_dir)
    except (OSError, ValueError):
        resolved_path = None
    if resolved_path is None:
        try:
            resolved_path = resolve_configured_path_value(
                tool_path,
                base_dir=base_dir,
                allow_command_name=True,
            )
        except (OSError, ValueError):
            resolved_path = None
    if resolved_path is None:
        return None

    resolved_text = os.fspath(resolved_path)
    if os.path.isdir(resolved_text):
        return resolved_text
    if os.path.splitext(resolved_text)[1]:
        return os.path.dirname(resolved_text)
    return resolved_text

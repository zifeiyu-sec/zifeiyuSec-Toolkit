#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_FILE_PATTERNS = (
    "README.md",
    "main.py",
    ".gitignore",
    "settings.example.ini",
    "core/**/*.py",
    "ui/**/*.py",
    "scripts/**/*.py",
    "docs/**/*.md",
    "data/**/*.json",
)
WINDOWS_ABS_PATH_RE = re.compile(r"(?<![\w/])(?:[A-Za-z]:[\\/][^\s`\"'<>|]+)")
POSIX_USER_PATH_RE = re.compile(r"(?<![\w])/(?:Users|home)/[^\s`\"'<>|]+")
MOJIBAKE_MARKERS = (
    "\u6fee\u6fd3",
    "\u93af",
    "\u7f03\u6220",
    "\u5a34\u5b2c",
    "\u9426",
    "\u9862",
    "\u7023",
)


def configure_console_encoding():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def iter_text_files():
    seen = set()
    for pattern in TEXT_FILE_PATTERNS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def format_tool_label(tool):
    tool_id = tool.get("id", "?") if isinstance(tool, dict) else "?"
    tool_name = str(tool.get("name", "") or "").strip() if isinstance(tool, dict) else ""
    return f"{tool_id}:{tool_name or '<unnamed>'}"


def check_tool_runtime_state(errors, tools, source_label):
    if not isinstance(tools, list):
        return

    dirty_tools = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue

        try:
            usage_count = int(tool.get("usage_count") or 0)
        except (TypeError, ValueError):
            usage_count = 1

        has_runtime_state = (
            bool(tool.get("is_favorite"))
            or usage_count != 0
            or bool(tool.get("last_used"))
        )
        if has_runtime_state:
            dirty_tools.append(format_tool_label(tool))

    if dirty_tools:
        preview = ", ".join(dirty_tools[:10])
        if len(dirty_tools) > 10:
            preview += f", ... 共 {len(dirty_tools)} 个"
        errors.append(
            f"{source_label} 包含运行时状态（收藏/使用次数/最近使用时间）: {preview}"
        )


def check_shipped_tool_data(errors):
    tools_path = ROOT / "data" / "tools.json"
    if not tools_path.exists():
        errors.append(f"缺少默认工具数据文件: {tools_path}")
        return

    payload = load_json(tools_path)
    if isinstance(payload, dict):
        tools = payload.get("tools")
    elif isinstance(payload, list):
        tools = payload
    else:
        errors.append(f"默认工具数据格式无效: {tools_path}")
        return

    if not isinstance(tools, list):
        errors.append(f"默认工具数据格式无效: {tools_path}")
        return

    check_tool_runtime_state(errors, tools, "默认工具数据")

    split_dir = ROOT / "data" / "tools"
    for split_file in sorted(path for path in split_dir.glob("*.json") if path.is_file()):
        split_payload = load_json(split_file)
        if isinstance(split_payload, dict):
            split_tools = split_payload.get("tools")
        elif isinstance(split_payload, list):
            split_tools = split_payload
        else:
            errors.append(f"拆分工具数据格式无效: {split_file}")
            continue

        if not isinstance(split_tools, list):
            errors.append(f"拆分工具数据格式无效: {split_file}")
            continue

        check_tool_runtime_state(
            errors,
            split_tools,
            f"拆分工具数据 {split_file.relative_to(ROOT)}",
        )


def check_default_notes(errors):
    notes_dir = ROOT / "resources" / "notes"
    note_files = sorted(path for path in notes_dir.glob("*.md") if path.is_file())
    if note_files:
        errors.append(
            "默认仓库仍包含用户笔记: "
            + ", ".join(str(path.relative_to(ROOT)) for path in note_files)
        )


def check_required_templates(errors):
    example_settings = ROOT / "settings.example.ini"
    if not example_settings.exists():
        errors.append(f"缺少示例配置文件: {example_settings}")


def check_release_files(errors):
    required_files = (
        "ZifeiyuSec.spec",
        "scripts/build_release.ps1",
        "requirements.txt",
        "README.md",
        "LICENSE",
        "settings.example.ini",
        "image.ico",
        "favicon.ico",
    )
    required_dirs = (
        "data",
        "docs",
        "images",
        "resources",
    )

    for relative_path in required_files:
        path = ROOT / relative_path
        if not path.is_file():
            errors.append(f"缺少交付文件: {relative_path}")

    for relative_path in required_dirs:
        path = ROOT / relative_path
        if not path.is_dir():
            errors.append(f"缺少交付目录: {relative_path}")

    gitignore = ROOT / ".gitignore"
    if gitignore.exists():
        text = gitignore.read_text(encoding="utf-8", errors="ignore")
        if "*.spec" in text and "!ZifeiyuSec.spec" not in text:
            errors.append("ZifeiyuSec.spec 被 .gitignore 忽略，克隆仓库后可能缺少 PyInstaller 打包配置。")


def check_absolute_paths(errors):
    for path in iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")

        for lineno, line in enumerate(text.splitlines(), start=1):
            matches = []
            matches.extend(match.group(0) for match in WINDOWS_ABS_PATH_RE.finditer(line))
            matches.extend(match.group(0) for match in POSIX_USER_PATH_RE.finditer(line))
            if not matches:
                continue

            filtered = []
            for match in matches:
                if match.startswith(("http://", "https://")):
                    continue
                filtered.append(match)

            if filtered:
                errors.append(
                    f"检测到绝对路径残留: {path.relative_to(ROOT)}:{lineno} -> {', '.join(filtered)}"
                )


def check_text_encoding_artifacts(errors):
    for path in iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")

        for lineno, line in enumerate(text.splitlines(), start=1):
            if any(marker in line for marker in MOJIBAKE_MARKERS):
                errors.append(f"检测到疑似乱码残留: {path.relative_to(ROOT)}:{lineno}")


def main():
    configure_console_encoding()

    errors = []

    check_shipped_tool_data(errors)
    check_default_notes(errors)
    check_required_templates(errors)
    check_release_files(errors)
    check_absolute_paths(errors)
    check_text_encoding_artifacts(errors)

    if errors:
        print("仓库体检未通过：")
        for item in errors:
            print(f"- {item}")
        return 1

    print("仓库体检通过：已校验预置工具库格式、交付文件、默认用户笔记和绝对路径残留。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

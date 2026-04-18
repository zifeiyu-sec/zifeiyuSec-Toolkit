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


def main():
    errors = []

    check_shipped_tool_data(errors)
    check_default_notes(errors)
    check_required_templates(errors)
    check_absolute_paths(errors)

    if errors:
        print("仓库体检未通过：")
        for item in errors:
            print(f"- {item}")
        return 1

    print("仓库体检通过：已校验预置工具库格式，且未发现默认用户笔记或绝对路径残留。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

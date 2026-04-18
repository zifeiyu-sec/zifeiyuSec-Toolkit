#!/usr/bin/env python3
"""
Create a Windows shortcut that launches this project via Python.

Usage:
    python scripts/create_desktop_shortcut.py

By default the shortcut is created on the current user's Desktop and points to
the preferred Python launcher plus ``main.py``. Launcher preference:

1. ``--python`` when provided
2. ``.venv\\Scripts\\pythonw.exe``
3. ``.venv\\Scripts\\python.exe``
4. current interpreter's ``pythonw.exe``
5. current interpreter's ``python.exe``
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _get_windows_desktop_directory():
    if os.name != "nt":
        return ""

    try:
        import ctypes

        CSIDL_DESKTOPDIRECTORY = 0x10
        SHGFP_TYPE_CURRENT = 0
        buffer = ctypes.create_unicode_buffer(260)
        result = ctypes.windll.shell32.SHGetFolderPathW(
            None,
            CSIDL_DESKTOPDIRECTORY,
            None,
            SHGFP_TYPE_CURRENT,
            buffer,
        )
        if result == 0:
            return buffer.value
    except Exception:
        return ""

    return ""


def get_desktop_path():
    candidates = [
        _get_windows_desktop_directory(),
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
        os.path.expanduser("~/Desktop"),
    ]
    for candidate in candidates:
        if candidate and os.path.isdir(candidate):
            return candidate
    return candidates[-1]


def resolve_python_launcher(repo_root: Path, explicit_python: str = "") -> Path:
    candidates = []

    if explicit_python:
        candidates.append(Path(explicit_python).expanduser())
    else:
        venv_scripts = repo_root / ".venv" / "Scripts"
        candidates.extend([
            venv_scripts / "pythonw.exe",
            venv_scripts / "python.exe",
        ])

        current_python = Path(sys.executable).resolve()
        if current_python.name.lower() == "python.exe":
            candidates.append(current_python.with_name("pythonw.exe"))
        candidates.append(current_python)

    seen = set()
    for candidate in candidates:
        resolved = candidate if candidate.is_absolute() else (repo_root / candidate).resolve()
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.exists() and resolved.is_file():
            return resolved

    raise FileNotFoundError("No usable Python launcher was found.")


def create_shortcut_win32(shortcut_path, target, args, workdir, icon):
    try:
        import win32com.client
    except Exception:
        return False

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortcut(str(shortcut_path))
    shortcut.TargetPath = str(target)
    if args:
        shortcut.Arguments = args
    if workdir:
        shortcut.WorkingDirectory = str(workdir)
    if icon and Path(icon).exists():
        shortcut.IconLocation = str(icon)
    shortcut.save()
    return True


def create_shortcut_powershell(shortcut_path, target, args, workdir, icon):
    def ps_quote(value: str):
        return "'" + value.replace("'", "''") + "'"

    cmd = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut("
        + ps_quote(str(shortcut_path))
        + ");"
        + "$s.TargetPath="
        + ps_quote(str(target))
        + ";"
    )
    if args:
        cmd += "$s.Arguments=" + ps_quote(args) + ";"
    if workdir:
        cmd += "$s.WorkingDirectory=" + ps_quote(str(workdir)) + ";"
    if icon and Path(icon).exists():
        cmd += "$s.IconLocation=" + ps_quote(str(icon)) + ";"
    cmd += "$s.Save();"

    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def build_shortcut_arguments(main_py: Path) -> str:
    return subprocess.list2cmdline([str(main_py)])


def resolve_icon(repo_root: Path):
    for name in ("image.ico", "favicon.ico", "image.png"):
        candidate = repo_root / name
        if candidate.exists():
            return candidate
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", "-n", default="子非鱼安全工具箱", help="Shortcut name")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root (default: inferred)",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Shortcut output directory (default: current user's Desktop)",
    )
    parser.add_argument("--python", default="", help="Explicit Python / Pythonw executable to use")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else Path(get_desktop_path())
    if not output_dir.exists():
        print("Shortcut output path not found:", output_dir)
        sys.exit(1)

    main_py = repo_root / "main.py"
    if not main_py.exists():
        print("main.py not found:", main_py)
        sys.exit(1)

    try:
        target = resolve_python_launcher(repo_root, args.python)
    except FileNotFoundError as exc:
        print(str(exc))
        sys.exit(1)

    shortcut_name = args.name.strip() + ".lnk"
    shortcut_path = output_dir / shortcut_name
    run_args = build_shortcut_arguments(main_py)
    workdir = str(repo_root)
    icon = resolve_icon(repo_root)

    created = create_shortcut_win32(shortcut_path, target, run_args, workdir, icon)
    if not created:
        created = create_shortcut_powershell(shortcut_path, target, run_args, workdir, icon)

    if created:
        print(f"Shortcut created: {shortcut_path}")
        sys.exit(0)

    print("Failed to create shortcut. Ensure PowerShell COM automation is available.")
    sys.exit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Create a Windows desktop shortcut for this application.

Usage:
    python scripts/create_desktop_shortcut.py [--name "子非鱼工具箱"]

The script will by default create a shortcut on the current user's Desktop that
points to `run_tool.vbs` (included in repository) so the app launches without a
console window. If `image.png` exists in the repository root it will be used as
the shortcut icon.

The script tries to use `win32com.client` when available, otherwise it falls
back to invoking PowerShell to create the .lnk file via COM.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path


def get_desktop_path():
    # First try the known USERPROFILE Desktop location
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
    if desktop and os.path.isdir(desktop):
        return desktop
    # Fallback to expanduser
    desktop = os.path.expanduser("~/Desktop")
    return desktop


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
    # Build PowerShell command to create shortcut via WScript.Shell COM object
    def ps_quote(p: str):
        # Use single quotes in PowerShell, escape single quotes by doubling
        return "'" + p.replace("'", "''") + "'"

    cmd = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + ps_quote(str(shortcut_path)) + ");"
        "$s.TargetPath=" + ps_quote(str(target)) + ";"
    )
    if args:
        cmd += "$s.Arguments=" + ps_quote(args) + ";"
    if workdir:
        cmd += "$s.WorkingDirectory=" + ps_quote(str(workdir)) + ";"
    if icon and Path(icon).exists():
        cmd += "$s.IconLocation=" + ps_quote(str(icon)) + ";"
    cmd += "$s.Save();"

    # Execute PowerShell command
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", "-n", default="子非鱼工具箱", help="Shortcut name")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]),
                        help="Repository root (default: inferred)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    desktop = Path(get_desktop_path())
    if not desktop.exists():
        print("Desktop path not found:", desktop)
        sys.exit(1)

    shortcut_name = args.name.strip() + ".lnk"
    shortcut_path = desktop / shortcut_name

    # Prefer run_tool.vbs (hides console). Fall back to run_tool.bat if missing.
    vbs = repo_root / "run_tool.vbs"
    bat = repo_root / "run_tool.bat"
    if vbs.exists():
        target = vbs
    elif bat.exists():
        target = bat
    else:
        # As last resort, point to pythonw running main.py in repo root
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        main_py = repo_root / "main.py"
        if Path(pythonw).exists() and main_py.exists():
            target = pythonw
            # We'll pass main.py as argument
            run_args = str(main_py)
        else:
            print("No suitable target found (no run_tool.vbs/run_tool.bat and pythonw missing).")
            sys.exit(1)

    run_args = ''
    workdir = str(repo_root)
    # Choose icon: prefer image.ico in repo root, else resources icon if exists
    icon = repo_root / "image.ico"
    if not icon.exists():
        svg_icon = repo_root / "resources" / "icons" / "new_default_icon.ico"
        icon = svg_icon if svg_icon.exists() else None

    # If target is pythonw with main.py passed as argument
    if isinstance(target, Path) and target.name.lower().startswith('python') and target.suffix.lower() in ('.exe',):
        # set target to pythonw and args to main.py
        run_args = str(repo_root / 'main.py')
    elif isinstance(target, Path) and target.suffix.lower() == '.vbs':
        # For vbs, target can be the vbs file itself
        run_args = ''
    elif isinstance(target, Path) and target.suffix.lower() == '.bat':
        run_args = ''

    # Create shortcut using win32com if available, otherwise PowerShell
    created = create_shortcut_win32(shortcut_path, target, run_args, workdir, icon)
    if not created:
        created = create_shortcut_powershell(shortcut_path, target, run_args, workdir, icon)

    if created:
        print(f"Shortcut created: {shortcut_path}")
        sys.exit(0)
    else:
        print("Failed to create shortcut. Try running with administrator privileges or ensure PowerShell is available.")
        sys.exit(2)


if __name__ == '__main__':
    main()

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class UpdateWorkerError(RuntimeError):
    """Raised when updater worker cannot complete an update session."""


@dataclass
class UpdateSession:
    session_path: Path
    app_root: Path
    zip_path: Path
    staging_dir: Path
    backup_dir: Path
    log_file: Path
    parent_pid: int
    preserve_paths: list[str]
    restart_cmd: list[str]
    restart_cwd: Path

    @classmethod
    def from_file(cls, session_path: Path) -> "UpdateSession":
        with session_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            raise UpdateWorkerError("更新会话文件格式错误。")

        session_dir = session_path.parent
        app_root = _resolve_path(payload.get("app_root"), session_dir)
        zip_path = _resolve_path(payload.get("zip_path"), session_dir)
        if not app_root:
            raise UpdateWorkerError("更新会话缺少 app_root。")
        if not zip_path:
            raise UpdateWorkerError("更新会话缺少 zip_path。")

        staging_dir = _resolve_path(payload.get("staging_dir"), session_dir) or session_dir / "staging"
        backup_dir = _resolve_path(payload.get("backup_dir"), session_dir) or session_dir / "backup"
        log_file = _resolve_path(payload.get("log_file"), session_dir) or session_dir / "update_worker.log"

        restart_cmd = _parse_restart_cmd(payload.get("restart_cmd"))
        if not restart_cmd:
            restart_cmd = [str(app_root / Path(sys.executable).name)]

        restart_cwd = _resolve_path(payload.get("restart_cwd"), session_dir) or app_root

        parent_pid = _parse_pid(payload.get("parent_pid"))
        preserve_paths = _parse_preserve_paths(payload.get("preserve_paths"))

        return cls(
            session_path=session_path,
            app_root=app_root,
            zip_path=zip_path,
            staging_dir=staging_dir,
            backup_dir=backup_dir,
            log_file=log_file,
            parent_pid=parent_pid,
            preserve_paths=preserve_paths,
            restart_cmd=restart_cmd,
            restart_cwd=restart_cwd,
        )


def _resolve_path(value: Any, base_dir: Path) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _parse_restart_cmd(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value]
        return [item for item in items if item]
    text = str(value or "").strip()
    return [text] if text else []


def _parse_pid(value: Any) -> int:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return 0
    return pid if pid > 0 else 0


def _normalize_rel(path_like: str) -> str:
    text = str(path_like or "").replace("\\", "/").strip().strip("/")
    while text.startswith("./"):
        text = text[2:]
    return text


def _parse_preserve_paths(value: Any) -> list[str]:
    if not isinstance(value, list):
        return [".runtime"]
    result = []
    for item in value:
        normalized = _normalize_rel(str(item))
        if normalized:
            result.append(normalized)
    return result or [".runtime"]


def _append_log(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}\n"
    with log_file.open("a", encoding="utf-8", errors="replace") as f:
        f.write(line)


def _is_process_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            SYNCHRONIZE = 0x00100000
            access = PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE
            handle = ctypes.windll.kernel32.OpenProcess(access, False, int(pid))
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for_parent_exit(parent_pid: int, log_file: Path, timeout_sec: int = 90) -> None:
    if parent_pid <= 0:
        return

    _append_log(log_file, f"等待主进程退出: pid={parent_pid}")
    deadline = time.time() + max(timeout_sec, 1)
    while time.time() < deadline:
        if not _is_process_running(parent_pid):
            _append_log(log_file, "主进程已退出，继续执行更新。")
            return
        time.sleep(0.3)

    _append_log(log_file, f"等待主进程退出超时({timeout_sec}s)，继续尝试更新。")


def _remove_entry(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=False)
    else:
        path.unlink(missing_ok=True)


def _copy_entry(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _is_preserved(name: str, preserve_paths: list[str]) -> bool:
    target = _normalize_rel(name).casefold()
    if not target:
        return False
    normalized_preserve = [item.casefold() for item in preserve_paths]
    for preserve in normalized_preserve:
        if target == preserve or target.startswith(f"{preserve}/"):
            return True
    return False


def _extract_payload(zip_path: Path, staging_dir: Path, log_file: Path) -> Path:
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    _append_log(log_file, f"解压更新包: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(staging_dir)

    entries = [item for item in staging_dir.iterdir() if item.name != "__MACOSX"]
    if not entries:
        raise UpdateWorkerError("更新包为空，未找到可用文件。")
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return staging_dir


def _rollback(replaced_entries: list[tuple[Path, Path]], created_entries: list[Path], log_file: Path) -> None:
    _append_log(log_file, "更新失败，开始执行回滚。")
    for target in reversed(created_entries):
        try:
            _remove_entry(target)
        except Exception as exc:
            _append_log(log_file, f"回滚删除失败: {target} ({exc})")

    for target, backup in reversed(replaced_entries):
        try:
            if not backup.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                _remove_entry(target)
            shutil.move(str(backup), str(target))
        except Exception as exc:
            _append_log(log_file, f"回滚恢复失败: {target} <- {backup} ({exc})")

    _append_log(log_file, "回滚流程结束。")


def _apply_payload(session: UpdateSession, payload_root: Path) -> None:
    app_root = session.app_root
    backup_root = session.backup_dir
    backup_root.mkdir(parents=True, exist_ok=True)

    replaced_entries: list[tuple[Path, Path]] = []
    created_entries: list[Path] = []

    entries = sorted(payload_root.iterdir(), key=lambda item: item.name.casefold())
    if not entries:
        raise UpdateWorkerError("更新包没有可部署文件。")

    try:
        incoming_names = {item.name for item in entries}
        existing_entries = sorted(app_root.iterdir(), key=lambda item: item.name.casefold())
        for existing in existing_entries:
            relative_name = existing.name
            if _is_preserved(relative_name, session.preserve_paths):
                continue
            if relative_name in incoming_names:
                continue

            backup_target = backup_root / relative_name
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            if backup_target.exists() or backup_target.is_symlink():
                _remove_entry(backup_target)
            shutil.move(str(existing), str(backup_target))
            replaced_entries.append((existing, backup_target))
            _append_log(session.log_file, f"已清理旧文件: {relative_name}")

        for src in entries:
            relative_name = src.name
            if _is_preserved(relative_name, session.preserve_paths):
                _append_log(session.log_file, f"保留目录跳过覆盖: {relative_name}")
                continue

            target = app_root / relative_name
            backup_target = backup_root / relative_name

            if target.exists() or target.is_symlink():
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                if backup_target.exists() or backup_target.is_symlink():
                    _remove_entry(backup_target)
                shutil.move(str(target), str(backup_target))
                replaced_entries.append((target, backup_target))

            _copy_entry(src, target)
            created_entries.append(target)
            _append_log(session.log_file, f"已更新: {relative_name}")
    except Exception:
        _rollback(replaced_entries, created_entries, session.log_file)
        raise


def _restart_app(session: UpdateSession) -> None:
    creationflags = 0
    if os.name == "nt":
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    subprocess.Popen(
        session.restart_cmd,
        cwd=str(session.restart_cwd),
        close_fds=True,
        creationflags=creationflags,
    )
    _append_log(session.log_file, f"已重启主程序: {' '.join(session.restart_cmd)}")


def run_updater_session(session_path: str | Path) -> int:
    session_path = Path(session_path).resolve()
    try:
        session = UpdateSession.from_file(session_path)
    except Exception as exc:
        fallback_log = session_path.parent / "update_worker.log"
        _append_log(fallback_log, f"加载更新会话失败: {exc}")
        return 2

    try:
        _append_log(session.log_file, f"开始执行更新，会话文件: {session.session_path}")
        if not session.zip_path.exists():
            raise UpdateWorkerError(f"更新包不存在: {session.zip_path}")
        if not session.app_root.exists():
            raise UpdateWorkerError(f"应用目录不存在: {session.app_root}")

        _wait_for_parent_exit(session.parent_pid, session.log_file)
        payload_root = _extract_payload(session.zip_path, session.staging_dir, session.log_file)
        _append_log(session.log_file, f"更新内容根目录: {payload_root}")
        _apply_payload(session, payload_root)

        try:
            if session.staging_dir.exists():
                shutil.rmtree(session.staging_dir, ignore_errors=True)
        except Exception as exc:
            _append_log(session.log_file, f"清理 staging 失败: {exc}")

        _restart_app(session)
        _append_log(session.log_file, "更新流程完成。")
        return 0
    except Exception as exc:
        _append_log(session.log_file, f"更新流程失败: {exc}")
        return 1


def run_updater_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--run-updater", action="store_true")
    parser.add_argument("--session", default="")
    args, _ = parser.parse_known_args(argv)

    if not args.run_updater:
        return 2
    session_text = str(args.session or "").strip()
    if not session_text:
        return 2
    return run_updater_session(session_text)


if __name__ == "__main__":
    sys.exit(run_updater_cli(sys.argv[1:]))

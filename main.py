#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Application entrypoint."""

from __future__ import annotations

import os
import signal
import sys
from typing import Sequence

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QApplication

from core.app import PentestToolManager
from core.logger import logger
from core.runtime_paths import (
    bootstrap_runtime_layout,
    get_runtime_state_root,
    resolve_icon_path_value,
    resolve_preferred_path,
)


def setup_fonts() -> QFont:
    font = QFont()
    font.setFamily("Microsoft YaHei")
    return font


def setup_console_encoding() -> None:
    stdout = getattr(sys, "stdout", None)
    stderr = getattr(sys, "stderr", None)

    for stream in (stdout, stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass

    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except (ImportError, AttributeError, OSError):
            pass


def get_runtime_config_dir() -> str:
    return os.fspath(get_runtime_state_root())


def maybe_run_updater_mode(argv: Sequence[str]) -> int | None:
    if "--run-updater" not in argv:
        return None

    from core.update_worker import run_updater_cli

    return run_updater_cli(list(argv))


def main() -> int:
    setup_console_encoding()

    updater_exit_code = maybe_run_updater_mode(sys.argv[1:])
    if updater_exit_code is not None:
        return updater_exit_code

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(setup_fonts())

    config_dir = get_runtime_config_dir()
    bootstrap_runtime_layout()
    os.makedirs(os.path.join(config_dir, "images"), exist_ok=True)

    window = PentestToolManager(config_dir=config_dir)

    # Allow overriding app icon with .runtime/image.ico first, then image.png.
    for icon_name in ("image.ico", "image.png"):
        icon_path = resolve_preferred_path(icon_name)
        if not icon_path.exists():
            continue
        icon = QIcon(os.fspath(icon_path))
        if icon.isNull():
            continue
        QApplication.setWindowIcon(icon)
        window.setWindowIcon(icon)
        break
    else:
        for fallback_name in ("write-github.svg", "github_1_1_1.svg"):
            icon_path = resolve_icon_path_value(fallback_name)
            if icon_path is None:
                continue
            icon = QIcon(os.fspath(icon_path))
            if icon.isNull():
                continue
            QApplication.setWindowIcon(icon)
            window.setWindowIcon(icon)
            break

    def signal_handler(received_signal, frame):
        del received_signal, frame
        logger.info("Exit signal received, closing window.")
        try:
            window.close()
        except Exception as exc:
            logger.exception("Cleanup failed: %s", exc)
        finally:
            app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

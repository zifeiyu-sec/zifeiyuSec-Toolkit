import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from core.runtime_paths import ensure_runtime_dir


def get_log_directory(log_dir=None):
    if log_dir:
        path = Path(log_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    return Path(ensure_runtime_dir("logs"))


def get_current_log_file_path(log_dir=None, at=None):
    log_root = get_log_directory(log_dir)
    moment = at or datetime.now()
    return log_root / f"zifeiyuSec_{moment.strftime('%Y%m%d')}.log"


def list_log_files(log_dir=None):
    log_root = get_log_directory(log_dir)
    if not log_root.exists():
        return []

    return sorted(
        (path for path in log_root.glob("zifeiyuSec_*.log") if path.is_file()),
        key=lambda path: (
            path.stat().st_mtime if path.exists() else 0,
            path.name,
        ),
        reverse=True,
    )


def get_latest_log_file_path(log_dir=None):
    files = list_log_files(log_dir)
    if files:
        return files[0]
    return get_current_log_file_path(log_dir)


class Logger:
    """日志管理类"""

    def __init__(self, log_dir=None):
        """初始化日志配置"""
        log_filename = os.fspath(get_current_log_file_path(log_dir))
        console_stream = self._get_console_stream()

        self.logger = logging.getLogger("zifeiyuSec")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        if self.logger.handlers:
            return

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        stream_handler = logging.StreamHandler(console_stream)
        stream_handler.setFormatter(formatter)

        file_handler = self._build_file_handler(log_filename, formatter)
        if file_handler is not None:
            self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def _get_console_stream(self):
        """返回支持 UTF-8 输出的控制台流。"""
        stream = sys.stdout
        if hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
        return stream

    def _build_file_handler(self, log_filename, formatter):
        candidate_paths = [log_filename]
        base_name, ext = os.path.splitext(log_filename)
        candidate_paths.append(f"{base_name}_{os.getpid()}{ext}")

        for candidate in candidate_paths:
            try:
                file_handler = logging.FileHandler(candidate, encoding='utf-8')
                file_handler.setFormatter(formatter)
                return file_handler
            except OSError:
                continue

        return None

    def get_logger(self):
        """获取日志记录器"""
        return self.logger


# 创建全局日志记录器实例
global_logger = Logger()
logger = global_logger.get_logger()

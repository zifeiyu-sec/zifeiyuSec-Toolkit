import logging
import os
import sys
from datetime import datetime
from core.runtime_paths import ensure_runtime_dir


class Logger:
    """日志管理类"""

    def __init__(self, log_dir=None):
        """初始化日志配置"""
        log_dir = os.path.abspath(log_dir) if log_dir else os.fspath(ensure_runtime_dir("logs"))
        os.makedirs(log_dir, exist_ok=True)
        log_filename = os.path.join(log_dir, f"zifeiyuSec_{datetime.now().strftime('%Y%m%d')}.log")
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

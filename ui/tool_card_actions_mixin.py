import os
import subprocess
import sys

from PyQt5.QtWidgets import QMessageBox
from core.tool_launch_service import ToolLaunchService
from core.runtime_paths import get_runtime_state_root, resolve_configured_path_value
from core.tool_metadata import resolve_tool_target_directory


class ToolCardActionsMixin:
    """ToolCardContainer 的本地终端/目录打开动作。"""

    def _get_tool_launch_service(self):
        window = self.window()
        service = getattr(window, "tool_launcher", None)
        if service is not None:
            return service

        service = getattr(self, "_tool_launch_service", None)
        if service is None:
            service = ToolLaunchService()
            self._tool_launch_service = service
        return service

    def resolve_tool_target_dir(self, tool):
        base_dir = getattr(self.window(), "config_dir", None) or os.fspath(get_runtime_state_root())
        return resolve_tool_target_directory(tool, base_dir=base_dir)

    def open_command_line(self, directory=None, tool_data=None):
        """在此处打开命令行"""
        base_dir = getattr(self.window(), "config_dir", None) or os.fspath(get_runtime_state_root())
        if not directory and tool_data is not None:
            directory = self.resolve_tool_target_dir(tool_data)

        if not directory:
            QMessageBox.warning(self, "错误", "未找到可用的工作目录")
            return

        resolved_directory = resolve_configured_path_value(directory, base_dir=base_dir, allow_command_name=False)
        if resolved_directory is not None:
            directory = os.fspath(resolved_directory)
        else:
            directory = str(directory or "").strip()

        if not os.path.exists(directory):
            QMessageBox.warning(self, "错误", f"目录不存在:\n{directory}")
            return

        try:
            self._get_tool_launch_service().open_terminal(working_dir=directory, base_dir=base_dir)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开命令行失败: {str(e)}")

    def warn_missing_tool_target_dir(self, tool_data=None):
        """提示当前工具没有可用的目录上下文。"""
        tool_name = ""
        if isinstance(tool_data, dict):
            tool_name = str(tool_data.get("name", "") or "").strip()
        if not tool_name:
            tool_name = "当前工具"
        QMessageBox.warning(self, "无法打开目录", f"{tool_name} 没有可用的工作目录或工具路径。")

    def open_directory(self, directory):
        """在此处打开目录"""
        base_dir = getattr(self.window(), "config_dir", None) or os.fspath(get_runtime_state_root())
        resolved_directory = resolve_configured_path_value(directory, base_dir=base_dir, allow_command_name=False)
        if resolved_directory is not None:
            directory = os.fspath(resolved_directory)
        else:
            directory = str(directory or "").strip()

        if not os.path.exists(directory):
            QMessageBox.warning(self, "错误", f"目录不存在:\n{directory}")
            return

        try:
            if sys.platform.startswith('win'):
                os.startfile(directory)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', directory])
            else:
                subprocess.Popen(['xdg-open', directory])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开目录失败: {str(e)}")

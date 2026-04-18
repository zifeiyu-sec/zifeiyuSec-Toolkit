import os
import subprocess
import sys

from PyQt5.QtWidgets import QMessageBox
from core.tool_launch_service import ToolLaunchService


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
        if not tool or tool.get("is_web_tool", False):
            return None

        working_dir = str(tool.get("working_directory", "") or "").strip()
        if working_dir:
            return working_dir

        tool_path = str(tool.get("path", "") or "").strip()
        if not tool_path or tool_path.startswith(("http://", "https://")):
            return None

        return os.path.dirname(tool_path) if os.path.splitext(tool_path)[1] else tool_path

    def open_command_line(self, directory=None, tool_data=None):
        """在此处打开命令行"""
        if not directory and tool_data is not None:
            directory = self.resolve_tool_target_dir(tool_data)

        if not directory:
            QMessageBox.warning(self, "错误", "未找到可用的工作目录")
            return

        if not os.path.isabs(directory):
            directory = os.path.abspath(directory)

        if not os.path.exists(directory):
            QMessageBox.warning(self, "错误", f"目录不存在:\n{directory}")
            return

        try:
            self._get_tool_launch_service().open_terminal(working_dir=directory)
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
        if not os.path.isabs(directory):
            directory = os.path.abspath(directory)

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

from __future__ import annotations

import os

from PyQt5.QtWidgets import QMessageBox

from core.logger import logger
from core.runtime_backup import RuntimeBackupService


class ImportController:
    def __init__(self, window):
        self.window = window

    @property
    def exchange(self):
        return self.window.tool_config_exchange

    def import_tianhu_tools(self, source_path):
        return self.exchange.import_tianhu_tools(source_path)

    def remove_tianhu_tools(self):
        return self.exchange.remove_tianhu_tools()

    def import_native_tools(self, file_path):
        return self.exchange.import_native_tools(file_path)

    def export_native_tools(self, file_path):
        return self.exchange.export_native_tools(file_path)

    def sync_official_tools(self, sync_url, update_existing=True, cancel_requested=None, progress_callback=None):
        return self.exchange.sync_official_tools_from_url(
            sync_url,
            update_existing=update_existing,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )


class RuntimeBackupController:
    def __init__(self, window):
        self.window = window

    def service(self):
        return RuntimeBackupService(self.window.config_dir)

    def get_default_backup_path(self):
        return self.service().get_default_backup_path()

    def create_backup(self, file_path):
        return self.service().create_backup(file_path)

    def restore_backup(self, file_path):
        return self.service().restore_backup(file_path)


class UpdateController:
    def __init__(self, window):
        self.window = window

    def check_for_updates(self, cancel_requested=None, progress_callback=None):
        return self.window.update_service.check_for_updates(
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )

    def can_self_update(self):
        return self.window.update_service.can_self_update()

    def get_release_page_url(self):
        return self.window.update_service.get_release_page_url()

    def get_update_mode(self):
        return self.window.update_service.get_update_mode()

    def start_one_click_update(self, update_info, cancel_requested=None, progress_callback=None):
        return self.window.update_service.start_one_click_update(
            update_info,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )


class ToolRunController:
    def __init__(self, window):
        self.window = window

    def launch_tool(self, tool_data):
        tool_data = tool_data or {}
        path = (tool_data.get("path") or "").strip()
        return self.window.tool_launcher.launch_tool(
            tool_data=tool_data,
            path=path,
            working_dir=tool_data.get("working_directory", ""),
            run_in_terminal=tool_data.get("run_in_terminal", False),
            base_dir=self.window.config_dir,
        )

    def record_usage(self, tool_id):
        if not tool_id:
            return False
        self.window.data_manager.update_tool_usage(tool_id)
        self.window._schedule_usage_flush()
        return True


class NavigationSearchController:
    def __init__(self, window):
        self.window = window

    def prewarm_search_index(self, tools):
        build_index = getattr(self.window, "_build_tool_search_index", None)
        if callable(build_index):
            build_index(tools)

    def invalidate_search_index(self):
        invalidate = getattr(self.window, "invalidate_search_index", None)
        if callable(invalidate):
            invalidate()

    def show_missing_tool_message(self, tool_id):
        QMessageBox.warning(self.window, "定位失败", f"未找到 ID 为 {tool_id} 的工具。")

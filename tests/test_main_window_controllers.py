import unittest
from unittest.mock import Mock

from _support import cleanup_test_dir, make_test_dir
from ui.main_window_controllers import (
    ImportController,
    NavigationSearchController,
    RuntimeBackupController,
    ToolRunController,
    UpdateController,
)


class MainWindowControllerTests(unittest.TestCase):
    def test_import_controller_delegates_to_exchange(self):
        window = Mock()
        window.tool_config_exchange.import_native_tools.return_value = {"imported": 1}

        result = ImportController(window).import_native_tools("tools.json")

        self.assertEqual({"imported": 1}, result)
        window.tool_config_exchange.import_native_tools.assert_called_once_with("tools.json")

    def test_tool_run_controller_launches_and_records_usage(self):
        window = Mock()
        window.config_dir = "C:/runtime"
        window.tool_launcher.launch_tool.return_value = {"success": True}
        tool = {
            "id": 3,
            "path": "tools/demo.exe",
            "working_directory": "tools",
            "run_in_terminal": True,
        }
        controller = ToolRunController(window)

        result = controller.launch_tool(tool)
        recorded = controller.record_usage(3)

        self.assertTrue(result["success"])
        window.tool_launcher.launch_tool.assert_called_once_with(
            tool_data=tool,
            path="tools/demo.exe",
            working_dir="tools",
            run_in_terminal=True,
            base_dir="C:/runtime",
        )
        self.assertTrue(recorded)
        window.data_manager.update_tool_usage.assert_called_once_with(3)
        window._schedule_usage_flush.assert_called_once()

    def test_update_controller_delegates_to_lazy_update_service(self):
        window = Mock()
        window.update_service.can_self_update.return_value = True

        controller = UpdateController(window)

        self.assertTrue(controller.can_self_update())
        window.update_service.can_self_update.assert_called_once()

    def test_navigation_search_controller_uses_optional_hooks(self):
        window = Mock()
        controller = NavigationSearchController(window)

        controller.prewarm_search_index([{"id": 1}])
        controller.invalidate_search_index()

        window._build_tool_search_index.assert_called_once_with([{"id": 1}])
        window.invalidate_search_index.assert_called_once()

    def test_runtime_backup_controller_creates_service(self):
        config_dir = make_test_dir(f"controller_backup_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(config_dir))
        window = Mock()
        window.config_dir = str(config_dir)
        controller = RuntimeBackupController(window)

        service = controller.service()

        self.assertEqual(config_dir, service.runtime_root)


if __name__ == "__main__":
    unittest.main()

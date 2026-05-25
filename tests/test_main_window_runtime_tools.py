import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from _support import cleanup_test_dir, make_test_dir
from core.data_manager import DataManager
from ui.main_window import MainWindow


class MainWindowRuntimeToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.config_dir = make_test_dir(f"main_window_runtime_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.config_dir))
        self._seed_data()

        self.load_tools_patcher = patch(
            "ui.main_window.DataManager.load_tools",
            autospec=True,
            side_effect=self._fake_load_tools,
        )
        self.info_patcher = patch("ui.main_window.QMessageBox.information")
        self.warning_patcher = patch("ui.main_window.QMessageBox.warning")
        self.icon_loader_patcher = patch("ui.main_window.icon_loader.shutdown")

        self.load_tools_patcher.start()
        self.info_patcher.start()
        self.warning_patcher.start()
        self.icon_loader_patcher.start()

        self.addCleanup(self.load_tools_patcher.stop)
        self.addCleanup(self.info_patcher.stop)
        self.addCleanup(self.warning_patcher.stop)
        self.addCleanup(self.icon_loader_patcher.stop)

    def _seed_data(self):
        data_manager = DataManager(config_dir=str(self.config_dir))
        categories = data_manager.load_categories()
        self.assertTrue(categories)
        tools = [
            {
                "id": 1,
                "name": "Demo Tool",
                "path": "tools/demo.exe",
                "description": "demo tool",
                "category_id": categories[0]["id"],
                "subcategory_id": None,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
            {
                "id": 2,
                "name": "Second Tool",
                "path": "tools/second.exe",
                "description": "second tool",
                "category_id": categories[0]["id"],
                "subcategory_id": None,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            }
        ]
        self.assertTrue(data_manager.save_tools(tools))
        (self.config_dir / "resources" / "notes").mkdir(parents=True, exist_ok=True)
        (self.config_dir / "resources" / "notes" / "tool_1.md").write_text("# Demo Note\n", encoding="utf-8")
        (self.config_dir / "settings.ini").write_text("[General]\ntheme=blue_white\n", encoding="utf-8")

    def _fake_load_tools(self, data_manager, callback=None):
        tools = data_manager._load_tools_sync()
        if callback is not None:
            callback(tools, None)
        return tools

    def _create_window(self):
        window = MainWindow(config_dir=str(self.config_dir))
        window.show()
        self.app.processEvents()
        self.addCleanup(lambda: window.deleteLater())
        return window

    def test_runtime_actions_exist_and_log_action_opens_current_log(self):
        window = self._create_window()

        self.assertTrue(hasattr(window, "backup_runtime_action"))
        self.assertTrue(hasattr(window, "restore_runtime_action"))
        self.assertTrue(hasattr(window, "view_runtime_log_action"))
        self.assertTrue(hasattr(window, "batch_delete_tools_action"))
        self.assertTrue(hasattr(window, "delete_all_tools_action"))

        log_dir = self.config_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "zifeiyuSec_20260501.log"
        log_file.write_text("demo log", encoding="utf-8")

        with patch("ui.main_window.QDesktopServices.openUrl", return_value=True) as open_mock:
            window.on_show_runtime_log()

        open_mock.assert_called_once()
        self.assertEqual(log_file.resolve(), Path(open_mock.call_args.args[0].toLocalFile()).resolve())

    def test_startup_defers_heavy_optional_services_until_needed(self):
        window = self._create_window()

        self.assertIsNone(window._image_manager)
        self.assertIsNone(window._update_service)
        self.assertIs(window.image_manager, window._image_manager)
        self.assertIs(window.update_service, window._update_service)

    def test_tool_run_passes_runtime_base_dir_to_launcher(self):
        window = self._create_window()

        class FakeLauncher:
            def __init__(self):
                self.kwargs = None

            def launch_tool(self, **kwargs):
                self.kwargs = kwargs
                return {
                    "success": True,
                    "path": kwargs.get("path", ""),
                    "working_directory": "",
                    "command_preview": kwargs.get("path", ""),
                    "launch_mode": "subprocess",
                }

        fake_launcher = FakeLauncher()
        window.tool_launcher = fake_launcher

        tool = {
            "name": "Relative Tool",
            "path": "tools/demo.exe",
            "working_directory": "",
            "run_in_terminal": False,
        }
        window.on_tool_run(tool)

        self.assertIsNotNone(fake_launcher.kwargs)
        self.assertEqual(str(self.config_dir), fake_launcher.kwargs.get("base_dir"))

    def test_backup_and_restore_runtime_config_round_trip(self):
        window = self._create_window()
        backup_path = self.config_dir / "runtime_backup.zip"

        with patch(
            "ui.main_window.QFileDialog.getSaveFileName",
            return_value=(str(backup_path), "Zip Archives (*.zip)"),
        ):
            window.on_backup_runtime_config()

        self.assertTrue(backup_path.exists())

        original_settings = (self.config_dir / "settings.ini").read_text(encoding="utf-8")
        original_tools = (self.config_dir / "data" / "tools.json").read_text(encoding="utf-8")
        original_note = (self.config_dir / "resources" / "notes" / "tool_1.md").read_text(encoding="utf-8")

        (self.config_dir / "settings.ini").write_text("[General]\ntheme=red_orange\n", encoding="utf-8")
        (self.config_dir / "data" / "tools.json").write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "id": 1,
                            "name": "Mutated Tool",
                            "path": "tools/demo.exe",
                            "description": "mutated",
                            "category_id": 1,
                            "subcategory_id": None,
                            "is_favorite": True,
                            "usage_count": 7,
                            "last_used": "2026-05-01T00:00:00Z",
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        stale_file = self.config_dir / "data" / "tools" / "stale.json"
        stale_file.parent.mkdir(parents=True, exist_ok=True)
        stale_file.write_text("stale", encoding="utf-8")
        (self.config_dir / "resources" / "notes" / "tool_1.md").write_text("# Mutated\n", encoding="utf-8")

        with patch(
            "ui.main_window.QFileDialog.getOpenFileName",
            return_value=(str(backup_path), "Zip Archives (*.zip)"),
        ), patch.object(window, "_themed_question", return_value=QMessageBox.Yes):
            window.on_restore_runtime_config()

        self.assertEqual(original_settings, (self.config_dir / "settings.ini").read_text(encoding="utf-8"))
        self.assertEqual(original_tools, (self.config_dir / "data" / "tools.json").read_text(encoding="utf-8"))
        self.assertEqual(original_note, (self.config_dir / "resources" / "notes" / "tool_1.md").read_text(encoding="utf-8"))
        self.assertFalse(stale_file.exists())
        self.assertEqual("blue_white", window.current_theme)
        self.assertEqual(["Demo Tool", "Second Tool"], [tool.get("name") for tool in window.data_manager._load_tools_sync()])

    def test_batch_delete_tools_action_removes_selected_tools(self):
        window = self._create_window()

        class FakeBulkDeleteDialog:
            def __init__(self, *args, **kwargs):
                pass

            def exec_(self):
                return QDialog.Accepted

            def get_selected_tool_ids(self):
                return [1]

        with patch("ui.main_window.ToolBulkDeleteDialog", FakeBulkDeleteDialog), patch.object(
            window,
            "_themed_question",
            return_value=QMessageBox.Yes,
        ):
            window.on_batch_delete_tools()

        self.assertEqual(["Second Tool"], [tool.get("name") for tool in window.data_manager._load_tools_sync()])

    def test_delete_all_tools_action_clears_tools_after_double_confirmation(self):
        window = self._create_window()

        with patch.object(window, "_themed_question", return_value=QMessageBox.Yes):
            window.on_delete_all_tools()

        self.assertEqual([], window.data_manager._load_tools_sync())


if __name__ == "__main__":
    unittest.main()

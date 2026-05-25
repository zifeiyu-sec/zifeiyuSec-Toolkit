import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox

from _support import cleanup_test_dir, make_test_dir
from core.data_manager import DataManager
from core.task_control import OperationCancelledError
from core.update_service import UpdateInfo
from ui.main_window import MainWindow


class MainWindowBackgroundTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.config_dir = make_test_dir(f"main_window_bg_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.config_dir))

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

    def _fake_load_tools(self, data_manager, callback=None):
        if callback is not None:
            callback([], None)
        return []

    def _create_window(self):
        window = MainWindow(config_dir=str(self.config_dir))
        window.show()
        self.app.processEvents()
        self.addCleanup(lambda: window.deleteLater())
        return window

    def _wait_until(self, predicate, timeout=3.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.01)
        self.app.processEvents()
        return predicate()

    def test_background_task_disables_remote_actions_and_restores_after_success(self):
        window = self._create_window()
        results = []
        errors = []

        def task(progress_callback=None, cancel_requested=None):
            if progress_callback:
                progress_callback("正在执行后台任务...")
            time.sleep(0.05)
            return "done"

        started = window._start_background_task(
            "demo_task",
            task,
            on_success=results.append,
            on_error=errors.append,
            status_message="正在执行后台任务...",
            cancel_message="正在取消后台任务...",
        )

        self.assertTrue(started)
        self.assertFalse(window.sync_official_tools_action.isEnabled())
        self.assertFalse(window.check_update_action.isEnabled())
        self.assertFalse(window.one_click_update_action.isEnabled())
        self.assertTrue(window.cancel_background_task_button.isVisible())
        self.assertTrue(window.cancel_background_task_button.isEnabled())
        self.assertIn("正在取消后台任务", window.background_task_label.text())

        self.assertTrue(self._wait_until(lambda: not window._has_active_background_task()))
        self.assertEqual(["done"], results)
        self.assertEqual([], errors)
        self.assertTrue(window.sync_official_tools_action.isEnabled())
        self.assertTrue(window.check_update_action.isEnabled())
        self.assertTrue(window.one_click_update_action.isEnabled())
        self.assertFalse(window.cancel_background_task_button.isVisible())
        self.assertFalse(window.background_task_label.isVisible())

    def test_one_click_update_chains_check_and_update_tasks(self):
        window = self._create_window()
        call_order = []
        update_info = UpdateInfo(
            current_version="3.1.0",
            latest_version="3.1.1",
            download_url="https://example.com/toolkit.zip",
            asset_name="toolkit.zip",
            release_url="https://example.com/release",
        )

        def fake_check_for_updates(cancel_requested=None, progress_callback=None):
            call_order.append("check")
            if progress_callback:
                progress_callback("checking updates...")
            time.sleep(0.05)
            return update_info, "new version detected"

        def fake_start_one_click_update(info, cancel_requested=None, progress_callback=None):
            call_order.append(f"start:{info.latest_version}")
            if progress_callback:
                progress_callback("downloading update package...")
            time.sleep(0.05)
            return "update flow started"

        window.update_service.can_self_update = lambda: True
        window.update_service.get_update_mode = lambda: "source"
        window.update_service.check_for_updates = fake_check_for_updates
        window.update_service.start_one_click_update = fake_start_one_click_update
        window._themed_question = lambda *_args, **_kwargs: QMessageBox.Yes

        with patch.object(window, "close") as close_mock:
            window.on_one_click_update()
            self.assertTrue(
                self._wait_until(lambda: close_mock.called and not window._has_active_background_task())
            )

        self.assertEqual(["check", "start:3.1.1"], call_order)
        self.assertTrue(window.sync_official_tools_action.isEnabled())
        self.assertTrue(window.check_update_action.isEnabled())
        self.assertTrue(window.one_click_update_action.isEnabled())

    def test_one_click_update_warns_when_release_page_cannot_open(self):
        window = self._create_window()
        window.update_service.can_self_update = lambda: False
        window.update_service.get_release_page_url = lambda: "https://example.com/release"
        window._themed_question = lambda *_args, **_kwargs: QMessageBox.Yes
        QMessageBox.warning.reset_mock()

        with patch("ui.main_window.webbrowser.open", return_value=False) as open_mock:
            window.on_one_click_update()

        open_mock.assert_called_once_with("https://example.com/release")
        QMessageBox.warning.assert_called_once()
        self.assertTrue(QMessageBox.warning.call_args.args[1])
        self.assertTrue(QMessageBox.warning.call_args.args[2])

    def test_close_with_active_task_requests_cancellation_and_exits_after_finish(self):
        window = self._create_window()
        task_started = []
        cancel_seen = []
        errors = []

        def task(progress_callback=None, cancel_requested=None):
            task_started.append(True)
            if progress_callback:
                progress_callback("running cancellable task...")
            deadline = time.time() + 1.0
            while time.time() < deadline:
                if cancel_requested and cancel_requested():
                    cancel_seen.append(True)
                    raise OperationCancelledError("cancelled test task")
                time.sleep(0.01)
            return "done"

        window._start_background_task(
            "cancel_demo",
            task,
            on_success=lambda _result: None,
            on_error=errors.append,
            status_message="正在执行可取消任务...",
            cancel_message="正在取消后台任务...",
        )
        self.assertTrue(self._wait_until(lambda: task_started))

        with patch.object(window, "_prompt_close_with_background_task", return_value="cancel_and_close"):
            window.close()

        self.assertTrue(self._wait_until(lambda: cancel_seen and not window._has_active_background_task()))
        self.assertEqual([], errors)
        self.assertFalse(window.isVisible())


class MainWindowSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.config_dir = make_test_dir(f"main_window_search_{self._testMethodName}")
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
        categories = [
            {
                "id": 1,
                "name": "Category 1",
                "priority": 1,
                "subcategories": [{"id": 101, "name": "Subcategory 1", "priority": 1}],
            },
            {
                "id": 2,
                "name": "Category 2",
                "priority": 2,
                "subcategories": [{"id": 201, "name": "Subcategory 2", "priority": 1}],
            },
        ]
        tools = [
            {
                "id": 1,
                "name": "Alpha Scanner",
                "path": "tools/alpha.exe",
                "description": "alpha category tool",
                "category_id": 1,
                "subcategory_id": 101,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
            {
                "id": 2,
                "name": "Bravo Suite",
                "path": "tools/bravo.exe",
                "description": "bravo global result",
                "category_id": 2,
                "subcategory_id": 201,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
        ]
        self.assertTrue(data_manager.save_categories(categories))
        self.assertTrue(data_manager.save_tools(tools))

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

    def _tool_names(self, window):
        return [tool.get("name") for tool in window.tool_container.model.tools()]

    def _visible_tool_names(self, window):
        if getattr(window, "current_view_mode", "") == "dashboard":
            return [tool.get("name") for tool in window.dashboard_container.favorite_section.container.model.tools()]
        return self._tool_names(window)

    def _run_search(self, window, text):
        window.search_input.setText(text)
        window.search_debounce_timer.stop()
        window.on_search(window.search_input.text())
        self.app.processEvents()

    def test_refresh_current_view_keeps_active_search_results(self):
        window = self._create_window()

        window.on_category_selected(1)
        self.app.processEvents()
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

        self._run_search(window, "Bravo")
        self.assertEqual(["Bravo Suite"], self._tool_names(window))

        window.refresh_current_view()
        self.app.processEvents()
        self.assertEqual(["Bravo Suite"], self._tool_names(window))

    def test_startup_uses_dashboard_without_entering_favorites(self):
        window = self._create_window()

        self.assertFalse(window.is_in_favorites)
        self.assertEqual("dashboard", window.current_view_mode)
        self.assertEqual("dashboard", window._get_current_layout_name())
        self.assertIs(window.dashboard_container, window.tool_stack.currentWidget())
        self.assertEqual("主界面", window.home_action.text())
        self.assertEqual("homeNavButton", window.home_button.objectName())
        self.assertIn("homeNavButton", window.home_button.styleSheet())
        self.assertFalse(hasattr(window, "favorites_button"))
        self.assertFalse(hasattr(window, "favorites_container"))

        initial_home_style = window.home_button.styleSheet()
        window.switch_theme("blue_white")
        self.app.processEvents()
        self.assertIn("homeNavButton", window.home_button.styleSheet())
        self.assertNotEqual(initial_home_style, window.home_button.styleSheet())

    def test_home_action_toggles_between_dashboard_and_main_view(self):
        window = self._create_window()

        window.on_home_action()
        self.app.processEvents()

        self.assertFalse(window.is_in_favorites)
        self.assertEqual("category", window.current_view_mode)
        self.assertEqual("首页", window.home_action.text())
        self.assertIs(window.tool_container, window.tool_stack.currentWidget())
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

        window.on_home_action()
        self.app.processEvents()

        self.assertFalse(window.is_in_favorites)
        self.assertEqual("dashboard", window.current_view_mode)
        self.assertEqual("主界面", window.home_action.text())
        self.assertIs(window.dashboard_container, window.tool_stack.currentWidget())

    def test_favorites_button_opens_dashboard_not_separate_page(self):
        DataManager(config_dir=str(self.config_dir)).toggle_favorite(1)
        window = self._create_window()

        window.on_category_selected(1)
        self.app.processEvents()
        self.assertEqual("category", window.current_view_mode)

        window.on_show_favorites()
        self.app.processEvents()

        self.assertFalse(window.is_in_favorites)
        self.assertEqual("dashboard", window.current_view_mode)
        self.assertIs(window.dashboard_container, window.tool_stack.currentWidget())
        self.assertEqual(["Alpha Scanner"], self._visible_tool_names(window))

    def test_selecting_category_clears_active_search_and_restores_category_view(self):
        window = self._create_window()

        self._run_search(window, "Bravo")
        self.assertEqual(["Bravo Suite"], self._tool_names(window))

        window.on_category_selected(1)
        self.app.processEvents()

        self.assertEqual("", window.search_input.text())
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

    def test_clearing_search_restores_selected_subcategory_view(self):
        window = self._create_window()

        window.on_category_selected(1)
        window.subcategory_view.select_subcategory(101)
        self.app.processEvents()
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

        self._run_search(window, "Bravo")
        self.assertEqual(["Bravo Suite"], self._tool_names(window))

        self._run_search(window, "")
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

    def test_successful_tool_launch_from_search_clears_search_results(self):
        window = self._create_window()

        window.on_category_selected(1)
        self.app.processEvents()
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

        self._run_search(window, "Bravo")
        self.assertEqual(["Bravo Suite"], self._tool_names(window))

        class FakeLauncher:
            def launch_tool(self, **kwargs):
                return {
                    "success": True,
                    "path": kwargs.get("path", ""),
                    "working_directory": "",
                    "command_preview": kwargs.get("path", ""),
                    "launch_mode": "subprocess",
                }

        window.tool_launcher = FakeLauncher()
        window.on_tool_run(
            {
                "id": 2,
                "name": "Bravo Suite",
                "path": "tools/bravo.exe",
                "working_directory": "",
                "run_in_terminal": False,
            }
        )
        self.app.processEvents()

        self.assertEqual("", window.search_input.text())
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

    def test_favorites_button_clears_search_and_shows_dashboard(self):
        DataManager(config_dir=str(self.config_dir)).toggle_favorite(1)
        window = self._create_window()

        window.on_category_selected(1)
        self.app.processEvents()
        self.assertEqual(["Alpha Scanner"], self._tool_names(window))

        self._run_search(window, "Bravo")
        self.assertEqual(["Bravo Suite"], self._tool_names(window))

        window.on_show_favorites()
        self.app.processEvents()
        self.assertFalse(window.is_in_favorites)
        self.assertEqual("dashboard", window.current_view_mode)
        self.assertEqual("", window.search_input.text())
        self.assertEqual(["Alpha Scanner"], self._visible_tool_names(window))


if __name__ == "__main__":
    unittest.main()

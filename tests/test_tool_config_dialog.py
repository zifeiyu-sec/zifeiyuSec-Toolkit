import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QGroupBox, QWidget

from _support import cleanup_test_dir, make_test_dir
from ui.tool_config_dialog import ToolConfigDialog


class _FakeSignal:
    def __init__(self):
        self.disconnected = False
        self.connections = []

    def disconnect(self, *_args, **_kwargs):
        self.disconnected = True

    def connect(self, callback):
        self.connections.append(callback)


class _FakeDownloader:
    def __init__(self, running=True):
        self._running = running
        self.download_finished = _FakeSignal()
        self.finished = _FakeSignal()
        self.interruption_requested = False
        self.quit_called = False
        self.wait_calls = []
        self.parent = object()
        self.delete_later_called = False

    def isRunning(self):
        return self._running

    def requestInterruption(self):
        self.interruption_requested = True

    def quit(self):
        self.quit_called = True

    def wait(self, timeout_ms):
        self.wait_calls.append(timeout_ms)
        return False

    def setParent(self, parent):
        self.parent = parent

    def deleteLater(self):
        self.delete_later_called = True


class ToolConfigDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.icon_dir = make_test_dir(f"tool_config_dialog_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.icon_dir))

    def _create_dialog(self):
        with patch("ui.tool_config_dialog.ensure_runtime_dir", return_value=self.icon_dir):
            return ToolConfigDialog(tool_data={"id": 1, "name": "Test", "path": "", "description": ""}, categories=[])

    def test_stop_active_downloader_detaches_running_thread(self):
        dialog = self._create_dialog()
        fake_downloader = _FakeDownloader(running=True)
        dialog.downloader = fake_downloader

        dialog._stop_active_downloader(wait_ms=10)

        self.assertIsNone(dialog.downloader)
        self.assertTrue(fake_downloader.interruption_requested)
        self.assertTrue(fake_downloader.quit_called)
        self.assertEqual([10], fake_downloader.wait_calls)
        self.assertTrue(fake_downloader.download_finished.disconnected)
        self.assertIsNone(fake_downloader.parent)
        self.assertIn(fake_downloader.deleteLater, fake_downloader.finished.connections)

        dialog.deleteLater()

    def test_done_cleans_up_async_resources_before_dialog_closes(self):
        dialog = self._create_dialog()
        dialog.favicon_timer.start(1000)
        fake_downloader = _FakeDownloader(running=True)
        dialog.downloader = fake_downloader

        dialog.done(0)

        self.assertFalse(dialog.favicon_timer.isActive())
        self.assertIsNone(dialog.downloader)
        self.assertTrue(fake_downloader.interruption_requested)
        self.assertTrue(fake_downloader.download_finished.disconnected)

    def test_arguments_field_copy_marks_terminal_only_behavior(self):
        dialog = self._create_dialog()

        self.assertIn("仅在终端工具模式下生效", dialog.args_edit.placeholderText())
        self.assertIn("非终端工具不会使用这里的内容", dialog.args_edit.toolTip())
        self.assertIn("打开工具", dialog.args_edit.toolTip())

    def test_dialog_size_tracks_parent_window_size(self):
        parent = QWidget()
        parent.resize(1000, 700)
        self.addCleanup(parent.deleteLater)

        with patch("ui.tool_config_dialog.ensure_runtime_dir", return_value=self.icon_dir):
            dialog = ToolConfigDialog(
                tool_data={"id": 1, "name": "Test", "path": "", "description": ""},
                categories=[],
                parent=parent,
            )
        self.addCleanup(dialog.deleteLater)

        screen = dialog.screen() or self.app.primaryScreen()
        available_geometry = screen.availableGeometry() if screen is not None else None
        min_width = 560
        min_height = 600
        max_width = 820
        max_height = 900
        if available_geometry is not None:
            max_width = min(max_width, int(available_geometry.width() * 0.82))
            max_height = min(max_height, int(available_geometry.height() * 0.96))
            min_width = min(min_width, max_width)
            min_height = min(min_height, max_height)

        expected_width = max(min_width, min(int(parent.width() * 0.62), max_width))
        expected_height = max(min_height, min(int(parent.height() * 0.90), max_height))

        self.assertEqual(expected_width, dialog.width())
        self.assertEqual(expected_height, dialog.height())

    def test_dialog_content_uses_comfortable_metrics(self):
        parent = QWidget()
        parent.resize(1000, 700)
        self.addCleanup(parent.deleteLater)

        with patch("ui.tool_config_dialog.ensure_runtime_dir", return_value=self.icon_dir):
            dialog = ToolConfigDialog(
                tool_data={"id": 1, "name": "Test", "path": "", "description": ""},
                categories=[],
                parent=parent,
            )
        self.addCleanup(dialog.deleteLater)

        self.assertGreaterEqual(dialog.icon_preview.width(), 52)
        self.assertGreaterEqual(dialog.icon_button.minimumHeight(), 24)
        self.assertGreaterEqual(dialog.description_edit.maximumHeight(), 100)

        for group in dialog.findChildren(QGroupBox):
            margins = group.layout().contentsMargins()
            self.assertLessEqual(margins.left(), 9)
            self.assertLessEqual(margins.top(), 9)
            self.assertLessEqual(margins.right(), 9)
            self.assertLessEqual(margins.bottom(), 9)

    def test_dialog_uses_themed_frameless_title_bar(self):
        dialog = self._create_dialog()

        self.assertTrue(dialog.windowFlags() & Qt.FramelessWindowHint)
        self.assertEqual("toolConfigTitleBar", dialog.title_bar.objectName())
        self.assertEqual(dialog.windowTitle(), dialog.title_label.text())
        self.assertEqual("toolConfigCloseButton", dialog.close_button.objectName())
        self.assertIn("QWidget#toolConfigTitleBar", dialog.styleSheet())
        self.assertIn("QPushButton#toolConfigCloseButton", dialog.styleSheet())

    def test_dialog_styles_follow_selected_theme_without_background_image(self):
        expectations = {
            "dark_green": ("rgba(0,229,255,0.46)", "rgba(5,18,18,0.56)"),
            "purple_neon": ("rgba(255,207,92,0.52)", "rgba(12,2,20,0.50)"),
            "red_orange": ("rgba(255,205,92,0.76)", "rgba(74,0,0,0.54)"),
            "blue_white": ("rgba(151,213,244,0.62)", "rgba(220,244,253,0.66)"),
            "celadon_mist": ("rgba(137,220,223,0.62)", "rgba(214,243,241,0.66)"),
        }

        dialog = self._create_dialog()
        for theme_name, expected_fragments in expectations.items():
            dialog.set_theme(theme_name)

            for expected_fragment in expected_fragments:
                self.assertIn(expected_fragment, dialog.styleSheet())
            self.assertIn("toolConfigScrollArea", dialog.styleSheet())
            self.assertNotIn("background-image", dialog.styleSheet())

    def test_should_extract_local_file_icon_only_for_exe(self):
        dialog = self._create_dialog()
        exe_path = self.icon_dir / "demo.exe"
        bat_path = self.icon_dir / "demo.bat"
        exe_path.write_bytes(b"exe")
        bat_path.write_bytes(b"@echo off")

        self.assertTrue(dialog._should_extract_local_file_icon(str(exe_path)))
        self.assertFalse(dialog._should_extract_local_file_icon(str(bat_path)))

    def test_relative_path_helpers_resolve_against_base_dir(self):
        config_dir = make_test_dir(f"tool_config_dialog_base_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(config_dir))
        tool_path = config_dir / "tools" / "demo.exe"
        tool_path.parent.mkdir(parents=True, exist_ok=True)
        tool_path.write_bytes(b"exe")

        with patch("ui.tool_config_dialog.ensure_runtime_dir", return_value=self.icon_dir):
            dialog = ToolConfigDialog(
                tool_data={"id": 1, "name": "Test", "path": "", "description": ""},
                categories=[],
                base_dir=config_dir,
            )
        self.addCleanup(dialog.deleteLater)

        self.assertEqual(os.fspath(tool_path.parent), dialog._derive_working_directory("tools/demo.exe"))
        self.assertTrue(dialog._should_extract_local_file_icon("tools/demo.exe"))

    def test_path_command_working_directory_uses_base_dir(self):
        config_dir = make_test_dir(f"tool_config_dialog_cmd_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(config_dir))

        with patch("ui.tool_config_dialog.ensure_runtime_dir", return_value=self.icon_dir):
            dialog = ToolConfigDialog(
                tool_data={"id": 1, "name": "Test", "path": "", "description": ""},
                categories=[],
                base_dir=config_dir,
            )
        self.addCleanup(dialog.deleteLater)

        self.assertEqual(os.fspath(config_dir), dialog._derive_working_directory("nmap"))

    def test_icon_preview_uses_theme_adaptive_default_icon(self):
        dialog = self._create_dialog()
        light_icon = self.icon_dir / "write-github.svg"
        dark_icon = self.icon_dir / "black-github.png"
        light_icon.write_text("<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16'></svg>", encoding="utf-8")
        dark_icon.write_bytes(
            bytes.fromhex(
                "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C4890000000D49444154789C6360606060000000050001A5F645400000000049454E44AE426082"
            )
        )

        def fake_get_icon_cache_key(path, theme_name=None):
            if path == "default_icon":
                return str(dark_icon if theme_name == "dark_green" else light_icon)
            return str(path)

        with patch("ui.tool_config_dialog.get_icon_cache_key", side_effect=fake_get_icon_cache_key):
            dialog.current_theme = "dark_green"
            dialog.selected_icon_name = ""
            dialog._update_icon_preview()
            dark_preview = dialog.icon_preview.pixmap()

            dialog.current_theme = "light"
            dialog._update_icon_preview()
            light_preview = dialog.icon_preview.pixmap()

        self.assertIsNotNone(dark_preview)
        self.assertIsNotNone(light_preview)


if __name__ == "__main__":
    unittest.main()

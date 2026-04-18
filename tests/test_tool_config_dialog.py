import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

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


if __name__ == "__main__":
    unittest.main()

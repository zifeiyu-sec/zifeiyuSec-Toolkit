import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.tool_launch_service import ToolLaunchService


class ToolLaunchServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="tool_launch_service_"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))
        self.service = ToolLaunchService()

    def test_open_file_with_default_app_uses_shell_execute_in_tool_directory(self):
        doc_path = self.temp_dir / "note.md"

        with patch("core.tool_launch_service.sys.platform", "win32"), patch.object(
            self.service,
            "_shell_execute_windows",
            return_value=True,
        ) as shell_execute_mock, patch("core.tool_launch_service.os.startfile") as startfile_mock:
            self.service._open_file_with_default_app(str(doc_path))

        shell_execute_mock.assert_called_once_with(str(doc_path), working_dir=str(self.temp_dir))
        startfile_mock.assert_not_called()

    def test_open_tool_terminal_for_gui_exe_only_opens_terminal(self):
        exe_path = self.temp_dir / "demo.exe"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(self.service, "is_windows_cui_exe", return_value=False), patch.object(
            self.service,
            "open_terminal",
            return_value=True,
        ) as open_terminal_mock, patch.object(
            self.service,
            "_build_windows_tool_command_argv",
        ) as build_command_mock:
            result = self.service.open_tool_terminal(
                path=str(exe_path),
                working_dir=str(self.temp_dir),
                tool_data={"path": str(exe_path)},
            )

        self.assertTrue(result)
        build_command_mock.assert_not_called()
        open_terminal_mock.assert_called_once_with(
            working_dir=str(self.temp_dir),
            path=str(exe_path),
        )

    def test_open_tool_terminal_for_console_exe_runs_command_in_terminal(self):
        exe_path = self.temp_dir / "console.exe"
        terminal_argv = ["console.exe", "--help"]

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(self.service, "is_windows_cui_exe", return_value=True), patch.object(
            self.service,
            "_build_windows_tool_command_argv",
            return_value=["console.exe", "--help"],
        ) as build_command_mock, patch.object(
            self.service,
            "_build_windows_terminal_argv",
            return_value=terminal_argv,
        ) as build_terminal_mock, patch.object(
            self.service,
            "open_terminal",
            return_value=True,
        ) as open_terminal_mock:
            result = self.service.open_tool_terminal(
                path=str(exe_path),
                working_dir=str(self.temp_dir),
                tool_data={"path": str(exe_path), "arguments": "--help"},
            )

        self.assertTrue(result)
        build_command_mock.assert_called_once()
        build_terminal_mock.assert_called_once()
        open_terminal_mock.assert_called_once_with(
            working_dir=str(self.temp_dir),
            command_argv=terminal_argv,
        )

    def test_open_tool_terminal_ignores_arguments_for_non_terminal_gui_exe(self):
        exe_path = self.temp_dir / "gui.exe"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(self.service, "is_windows_cui_exe", return_value=False), patch.object(
            self.service,
            "open_terminal",
            return_value=True,
        ) as open_terminal_mock, patch.object(
            self.service,
            "_build_windows_tool_command_argv",
        ) as build_command_mock:
            result = self.service.open_tool_terminal(
                path=str(exe_path),
                working_dir=str(self.temp_dir),
                tool_data={"path": str(exe_path), "arguments": "gui.exe --help"},
                prefer_config_command=False,
            )

        self.assertTrue(result)
        build_command_mock.assert_not_called()
        open_terminal_mock.assert_called_once_with(
            working_dir=str(self.temp_dir),
            path=str(exe_path),
        )

    def test_open_tool_terminal_prefers_config_command_for_terminal_wrapper(self):
        batch_path = self.temp_dir / "cmd.bat"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "open_terminal",
            return_value=True,
        ) as open_terminal_mock, patch.object(
            self.service,
            "_build_windows_tool_command_argv",
        ) as build_command_mock:
            result = self.service.open_tool_terminal(
                path=str(batch_path),
                working_dir=str(self.temp_dir),
                tool_data={"path": str(batch_path), "arguments": "httpx.exe -h"},
                prefer_config_command=True,
            )

        self.assertTrue(result)
        build_command_mock.assert_not_called()
        open_terminal_mock.assert_called_once_with(
            working_dir=str(self.temp_dir),
            startup_command="httpx.exe -h",
            path=str(batch_path),
        )

    def test_format_terminal_startup_command_prefers_local_executable_in_working_directory(self):
        batch_path = self.temp_dir / "cmd.bat"
        local_httpx = self.temp_dir / "httpx.exe"
        local_httpx.write_text("stub", encoding="utf-8")

        formatted = self.service._format_terminal_startup_command("httpx.exe -h", str(batch_path))

        self.assertEqual(f'{local_httpx} -h', formatted)

    def test_launch_local_tool_with_terminal_flag_runs_config_command_in_terminal(self):
        batch_path = self.temp_dir / "cmd.bat"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "_build_windows_tool_command_argv",
            return_value=[str(batch_path)],
        ), patch.object(
            self.service,
            "open_tool_terminal",
            return_value=True,
        ) as open_tool_terminal_mock:
            result = self.service.launch_local_tool_with_diagnostics(
                path=str(batch_path),
                working_dir=str(self.temp_dir),
                run_in_terminal=True,
                tool_data={
                    "path": str(batch_path),
                    "arguments": "httpx.exe -h",
                    "run_in_terminal": True,
                },
            )

        self.assertTrue(result["success"])
        self.assertEqual("terminal", result["launch_mode"])
        self.assertIn("httpx.exe", result["command_preview"])
        self.assertIn("-h", result["command_preview"])
        open_tool_terminal_mock.assert_called_once_with(
            path=str(batch_path),
            working_dir=str(self.temp_dir),
            tool_data={
                "path": str(batch_path),
                "arguments": "httpx.exe -h",
                "run_in_terminal": True,
            },
            prefer_config_command=True,
        )

    def test_launch_local_tool_type_label_terminal_runs_config_command_in_terminal(self):
        batch_path = self.temp_dir / "cmd.bat"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "_build_windows_tool_command_argv",
            return_value=[str(batch_path)],
        ), patch.object(
            self.service,
            "open_tool_terminal",
            return_value=True,
        ) as open_tool_terminal_mock:
            result = self.service.launch_local_tool_with_diagnostics(
                path=str(batch_path),
                working_dir=str(self.temp_dir),
                run_in_terminal=False,
                tool_data={
                    "path": str(batch_path),
                    "arguments": "httpx.exe -h",
                    "type_label": "终端",
                },
            )

        self.assertTrue(result["success"])
        self.assertEqual("terminal", result["launch_mode"])
        self.assertIn("httpx.exe", result["command_preview"])
        self.assertIn("-h", result["command_preview"])
        open_tool_terminal_mock.assert_called_once_with(
            path=str(batch_path),
            working_dir=str(self.temp_dir),
            tool_data={
                "path": str(batch_path),
                "arguments": "httpx.exe -h",
                "type_label": "终端",
            },
            prefer_config_command=True,
        )

        script_path = self.temp_dir / "launcher.vbs"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "_open_file_with_default_app",
            return_value=None,
        ) as open_file_mock, patch.object(
            self.service,
            "_build_windows_tool_command_argv",
        ) as build_command_mock:
            result = self.service.launch_local_tool(
                path=str(script_path),
                tool_data={"path": str(script_path)},
            )

        self.assertTrue(result)
        open_file_mock.assert_called_once_with(str(script_path), working_dir=str(self.temp_dir))
        build_command_mock.assert_not_called()

    def test_launch_local_tool_shell_opens_plain_exe_like_double_click(self):
        exe_path = self.temp_dir / "demo.exe"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "_open_file_with_default_app",
            return_value=None,
        ) as open_file_mock, patch.object(
            self.service,
            "_build_windows_tool_command_argv",
        ) as build_command_mock:
            result = self.service.launch_local_tool(
                path=str(exe_path),
                tool_data={"path": str(exe_path)},
            )

        self.assertTrue(result)
        open_file_mock.assert_called_once_with(str(exe_path), working_dir=str(self.temp_dir))
        build_command_mock.assert_not_called()

    def test_launch_local_tool_non_terminal_exe_ignores_arguments_and_shell_opens(self):
        exe_path = self.temp_dir / "normal.exe"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "_open_file_with_default_app",
            return_value=None,
        ) as open_file_mock, patch.object(
            self.service,
            "_build_windows_tool_command_argv",
        ) as build_command_mock, patch(
            "core.tool_launch_service.subprocess.Popen",
        ) as popen_mock:
            result = self.service.launch_local_tool(
                path=str(exe_path),
                working_dir=str(self.temp_dir),
                tool_data={"path": str(exe_path), "arguments": "--help"},
            )

        self.assertTrue(result)
        open_file_mock.assert_called_once_with(str(exe_path), working_dir=str(self.temp_dir))
        build_command_mock.assert_not_called()
        popen_mock.assert_not_called()

    def test_launch_local_tool_retries_with_elevation_on_winerror_740_when_terminal_command_argv_used(self):
        exe_path = self.temp_dir / "admin.exe"
        elevation_error = OSError("elevation required")
        elevation_error.winerror = 740

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "is_windows_cui_exe",
            return_value=True,
        ), patch.object(
            self.service,
            "_build_windows_tool_command_argv",
            return_value=[str(exe_path), "--help"],
        ), patch.object(
            self.service,
            "open_tool_terminal",
            side_effect=elevation_error,
        ), patch.object(
            self.service,
            "_launch_windows_elevated",
            return_value=True,
        ) as elevated_mock:
            result = self.service.launch_local_tool_with_diagnostics(
                path=str(exe_path),
                working_dir=str(self.temp_dir),
                tool_data={"path": str(exe_path), "arguments": "--help", "run_in_terminal": True},
            )

        self.assertTrue(result["success"])
        self.assertEqual("elevated", result["launch_mode"])
        self.assertTrue(result["requires_elevation"])
        elevated_mock.assert_called_once()

    def test_launch_local_tool_with_diagnostics_returns_shell_open_metadata(self):
        exe_path = self.temp_dir / "diagnostic.exe"

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "_open_file_with_default_app",
            return_value=None,
        ) as open_file_mock:
            result = self.service.launch_local_tool_with_diagnostics(
                path=str(exe_path),
                tool_data={"path": str(exe_path)},
            )

        self.assertTrue(result["success"])
        self.assertEqual(str(exe_path), result["path"])
        self.assertEqual(str(self.temp_dir), result["working_directory"])
        self.assertEqual(str(exe_path), result["command_preview"])
        self.assertEqual("shell_open", result["launch_mode"])
        self.assertEqual("", result["error_message"])
        self.assertFalse(result["requires_elevation"])
        open_file_mock.assert_called_once_with(str(exe_path), working_dir=str(self.temp_dir))

    def test_launch_local_tool_with_diagnostics_marks_elevated_launch(self):
        exe_path = self.temp_dir / "elevated.exe"
        elevation_error = OSError("elevation required")
        elevation_error.winerror = 740

        with patch("core.tool_launch_service.os.path.exists", return_value=True), patch(
            "core.tool_launch_service.os.path.isdir",
            return_value=False,
        ), patch.object(
            self.service,
            "is_windows_cui_exe",
            return_value=True,
        ), patch.object(
            self.service,
            "_build_windows_tool_command_argv",
            return_value=[str(exe_path), "--help"],
        ), patch.object(
            self.service,
            "open_tool_terminal",
            side_effect=elevation_error,
        ), patch.object(
            self.service,
            "_launch_windows_elevated",
            return_value=True,
        ):
            result = self.service.launch_local_tool_with_diagnostics(
                path=str(exe_path),
                working_dir=str(self.temp_dir),
                tool_data={"path": str(exe_path), "arguments": "--help", "run_in_terminal": True},
            )

        self.assertTrue(result["success"])
        self.assertEqual("elevated", result["launch_mode"])
        self.assertTrue(result["requires_elevation"])
        self.assertEqual(str(self.temp_dir), result["working_directory"])
        self.assertIn("--help", result["command_preview"])

    def test_launch_tool_returns_web_launch_metadata(self):
        with patch("core.tool_launch_service.webbrowser.open", return_value=True) as open_mock:
            result = self.service.launch_tool(
                tool_data={"path": "https://example.com", "is_web_tool": True, "arguments": "ignored"},
            )

        self.assertTrue(result["success"])
        self.assertEqual("https://example.com", result["path"])
        self.assertEqual("https://example.com", result["command_preview"])
        self.assertEqual("web", result["launch_mode"])
        self.assertEqual("", result["error_message"])
        open_mock.assert_called_once_with("https://example.com")

    def test_launch_tool_returns_failure_metadata_when_local_path_missing(self):
        missing_path = self.temp_dir / "missing.exe"

        result = self.service.launch_tool(
            tool_data={"path": str(missing_path), "is_web_tool": False},
            path=str(missing_path),
        )

        self.assertFalse(result["success"])
        self.assertEqual(str(missing_path), result["path"])
        self.assertEqual(str(self.temp_dir), result["working_directory"])
        self.assertEqual("", result["launch_mode"])
        self.assertIn("工具路径不存在", result["error_message"])


if __name__ == "__main__":
    unittest.main()

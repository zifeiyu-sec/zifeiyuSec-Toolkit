import os
import unittest
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from core.tool_metadata import (
    infer_display_tool_type_label,
    infer_import_tool_type_label,
    is_tool_path_available,
    resolve_tool_target_directory,
)


class ToolMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = make_test_dir(f"tool_metadata_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.temp_dir))

    def test_infer_display_tool_type_label_keeps_existing_rules(self):
        self.assertEqual("自定义", infer_display_tool_type_label({"type_label": "自定义"}))
        self.assertEqual("网页", infer_display_tool_type_label({"path": "https://example.com"}))
        self.assertEqual("终端", infer_display_tool_type_label({"path": "tools/run.py"}))
        self.assertEqual("文档", infer_display_tool_type_label({"path": "README.md"}))
        self.assertEqual("应用", infer_display_tool_type_label({"path": "demo.exe"}))
        self.assertEqual("其他", infer_display_tool_type_label({}))

    def test_infer_display_tool_type_label_handles_path_commands(self):
        self.assertEqual("终端", infer_display_tool_type_label({"path": "nmap"}))
        self.assertEqual("终端", infer_display_tool_type_label({"path": "dirsearch", "run_in_terminal": True}))

    def test_infer_import_tool_type_label_keeps_tianhu_rules(self):
        self.assertEqual("网页", infer_import_tool_type_label("", is_web_tool=True))
        self.assertEqual("终端", infer_import_tool_type_label("launcher.exe", source_type="python"))
        self.assertEqual("目录", infer_import_tool_type_label("tools/dirsearch", source_type=""))
        self.assertEqual("终端", infer_import_tool_type_label("dirsearch", source_type=""))
        self.assertEqual("文档", infer_import_tool_type_label("readme.json", source_type=""))
        self.assertEqual("应用", infer_import_tool_type_label("app.exe", source_type=""))

    def test_is_tool_path_available_resolves_relative_paths_against_config_dir(self):
        tool_path = self.temp_dir / "tools" / "demo.exe"
        tool_path.parent.mkdir(parents=True, exist_ok=True)
        tool_path.write_text("stub", encoding="utf-8")

        self.assertTrue(is_tool_path_available({"path": "tools/demo.exe"}, base_dir=self.temp_dir))
        self.assertFalse(is_tool_path_available({"path": "tools/missing.exe"}, base_dir=self.temp_dir))

    def test_is_tool_path_available_uses_path_commands(self):
        command_path = self.temp_dir / "python.exe"
        command_path.write_text("stub", encoding="utf-8")

        with patch("core.runtime_paths.shutil.which", return_value=os.fspath(command_path)):
            self.assertTrue(is_tool_path_available({"path": "python.exe"}, base_dir=self.temp_dir))

    def test_resolve_tool_target_directory_uses_working_dir_then_path_commands(self):
        tools_dir = self.temp_dir / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        command_path = self.temp_dir / "bin" / "nmap.exe"
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command_path.write_text("stub", encoding="utf-8")

        self.assertEqual(
            os.fspath(tools_dir),
            resolve_tool_target_directory(
                {"path": "nmap", "working_directory": "tools"},
                base_dir=self.temp_dir,
            ),
        )
        with patch("core.runtime_paths.shutil.which", return_value=os.fspath(command_path)):
            self.assertEqual(
                os.fspath(command_path.parent),
                resolve_tool_target_directory({"path": "nmap.exe"}, base_dir=self.temp_dir),
            )


if __name__ == "__main__":
    unittest.main()

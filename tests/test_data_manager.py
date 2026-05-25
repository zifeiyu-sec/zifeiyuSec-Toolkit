import json
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from core.data_manager import DataManager


class DataManagerTests(unittest.TestCase):
    def setUp(self):
        self.config_dir = make_test_dir(f"data_manager_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.config_dir))
        self.data_manager = DataManager(config_dir=str(self.config_dir))

    def test_initialization_creates_template_files(self):
        categories_payload = json.loads(Path(self.data_manager.categories_file).read_text(encoding="utf-8"))
        tools_payload = json.loads(Path(self.data_manager.tools_file).read_text(encoding="utf-8"))
        repo_root = Path(__file__).resolve().parents[1]
        template_categories_payload = json.loads((repo_root / "data" / "categories.json").read_text(encoding="utf-8"))
        template_tools_payload = json.loads((repo_root / "data" / "tools.json").read_text(encoding="utf-8"))

        self.assertIn("categories", categories_payload)
        self.assertTrue(categories_payload["categories"])
        self.assertEqual(template_categories_payload, categories_payload)
        self.assertEqual(template_tools_payload, tools_payload)

    def test_tool_round_trip_and_usage_helpers(self):
        categories = [
            {
                "id": 1,
                "name": "分类一",
                "priority": 1,
                "subcategories": [
                    {"id": 101, "name": "子分类一", "priority": 1},
                ],
            }
        ]
        tool = {
            "id": 1,
            "name": "Demo Tool",
            "path": "tools/demo.exe",
            "description": "demo",
            "category_id": 1,
            "subcategory_id": 101,
            "tags": ["alpha", "beta", "alpha"],
            "is_favorite": False,
            "usage_count": 0,
            "last_used": None,
        }

        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools([tool]))

        on_disk_tools = json.loads(Path(self.data_manager.tools_file).read_text(encoding="utf-8"))["tools"]
        self.assertNotIn("tags", on_disk_tools[0])

        loaded_tools = self.data_manager.load_tools()
        self.assertEqual(1, len(loaded_tools))
        self.assertNotIn("tags", loaded_tools[0])

        self.assertTrue(self.data_manager.toggle_favorite(1))
        self.data_manager.update_tool_usage(1)

        updated_tool = self.data_manager.get_tool_by_id(1)
        self.assertTrue(updated_tool["is_favorite"])
        self.assertEqual(1, updated_tool["usage_count"])
        self.assertTrue(updated_tool["last_used"])

    def test_usage_updates_are_buffered_until_flush(self):
        tool = {
            "id": 1,
            "name": "Buffered Tool",
            "path": "tools/buffered.exe",
            "description": "demo",
            "category_id": None,
            "subcategory_id": None,
            "tags": [],
            "is_favorite": False,
            "usage_count": 0,
            "last_used": None,
        }
        self.assertTrue(self.data_manager.save_tools([tool]))

        self.assertTrue(self.data_manager.update_tool_usage(1))
        cached_tool = self.data_manager.get_tool_by_id(1)
        self.assertEqual(1, cached_tool["usage_count"])
        self.assertTrue(cached_tool["last_used"])

        on_disk_tools = json.loads(Path(self.data_manager.tools_file).read_text(encoding="utf-8"))["tools"]
        self.assertEqual(0, on_disk_tools[0]["usage_count"])
        self.assertIsNone(on_disk_tools[0]["last_used"])

        self.assertTrue(self.data_manager.flush_pending_usage_updates())
        flushed_tools = json.loads(Path(self.data_manager.tools_file).read_text(encoding="utf-8"))["tools"]
        self.assertEqual(1, flushed_tools[0]["usage_count"])
        self.assertTrue(flushed_tools[0]["last_used"])

    def test_delete_tools_removes_selected_records_and_pending_usage_updates(self):
        tools = [
            {
                "id": 1,
                "name": "Tool 1",
                "path": "tools/one.exe",
                "description": "one",
                "category_id": None,
                "subcategory_id": None,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
            {
                "id": 2,
                "name": "Tool 2",
                "path": "tools/two.exe",
                "description": "two",
                "category_id": None,
                "subcategory_id": None,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
            {
                "id": 3,
                "name": "Tool 3",
                "path": "tools/three.exe",
                "description": "three",
                "category_id": None,
                "subcategory_id": None,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
        ]
        self.assertTrue(self.data_manager.save_tools(tools))
        self.assertTrue(self.data_manager.update_tool_usage(2))

        result = self.data_manager.delete_tools([2, 99])

        self.assertTrue(result["success"])
        self.assertEqual(2, result["requested"])
        self.assertEqual(1, result["deleted"])
        self.assertEqual(2, result["remaining"])
        self.assertEqual([1, 3], [tool["id"] for tool in self.data_manager.load_tools()])
        self.assertTrue(self.data_manager.flush_pending_usage_updates())
        self.assertEqual([1, 3], [tool["id"] for tool in self.data_manager.load_tools()])

    def test_delete_all_tools_clears_tool_records_and_split_files(self):
        categories = [
            {
                "id": 1,
                "name": "分类一",
                "priority": 1,
                "subcategories": [],
            }
        ]
        tools = [
            {
                "id": 1,
                "name": "Tool 1",
                "path": "tools/one.exe",
                "description": "one",
                "category_id": 1,
                "subcategory_id": None,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            }
        ]
        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools(tools))
        split_dir = Path(self.data_manager.tools_split_dir)
        self.assertTrue(any(split_dir.glob("*.json")))

        result = self.data_manager.delete_all_tools()

        self.assertTrue(result["success"])
        self.assertEqual(1, result["deleted"])
        self.assertEqual([], self.data_manager.load_tools())
        self.assertFalse(any(split_dir.glob("*.json")))

    def test_audit_tools_data_resolves_relative_paths_against_config_dir_and_keeps_commands(self):
        tools_dir = Path(self.data_manager.config_dir) / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        (tools_dir / "demo.exe").write_text("stub", encoding="utf-8")
        icon_path = tools_dir / "write-github.svg"
        icon_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
        path_command = self.config_dir / "bin" / "python.exe"
        path_command.parent.mkdir(parents=True, exist_ok=True)
        path_command.write_text("stub", encoding="utf-8")

        categories = [
            {
                "id": 1,
                "name": "分类一",
                "priority": 1,
                "subcategories": [
                    {"id": 101, "name": "子分类一", "priority": 1},
                ],
            }
        ]
        tools = [
            {
                "id": 1,
                "name": "Relative File Tool",
                "path": "tools/demo.exe",
                "description": "demo",
                "category_id": 1,
                "subcategory_id": 101,
                "icon": "write-github.svg",
                "working_directory": "tools",
                "is_web_tool": False,
            },
            {
                "id": 2,
                "name": "Command Tool",
                "path": "python.exe",
                "description": "command",
                "category_id": 1,
                "subcategory_id": 101,
                "icon": "write-github.svg",
                "working_directory": "",
                "is_web_tool": False,
            },
        ]

        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools(tools))

        with patch("core.data_manager.resolve_icon_path_value", return_value=icon_path), patch(
            "core.runtime_paths.shutil.which",
            return_value=os.fspath(path_command),
        ):
            audit_result = self.data_manager.audit_tools_data()

        self.assertEqual(2, audit_result["total_tools"])
        self.assertEqual(0, audit_result["total_issues"])
        self.assertEqual({}, audit_result["counts"])

    def test_audit_tools_data_reports_intentional_placeholder_local_paths_as_unconfigured(self):
        icon_path = self.config_dir / "placeholder.svg"
        icon_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
        categories = [
            {
                "id": 1,
                "name": "分类一",
                "priority": 1,
                "subcategories": [{"id": 101, "name": "子分类一", "priority": 1}],
            }
        ]
        tools = [
            {
                "id": 1,
                "name": "Placeholder Tool",
                "path": "CHANGE_ME_LOCAL_PATH",
                "description": "demo",
                "category_id": 1,
                "subcategory_id": 101,
                "icon": "placeholder.svg",
                "working_directory": "CHANGE_ME_WORKING_DIRECTORY",
                "is_web_tool": False,
            }
        ]

        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools(tools))

        with patch("core.data_manager.resolve_icon_path_value", return_value=icon_path):
            audit_result = self.data_manager.audit_tools_data()

        self.assertEqual(1, audit_result["total_issues"])
        self.assertEqual(1, audit_result["counts"].get("placeholder_path"))
        self.assertEqual("placeholder_path", audit_result["issues"][0]["issue_type"])

    def test_audit_tools_data_flags_html_icon_file_as_invalid(self):
        html_icon = self.config_dir / "fake-icon.svg"
        html_icon.write_text("<html><body>not an icon</body></html>", encoding="utf-8")
        path_command = self.config_dir / "bin" / "python.exe"
        path_command.parent.mkdir(parents=True, exist_ok=True)
        path_command.write_text("stub", encoding="utf-8")
        categories = [
            {
                "id": 1,
                "name": "分类一",
                "priority": 1,
                "subcategories": [{"id": 101, "name": "子分类一", "priority": 1}],
            }
        ]
        tools = [
            {
                "id": 1,
                "name": "Broken Icon Tool",
                "path": "python.exe",
                "description": "demo",
                "category_id": 1,
                "subcategory_id": 101,
                "icon": "fake-icon.svg",
                "working_directory": "",
                "is_web_tool": False,
            }
        ]

        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools(tools))

        with patch("core.data_manager.resolve_icon_path_value", return_value=html_icon), patch(
            "core.runtime_paths.shutil.which",
            return_value=os.fspath(path_command),
        ):
            audit_result = self.data_manager.audit_tools_data()

        self.assertEqual(1, audit_result["total_issues"])
        self.assertEqual(1, audit_result["counts"].get("invalid_icon"))
        self.assertEqual("invalid_icon", audit_result["issues"][0]["issue_type"])

    def test_save_tools_keeps_aggregate_file_when_split_save_fails(self):
        categories = [
            {
                "id": 1,
                "name": "分类一",
                "priority": 1,
                "subcategories": [],
            }
        ]
        tools = [
            {
                "id": 1,
                "name": "Aggregate Wins",
                "path": "tools/aggregate.exe",
                "description": "demo",
                "category_id": 1,
                "subcategory_id": None,
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            }
        ]
        self.assertTrue(self.data_manager.save_categories(categories))

        with patch.object(self.data_manager, "_save_tools_split_files", side_effect=OSError("split failed")):
            self.assertTrue(self.data_manager.save_tools(tools))

        saved_tools = json.loads(Path(self.data_manager.tools_file).read_text(encoding="utf-8"))["tools"]
        self.assertEqual(["Aggregate Wins"], [tool["name"] for tool in saved_tools])

    def test_load_tools_prefers_aggregate_file_over_split_files(self):
        aggregate_tool = {
            "id": 1,
            "name": "Aggregate Tool",
            "path": "tools/aggregate.exe",
            "description": "aggregate",
            "category_id": None,
            "subcategory_id": None,
            "tags": [],
            "is_favorite": False,
            "usage_count": 0,
            "last_used": None,
        }
        split_tool = {
            "id": 2,
            "name": "Split Tool",
            "path": "tools/split.exe",
            "description": "split",
            "category_id": None,
            "subcategory_id": None,
            "tags": [],
            "is_favorite": False,
            "usage_count": 0,
            "last_used": None,
        }

        Path(self.data_manager.tools_file).write_text(
            json.dumps({"tools": [aggregate_tool]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        split_dir = Path(self.data_manager.tools_split_dir)
        split_dir.mkdir(parents=True, exist_ok=True)
        (split_dir / "99_uncategorized.json").write_text(
            json.dumps({"tools": [split_tool]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        self.data_manager._invalidate_tools_cache()
        loaded_tools = self.data_manager.load_tools()

        self.assertEqual(["Aggregate Tool"], [tool["name"] for tool in loaded_tools])

    def test_audit_tools_data_reports_duplicate_names_and_split_mismatch(self):
        categories = [
            {
                "id": 1,
                "name": "Category",
                "priority": 1,
                "subcategories": [],
            }
        ]
        tools = [
            {
                "id": 1,
                "name": "Duplicate",
                "path": "https://example.com/one",
                "description": "one",
                "category_id": 1,
                "subcategory_id": None,
                "icon": "write-github.svg",
                "is_web_tool": True,
            },
            {
                "id": 2,
                "name": "duplicate",
                "path": "https://example.com/two",
                "description": "two",
                "category_id": 1,
                "subcategory_id": None,
                "icon": "write-github.svg",
                "is_web_tool": True,
            },
        ]
        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools(tools))

        split_file = next(Path(self.data_manager.tools_split_dir).glob("*.json"))
        split_file.write_text(json.dumps({"tools": [tools[0]]}, ensure_ascii=False), encoding="utf-8")
        self.data_manager.invalidate_cache()

        with patch("core.data_manager.resolve_icon_path_value", return_value=self.config_dir / "icon.svg"), patch(
            "core.data_manager.is_valid_icon_file",
            return_value=True,
        ):
            audit_result = self.data_manager.audit_tools_data()

        self.assertEqual(2, audit_result["counts"].get("duplicate_name"))
        self.assertEqual(1, audit_result["counts"].get("split_mismatch"))
        self.assertFalse(audit_result["split_consistency"]["consistent"])
        self.assertTrue(any(issue["issue_type"] == "split_mismatch" for issue in audit_result["issues"]))

    def test_rebuild_tools_split_mirror_backs_up_and_restores_consistency(self):
        categories = [
            {
                "id": 1,
                "name": "Category",
                "priority": 1,
                "subcategories": [],
            }
        ]
        tools = [
            {
                "id": 1,
                "name": "Mirror Tool",
                "path": "https://example.com/tool",
                "description": "tool",
                "category_id": 1,
                "subcategory_id": None,
                "is_web_tool": True,
            }
        ]
        self.assertTrue(self.data_manager.save_categories(categories))
        self.assertTrue(self.data_manager.save_tools(tools))

        stale_file = Path(self.data_manager.tools_split_dir) / "stale.json"
        stale_file.write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "id": 99,
                            "name": "Stale Tool",
                            "path": "https://example.com/stale",
                            "category_id": 1,
                            "subcategory_id": None,
                            "is_web_tool": True,
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        before = self.data_manager.audit_tools_split_consistency()
        self.assertFalse(before["consistent"])

        result = self.data_manager.rebuild_tools_split_mirror(backup=True)

        self.assertTrue(result["success"])
        self.assertTrue(result["backup_path"])
        self.assertTrue(Path(result["backup_path"]).exists())
        self.assertTrue(self.data_manager.audit_tools_split_consistency()["consistent"])

    def test_load_categories_uses_cache_until_file_changes(self):
        categories_first = self.data_manager.load_categories()
        categories_second = self.data_manager.load_categories()

        self.assertIs(categories_first, categories_second)

    def test_reorder_tools_moves_specified_ids_to_front_and_keeps_rest(self):
        tools = [
            {
                "id": 1,
                "name": "Tool 1",
                "path": "tools/one.exe",
                "description": "one",
                "category_id": None,
                "subcategory_id": None,
                "tags": [],
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
            {
                "id": 2,
                "name": "Tool 2",
                "path": "tools/two.exe",
                "description": "two",
                "category_id": None,
                "subcategory_id": None,
                "tags": [],
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
            {
                "id": 3,
                "name": "Tool 3",
                "path": "tools/three.exe",
                "description": "three",
                "category_id": None,
                "subcategory_id": None,
                "tags": [],
                "is_favorite": False,
                "usage_count": 0,
                "last_used": None,
            },
        ]
        self.assertTrue(self.data_manager.save_tools(tools))

        self.assertTrue(self.data_manager.reorder_tools([3, 1]))
        reordered = self.data_manager.load_tools()

        self.assertEqual([3, 1, 2], [tool["id"] for tool in reordered])


if __name__ == "__main__":
    unittest.main()

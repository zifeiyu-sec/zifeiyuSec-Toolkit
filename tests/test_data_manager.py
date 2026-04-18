import json
import shutil
import unittest
from pathlib import Path

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

import os
import unittest
from math import ceil
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QListView, QScrollArea

from _support import cleanup_test_dir, make_test_dir
from core.data_manager import DataManager
from core.style_manager import ThemeManager
from ui.data_health_dialog import DataHealthDialog
from ui.record_list_model import RecordListModel
from ui.main_window_search_mixin import MainWindowSearchMixin
from ui.startup_dashboard import DashboardContainer
from ui.tool_bulk_delete_dialog import ToolBulkDeleteDialog


class UserExperienceViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_record_list_model_supports_virtual_checkable_records(self):
        model = RecordListModel(
            text_func=lambda record: record["name"],
            key_func=lambda record: record["id"],
            checkable=True,
        )
        model.set_records([{"id": 1, "name": "Alpha"}, {"id": 2, "name": "Bravo"}])

        self.assertEqual(2, model.rowCount())
        index = model.index(1, 0)
        self.assertEqual("Bravo", model.data(index, Qt.DisplayRole))
        self.assertEqual(Qt.Unchecked, model.data(index, Qt.CheckStateRole))

        self.assertTrue(model.setData(index, Qt.Checked, Qt.CheckStateRole))
        self.assertEqual({2}, model.checked_keys())

    def test_bulk_delete_dialog_uses_qabstract_model_and_preserves_selection(self):
        tools = [
            {"id": 1, "name": "Alpha", "path": "tools/a.exe", "category_id": 1},
            {"id": 2, "name": "Bravo", "path": "tools/b.exe", "category_id": 1},
        ]
        dialog = ToolBulkDeleteDialog(tools, categories=[{"id": 1, "name": "Ops"}])
        self.addCleanup(dialog.deleteLater)

        self.assertIsInstance(dialog.list_view, QListView)
        self.assertIsInstance(dialog.list_model, RecordListModel)
        self.assertEqual(2, dialog.list_model.rowCount())

        dialog.select_visible_tools()
        self.assertEqual({1, 2}, dialog.checked_tool_ids)
        dialog.search_input.setText("Bravo")
        self.app.processEvents()

        self.assertEqual([2], dialog.visible_tool_ids)
        self.assertEqual({1, 2}, dialog.checked_tool_ids)

    def test_data_health_dialog_shows_runtime_data_dir_and_split_rebuild_state(self):
        config_dir = make_test_dir(f"data_health_dialog_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(config_dir))
        data_manager = DataManager(config_dir=str(config_dir))
        self.assertTrue(data_manager.save_categories([
            {"id": 1, "name": "Category", "priority": 1, "subcategories": []}
        ]))
        self.assertTrue(data_manager.save_tools([
            {
                "id": 1,
                "name": "Demo",
                "path": "https://example.com",
                "description": "demo",
                "category_id": 1,
                "subcategory_id": None,
                "is_web_tool": True,
            }
        ]))
        split_file = next(Path(data_manager.tools_split_dir).glob("*.json"))
        split_file.write_text(
            '{"tools": [{"id": 99, "name": "Stale", "path": "https://example.com/stale", "category_id": 1, "is_web_tool": true}]}',
            encoding="utf-8",
        )

        dialog = DataHealthDialog(data_manager)
        self.addCleanup(dialog.deleteLater)

        self.assertIn(str(config_dir / "data"), dialog.data_dir_label.text())
        self.assertTrue(dialog.rebuild_split_btn.isEnabled())
        self.assertEqual(1, dialog.audit_result["counts"].get("split_mismatch"))

    def test_dashboard_groups_recent_and_favorites(self):
        dashboard = DashboardContainer()
        self.addCleanup(dashboard.deleteLater)
        dashboard.display_tools([
            {
                "id": 1,
                "name": "Recent",
                "path": "tools/recent.exe",
                "usage_count": 3,
                "last_used": "2026-05-01T00:00:00Z",
            },
            {
                "id": 2,
                "name": "Favorite",
                "path": "tools/favorite.exe",
                "is_favorite": True,
            },
        ])

        self.assertEqual(["Recent"], [tool.get("name") for tool in dashboard.recent_section.container.model.tools()])
        self.assertEqual(["Favorite"], [tool.get("name") for tool in dashboard.favorite_section.container.model.tools()])

    def test_dashboard_sections_fit_complete_card_rows(self):
        dashboard = DashboardContainer()
        self.addCleanup(dashboard.deleteLater)
        dashboard.resize(1500, 900)
        dashboard.show()
        self.app.processEvents()

        tools = [
            {
                "id": index,
                "name": f"Favorite {index}",
                "path": f"tools/favorite-{index}.exe",
                "is_favorite": True,
            }
            for index in range(1, 9)
        ]
        dashboard.display_tools(tools)
        self.app.processEvents()

        section = dashboard.favorite_section
        section._sync_container_height()
        self.app.processEvents()

        grid_size = section.container.view.gridSize()
        columns = max(1, section.container.view.viewport().width() // max(1, grid_size.width()))
        rows = ceil(section.container.model.rowCount() / columns)

        self.assertIsInstance(dashboard.scroll_area, QScrollArea)
        self.assertEqual(Qt.ScrollBarAlwaysOff, section.container.view.verticalScrollBarPolicy())
        self.assertGreaterEqual(section.container.height(), rows * grid_size.height())

    def test_dashboard_height_sync_does_not_force_duplicate_tool_layouts(self):
        dashboard = DashboardContainer()
        self.addCleanup(dashboard.deleteLater)
        section = dashboard.favorite_section
        tools = [
            {"id": index, "name": f"Favorite {index}", "path": f"tools/favorite-{index}.exe", "is_favorite": True}
            for index in range(1, 5)
        ]

        with patch.object(section.container, "update_card_layout", wraps=section.container.update_card_layout) as layout_mock:
            section.display_tools(tools)
            self.app.processEvents()

        force_values = [call.kwargs.get("force", False) for call in layout_mock.call_args_list]
        self.assertTrue(force_values)
        self.assertNotIn(True, force_values)

    def test_dashboard_recent_section_limits_to_four_most_recent_tools(self):
        dashboard = DashboardContainer()
        self.addCleanup(dashboard.deleteLater)

        dashboard.display_tools([
            {"id": 1, "name": "Used 1", "path": "tools/1.exe", "usage_count": 1, "last_used": "2026-05-01T00:00:00Z"},
            {"id": 2, "name": "Used 7", "path": "tools/2.exe", "usage_count": 7, "last_used": "2026-04-01T00:00:00Z"},
            {"id": 3, "name": "Used 5", "path": "tools/3.exe", "usage_count": 5, "last_used": "2026-05-02T00:00:00Z"},
            {"id": 4, "name": "Used 3", "path": "tools/4.exe", "usage_count": 3, "last_used": "2026-05-03T00:00:00Z"},
            {"id": 5, "name": "Used 9", "path": "tools/5.exe", "usage_count": 9, "last_used": "2026-03-01T00:00:00Z"},
            {"id": 6, "name": "Used 2", "path": "tools/6.exe", "usage_count": 2, "last_used": "2026-05-04T00:00:00Z"},
        ])

        self.assertEqual(
            ["Used 2", "Used 3", "Used 5", "Used 1"],
            [tool.get("name") for tool in dashboard.recent_section.container.model.tools()],
        )

    def test_search_direct_hits_skip_expensive_fuzzy_scoring(self):
        search = MainWindowSearchMixin()

        with patch("ui.main_window_search_mixin.difflib.SequenceMatcher") as sequence_matcher:
            self.assertEqual(104, search._score_tool_match_text("bravo suite", "global result", "bravo"))
            self.assertEqual(68, search._score_tool_match_text("alpha scanner", "bravo global result", "bravo"))

        sequence_matcher.assert_not_called()

    def test_search_index_prebuilds_fuzzy_candidates(self):
        class SearchHarness(MainWindowSearchMixin):
            def _get_search_scope_tools(self):
                return [
                    {
                        "id": 1,
                        "name": "Directory Scanner",
                        "description": "Fast dirsearch wrapper",
                    }
                ]

        search = SearchHarness()
        index = search._build_tool_search_index()

        self.assertEqual(1, len(index))
        self.assertIn("fuzzy_candidates", index[0])
        self.assertIn("directory scanner", index[0]["fuzzy_candidates"])
        self.assertIn("dirsearch", index[0]["fuzzy_candidates"])

    def test_theme_manager_exposes_shared_experience_styles(self):
        manager = ThemeManager()

        for theme_name in ("dark_green", "blue_white", "celadon_mist", "purple_neon", "red_orange"):
            dialog_style = manager.get_dialog_list_style(theme_name)
            toast_style = manager.get_toast_style(theme_name, kind="success")
            dashboard_style = manager.get_dashboard_style(theme_name)
            home_style = manager.get_home_nav_button_style(theme_name)

            self.assertIn("QListView", dialog_style)
            self.assertIn("QFrame#toastFrame", toast_style)
            self.assertIn("dashboardSectionTitle", dashboard_style)
            self.assertIn("QToolButton#homeNavButton", home_style)


if __name__ == "__main__":
    unittest.main()

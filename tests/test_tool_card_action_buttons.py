import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication, QListView, QMenu, QStyleOptionViewItem, QToolButton

from ui.favorites_grid_view import FavoriteToolCard, FavoritesGridContainer
from ui.tool_card_action_icons import (
    ACTION_BUTTON_OPEN_DIRECTORY,
    ACTION_BUTTON_OPEN_NOTES,
    ACTION_BUTTON_OPEN_TERMINAL,
    ACTION_BUTTON_RUN,
    ACTION_BUTTON_TOGGLE_FAVORITE,
)
from core.path_status_service import PathStatus, PathStatusResult
from core.style_manager import ThemeManager
from ui.tool_model_view import ToolCardContainer, ToolDelegate


class ToolCardActionButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_favorite_card_exposes_five_same_size_action_buttons(self):
        card = FavoriteToolCard(
            {
                "id": 1,
                "name": "Demo Tool",
                "path": "tools/demo.exe",
                "description": "demo",
                "is_favorite": False,
            }
        )

        buttons = card.findChildren(QToolButton, "favoriteCardAction")
        self.assertEqual(5, len(buttons))
        self.assertEqual(QSize(30, 26), card.run_button.size())
        self.assertEqual(card.run_button.size(), card.favorite_button.size())
        self.assertEqual(card.run_button.size(), card.notes_button.size())
        self.assertFalse(card.favorite_button.icon().isNull())
        self.assertFalse(card.notes_button.icon().isNull())

    def test_dark_green_favorite_card_text_colors_are_applied_to_labels(self):
        container = FavoritesGridContainer()
        self.addCleanup(container.deleteLater)
        card = FavoriteToolCard(
            {
                "id": 1,
                "name": "Demo Tool",
                "path": "tools/demo.exe",
                "description": "demo",
                "is_favorite": True,
            },
            theme_name="dark_green",
        )
        self.addCleanup(card.deleteLater)

        container._apply_card_theme(card)

        self.assertIn("color: #00ff41", card.name_label.styleSheet())
        self.assertIn("color: #7cc38b", card.desc_label.styleSheet())

    def test_main_tool_grid_uses_most_columns_that_fit(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)

        preset = container._get_layout_preset()
        spacing = container.view.spacing()

        self.assertEqual(4, container._resolve_columns(1300, spacing, preset))
        self.assertEqual(3, container._resolve_columns(1100, spacing, preset))
        self.assertEqual(2, container._resolve_columns(800, spacing, preset))
        self.assertEqual(1, container._resolve_columns(560, spacing, preset))

    def test_main_tool_grid_wraps_left_to_right_even_when_mode_is_unchanged(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)

        container.set_layout_mode("main")

        self.assertEqual(QListView.IconMode, container.view.viewMode())
        self.assertEqual(QListView.LeftToRight, container.view.flow())
        self.assertTrue(container.view.isWrapping())

    def test_main_tool_grid_places_two_cards_per_row_when_width_allows(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        container.resize(880, 620)
        container.display_tools(
            [
                {"id": tool_id, "name": f"Tool {tool_id}", "path": f"tool-{tool_id}.exe"}
                for tool_id in range(4)
            ]
        )

        container.show()
        self.app.processEvents()
        container.update_card_layout(force=True)
        self.app.processEvents()

        first_card = container.view.visualRect(container.model.index(0, 0))
        second_card = container.view.visualRect(container.model.index(1, 0))
        third_card = container.view.visualRect(container.model.index(2, 0))

        self.assertEqual(first_card.y(), second_card.y())
        self.assertGreater(second_card.x(), first_card.x())
        self.assertEqual(first_card.x(), third_card.x())
        self.assertGreater(third_card.y(), first_card.y())

    def test_tool_grid_queues_path_status_for_paint(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        tool = {"id": 3, "name": "Missing Tool", "path": "missing.exe"}

        with patch.object(container.path_status_service, "request", return_value=None) as request_mock:
            container.display_tools([tool])
            option = QStyleOptionViewItem()
            color = container.delegate._get_status_color(container.model.get_tool(container.model.index(0, 0)), option)

        request_mock.assert_called_once()
        self.assertEqual(1, len(container._path_status_queue))
        self.assertEqual(QColor(245, 158, 11), color)

    def test_tool_grid_prioritizes_visible_path_status_checks(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        container.resize(880, 260)
        tools = [
            {"id": tool_id, "name": f"Tool {tool_id}", "path": f"tool-{tool_id}.exe"}
            for tool_id in range(60)
        ]

        with patch.object(container.path_status_service, "request", return_value=None) as request_mock:
            container.display_tools(tools)

        self.assertLess(request_mock.call_count, len(tools) // 2)
        self.assertGreater(request_mock.call_count, 0)
        self.assertLess(len(container._path_status_queue), len(tools) // 2)
        self.assertGreater(len(container._path_status_queue), 0)

    def test_tool_grid_can_resolve_path_status_synchronously_for_tests(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        container._async_path_status_enabled = False
        tool = {"id": 3, "name": "Missing Tool", "path": "missing.exe"}

        missing_result = PathStatusResult(
            cache_key=container._path_status_cache_key(tool, container._resolve_metadata_base_dir()),
            status=PathStatus.MISSING,
            available=False,
        )
        with patch.object(container.path_status_service, "resolve_now", return_value=missing_result) as resolve_mock:
            container.display_tools([tool])
            option = QStyleOptionViewItem()
            color = container.delegate._get_status_color(container.model.get_tool(container.model.index(0, 0)), option)

        resolve_mock.assert_called_once()
        self.assertEqual(QColor(220, 38, 38), color)

    def test_tool_grid_reuses_metadata_for_duplicate_paths(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        tools = [
            {"id": 1, "name": "One", "path": "CHANGE_ME_LOCAL_PATH"},
            {"id": 2, "name": "Two", "path": "CHANGE_ME_LOCAL_PATH"},
        ]

        with patch("ui.tool_model_view.infer_display_tool_type_label", return_value="应用") as type_mock:
            with patch("ui.tool_model_view.get_icon_cache_key", return_value="cached-icon") as icon_mock:
                container.display_tools(tools)

        self.assertEqual(1, len(container._path_status_queue))
        type_mock.assert_called_once()
        icon_mock.assert_called_once()

    def test_tool_grid_updates_matching_row_when_auto_icon_is_ready(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        tool = {"id": 1, "name": "Web Tool", "path": "https://example.com", "is_web_tool": True}

        with patch("ui.tool_model_view.get_icon_cache_key", return_value="fallback-icon"):
            container.display_tools([tool])

        container._update_rows_for_auto_icon("resolved-web-icon", tool)

        stored_tool = container.model.get_tool(container.model.index(0, 0))
        self.assertEqual("resolved-web-icon", stored_tool["_icon_cache_key"])

    def test_tool_delegate_caches_action_icons(self):
        delegate = ToolDelegate()

        with patch("ui.tool_model_view.load_tool_card_action_icon", return_value=Mock()) as load_icon_mock:
            first = delegate._get_action_icons(None)
            second = delegate._get_action_icons(None)

        self.assertIs(first, second)
        self.assertEqual(5, load_icon_mock.call_count)

    def test_tool_context_menu_uses_current_theme_style(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        container.set_theme("blue_white")
        container.display_tools([{"id": 1, "name": "Demo", "path": "tools/demo.exe"}])
        container.show()
        self.app.processEvents()

        captured_menus = []

        def fake_exec(menu, *_args, **_kwargs):
            captured_menus.append(menu)

        with patch.object(QMenu, "exec_", fake_exec):
            container.show_context_menu(container.view.visualRect(container.model.index(0, 0)).center())

        self.assertEqual(1, len(captured_menus))
        self.assertIn("#edf8fc", captured_menus[0].styleSheet())
        self.assertIn("rgba(184,241,250,0.72)", captured_menus[0].styleSheet())

    def test_context_menu_style_matches_light_themes(self):
        manager = ThemeManager()

        blue_style = manager.get_context_menu_style("blue_white")
        celadon_style = manager.get_context_menu_style("celadon_mist")

        self.assertIn("#edf8fc", blue_style)
        self.assertIn("rgba(184,241,250,0.72)", blue_style)
        self.assertIn("#eef6f3", celadon_style)
        self.assertIn("rgba(174,220,214,0.26)", celadon_style)

    def test_favorites_grid_columns_follow_available_width(self):
        container = FavoritesGridContainer()
        self.addCleanup(container.deleteLater)

        self.assertEqual(4, container._resolve_column_count(1120))
        self.assertEqual(3, container._resolve_column_count(900))
        self.assertEqual(2, container._resolve_column_count(620))
        self.assertEqual(1, container._resolve_column_count(320))

    def test_favorites_grid_reuses_metadata_for_duplicate_paths(self):
        container = FavoritesGridContainer()
        self.addCleanup(container.deleteLater)
        tools = [
            {"id": 1, "name": "One", "path": "CHANGE_ME_LOCAL_PATH", "is_favorite": True},
            {"id": 2, "name": "Two", "path": "CHANGE_ME_LOCAL_PATH", "is_favorite": True},
        ]

        with patch("ui.tool_model_view.infer_display_tool_type_label", return_value="应用") as type_mock:
            with patch("ui.tool_model_view.get_icon_cache_key", return_value="cached-icon") as icon_mock:
                container.display_tools(tools)

        self.assertEqual(1, len(container._path_status_queue))
        type_mock.assert_called_once()
        icon_mock.assert_called_once()

    def test_tool_card_container_routes_favorite_and_notes_buttons(self):
        container = ToolCardContainer()
        self.addCleanup(container.deleteLater)
        tool = {
            "id": 7,
            "name": "Demo Tool",
            "path": "tools/demo.exe",
            "description": "demo",
            "is_web_tool": False,
        }
        container.model.update_data([tool])
        index = container.model.index(0, 0)
        stored_tool = container.model.get_tool(index)

        run_calls = []
        favorite_calls = []
        notes_mock = Mock()
        command_mock = Mock()
        directory_mock = Mock()

        container.run_tool.connect(lambda payload: run_calls.append(payload))
        container.toggle_favorite.connect(lambda tool_id: favorite_calls.append(tool_id))
        container._open_notes_for_tool = notes_mock
        container.resolve_tool_target_dir = Mock(return_value="C:\\tmp")
        container.open_command_line = command_mock
        container.open_directory = directory_mock

        container.on_button_clicked(index, ACTION_BUTTON_RUN)
        container.on_button_clicked(index, ACTION_BUTTON_TOGGLE_FAVORITE)
        container.on_button_clicked(index, ACTION_BUTTON_OPEN_NOTES)
        container.on_button_clicked(index, ACTION_BUTTON_OPEN_TERMINAL)
        container.on_button_clicked(index, ACTION_BUTTON_OPEN_DIRECTORY)

        self.assertEqual([stored_tool], run_calls)
        self.assertEqual([tool["id"]], favorite_calls)
        notes_mock.assert_called_once_with(stored_tool)
        command_mock.assert_called_once_with("C:\\tmp", tool_data=stored_tool)
        directory_mock.assert_called_once_with("C:\\tmp")

    def test_favorites_grid_container_routes_favorite_and_notes_on_web_tools(self):
        container = FavoritesGridContainer()
        self.addCleanup(container.deleteLater)
        tool = {
            "id": 8,
            "name": "Web Tool",
            "path": "https://example.com",
            "is_web_tool": True,
        }

        run_calls = []
        favorite_calls = []
        notes_mock = Mock()

        container.run_tool.connect(lambda payload: run_calls.append(payload))
        container.toggle_favorite.connect(lambda tool_id: favorite_calls.append(tool_id))
        container._open_notes_for_tool = notes_mock

        container._handle_tool_button_click(tool, ACTION_BUTTON_TOGGLE_FAVORITE)
        container._handle_tool_button_click(tool, ACTION_BUTTON_OPEN_NOTES)

        self.assertEqual([], run_calls)
        self.assertEqual([tool["id"]], favorite_calls)
        notes_mock.assert_called_once_with(tool)

    def test_favorites_grid_container_reorders_cards_and_emits_order(self):
        container = FavoritesGridContainer()
        self.addCleanup(container.deleteLater)
        tools = [
            {"id": 1, "name": "Alpha", "path": "tools/a.exe", "is_favorite": True},
            {"id": 2, "name": "Bravo", "path": "tools/b.exe", "is_favorite": True},
            {"id": 3, "name": "Charlie", "path": "tools/c.exe", "is_favorite": True},
        ]
        emitted_orders = []
        container.tool_order_changed.connect(lambda ordered_ids: emitted_orders.append(ordered_ids))

        container.display_tools(tools)
        moved = container._move_favorite_tool_to_target(1, 3)

        self.assertTrue(moved)
        self.assertEqual([2, 3, 1], [tool["id"] for tool in container._tools])
        self.assertEqual([2, 3, 1], [tool["id"] for tool in container.model.tools()])
        self.assertEqual([[2, 3, 1]], emitted_orders)

    def test_favorites_grid_container_moves_card_to_end(self):
        container = FavoritesGridContainer()
        self.addCleanup(container.deleteLater)
        tools = [
            {"id": 1, "name": "Alpha", "path": "tools/a.exe", "is_favorite": True},
            {"id": 2, "name": "Bravo", "path": "tools/b.exe", "is_favorite": True},
            {"id": 3, "name": "Charlie", "path": "tools/c.exe", "is_favorite": True},
        ]
        emitted_orders = []
        container.tool_order_changed.connect(lambda ordered_ids: emitted_orders.append(ordered_ids))

        container.display_tools(tools)
        moved = container._move_favorite_tool_to_end(1)

        self.assertTrue(moved)
        self.assertEqual([2, 3, 1], [tool["id"] for tool in container._tools])
        self.assertEqual([2, 3, 1], [tool["id"] for tool in container.model.tools()])
        self.assertEqual([[2, 3, 1]], emitted_orders)


if __name__ == "__main__":
    unittest.main()

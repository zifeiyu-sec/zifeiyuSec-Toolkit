import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from ui.icon_loader import get_icon_cache_key


class IconLoaderTests(unittest.TestCase):
    def setUp(self):
        self.workspace = make_test_dir(f"icon_loader_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.workspace))

        self.exe_path = self.workspace / "nmap.exe"
        self.exe_path.write_bytes(b"fake-exe")

        self.icon_cache_dir = self.workspace / "exe_cache"
        self.icon_cache_dir.mkdir(parents=True, exist_ok=True)

    def test_get_icon_cache_key_prefers_executable_cache_for_default_icon(self):
        tool = {
            "path": str(self.exe_path),
            "icon": "favicon.ico",
            "is_web_tool": False,
        }

        with patch("ui.icon_loader.ensure_runtime_dir", return_value=self.icon_cache_dir):
            icon_key = get_icon_cache_key(tool)

        self.assertIsNotNone(icon_key)
        self.assertTrue(icon_key.endswith(".png"))
        self.assertIn(str(self.icon_cache_dir), icon_key)

    def test_get_icon_cache_key_keeps_custom_icon_when_it_is_resolvable(self):
        custom_icon = self.workspace / "custom.png"
        custom_icon.write_bytes(b"fake-png")
        tool = {
            "path": str(self.exe_path),
            "icon": str(custom_icon),
            "is_web_tool": False,
        }

        with patch("ui.icon_loader.ensure_runtime_dir", return_value=self.icon_cache_dir):
            icon_key = get_icon_cache_key(tool)

        self.assertEqual(str(custom_icon), icon_key)

    def test_get_icon_cache_key_falls_back_to_executable_cache_for_invalid_custom_icon(self):
        tool = {
            "path": str(self.exe_path),
            "icon": str(self.workspace / "missing.png"),
            "is_web_tool": False,
        }

        with patch("ui.icon_loader.ensure_runtime_dir", return_value=self.icon_cache_dir):
            icon_key = get_icon_cache_key(tool)

        self.assertIsNotNone(icon_key)
        self.assertTrue(icon_key.endswith(".png"))
        self.assertIn(str(self.icon_cache_dir), icon_key)

    def test_get_icon_cache_key_uses_theme_adaptive_default_for_legacy_icon_alias(self):
        resolved_icons = {
            "write-github.svg": str(self.workspace / "write-github.svg"),
            "black-github.png": str(self.workspace / "black-github.png"),
            "github_1_1_1.svg": str(self.workspace / "github_1_1_1.svg"),
            "favicon.ico": str(self.workspace / "favicon.ico"),
        }

        def fake_resolve_icon_path(value):
            name = Path(str(value)).name
            return resolved_icons.get(name)

        with patch("ui.icon_loader.resolve_icon_path", side_effect=fake_resolve_icon_path):
            dark_key = get_icon_cache_key("github_1_1_1.svg", theme_name="dark_green")
            light_key = get_icon_cache_key("github_1_1_1.svg", theme_name="light")

        self.assertEqual(resolved_icons["black-github.png"], dark_key)
        self.assertEqual(resolved_icons["write-github.svg"], light_key)

    def test_get_icon_cache_key_uses_theme_adaptive_default_for_default_placeholder(self):
        resolved_icons = {
            "write-github.svg": str(self.workspace / "write-github.svg"),
            "black-github.png": str(self.workspace / "black-github.png"),
            "github_1_1_1.svg": str(self.workspace / "github_1_1_1.svg"),
            "favicon.ico": str(self.workspace / "favicon.ico"),
        }

        def fake_resolve_icon_path(value):
            name = Path(str(value)).name
            return resolved_icons.get(name)

        tool = {
            "path": "https://example.com",
            "icon": "default_icon",
            "is_web_tool": True,
        }

        with patch("ui.icon_loader.resolve_icon_path", side_effect=fake_resolve_icon_path):
            dark_key = get_icon_cache_key(tool, theme_name="dark_green")
            light_key = get_icon_cache_key(tool, theme_name="light")

        self.assertEqual(resolved_icons["black-github.png"], dark_key)
        self.assertEqual(resolved_icons["write-github.svg"], light_key)

    def test_get_icon_cache_key_keeps_explicit_default_filenames_literal(self):
        resolved_icons = {
            "write-github.svg": str(self.workspace / "write-github.svg"),
            "black-github.png": str(self.workspace / "black-github.png"),
            "github_1_1_1.svg": str(self.workspace / "github_1_1_1.svg"),
            "favicon.ico": str(self.workspace / "favicon.ico"),
        }

        def fake_resolve_icon_path(value):
            name = Path(str(value)).name
            return resolved_icons.get(name)

        tool = {
            "path": "https://example.com",
            "icon": "black-github.png",
            "is_web_tool": True,
        }

        with patch("ui.icon_loader.resolve_icon_path", side_effect=fake_resolve_icon_path):
            dark_key = get_icon_cache_key(tool, theme_name="dark_green")
            light_key = get_icon_cache_key(tool, theme_name="light")
            svg_key = get_icon_cache_key("write-github.svg", theme_name="dark_green")

        self.assertEqual(resolved_icons["black-github.png"], dark_key)
        self.assertEqual(resolved_icons["black-github.png"], light_key)
        self.assertEqual(resolved_icons["write-github.svg"], svg_key)


if __name__ == "__main__":
    unittest.main()

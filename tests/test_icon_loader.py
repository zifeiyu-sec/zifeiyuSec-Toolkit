import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from core.auto_icon_resolver import clear_auto_icon_index_cache, record_auto_icon_path
from ui.icon_loader import get_icon_cache_key, icon_loader


class IconLoaderTests(unittest.TestCase):
    def setUp(self):
        self.workspace = make_test_dir(f"icon_loader_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.workspace))
        self.addCleanup(clear_auto_icon_index_cache)

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

        with patch("core.icon_resolution_service.resolve_icon_path_value", side_effect=fake_resolve_icon_path):
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

        with patch("core.icon_resolution_service.resolve_icon_path_value", side_effect=fake_resolve_icon_path):
            dark_key = get_icon_cache_key(tool, theme_name="dark_green")
            light_key = get_icon_cache_key(tool, theme_name="light")

        self.assertEqual(resolved_icons["black-github.png"], dark_key)
        self.assertEqual(resolved_icons["write-github.svg"], light_key)

    def test_get_icon_cache_key_uses_theme_adaptive_default_for_explicit_default_filenames(self):
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

        with patch("core.icon_resolution_service.resolve_icon_path_value", side_effect=fake_resolve_icon_path):
            dark_key = get_icon_cache_key(tool, theme_name="dark_green")
            light_key = get_icon_cache_key(tool, theme_name="light")
            svg_key = get_icon_cache_key("write-github.svg", theme_name="dark_green")

        self.assertEqual(resolved_icons["black-github.png"], dark_key)
        self.assertEqual(resolved_icons["write-github.svg"], light_key)
        self.assertEqual(resolved_icons["black-github.png"], svg_key)

    def test_get_icon_cache_key_uses_theme_adaptive_default_for_github_favicon_alias(self):
        resolved_icons = {
            "write-github.svg": str(self.workspace / "write-github.svg"),
            "black-github.png": str(self.workspace / "black-github.png"),
            "github.com_favicon.ico": str(self.workspace / "github.com_favicon.ico"),
            "favicon.ico": str(self.workspace / "favicon.ico"),
        }

        def fake_resolve_icon_path(value):
            name = Path(str(value)).name
            return resolved_icons.get(name)

        with patch("core.icon_resolution_service.resolve_icon_path_value", side_effect=fake_resolve_icon_path):
            dark_key = get_icon_cache_key("github.com_favicon.ico", theme_name="purple_neon")
            light_key = get_icon_cache_key("github.com_favicon.ico", theme_name="celadon_mist")

        self.assertEqual(resolved_icons["black-github.png"], dark_key)
        self.assertEqual(resolved_icons["write-github.svg"], light_key)

    def test_get_icon_cache_key_falls_back_to_theme_default_for_missing_named_icon(self):
        resolved_icons = {
            "write-github.svg": str(self.workspace / "write-github.svg"),
            "black-github.png": str(self.workspace / "black-github.png"),
            "favicon.ico": str(self.workspace / "favicon.ico"),
        }

        def fake_resolve_icon_path(value):
            name = Path(str(value)).name
            return resolved_icons.get(name)

        tool = {
            "path": "https://example.com",
            "icon": "missing-custom-icon.png",
            "is_web_tool": True,
        }

        with patch("core.icon_resolution_service.resolve_icon_path_value", side_effect=fake_resolve_icon_path):
            dark_key = get_icon_cache_key(tool, theme_name="dark_green")
            light_key = get_icon_cache_key(tool, theme_name="blue_white")

        self.assertEqual(resolved_icons["black-github.png"], dark_key)
        self.assertEqual(resolved_icons["write-github.svg"], light_key)

    def test_warm_tool_icon_queues_local_sidecar_icon_without_manual_config(self):
        tool_dir = self.workspace / "sidecar_tool"
        tool_dir.mkdir()
        tool_path = tool_dir / "runner.bat"
        tool_path.write_text("@echo off", encoding="utf-8")
        sidecar_icon = tool_dir / "logo.png"
        sidecar_icon.write_bytes(b"fake-png")
        tool = {
            "path": str(tool_path),
            "icon": "default_icon",
            "is_web_tool": False,
        }

        icon_key = get_icon_cache_key(tool, theme_name="dark_green")

        self.assertEqual(str(sidecar_icon), icon_key)

    def test_get_icon_cache_key_uses_known_tool_registry_without_manual_config(self):
        registry_icon = self.workspace / "nmap.png"
        registry_icon.write_bytes(b"fake-png")
        tool = {
            "name": "Nmap",
            "path": "nmap",
            "icon": "default_icon",
            "is_web_tool": False,
        }

        def fake_resolve_icon_path_value(value):
            if Path(str(value)).name == "nmap.png":
                return registry_icon
            return None

        with patch("core.auto_icon_resolver.resolve_icon_path_value", side_effect=fake_resolve_icon_path_value):
            icon_key = get_icon_cache_key(tool)

        self.assertEqual(str(registry_icon), icon_key)

    def test_get_icon_cache_key_uses_cached_web_icon_without_manual_config(self):
        auto_cache_dir = self.workspace / "auto_cache"
        web_icon = self.workspace / "example_favicon.png"
        web_icon.write_bytes(b"fake-png")
        tool = {
            "name": "Example",
            "path": "https://example.com/app",
            "icon": "default_icon",
            "is_web_tool": True,
        }

        with patch("core.auto_icon_resolver.ensure_runtime_dir", return_value=auto_cache_dir):
            record_auto_icon_path(tool, web_icon, "web")
            icon_key = get_icon_cache_key(tool)

        self.assertEqual(str(web_icon), icon_key)

    def test_warm_tool_icon_queues_executable_extraction_when_cache_is_missing(self):
        tool = {
            "path": str(self.exe_path),
            "icon": "favicon.ico",
            "is_web_tool": False,
        }
        icon_loader.clear_cache()

        with patch("ui.icon_loader.ensure_runtime_dir", return_value=self.icon_cache_dir):
            icon_loader.warm_tool_icon(tool, theme_name="dark_green")

        self.assertEqual(1, len(icon_loader._exe_icon_queue))
        target_path, queued_tool = icon_loader._exe_icon_queue[0]
        self.assertEqual(str(self.exe_path), queued_tool["path"])
        self.assertTrue(target_path.endswith(".png"))

    def test_get_icon_uses_precomputed_cache_key_without_recomputing(self):
        tool = {
            "path": str(self.exe_path),
            "icon": "favicon.ico",
            "is_web_tool": False,
            "_icon_cache_key": str(self.workspace / "cached-icon.png"),
            "_icon_cache_theme": "dark_green",
        }

        with patch("ui.icon_loader.get_icon_cache_key", side_effect=AssertionError("should not recompute")):
            with patch.object(icon_loader, "_get_icon_from_path", return_value="cached-icon") as get_icon_mock:
                icon = icon_loader.get_icon(tool, theme_name="dark_green")

        self.assertEqual("cached-icon", icon)
        get_icon_mock.assert_called_once_with(str(self.workspace / "cached-icon.png"), theme_name="dark_green")

    def test_get_icon_from_missing_path_uses_theme_default_icon(self):
        missing_icon = str(self.workspace / "missing-github.png")

        with patch.object(icon_loader, "_get_default_icon", return_value="theme-default") as default_icon_mock:
            icon = icon_loader._get_icon_from_path(missing_icon, theme_name="dark_green")

        self.assertEqual("theme-default", icon)
        default_icon_mock.assert_called_once_with("dark_green")


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from core.icon_resolution_service import IconResolutionService, IconSource


class IconResolutionServiceTests(unittest.TestCase):
    def setUp(self):
        self.workspace = make_test_dir(f"icon_resolution_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.workspace))
        self.service = IconResolutionService()

    def test_resolves_custom_icon_source(self):
        custom_icon = self.workspace / "custom.png"
        custom_icon.write_bytes(b"png")

        with patch("core.icon_resolution_service.resolve_icon_path_value", return_value=custom_icon):
            result = self.service.resolve({"icon": "custom.png"})

        self.assertEqual(IconSource.CUSTOM, result.source)
        self.assertEqual(str(custom_icon), result.path)

    def test_resolves_known_registry_source(self):
        registry_icon = self.workspace / "nmap.png"
        registry_icon.write_bytes(b"png")

        with patch("core.icon_resolution_service.resolve_cached_auto_icon_path", return_value=""):
            with patch("core.icon_resolution_service.resolve_known_tool_icon_path", return_value=str(registry_icon)):
                result = self.service.resolve({"name": "Nmap", "path": "nmap", "icon": "default_icon"})

        self.assertEqual(IconSource.KNOWN_REGISTRY, result.source)
        self.assertEqual(str(registry_icon), result.path)

    def test_resolves_sidecar_source(self):
        sidecar_icon = self.workspace / "logo.png"
        sidecar_icon.write_bytes(b"png")

        with patch("core.icon_resolution_service.resolve_cached_auto_icon_path", return_value=""):
            with patch("core.icon_resolution_service.resolve_known_tool_icon_path", return_value=""):
                with patch("core.icon_resolution_service.resolve_local_sidecar_icon_path", return_value=str(sidecar_icon)):
                    result = self.service.resolve({"path": str(self.workspace / "tool.exe")})

        self.assertEqual(IconSource.SIDECAR, result.source)
        self.assertEqual(str(sidecar_icon), result.path)

    def test_resolves_web_favicon_source_from_auto_cache(self):
        cached = str(self.workspace / "auto_cache" / "web" / "example.ico")

        with patch("core.icon_resolution_service.resolve_cached_auto_icon_path", return_value=cached):
            result = self.service.resolve({"path": "https://example.com", "is_web_tool": True})

        self.assertEqual(IconSource.WEB_FAVICON, result.source)
        self.assertEqual(cached, result.path)

    def test_pinned_missing_icon_reports_failed(self):
        with patch("core.icon_resolution_service.resolve_icon_path_value", return_value=None):
            result = self.service.resolve({"icon": "missing.png", "icon_pinned": True})

        self.assertEqual(IconSource.FAILED, result.source)
        self.assertTrue(result.pinned)

    def test_pin_icon_marks_tool(self):
        icon_path = self.workspace / "pin.png"
        icon_path.write_bytes(b"png")
        tool = {}

        self.service.pin_icon(tool, str(icon_path))

        self.assertEqual(str(icon_path), tool["icon"])
        self.assertTrue(tool["icon_pinned"])

    def test_clear_cache_returns_cache_dir(self):
        with patch("core.icon_resolution_service.ensure_runtime_dir", return_value=self.workspace / "cache"):
            cache_dir = self.service.clear_cache(include_files=False)

        self.assertEqual(str(self.workspace / "cache"), cache_dir)


if __name__ == "__main__":
    unittest.main()

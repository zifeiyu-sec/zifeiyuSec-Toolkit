import unittest
from unittest.mock import patch

from core.native_title_bar import (
    DWMWA_BORDER_COLOR,
    DWMWA_CAPTION_COLOR,
    DWMWA_TEXT_COLOR,
    DWMWA_USE_IMMERSIVE_DARK_MODE,
    _hex_to_colorref,
    apply_native_title_bar_theme,
    resolve_title_bar_colors,
)


class NativeTitleBarTests(unittest.TestCase):
    def test_resolve_title_bar_colors_follows_theme(self):
        celadon = resolve_title_bar_colors("celadon_mist")
        self.assertEqual("#cceeee", celadon["caption"])
        self.assertEqual("#104c52", celadon["text"])
        self.assertFalse(celadon["dark"])

        purple = resolve_title_bar_colors("purple_neon")
        self.assertTrue(purple["dark"])
        self.assertEqual("#160322", purple["caption"])

    def test_hex_to_colorref_uses_windows_bgr_order(self):
        self.assertEqual(0x563412, _hex_to_colorref("#123456"))

    def test_apply_native_title_bar_theme_sets_dwm_attributes(self):
        class FakeWindow:
            def winId(self):
                return 12345

        calls = []

        def fake_set_attribute(hwnd, attribute, value):
            calls.append((hwnd, attribute, value))
            return True

        with patch("core.native_title_bar.sys.platform", "win32"):
            with patch("core.native_title_bar._set_dwm_attribute", side_effect=fake_set_attribute):
                applied = apply_native_title_bar_theme(FakeWindow(), "celadon_mist")

        self.assertTrue(applied)
        self.assertIn((12345, DWMWA_USE_IMMERSIVE_DARK_MODE, 0), calls)
        self.assertIn((12345, DWMWA_CAPTION_COLOR, _hex_to_colorref("#cceeee")), calls)
        self.assertIn((12345, DWMWA_TEXT_COLOR, _hex_to_colorref("#104c52")), calls)
        self.assertIn((12345, DWMWA_BORDER_COLOR, _hex_to_colorref("#89dcdf")), calls)


if __name__ == "__main__":
    unittest.main()

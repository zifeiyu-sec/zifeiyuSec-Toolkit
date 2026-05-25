import unittest

from core.style_manager import ThemeManager


class ThemeManagerTests(unittest.TestCase):
    def test_celadon_mist_theme_is_registered_with_core_fragments(self):
        manager = ThemeManager()

        self.assertIn("celadon_mist", manager.themes)
        self.assertEqual("青碧国风主题", manager.themes["celadon_mist"]["name"])

        style = manager.get_theme_style("celadon_mist")
        self.assertIn("QWidget#windowCanvas", style)
        self.assertIn("background-image: url(", style)
        self.assertIn("国风.png", style)

        self.assertTrue(manager.get_category_view_style("celadon_mist"))
        self.assertTrue(manager.get_dialog_style("celadon_mist"))
        self.assertTrue(manager.get_messagebox_style("celadon_mist"))

    def test_celadon_mist_theme_reuses_dialog_and_messagebox_fragments(self):
        manager = ThemeManager()

        dialog_style = manager.get_dialog_style("celadon_mist")
        self.assertIn("QDialog { background-color: #e7f6f5; }", dialog_style)
        self.assertIn("QLineEdit, QTextEdit, QComboBox, QSpinBox", dialog_style)

        messagebox_style = manager.get_messagebox_style("celadon_mist")
        self.assertIn("QMessageBox", messagebox_style)
        self.assertIn("QPushButton:hover", messagebox_style)

    def test_blue_white_theme_exposes_dark_glass_layout_fragments(self):
        manager = ThemeManager()

        self.assertIn("blue_white", manager.themes)

        style = manager.get_theme_style("blue_white")
        self.assertIn("QWidget#windowCanvas", style)
        self.assertIn("blue_white.png", style)
        self.assertIn("QWidget#contentPanel", style)
        self.assertIn("QScrollBar:vertical", style)

        self.assertTrue(manager.get_category_view_style("blue_white"))
        self.assertTrue(manager.get_dialog_style("blue_white"))
        self.assertTrue(manager.get_messagebox_style("blue_white"))

    def test_dark_green_theme_uses_generated_background(self):
        manager = ThemeManager()

        self.assertIn("dark_green", manager.themes)
        self.assertEqual("黑客矩阵主题", manager.themes["dark_green"]["name"])

        style = manager.get_theme_style("dark_green")
        self.assertIn("QWidget#windowCanvas", style)
        self.assertIn("\u9ed1\u5ba2.png", style)
        self.assertIn("QWidget#contentPanel", style)
        self.assertIn("QScrollBar:vertical", style)

        self.assertTrue(manager.get_category_view_style("dark_green"))
        self.assertTrue(manager.get_dialog_style("dark_green"))
        self.assertTrue(manager.get_messagebox_style("dark_green"))

    def test_purple_neon_theme_exposes_acrylic_layout_fragments(self):
        manager = ThemeManager()

        self.assertIn("purple_neon", manager.themes)

        style = manager.get_theme_style("purple_neon")
        self.assertIn("QWidget#windowCanvas", style)
        self.assertIn("\u7d2b\u91d1.png", style)
        self.assertIn("QScrollBar:vertical", style)

        self.assertTrue(manager.get_category_view_style("purple_neon"))
        self.assertTrue(manager.get_dialog_style("purple_neon"))
        self.assertTrue(manager.get_messagebox_style("purple_neon"))

    def test_red_orange_theme_exposes_acrylic_layout_fragments(self):
        manager = ThemeManager()

        self.assertIn("red_orange", manager.themes)

        style = manager.get_theme_style("red_orange")
        self.assertIn("QWidget#windowCanvas", style)
        self.assertIn("\u7ea2\u8272.png", style)
        self.assertIn("QScrollBar:vertical", style)

        self.assertTrue(manager.get_category_view_style("red_orange"))
        self.assertTrue(manager.get_dialog_style("red_orange"))
        self.assertTrue(manager.get_messagebox_style("red_orange"))


if __name__ == "__main__":
    unittest.main()

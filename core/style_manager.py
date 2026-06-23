# -*- coding: utf-8 -*-
"""
主题样式管理器
集中管理应用程序的所有主题样式，避免重复代码
"""
from pathlib import Path


class ThemeManager:
    """主题样式管理器"""
    _themes_cache = None

    def __init__(self):
        """初始化主题管理器"""
        if ThemeManager._themes_cache is None:
            ThemeManager._themes_cache = {
                "dark_green": {
                    "name": "黑客矩阵主题",
                    "styles": self._get_dark_green_styles(),
                    "messagebox": self._get_dark_green_messagebox_style(),
                    "toolcard": self._get_dark_green_toolcard_style(),
                    "category_view": self._get_dark_green_category_style(),
                    "dialog": self._get_dark_green_dialog_style()
                },
                "blue_white": {
                    "name": "蓝白主题",
                    "styles": self._get_blue_white_styles(),
                    "messagebox": self._get_blue_white_messagebox_style(),
                    "toolcard": self._get_blue_white_toolcard_style(),
                    "category_view": self._get_blue_white_category_style(),
                    "dialog": self._get_blue_white_dialog_style()
                },
                "celadon_mist": {
                    "name": "青碧国风主题",
                    "styles": self._get_celadon_mist_styles(),
                    "messagebox": self._get_celadon_mist_messagebox_style(),
                    "toolcard": self._get_celadon_mist_toolcard_style(),
                    "category_view": self._get_celadon_mist_category_style(),
                    "dialog": self._get_celadon_mist_dialog_style()
                },
                "purple_neon": {
                    "name": "紫霓主题",
                    "styles": self._get_purple_neon_styles(),
                    "messagebox": self._get_purple_neon_messagebox_style(),
                    "toolcard": self._get_purple_neon_toolcard_style(),
                    "category_view": self._get_purple_neon_category_style(),
                    "dialog": self._get_purple_neon_dialog_style()
                },
                "red_orange": {
                    "name": "红橙主题",
                    "styles": self._get_red_orange_styles(),
                    "messagebox": self._get_red_orange_messagebox_style(),
                    "toolcard": self._get_red_orange_toolcard_style(),
                    "category_view": self._get_red_orange_category_style(),
                    "dialog": self._get_red_orange_dialog_style()
                }
            }
        self.themes = ThemeManager._themes_cache
    
    def get_theme_style(self, theme_name):
        """获取主题样式
        
        Args:
            theme_name: 主题名称
            
        Returns:
            主题样式字符串，如果主题不存在返回默认主题样式
        """
        # 返回完整样式，包含主样式、消息框样式与工具卡片样式，
        # 以保证对话框、弹出列表等也能正确继承主题配色。
        theme = self.themes.get(theme_name, self.themes["dark_green"])
        parts = [theme.get('styles', ''), theme.get('messagebox', ''), theme.get('toolcard', '')]
        return "\n".join(parts)

    def get_category_view_style(self, theme_name):
        """获取分类视图样式"""
        return self.themes.get(theme_name, self.themes["dark_green"]).get('category_view', '')

    def get_dialog_style(self, theme_name):
        """获取对话框样式"""
        return self.themes.get(theme_name, self.themes["dark_green"]).get('dialog', '')
    
    def get_messagebox_style(self, theme_name):
        """获取消息框样式
        
        Args:
            theme_name: 主题名称
            
        Returns:
            消息框样式字符串，如果主题不存在返回默认主题样式
        """
        return self.themes.get(theme_name, self.themes["dark_green"])['messagebox']
    
    def get_toolcard_style(self, theme_name):
        """获取工具卡片样式
        
        Args:
            theme_name: 主题名称
            
        Returns:
            工具卡片样式字符串，如果主题不存在返回默认主题样式
        """
        return self.themes.get(theme_name, self.themes["dark_green"])['toolcard']

    def get_dialog_list_palette(self, theme_name):
        """Return shared palette tokens for list-heavy dialogs."""
        palettes = {
            "blue_white": {
                "bg": "#edf8fc",
                "text": "#29445f",
                "muted": "#5f7890",
                "panel": "rgba(255,255,255,0.62)",
                "item": "rgba(255,255,255,0.54)",
                "border": "rgba(255,255,255,0.78)",
                "hover": "rgba(246,253,255,0.98)",
                "selected": "rgba(184,241,250,0.72)",
                "success": "#1f7a5b",
            },
            "celadon_mist": {
                "bg": "#eef6f3",
                "text": "#333333",
                "muted": "#58716a",
                "panel": "rgba(255,255,255,0.42)",
                "item": "rgba(255,255,255,0.54)",
                "border": "rgba(255,255,255,0.52)",
                "hover": "rgba(245,251,248,0.86)",
                "selected": "rgba(174,220,214,0.26)",
                "success": "#2f7d68",
            },
            "purple_neon": {
                "bg": "rgba(8,2,13,0.98)",
                "text": "#ffe6a3",
                "muted": "#d9b76d",
                "panel": "rgba(13,2,22,0.42)",
                "item": "rgba(45,7,67,0.34)",
                "border": "rgba(255,207,92,0.44)",
                "hover": "rgba(189,58,255,0.30)",
                "selected": "rgba(255,207,92,0.30)",
                "success": "#ffe893",
            },
            "red_orange": {
                "bg": "rgba(22,0,0,0.98)",
                "text": "#ffe6b0",
                "muted": "#e1b575",
                "panel": "rgba(45,0,0,0.46)",
                "item": "rgba(70,0,0,0.34)",
                "border": "rgba(255,198,72,0.42)",
                "hover": "rgba(255,66,38,0.26)",
                "selected": "rgba(255,98,131,0.24)",
                "success": "#ffd260",
            },
            "dark_green": {
                "bg": "rgba(16,39,29,0.98)",
                "text": "#ecfff2",
                "muted": "#acd3bd",
                "panel": "rgba(247,255,250,0.08)",
                "item": "rgba(247,255,250,0.07)",
                "border": "rgba(233,255,240,0.16)",
                "hover": "rgba(247,255,250,0.16)",
                "selected": "rgba(123,240,181,0.26)",
                "success": "#7df1b7",
            },
        }
        return dict(palettes.get(theme_name, palettes["dark_green"]))

    def get_dialog_list_style(self, theme_name):
        """Shared style for virtual list dialogs."""
        palette = self.get_dialog_list_palette(theme_name)
        return f"""
            QDialog {{
                background: {palette['bg']};
                color: {palette['text']};
            }}
            QLabel {{
                color: {palette['text']};
            }}
            QLabel#titleLabel,
            QLabel#dashboardSectionTitle {{
                font-size: 16px;
                font-weight: 600;
            }}
            QLabel#hintLabel,
            QLabel#summaryLabel,
            QLabel#dashboardEmptyLabel {{
                color: {palette['muted']};
            }}
            QLineEdit, QComboBox {{
                background: {palette['panel']};
                color: {palette['text']};
                border: 1px solid {palette['border']};
                border-radius: 14px;
                padding: 8px 11px;
                selection-background-color: {palette['selected']};
            }}
            QLineEdit:focus, QComboBox:focus {{
                background: {palette['hover']};
                border-color: {palette['selected']};
            }}
            QComboBox QAbstractItemView {{
                background: {palette['bg']};
                color: {palette['text']};
                border: 1px solid {palette['border']};
                selection-background-color: {palette['selected']};
            }}
            QListView {{
                background: {palette['panel']};
                color: {palette['text']};
                border: 1px solid {palette['border']};
                border-radius: 18px;
                padding: 8px;
                outline: none;
            }}
            QListView::item {{
                background: {palette['item']};
                border: 1px solid {palette['border']};
                border-radius: 12px;
                padding: 9px 11px;
                margin-bottom: 6px;
            }}
            QListView::item:hover {{
                background: {palette['hover']};
            }}
            QListView::item:selected {{
                background: {palette['selected']};
            }}
            QPushButton {{
                background: {palette['panel']};
                color: {palette['text']};
                border: 1px solid {palette['border']};
                border-radius: 12px;
                padding: 7px 12px;
            }}
            QPushButton:hover {{
                background: {palette['hover']};
            }}
            QPushButton:disabled {{
                color: {palette['muted']};
            }}
            QPushButton#dangerButton {{
                background: rgba(214, 72, 72, 0.22);
                border-color: rgba(238, 118, 118, 0.58);
            }}
            QPushButton#dangerButton:hover {{
                background: rgba(214, 72, 72, 0.34);
            }}
        """

    def get_dashboard_style(self, theme_name):
        """Shared dashboard wrapper style."""
        palette = self.get_dialog_list_palette(theme_name)
        return f"""
            QWidget {{
                color: {palette['text']};
                background: transparent;
            }}
            QScrollArea#dashboardScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea#dashboardScrollArea > QWidget {{
                background: transparent;
            }}
            QWidget#dashboardPage {{
                background: transparent;
            }}
            QLabel#dashboardSectionTitle {{
                color: {palette['text']};
                font-size: 16px;
                font-weight: 700;
                padding-left: 4px;
            }}
            QLabel#dashboardEmptyLabel {{
                color: {palette['muted']};
                background: {palette['panel']};
                border: 1px solid {palette['border']};
                border-radius: 14px;
                padding: 14px 16px;
            }}
        """

    def get_context_menu_style(self, theme_name):
        """Shared theme style for transient context menus."""
        palette = self.get_dialog_list_palette(theme_name)
        return f"""
            QMenu {{
                background: {palette['bg']};
                color: {palette['text']};
                border: 1px solid {palette['border']};
                border-radius: 14px;
                padding: 7px;
            }}
            QMenu::item {{
                background: transparent;
                color: {palette['text']};
                border-radius: 9px;
                padding: 7px 18px;
            }}
            QMenu::item:selected {{
                background: {palette['selected']};
                color: {palette['text']};
            }}
            QMenu::item:disabled {{
                color: {palette['muted']};
            }}
            QMenu::separator {{
                height: 1px;
                margin: 6px 9px;
                background: {palette['border']};
            }}
        """

    def get_toast_style(self, theme_name, kind="info"):
        """Shared non-blocking toast style."""
        palette = self.get_dialog_list_palette(theme_name)
        accent = palette["success"] if kind == "success" else palette["selected"]
        return f"""
            QFrame#toastFrame {{
                background: {palette['panel']};
                border: 1px solid {accent};
                border-radius: 14px;
            }}
            QLabel#toastTitle {{
                color: {palette['text']};
                font-size: 13px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
            QLabel#toastMessage {{
                color: {palette['muted']};
                font-size: 12px;
                background: transparent;
                border: none;
            }}
        """

    def get_home_nav_button_style(self, theme_name):
        """Prominent toolbar navigation button style for each theme."""
        palettes = {
            "dark_green": {
                "bg": "rgba(0, 255, 65, 0.18)",
                "bg2": "rgba(0, 229, 255, 0.10)",
                "hover": "rgba(0, 255, 65, 0.28)",
                "pressed": "rgba(0, 255, 65, 0.36)",
                "border": "rgba(0, 255, 65, 0.88)",
                "text": "#00ff41",
                "glow": "rgba(0, 229, 255, 0.58)",
            },
            "blue_white": {
                "bg": "rgba(72, 145, 244, 0.22)",
                "bg2": "rgba(184, 241, 250, 0.42)",
                "hover": "rgba(72, 145, 244, 0.32)",
                "pressed": "rgba(44, 113, 206, 0.38)",
                "border": "rgba(72, 145, 244, 0.82)",
                "text": "#163f73",
                "glow": "rgba(255, 255, 255, 0.82)",
            },
            "celadon_mist": {
                "bg": "rgba(16, 142, 150, 0.22)",
                "bg2": "rgba(174, 220, 214, 0.42)",
                "hover": "rgba(16, 142, 150, 0.32)",
                "pressed": "rgba(16, 116, 124, 0.36)",
                "border": "rgba(16, 142, 150, 0.78)",
                "text": "#0f5f66",
                "glow": "rgba(240, 255, 255, 0.82)",
            },
            "purple_neon": {
                "bg": "rgba(255, 207, 92, 0.24)",
                "bg2": "rgba(189, 58, 255, 0.22)",
                "hover": "rgba(255, 207, 92, 0.34)",
                "pressed": "rgba(255, 207, 92, 0.42)",
                "border": "rgba(255, 232, 147, 0.90)",
                "text": "#fff0b8",
                "glow": "rgba(189, 58, 255, 0.62)",
            },
            "red_orange": {
                "bg": "rgba(255, 205, 92, 0.22)",
                "bg2": "rgba(255, 66, 38, 0.24)",
                "hover": "rgba(255, 205, 92, 0.34)",
                "pressed": "rgba(255, 98, 56, 0.40)",
                "border": "rgba(255, 232, 147, 0.90)",
                "text": "#fff4c7",
                "glow": "rgba(255, 86, 48, 0.58)",
            },
        }
        palette = palettes.get(theme_name, palettes["dark_green"])
        return f"""
            QToolButton#homeNavButton {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 {palette['bg']},
                    stop: 1 {palette['bg2']}
                );
                color: {palette['text']};
                border: 1px solid {palette['border']};
                border-bottom: 2px solid {palette['glow']};
                border-radius: 16px;
                padding: 10px 22px;
                font-size: 14px;
                font-weight: 800;
            }}
            QToolButton#homeNavButton:hover {{
                background: {palette['hover']};
                border-color: {palette['glow']};
            }}
            QToolButton#homeNavButton:pressed {{
                background: {palette['pressed']};
                padding-top: 11px;
                padding-bottom: 9px;
            }}
        """

    def _asset_qss_url(self, relative_path):
        """返回可用于 QSS url() 的绝对路径。"""
        return (Path(__file__).resolve().parents[1] / relative_path).as_posix()

    def _get_dark_green_styles(self):
        """获取黑客矩阵主题样式"""
        background_url = self._asset_qss_url("images/background/\u9ed1\u5ba2.png")
        return """
            QMainWindow {
                background-color: #0a0e0f;
                border: none;
            }

            QWidget#windowCanvas {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #0d1514,
                    stop: 0.34 #07100f,
                    stop: 0.70 #0a1512,
                    stop: 1 #030606
                );
                background-image: url(%s);
                background-position: center center;
                background-repeat: no-repeat;
                border: 1px solid rgba(0, 255, 65, 0.24);
                border-right: 1px solid rgba(255, 51, 102, 0.34);
                border-bottom: 1px solid rgba(255, 51, 102, 0.26);
                border-radius: 28px;
            }

            QMenuBar {
                background: rgba(243, 255, 247, 0.04);
                color: #eefef3;
                border: none;
                border-bottom: 1px solid rgba(233, 255, 240, 0.12);
            }

            QMenuBar::item {
                padding: 6px 12px;
                margin: 4px 2px;
                border-radius: 10px;
            }

            QMenuBar::item:selected {
                background: rgba(243, 255, 247, 0.10);
                color: #fff3c7;
            }

            QMenu {
                background: rgba(5, 12, 11, 0.96);
                color: #d8fbe2;
                border: 1px solid rgba(0, 255, 65, 0.22);
                border-radius: 16px;
                padding: 8px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 10px;
            }

            QMenu::item:selected {
                background: rgba(0, 255, 65, 0.16);
                color: #00ff41;
            }

            QMenu::separator {
                height: 1px;
                margin: 6px 10px;
                background: rgba(214, 255, 226, 0.12);
            }

            QToolBar {
                background-color: rgba(5, 8, 10, 0.46);
                border: 1px solid rgba(0, 255, 65, 0.34);
                border-right: 1px solid rgba(255, 51, 102, 0.20);
                border-radius: 22px;
                margin: 6px 6px 0 6px;
                padding: 12px 16px;
                spacing: 12px;
            }

            QToolBar::separator {
                background: rgba(214, 255, 226, 0.12);
                width: 1px;
                margin: 8px 10px;
            }

            QToolButton {
                background: rgba(5, 18, 18, 0.50);
                border: 1px solid rgba(0, 229, 255, 0.34);
                padding: 9px 18px;
                border-radius: 15px;
                color: #9deec0;
                font-weight: 600;
                font-size: 13px;
            }

            QToolButton:hover {
                background: rgba(0, 45, 27, 0.62);
                border: 1px solid rgba(0, 255, 65, 0.88);
                color: #00ff41;
            }

            QToolButton:pressed {
                background: rgba(0, 255, 65, 0.18);
                border-color: rgba(0, 255, 65, 0.88);
                color: #eaffef;
            }

            QStatusBar {
                background: rgba(5, 8, 10, 0.50);
                border: 1px solid rgba(0, 255, 65, 0.18);
                border-radius: 18px;
                color: #ff8c00;
                font-size: 12px;
            }

            QStatusBar::item {
                border: none;
            }

            QSplitter {
                background: transparent;
            }

            QSplitter::handle {
                background: rgba(202, 247, 221, 0.08);
                width: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }

            QSplitter::handle:hover {
                background: rgba(125, 241, 183, 0.20);
            }

            QLineEdit {
                background: rgba(5, 18, 18, 0.56);
                border: 1px solid rgba(13, 115, 119, 0.72);
                border-radius: 16px;
                padding: 10px 14px;
                color: #00e676;
                font-size: 13px;
                selection-background-color: rgba(0, 255, 65, 0.28);
            }

            QLineEdit:focus {
                border: 1px solid rgba(0, 255, 65, 0.72);
                background: rgba(5, 22, 18, 0.68);
                outline: none;
            }

            QPushButton:disabled,
            QLineEdit:disabled {
                color: rgba(190, 225, 202, 0.46);
            }

            QPushButton {
                background: rgba(5, 18, 18, 0.50);
                border: 1px solid rgba(0, 229, 255, 0.34);
                border-radius: 14px;
                padding: 9px 16px;
                color: #9fcbb2;
                font-weight: 600;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(0, 45, 27, 0.62);
                border: 1px solid rgba(0, 255, 65, 0.88);
                color: #00ff41;
            }

            QPushButton:pressed {
                background: rgba(0, 255, 65, 0.16);
                border-color: rgba(0, 255, 65, 0.82);
            }

            QPushButton:default {
                border: 1px solid rgba(0, 255, 65, 0.68);
                background: rgba(0, 255, 65, 0.18);
                color: #00ff41;
            }

            QGroupBox {
                background: rgba(247, 255, 250, 0.05);
                border: 1px solid rgba(233, 255, 240, 0.12);
                border-radius: 18px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #eefef3;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            QLabel {
                color: #e9fbef;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 14px;
                font-weight: 700;
                color: #00ff41;
            }

            QLabel#contentModeLabel {
                color: #00e5ff;
                font-size: 12px;
                padding: 5px 12px;
                background: rgba(15, 42, 47, 0.72);
                border: 1px solid rgba(0, 229, 255, 0.38);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(5, 20, 22, 0.30),
                    stop: 0.52 rgba(2, 12, 14, 0.22),
                    stop: 1 rgba(0, 6, 8, 0.34)
                );
                border: 1px solid rgba(0, 229, 255, 0.34);
                border-right: 1px solid rgba(255, 51, 102, 0.22);
                border-bottom: 1px solid rgba(255, 51, 102, 0.16);
                border-radius: 28px;
            }

            QWidget#contentInfoBar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(0, 45, 40, 0.42),
                    stop: 1 rgba(0, 14, 16, 0.34)
                );
                border: 1px solid rgba(0, 255, 65, 0.52);
                border-right: 1px solid rgba(255, 51, 102, 0.24);
                border-radius: 18px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            QTextEdit,
            QPlainTextEdit {
                background: rgba(247, 255, 250, 0.08);
                border: 1px solid rgba(233, 255, 240, 0.14);
                border-radius: 16px;
                padding: 10px;
                color: #effff5;
                font-size: 13px;
                selection-background-color: rgba(109, 233, 174, 0.36);
            }

            QTextEdit:focus,
            QPlainTextEdit:focus {
                border: 1px solid rgba(121, 239, 181, 0.60);
                background: rgba(247, 255, 250, 0.12);
            }

            QComboBox {
                background: rgba(247, 255, 250, 0.08);
                color: #effff5;
                border: 1px solid rgba(233, 255, 240, 0.14);
                border-radius: 14px;
                padding: 8px 12px;
            }

            QComboBox::drop-down {
                border: none;
                width: 18px;
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #e7fbef;
                selection-background-color: rgba(149, 247, 195, 0.34);
                selection-color: #fff3c7;
            }

            QComboBox QAbstractItemView {
                background: rgba(18, 41, 31, 0.97);
                color: #ecfff2;
                border: 1px solid rgba(233, 255, 240, 0.16);
                selection-background-color: rgba(125, 241, 183, 0.24);
            }

            QScrollBar:vertical {
                background: rgba(26, 46, 51, 0.44);
                width: 8px;
                margin: 4px 0 4px 0;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical {
                background: rgba(0, 255, 65, 0.34);
                min-height: 30px;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(0, 255, 65, 0.66);
            }

            QScrollBar:horizontal {
                background: rgba(26, 46, 51, 0.44);
                height: 8px;
                margin: 0 4px 0 4px;
                border-radius: 4px;
            }

            QScrollBar::handle:horizontal {
                background: rgba(0, 255, 65, 0.34);
                min-width: 30px;
                border-radius: 4px;
            }

            QScrollBar::handle:horizontal:hover {
                background: rgba(0, 255, 65, 0.66);
            }

            QScrollBar::add-line,
            QScrollBar::sub-line,
            QScrollBar::add-page,
            QScrollBar::sub-page {
                border: none;
                background: transparent;
            }

            QInputDialog, QDialog, QProgressDialog {
                background-color: rgba(16, 39, 29, 0.98);
                color: #ecfff2;
            }""" % background_url
    
    def _get_blue_white_styles(self):
        """获取蓝白主题样式"""
        background_url = self._asset_qss_url("images/background/blue_white.png")
        return """
            QMainWindow {
                background-color: #d8eff6;
                border: none;
            }

            QWidget#windowCanvas {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f6fdff,
                    stop: 0.34 #e4f7fb,
                    stop: 0.72 #eaf4ff,
                    stop: 1 #c7eaf4
                );
                background-image: url(%s);
                background-position: center center;
                background-repeat: no-repeat;
                border: 1px solid rgba(255, 255, 255, 0.86);
                border-radius: 28px;
            }

            QMenuBar {
                background: rgba(255, 255, 255, 0.34);
                color: #203b56;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.50);
            }

            QMenuBar::item {
                padding: 6px 12px;
                margin: 4px 2px;
                border-radius: 10px;
            }

            QMenuBar::item:selected {
                background: rgba(255, 255, 255, 0.62);
                color: #17334c;
            }

            QMenu {
                background: rgba(241, 247, 253, 0.94);
                color: #2a4563;
                border: 1px solid rgba(228, 240, 252, 0.88);
                border-radius: 16px;
                padding: 8px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 10px;
            }

            QMenu::item:selected {
                background: rgba(214, 235, 253, 0.74);
            }

            QMenu::separator {
                height: 1px;
                margin: 6px 10px;
                background: rgba(181, 208, 232, 0.26);
            }

            QToolBar {
                background-color: rgba(232, 248, 255, 0.30);
                border: 1px solid rgba(151, 213, 244, 0.50);
                border-radius: 22px;
                margin: 6px 6px 0 6px;
                padding: 12px 16px;
                spacing: 12px;
            }

            QToolBar::separator {
                background: rgba(98, 144, 174, 0.18);
                width: 1px;
                margin: 8px 10px;
            }

            QToolButton {
                background: rgba(232, 248, 255, 0.64);
                border: 1px solid rgba(151, 213, 244, 0.58);
                padding: 9px 18px;
                border-radius: 15px;
                color: #2e4964;
                font-weight: 600;
                font-size: 13px;
            }

            QToolButton:hover {
                background: rgba(246, 253, 255, 0.86);
                border: 1px solid rgba(124, 203, 239, 0.62);
            }

            QToolButton:pressed {
                background: rgba(225, 240, 255, 0.88);
                border-color: rgba(127, 196, 244, 0.70);
            }

            QStatusBar {
                background: rgba(255, 255, 255, 0.34);
                border: 1px solid rgba(255, 255, 255, 0.62);
                border-radius: 18px;
                color: #35516e;
                font-size: 12px;
            }

            QStatusBar::item {
                border: none;
            }

            QSplitter {
                background: transparent;
            }

            QSplitter::handle {
                background: rgba(124, 170, 199, 0.12);
                width: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }

            QSplitter::handle:hover {
                background: rgba(89, 187, 231, 0.24);
            }

            QLineEdit {
                background: rgba(255, 255, 255, 0.62);
                border: 1px solid rgba(255, 255, 255, 0.78);
                border-radius: 16px;
                padding: 10px 14px;
                color: #31506c;
                font-size: 13px;
                selection-background-color: rgba(117, 199, 255, 0.36);
            }

            QLineEdit:focus {
                border: 1px solid rgba(108, 197, 238, 0.72);
                background: rgba(255, 255, 255, 0.86);
                outline: none;
            }

            QPushButton:disabled,
            QLineEdit:disabled {
                color: rgba(110, 130, 156, 0.54);
            }

            QPushButton {
                background: rgba(232, 248, 255, 0.64);
                border: 1px solid rgba(151, 213, 244, 0.58);
                border-radius: 14px;
                padding: 9px 16px;
                color: #2f4a66;
                font-weight: 600;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(246, 253, 255, 0.88);
                border: 1px solid rgba(124, 203, 239, 0.64);
            }

            QPushButton:pressed {
                background: rgba(224, 239, 252, 0.94);
                border-color: rgba(128, 193, 238, 0.72);
            }

            QPushButton:default {
                border: 1px solid rgba(137, 208, 255, 0.72);
                background: rgba(239, 248, 255, 0.84);
            }

            QGroupBox {
                background: rgba(230, 248, 255, 0.38);
                border: 1px solid rgba(151, 213, 244, 0.48);
                border-radius: 18px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #24425f;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            QLabel {
                color: #2f4d6b;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 14px;
                font-weight: 700;
                color: #17334c;
            }

            QLabel#contentModeLabel {
                color: #4a87b8;
                font-size: 12px;
                padding: 5px 12px;
                background: rgba(230, 248, 255, 0.58);
                border: 1px solid rgba(151, 213, 244, 0.54);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(232, 249, 255, 0.36),
                    stop: 0.55 rgba(191, 232, 252, 0.24),
                    stop: 1 rgba(135, 207, 244, 0.18)
                );
                border: 1px solid rgba(151, 213, 244, 0.52);
                border-radius: 28px;
            }

            QWidget#contentInfoBar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(232, 249, 255, 0.58),
                    stop: 1 rgba(183, 229, 251, 0.36)
                );
                border: 1px solid rgba(151, 213, 244, 0.56);
                border-radius: 18px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            QTextEdit,
            QPlainTextEdit {
                background: rgba(255, 255, 255, 0.64);
                border: 1px solid rgba(255, 255, 255, 0.78);
                border-radius: 16px;
                padding: 10px;
                color: #31506c;
                font-size: 13px;
                selection-background-color: rgba(117, 199, 255, 0.36);
            }

            QTextEdit:focus,
            QPlainTextEdit:focus {
                border: 1px solid rgba(108, 197, 238, 0.72);
                background: rgba(255, 255, 255, 0.86);
            }

            QComboBox {
                background: rgba(255, 255, 255, 0.64);
                color: #31506c;
                border: 1px solid rgba(255, 255, 255, 0.78);
                border-radius: 14px;
                padding: 8px 12px;
            }

            QComboBox::drop-down {
                border: none;
                width: 18px;
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #2c4c68;
                selection-background-color: rgba(173, 240, 250, 0.58);
                selection-color: #17334c;
            }

            QComboBox QAbstractItemView {
                background: rgba(244, 249, 255, 0.98);
                color: #2a4563;
                border: 1px solid rgba(218, 231, 244, 0.84);
                selection-background-color: rgba(214, 235, 253, 0.80);
            }

            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.30);
                width: 11px;
                margin: 4px 0 4px 0;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: rgba(134, 177, 205, 0.42);
                min-height: 30px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(75, 174, 224, 0.58);
            }

            QScrollBar:horizontal {
                background: rgba(255, 255, 255, 0.30);
                height: 11px;
                margin: 0 4px 0 4px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal {
                background: rgba(134, 177, 205, 0.42);
                min-width: 30px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal:hover {
                background: rgba(75, 174, 224, 0.58);
            }

            QScrollBar::add-line,
            QScrollBar::sub-line,
            QScrollBar::add-page,
            QScrollBar::sub-page {
                border: none;
                background: transparent;
            }

            QInputDialog, QDialog, QProgressDialog {
                background-color: rgba(235, 247, 252, 0.98);
                color: #2a4563;
            }""" % background_url
    
    def _get_dark_green_messagebox_style(self):
        """获取黑客矩阵主题消息框样式"""
        return """
            QMessageBox {
                background: rgba(16, 39, 29, 0.98);
                color: #ecfff2;
            }
            QLabel {
                color: #ecfff2;
            }
            QPushButton {
                background-color: rgba(247, 255, 250, 0.08);
                color: #effff5;
                border: 1px solid rgba(233, 255, 240, 0.16);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(247, 255, 250, 0.14);
                border-color: rgba(125, 241, 183, 0.34);
            }"""

    def _get_blue_white_messagebox_style(self):
        """获取蓝白主题消息框样式"""
        return """
            QMessageBox {
                background: #edf8fc;
                color: #28435f;
            }
            QLabel {
                color: #28435f;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.84);
                color: #2d4864;
                border: 1px solid rgba(208, 225, 241, 0.82);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(243, 249, 255, 0.98);
                border-color: rgba(142, 214, 255, 0.76);
            }"""
    
    def _get_dark_green_toolcard_style(self):
        """获取黑客矩阵主题工具卡片样式"""
        return """
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(5, 20, 22, 0.42),
                    stop: 0.58 rgba(0, 24, 22, 0.34),
                    stop: 1 rgba(0, 6, 8, 0.48)
                );
                border: 1px solid rgba(0, 229, 255, 0.46);
                border-radius: 16px;
            }

            QLabel {
                color: #e0f2f1;
            }

            QPushButton {
                background-color: rgba(5, 18, 18, 0.50);
                border: 1px solid rgba(0, 229, 255, 0.38);
                border-radius: 12px;
                color: #9fcbb2;
            }

            QPushButton:hover {
                background-color: rgba(0, 45, 27, 0.62);
                border: 1px solid rgba(0, 255, 65, 0.88);
                color: #00ff41;
            }

            QPushButton:pressed {
                background-color: rgba(0, 255, 65, 0.16);
            }"""

    def _get_blue_white_toolcard_style(self):
        """获取蓝白主题工具卡片样式"""
        return """
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(238, 251, 255, 0.66),
                    stop: 0.58 rgba(199, 237, 253, 0.48),
                    stop: 1 rgba(145, 214, 247, 0.28)
                );
                border: 1px solid rgba(151, 213, 244, 0.62);
                border-radius: 16px;
            }

            QLabel {
                color: #27415d;
            }

            QPushButton {
                background-color: rgba(234, 249, 255, 0.78);
                border: 1px solid rgba(151, 213, 244, 0.58);
                border-radius: 12px;
                color: #2d4764;
            }

            QPushButton:hover {
                background-color: rgba(244, 249, 255, 0.98);
                border: 1px solid rgba(142, 214, 255, 0.74);
            }

            QPushButton:pressed {
                background-color: rgba(225, 238, 251, 0.96);
            }"""

    def _get_dark_green_category_style(self):
        """获取黑客矩阵主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
                outline: none;
            }

            QListWidget::item {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(0, 255, 65, 0.13),
                    stop: 0.48 rgba(0, 26, 22, 0.30),
                    stop: 1 rgba(0, 10, 12, 0.24)
                );
                border: 1px solid rgba(0, 255, 65, 0.58);
                border-right: 1px solid rgba(255, 51, 102, 0.20);
                border-left: 3px solid rgba(0, 255, 65, 0.74);
                border-radius: 8px;
                padding: 13px 14px;
                margin-bottom: 8px;
                color: #aeea00;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(0, 45, 27, 0.58);
                border-color: rgba(0, 255, 65, 0.92);
                border-right: 1px solid rgba(255, 51, 102, 0.34);
                color: #00ff41;
            }

            QListWidget::item:selected {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(0, 255, 65, 0.42),
                    stop: 1 rgba(0, 45, 27, 0.62)
                );
                color: #00ff41;
                border-color: rgba(0, 255, 65, 0.82);
                border-right: 1px solid rgba(255, 51, 102, 0.38);
                border-left: 3px solid #00ff41;
            }
        """

    def _get_blue_white_category_style(self):
        """获取蓝白主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
                outline: none;
            }

            QListWidget::item {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(235, 250, 255, 0.60),
                    stop: 0.62 rgba(198, 237, 253, 0.38),
                    stop: 1 rgba(148, 216, 248, 0.24)
                );
                border: 1px solid rgba(151, 213, 244, 0.56);
                border-radius: 16px;
                padding: 13px 14px;
                margin-bottom: 8px;
                color: #244b68;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(218, 245, 255, 0.72);
                border-color: rgba(103, 196, 238, 0.66);
            }

            QListWidget::item:selected {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(148, 239, 250, 0.76),
                    stop: 1 rgba(255, 255, 255, 0.66)
                );
                color: #153c5b;
                border-color: rgba(104, 206, 239, 0.78);
            }
        """

    def _get_dark_green_dialog_style(self):
        """获取黑客矩阵主题对话框样式"""
        return """
            QDialog { background-color: rgba(16,39,29,0.98); }
            QGroupBox {
                background-color: rgba(247,255,250,0.06);
                border: 1px solid rgba(233,255,240,0.16);
                border-radius: 18px;
                margin-top: 16px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                top: -2px;
                padding: 2px 10px 3px 10px;
                background-color: rgba(247,255,250,0.08);
                border: 1px solid rgba(233,255,240,0.18);
                border-radius: 10px;
                color: #ecfff2;
                font-weight: 600;
            }
            QLabel { color: #e8fbef; }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
                background: rgba(247,255,250,0.08);
                color: #effff5;
                border: 1px solid rgba(233,255,240,0.16);
                border-radius: 14px;
                padding: 7px 10px;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid rgba(121,239,181,0.62);
                background: rgba(247,255,250,0.12);
            }
            QPushButton {
                background-color: rgba(247,255,250,0.08);
                color: #effff5;
                border: 1px solid rgba(233,255,240,0.16);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(247,255,250,0.14);
                border-color: rgba(125,241,183,0.34);
            }
        """

    def _get_blue_white_dialog_style(self):
        """获取蓝白主题对话框样式"""
        return """
            QDialog { background-color: #edf8fc; }
            QGroupBox {
                background-color: rgba(255,255,255,0.56);
                border: 1px solid rgba(255,255,255,0.78);
                border-radius: 16px;
                margin-top: 16px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                top: -2px;
                padding: 2px 10px 3px 10px;
                background-color: rgba(255,255,255,0.92);
                border: 1px solid rgba(255,255,255,0.84);
                border-radius: 10px;
                color: #2d4864;
                font-weight: 600;
            }
            QLabel { color: #34516d; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background: rgba(255,255,255,0.72);
                color: #34516d;
                border: 1px solid rgba(255,255,255,0.78);
                border-radius: 14px;
                padding: 7px 10px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid rgba(108,197,238,0.74);
                background: rgba(255,255,255,0.94);
            }
            QPushButton {
                background-color: rgba(255,255,255,0.72);
                color: #2d4864;
                border: 1px solid rgba(255,255,255,0.78);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(246,253,255,0.96);
                border-color: rgba(108,197,238,0.76);
            }
        """

    def _get_celadon_mist_styles(self):
        """获取青碧国风轻科技主题样式"""
        background_url = self._asset_qss_url("images/background/国风.png")
        return f"""
            QMainWindow {{
                background-color: #bfe3e3;
                border: none;
            }}

            QWidget#windowCanvas {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #f8ffff,
                    stop: 0.24 #e7f8f7,
                    stop: 0.54 #cfeceb,
                    stop: 0.78 #a9d6d6,
                    stop: 1 #7fbec1
                );
                background-image: url({background_url});
                background-position: center center;
                background-repeat: no-repeat;
                border: 1px solid rgba(255, 255, 255, 0.84);
                border-radius: 30px;
            }}
            QMenuBar {{
                background: rgba(255, 255, 255, 0.12);
                color: #164d52;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.56);
            }}

            QMenuBar::item {{
                padding: 6px 11px;
                margin: 4px 2px;
                border-radius: 10px;
            }}

            QMenuBar::item:selected {{
                background: rgba(255, 255, 255, 0.44);
            }}

            QMenu {{
                background: rgba(240, 252, 251, 0.94);
                color: #164d52;
                border: 1px solid rgba(255, 255, 255, 0.86);
                border-radius: 18px;
                padding: 8px;
            }}

            QMenu::item {{
                padding: 8px 18px;
                border-radius: 10px;
            }}

            QMenu::item:selected {{
                background: rgba(20, 153, 160, 0.22);
            }}

            QToolBar {{
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.86);
                border-radius: 26px;
                margin: 10px 10px 0 10px;
                padding: 12px 18px;
                spacing: 12px;
            }}

            QToolButton {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(236, 255, 255, 0.74),
                    stop: 1 rgba(184, 237, 238, 0.48)
                );
                border: 1px solid rgba(152, 224, 226, 0.62);
                padding: 10px 18px;
                border-radius: 16px;
                color: #15545a;
                font-weight: 600;
                font-size: 13px;
            }}

            QToolButton:hover {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(255, 255, 255, 0.88),
                    stop: 1 rgba(205, 240, 240, 0.64)
                );
                border: 1px solid rgba(22, 151, 158, 0.44);
            }}

            QToolButton:pressed {{
                background: rgba(17, 142, 150, 0.32);
            }}

            QStatusBar {{
                background: rgba(255, 255, 255, 0.18);
                border: 1px solid rgba(255, 255, 255, 0.58);
                border-radius: 18px;
                color: #447174;
                font-size: 12px;
            }}

            QStatusBar::item {{
                border: none;
            }}

            QSplitter {{
                background: transparent;
            }}

            QSplitter::handle {{
                background: rgba(24, 130, 137, 0.12);
                width: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }}

            QSplitter::handle:hover {{
                background: rgba(24, 130, 137, 0.24);
            }}

            QLineEdit {{
                background: rgba(255, 255, 255, 0.62);
                border: 1px solid rgba(255, 255, 255, 0.88);
                border-radius: 15px;
                padding: 10px 14px;
                color: #164d52;
                font-size: 13px;
            }}

            QLineEdit:focus {{
                border: 1px solid rgba(16, 143, 151, 0.58);
                background: rgba(255, 255, 255, 0.84);
                outline: none;
            }}

            QPushButton {{
                background: rgba(255, 255, 255, 0.56);
                border: 1px solid rgba(255, 255, 255, 0.86);
                border-radius: 14px;
                padding: 9px 16px;
                color: #164d52;
                font-weight: 600;
                font-size: 13px;
            }}

            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.76);
                border: 1px solid rgba(22, 151, 158, 0.42);
            }}

            QPushButton:pressed {{
                background: rgba(17, 142, 150, 0.28);
            }}

            QPushButton:default {{
                border: 1px solid rgba(18, 150, 157, 0.54);
                background: rgba(25, 160, 166, 0.30);
                color: #0c555c;
            }}

            QGroupBox {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(228, 255, 255, 0.42),
                    stop: 0.58 rgba(184, 238, 239, 0.28),
                    stop: 1 rgba(107, 197, 202, 0.18)
                );
                border: 1px solid rgba(139, 220, 223, 0.52);
                border-radius: 22px;
                margin-top: 12px;
                padding: 18px;
            }}

            QGroupBox::title {{
                background: rgba(226, 255, 255, 0.78);
                color: #15545a;
                font-weight: 700;
                font-size: 14px;
                padding: 4px 12px 6px 12px;
                border: 1px solid rgba(142, 220, 223, 0.58);
                border-radius: 12px;
                margin-top: -12px;
            }}

            QLabel {{
                color: #164d52;
                font-size: 13px;
            }}

            QLabel#contentTitleLabel {{
                font-size: 14px;
                font-weight: 700;
                color: #0d6870;
            }}

            QLabel#contentModeLabel {{
                color: #356d70;
                font-size: 12px;
                padding: 5px 12px;
                background: rgba(222, 252, 252, 0.52);
                border: 1px solid rgba(144, 220, 223, 0.56);
                border-radius: 999px;
            }}

            QWidget#contentPanel {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                stop: 0 rgba(230, 255, 255, 0.24),
                stop: 0.55 rgba(178, 236, 237, 0.18),
                stop: 1 rgba(91, 188, 195, 0.14)
                );
                border: 1px solid rgba(141, 221, 224, 0.58);
                border-radius: 24px;
            }}
            QWidget#contentInfoBar {{
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(226, 255, 255, 0.36),
                    stop: 1 rgba(160, 230, 232, 0.22)
                );
                border: 1px solid rgba(139, 220, 223, 0.52);
                border-radius: 20px;
            }}
            QStackedWidget#contentStack {{
                background: transparent;
                border: none;
            }}

            QTextEdit {{
                background: rgba(255, 255, 255, 0.62);
                border: 1px solid rgba(255, 255, 255, 0.86);
                border-radius: 15px;
                padding: 10px;
                color: #164d52;
                font-size: 13px;
            }}

            QTextEdit:focus {{
                border: 1px solid rgba(16, 143, 151, 0.56);
                background: rgba(255, 255, 255, 0.84);
                outline: none;
            }}

            QComboBox {{
                background: rgba(255, 255, 255, 0.62);
                color: #164d52;
                border: 1px solid rgba(255, 255, 255, 0.86);
                border-radius: 20px;
                padding: 7px 12px;
            }}

            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}

            QListView, QTreeView, QTableView, QAbstractItemView {{
                background: transparent;
                color: #164d52;
                selection-background-color: rgba(17, 142, 150, 0.28);
                selection-color: #0d4f56;
            }}

            QComboBox QAbstractItemView {{
                background: rgba(240, 252, 251, 0.94);
                color: #164d52;
                border: 1px solid rgba(255, 255, 255, 0.84);
            }}

            QScrollBar:vertical {{
                background: rgba(255, 255, 255, 0.18);
                width: 10px;
                margin: 6px 2px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical {{
                background: rgba(17, 142, 150, 0.34);
                min-height: 28px;
                border-radius: 5px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: rgba(15, 124, 132, 0.50);
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar:horizontal, QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal, QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {{
                background: transparent;
                border: none;
                height: 0;
                width: 0;
            }}

            QInputDialog, QDialog, QProgressDialog {{
                background-color: #edf6f4;
                color: #333333;
            }}
        """

    def _get_celadon_mist_messagebox_style(self):
        """获取青碧国风主题消息框样式"""
        return """
            QMessageBox {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(255, 255, 255, 0.96),
                    stop: 1 rgba(230, 247, 246, 0.90)
                );
                color: #244d50;
                border: 1px solid rgba(255,255,255,0.78);
                border-radius: 20px;
            }
            QLabel {
                color: #244d50;
            }
            QPushButton {
                background-color: rgba(255,255,255,0.66);
                color: #244d50;
                border: 1px solid rgba(255,255,255,0.74);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(240,252,251,0.88);
                border-color: rgba(36,154,158,0.36);
            }
        """

    def _get_celadon_mist_toolcard_style(self):
        """获取青碧国风主题工具卡片样式"""
        return """
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(232, 255, 255, 0.64),
                    stop: 0.58 rgba(184, 239, 240, 0.46),
                    stop: 1 rgba(116, 207, 212, 0.28)
                );
                border: 1px solid rgba(137, 220, 223, 0.62);
                border-radius: 12px;
            }

            QLabel {
                color: #164d52;
            }

            QPushButton {
                background-color: rgba(226,255,255,0.62);
                border: 1px solid rgba(139,220,223,0.58);
                border-radius: 11px;
                color: #164d52;
            }

            QPushButton:hover {
                background-color: rgba(255,255,255,0.78);
                border-color: rgba(17,142,150,0.44);
            }

            QPushButton:pressed {
                background-color: rgba(17,142,150,0.28);
            }
        """

    def _get_celadon_mist_category_style(self):
        """获取青碧国风主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
            }

            QListWidget::item {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(224, 255, 255, 0.58),
                    stop: 0.62 rgba(177, 235, 236, 0.36),
                    stop: 1 rgba(123, 211, 216, 0.24)
                );
                border: 1px solid rgba(137, 220, 223, 0.58);
                border-radius: 18px;
                padding: 12px 14px;
                margin-bottom: 8px;
                color: #14565c;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(205, 250, 250, 0.68);
                border-color: rgba(17, 142, 150, 0.48);
            }

            QListWidget::item:selected {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(13, 137, 146, 0.88),
                    stop: 0.24 rgba(26, 164, 170, 0.58),
                    stop: 1 rgba(255, 255, 255, 0.46)
                );
                color: #083f46;
                border-color: rgba(255, 255, 255, 0.92);
            }
        """

    def _get_celadon_mist_dialog_style(self):
        """获取青碧国风主题对话框样式"""
        return """
            QDialog { background-color: #e7f6f5; }
            QGroupBox { background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 rgba(255,255,255,0.62), stop: 1 rgba(229,247,246,0.38)); border: 1px solid rgba(255,255,255,0.72); border-radius: 16px; margin-top: 8px; padding: 16px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 3px 10px 5px 10px; color: #17686c; font-weight: 700; background: rgba(255,255,255,0.82); border: 1px solid rgba(255,255,255,0.70); border-radius: 10px; }
            QLabel { color: #244d50; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox {
                background: rgba(255,255,255,0.66);
                color: #244d50;
                border: 1px solid rgba(255,255,255,0.72);
                border-radius: 11px;
                padding: 7px;
            }
            QPushButton {
                background-color: rgba(255,255,255,0.66);
                color: #244d50;
                border: 1px solid rgba(255,255,255,0.72);
                border-radius: 11px;
                padding: 7px 12px;
            }
            QPushButton:hover { background-color: rgba(240,252,251,0.88); border-color: rgba(36,154,158,0.36); }
        """

    def _get_purple_neon_styles(self):
        """获取紫霓（暗紫霓虹）主题样式"""
        background_url = self._asset_qss_url("images/background/紫金.png")
        return """
            QMainWindow {
                background-color: #08020d;
                border: none;
            }

            QWidget#windowCanvas {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #340647,
                    stop: 0.34 #12031b,
                    stop: 0.72 #2b073a,
                    stop: 1 #050008
                );
                background-image: url(%s);
                background-position: center center;
                background-repeat: no-repeat;
                border: 1px solid rgba(255, 207, 92, 0.56);
                border-radius: 28px;
            }

            QMenuBar {
                background: rgba(13, 2, 22, 0.36);
                color: #ffe6a3;
                border: none;
                border-bottom: 1px solid rgba(255, 207, 92, 0.36);
            }

            QMenuBar::item {
                padding: 6px 12px;
                margin: 4px 2px;
                border-radius: 10px;
            }

            QMenuBar::item:selected {
                background: rgba(255, 207, 92, 0.24);
                color: #fff0b8;
            }

            QMenu {
                background: rgba(12, 2, 20, 0.96);
                color: #ffe6a3;
                border: 1px solid rgba(255, 207, 92, 0.58);
                border-radius: 16px;
                padding: 8px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 10px;
            }

            QMenu::item:selected {
                background: rgba(189, 58, 255, 0.26);
                color: #fff0b8;
            }

            QMenu::separator {
                height: 1px;
                margin: 6px 10px;
                background: rgba(255, 207, 92, 0.38);
            }

            QToolBar {
                background-color: rgba(31, 4, 48, 0.42);
                border: 1px solid rgba(255, 207, 92, 0.52);
                border-radius: 22px;
                margin: 6px 6px 0 6px;
                padding: 12px 16px;
                spacing: 12px;
            }

            QToolBar::separator {
                background: rgba(255, 207, 92, 0.42);
                width: 1px;
                margin: 8px 10px;
            }

            QToolButton {
                background: rgba(45, 7, 67, 0.42);
                border: 1px solid rgba(255, 207, 92, 0.44);
                padding: 9px 18px;
                border-radius: 15px;
                color: #ffe6a3;
                font-weight: 600;
                font-size: 13px;
            }

            QToolButton:hover {
                background: rgba(189, 58, 255, 0.30);
                border-color: rgba(255, 232, 147, 0.86);
                color: #fff0b8;
            }

            QToolButton:pressed {
                background: rgba(255, 207, 92, 0.28);
                border-color: rgba(255, 232, 147, 0.90);
            }

            QStatusBar {
                background: rgba(13, 2, 22, 0.42);
                border: 1px solid rgba(255, 207, 92, 0.38);
                border-radius: 18px;
                color: #ffd36a;
                font-size: 12px;
            }

            QStatusBar::item {
                border: none;
            }

            QSplitter {
                background: transparent;
            }

            QSplitter::handle {
                background: rgba(255, 207, 92, 0.18);
                width: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }

            QSplitter::handle:hover {
                background: rgba(189, 58, 255, 0.34);
            }

            QLineEdit {
                background: rgba(12, 2, 20, 0.50);
                border: 1px solid rgba(255, 207, 92, 0.44);
                border-radius: 16px;
                padding: 10px 14px;
                color: #fff0b8;
                font-size: 13px;
                selection-background-color: rgba(189, 58, 255, 0.42);
            }

            QLineEdit:focus {
                border: 1px solid rgba(255, 232, 147, 0.88);
                background: rgba(45, 7, 67, 0.58);
                outline: none;
            }

            QPushButton:disabled,
            QLineEdit:disabled {
                color: rgba(255, 211, 106, 0.46);
            }

            QPushButton {
                background: rgba(45, 7, 67, 0.42);
                border: 1px solid rgba(255, 207, 92, 0.46);
                border-radius: 14px;
                padding: 9px 16px;
                color: #ffe6a3;
                font-weight: 600;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(189, 58, 255, 0.30);
                border-color: rgba(255, 232, 147, 0.84);
                color: #fff0b8;
            }

            QPushButton:pressed {
                background: rgba(255, 207, 92, 0.28);
                border-color: rgba(255, 232, 147, 0.88);
            }

            QPushButton:default {
                border: 1px solid rgba(255, 232, 147, 0.82);
                background: rgba(255, 207, 92, 0.24);
            }

            QGroupBox {
                background: rgba(13, 2, 22, 0.38);
                border: 1px solid rgba(255, 207, 92, 0.38);
                border-radius: 18px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #fff0b8;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            QLabel {
                color: #ffe6a3;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 14px;
                font-weight: 700;
                color: #fff0b8;
            }

            QLabel#contentModeLabel {
                color: #ffd36a;
                font-size: 12px;
                padding: 5px 12px;
                background: rgba(45, 7, 67, 0.38);
                border: 1px solid rgba(255, 207, 92, 0.46);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(45, 7, 67, 0.30),
                    stop: 0.52 rgba(189, 58, 255, 0.18),
                    stop: 1 rgba(7, 0, 12, 0.44)
                );
                border: 1px solid rgba(255, 207, 92, 0.46);
                border-radius: 28px;
            }

            QWidget#contentInfoBar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(255, 207, 92, 0.24),
                    stop: 0.55 rgba(45, 7, 67, 0.38),
                    stop: 1 rgba(189, 58, 255, 0.20)
                );
                border: 1px solid rgba(255, 207, 92, 0.54);
                border-radius: 18px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            QTextEdit,
            QPlainTextEdit {
                background: rgba(12, 2, 20, 0.50);
                border: 1px solid rgba(255, 207, 92, 0.40);
                border-radius: 16px;
                padding: 10px;
                color: #ffe6a3;
                font-size: 13px;
                selection-background-color: rgba(189, 58, 255, 0.42);
            }

            QTextEdit:focus,
            QPlainTextEdit:focus {
                border: 1px solid rgba(255, 232, 147, 0.86);
                background: rgba(45, 7, 67, 0.54);
            }

            QComboBox {
                background: rgba(12, 2, 20, 0.50);
                color: #ffe6a3;
                border: 1px solid rgba(255, 207, 92, 0.40);
                border-radius: 14px;
                padding: 8px 12px;
            }

            QComboBox::drop-down {
                border: none;
                width: 18px;
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #ffe6a3;
                selection-background-color: rgba(189, 58, 255, 0.40);
                selection-color: #fff0b8;
            }

            QComboBox QAbstractItemView {
                background: rgba(12, 2, 20, 0.97);
                color: #ffe6a3;
                border: 1px solid rgba(255, 207, 92, 0.44);
                selection-background-color: rgba(189, 58, 255, 0.34);
            }

            QScrollBar:vertical {
                background: rgba(13, 2, 22, 0.38);
                width: 11px;
                margin: 4px 0 4px 0;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: rgba(255, 207, 92, 0.58);
                min-height: 30px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(255, 232, 147, 0.86);
            }

            QScrollBar:horizontal {
                background: rgba(13, 2, 22, 0.38);
                height: 11px;
                margin: 0 4px 0 4px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal {
                background: rgba(255, 207, 92, 0.58);
                min-width: 30px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal:hover {
                background: rgba(255, 232, 147, 0.86);
            }

            QScrollBar::add-line,
            QScrollBar::sub-line,
            QScrollBar::add-page,
            QScrollBar::sub-page {
                border: none;
                background: transparent;
            }

            QInputDialog, QDialog, QProgressDialog {
                background-color: rgba(8, 2, 13, 0.98);
                color: #ffe6a3;
            }
        """ % background_url

    def _get_purple_neon_messagebox_style(self):
        """获取紫霓主题消息框样式"""
        return """
            QMessageBox {
                background: rgba(8, 2, 13, 0.98);
                color: #ffe6a3;
            }
            QLabel {
                color: #ffe6a3;
            }
            QPushButton {
                background-color: rgba(45, 7, 67, 0.46);
                color: #ffe6a3;
                border: 1px solid rgba(255, 207, 92, 0.48);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(189, 58, 255, 0.30);
                border-color: rgba(255, 232, 147, 0.86);
                color: #fff0b8;
            }
        """

    def _get_purple_neon_toolcard_style(self):
        """获取紫霓主题工具卡片样式"""
        return """
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(45, 7, 67, 0.38),
                    stop: 0.58 rgba(189, 58, 255, 0.18),
                    stop: 1 rgba(7, 0, 12, 0.50)
                );
                border: 1px solid rgba(255, 207, 92, 0.52);
                border-radius: 16px;
            }

            QLabel {
                color: #ffe6a3;
            }

            QPushButton {
                background-color: rgba(45, 7, 67, 0.46);
                border: 1px solid rgba(255, 207, 92, 0.48);
                border-radius: 12px;
                color: #ffe6a3;
            }

            QPushButton:hover {
                background-color: rgba(189, 58, 255, 0.30);
                border-color: rgba(255, 232, 147, 0.86);
                color: #fff0b8;
            }

            QPushButton:pressed {
                background-color: rgba(255, 207, 92, 0.28);
            }
        """

    def _get_purple_neon_category_style(self):
        """获取紫霓主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
                outline: none;
            }

            QListWidget::item {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(255, 207, 92, 0.22),
                    stop: 0.46 rgba(45, 7, 67, 0.42),
                    stop: 1 rgba(189, 58, 255, 0.14)
                );
                border: 1px solid rgba(255, 207, 92, 0.46);
                border-radius: 16px;
                padding: 13px 14px;
                margin-bottom: 8px;
                color: #ffe6a3;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(189, 58, 255, 0.30);
                border-color: rgba(255, 232, 147, 0.82);
                color: #fff0b8;
            }

            QListWidget::item:selected {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(255, 207, 92, 0.38),
                    stop: 0.58 rgba(189, 58, 255, 0.34),
                    stop: 1 rgba(45, 7, 67, 0.50)
                );
                color: #fff0b8;
                border-color: rgba(255, 232, 147, 0.90);
            }
        """

    def _get_purple_neon_dialog_style(self):
        """获取紫霓主题对话框样式"""
        return """
            QDialog { background-color: rgba(8,2,13,0.98); }
            QGroupBox {
                background-color: rgba(45,7,67,0.38);
                border: 1px solid rgba(255,207,92,0.46);
                border-radius: 18px;
                margin-top: 16px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                top: -2px;
                padding: 2px 10px 3px 10px;
                background-color: rgba(45,7,67,0.52);
                border: 1px solid rgba(255,207,92,0.56);
                border-radius: 10px;
                color: #fff0b8;
                font-weight: 600;
            }
            QLabel { color: #ffe6a3; }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
                background: rgba(12,2,20,0.50);
                color: #ffe6a3;
                border: 1px solid rgba(255,207,92,0.44);
                border-radius: 14px;
                padding: 7px 10px;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid rgba(255,232,147,0.86);
                background: rgba(45,7,67,0.54);
            }
            QPushButton {
                background-color: rgba(45,7,67,0.46);
                color: #ffe6a3;
                border: 1px solid rgba(255,207,92,0.48);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(189,58,255,0.30);
                border-color: rgba(255,232,147,0.86);
                color: #fff0b8;
            }
        """

    def _get_red_orange_styles(self):
        """获取红橙主题样式"""
        background_url = self._asset_qss_url("images/background/红色.png")
        return """
            QMainWindow {
                background-color: #260000;
                border: none;
            }

            QWidget#windowCanvas {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #7a0906,
                    stop: 0.32 #3a0000,
                    stop: 0.68 #680403,
                    stop: 1 #1a0000
                );
                background-image: url(%s);
                background-position: center center;
                background-repeat: no-repeat;
                border: 1px solid rgba(255, 205, 92, 0.62);
                border-radius: 28px;
            }

            QMenuBar {
                background: rgba(106, 0, 0, 0.42);
                color: #ffe6b0;
                border: none;
                border-bottom: 1px solid rgba(255, 205, 92, 0.48);
            }

            QMenuBar::item {
                padding: 6px 12px;
                margin: 4px 2px;
                border-radius: 10px;
            }

            QMenuBar::item:selected {
                background: rgba(255, 205, 92, 0.25);
                color: #fff3c7;
            }

            QMenu {
                background: rgba(58, 0, 0, 0.96);
                color: #ffe6b0;
                border: 1px solid rgba(255, 205, 92, 0.58);
                border-radius: 16px;
                padding: 8px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 10px;
            }

            QMenu::item:selected {
                background: rgba(255, 66, 38, 0.30);
            }

            QMenu::separator {
                height: 1px;
                margin: 6px 10px;
                background: rgba(255, 210, 96, 0.42);
            }

            QToolBar {
                background-color: rgba(82, 0, 0, 0.50);
                border: 1px solid rgba(255, 205, 92, 0.64);
                border-top-color: rgba(255, 232, 147, 0.58);
                border-bottom-color: rgba(190, 40, 24, 0.56);
                border-radius: 22px;
                margin: 6px 6px 0 6px;
                padding: 12px 16px;
                spacing: 12px;
            }

            QToolBar::separator {
                background: rgba(255, 210, 96, 0.42);
                width: 1px;
                margin: 8px 10px;
            }

            QToolButton {
                background: rgba(96, 0, 0, 0.50);
                border: 1px solid rgba(255, 205, 92, 0.66);
                padding: 9px 18px;
                border-radius: 15px;
                color: #ffe6b0;
                font-weight: 600;
                font-size: 13px;
            }

            QToolButton:hover {
                background: rgba(150, 16, 8, 0.58);
                border-color: rgba(255, 232, 147, 0.94);
                color: #fff0b8;
            }

            QToolButton:pressed {
                background: rgba(132, 0, 0, 0.66);
                border-color: rgba(255, 236, 153, 0.72);
            }

            QToolButton:checked {
                background: rgba(132, 0, 0, 0.72);
                border-color: rgba(255, 232, 147, 0.98);
                color: #ffdc70;
            }

            QStatusBar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(88, 0, 0, 0.58),
                    stop: 0.08 rgba(255, 210, 96, 0.26),
                    stop: 0.14 rgba(98, 0, 0, 0.56),
                    stop: 1 rgba(54, 0, 0, 0.48)
                );
                border: 1px solid rgba(255, 205, 92, 0.58);
                border-radius: 18px;
                color: #ffdc70;
                font-size: 12px;
            }

            QStatusBar::item {
                border: none;
            }

            QSplitter {
                background: transparent;
            }

            QSplitter::handle {
                background: rgba(255, 205, 92, 0.26);
                width: 10px;
                border-radius: 5px;
                margin: 10px 0;
            }

            QSplitter::handle:hover {
                background: rgba(255, 220, 112, 0.46);
            }

            QLineEdit {
                background: rgba(74, 0, 0, 0.54);
                border: 1px solid rgba(255, 224, 140, 0.70);
                border-radius: 16px;
                padding: 10px 14px;
                color: #ffdc70;
                font-size: 13px;
                selection-background-color: rgba(255, 66, 38, 0.42);
                selection-color: #fff6d6;
            }

            QLineEdit:focus {
                border: 1px solid rgba(255, 220, 112, 0.84);
                background: rgba(126, 0, 0, 0.62);
                outline: none;
            }

            QPushButton:disabled,
            QLineEdit:disabled {
                color: rgba(255, 198, 72, 0.46);
            }

            QPushButton {
                background: rgba(74, 0, 0, 0.54);
                border: 1px solid rgba(255, 205, 92, 0.62);
                border-radius: 14px;
                padding: 9px 16px;
                color: #ffe6b0;
                font-weight: 600;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(150, 16, 8, 0.54);
                border-color: rgba(255, 232, 147, 0.94);
            }

            QPushButton:pressed {
                background: rgba(255, 205, 92, 0.30);
                border-color: rgba(255, 236, 153, 0.72);
            }

            QPushButton:default {
                border: 1px solid rgba(255, 220, 112, 0.76);
                background: rgba(255, 205, 92, 0.28);
            }

            QGroupBox {
                background: rgba(82, 0, 0, 0.44);
                border: 1px solid rgba(255, 205, 92, 0.50);
                border-radius: 18px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #fff0b8;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            QLabel {
                color: #ffe6b0;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 14px;
                font-weight: 700;
                color: #fff3c7;
            }

            QLabel#contentModeLabel {
                color: #ffc95e;
                font-size: 12px;
                padding: 5px 12px;
                background: rgba(112, 0, 0, 0.48);
                border: 1px solid rgba(255, 205, 92, 0.60);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(104, 0, 0, 0.58),
                    stop: 0.50 rgba(156, 14, 8, 0.34),
                    stop: 1 rgba(60, 0, 0, 0.46)
                );
                border: 1px solid rgba(255, 205, 92, 0.66);
                border-radius: 28px;
            }

            QWidget#contentInfoBar {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(255, 210, 96, 0.24),
                    stop: 0.42 rgba(126, 0, 0, 0.48),
                    stop: 1 rgba(70, 0, 0, 0.34)
                );
                border: 1px solid rgba(255, 205, 92, 0.68);
                border-radius: 18px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            QTextEdit,
            QPlainTextEdit {
                background: rgba(74, 0, 0, 0.54);
                border: 1px solid rgba(255, 205, 92, 0.54);
                border-radius: 16px;
                padding: 10px;
                color: #ffe6b0;
                font-size: 13px;
                selection-background-color: rgba(255, 66, 38, 0.42);
            }

            QTextEdit:focus,
            QPlainTextEdit:focus {
                border: 1px solid rgba(255, 220, 112, 0.84);
                background: rgba(126, 0, 0, 0.62);
            }

            QComboBox {
                background: rgba(74, 0, 0, 0.54);
                color: #ffe6b0;
                border: 1px solid rgba(255, 205, 92, 0.54);
                border-radius: 14px;
                padding: 8px 12px;
            }

            QComboBox::drop-down {
                border: none;
                width: 18px;
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #ffe6b0;
                selection-background-color: rgba(255, 66, 38, 0.42);
                selection-color: #fff3c7;
            }

            QComboBox QAbstractItemView {
                background: rgba(36, 0, 0, 0.97);
                color: #ffe6b0;
                border: 1px solid rgba(255, 205, 92, 0.60);
                selection-background-color: rgba(255, 66, 38, 0.34);
            }

            QScrollBar:vertical {
                background: rgba(106, 0, 0, 0.42);
                width: 11px;
                margin: 4px 0 4px 0;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: rgba(255, 205, 92, 0.58);
                min-height: 30px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(255, 232, 147, 0.90);
            }

            QScrollBar:horizontal {
                background: rgba(106, 0, 0, 0.42);
                height: 11px;
                margin: 0 4px 0 4px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal {
                background: rgba(255, 205, 92, 0.58);
                min-width: 30px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal:hover {
                background: rgba(255, 232, 147, 0.90);
            }

            QScrollBar::add-line,
            QScrollBar::sub-line,
            QScrollBar::add-page,
            QScrollBar::sub-page {
                border: none;
                background: transparent;
            }

            QInputDialog, QDialog, QProgressDialog {
                background-color: rgba(42, 0, 0, 0.98);
                color: #ffe6b0;
            }
        """ % background_url

    def _get_red_orange_messagebox_style(self):
        """获取红橙主题消息框样式"""
        return """
            QMessageBox {
                background: rgba(42, 0, 0, 0.98);
                color: #ffe6b0;
            }
            QLabel {
                color: #ffe6b0;
            }
            QPushButton {
                background-color: rgba(112, 0, 0, 0.48);
                color: #ffe6b0;
                border: 1px solid rgba(255, 205, 92, 0.60);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(176, 24, 12, 0.54);
                border-color: rgba(255, 232, 147, 0.94);
            }
        """

    def _get_red_orange_toolcard_style(self):
        """获取红橙主题工具卡片样式"""
        return """
            QFrame {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 rgba(112, 0, 0, 0.68),
                    stop: 0.48 rgba(180, 18, 8, 0.38),
                    stop: 1 rgba(58, 0, 0, 0.70)
                );
                border: 1px solid rgba(255, 205, 92, 0.76);
                border-radius: 16px;
            }

            QLabel {
                color: #ffe6b0;
            }

            QPushButton {
                background-color: rgba(96, 0, 0, 0.54);
                border: 1px solid rgba(255, 205, 92, 0.64);
                border-radius: 12px;
                color: #ffe6b0;
            }

            QPushButton:hover {
                background-color: rgba(150, 16, 8, 0.58);
                border-color: rgba(255, 232, 147, 0.94);
            }

            QPushButton:pressed {
                background-color: rgba(255, 198, 72, 0.24);
            }
        """

    def _get_red_orange_category_style(self):
        """获取红橙主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
                outline: none;
            }

            QListWidget::item {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(112, 0, 0, 0.58),
                    stop: 0.52 rgba(176, 18, 8, 0.34),
                    stop: 1 rgba(70, 0, 0, 0.42)
                );
                border: 1px solid rgba(255, 205, 92, 0.68);
                border-radius: 16px;
                padding: 13px 14px;
                margin-bottom: 8px;
                color: #ffecc2;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(156, 16, 8, 0.62),
                    stop: 0.58 rgba(255, 210, 96, 0.20),
                    stop: 1 rgba(86, 0, 0, 0.48)
                );
                border-color: rgba(255, 232, 147, 0.94);
            }

            QListWidget::item:selected {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 rgba(176, 24, 12, 0.74),
                    stop: 0.58 rgba(255, 210, 96, 0.26),
                    stop: 1 rgba(104, 0, 0, 0.56)
                );
                color: #ffdc70;
                border-color: rgba(255, 232, 147, 0.96);
            }
        """

    def _get_red_orange_dialog_style(self):
        """获取红橙主题对话框样式"""
        return """
            QDialog { background-color: rgba(42,0,0,0.98); }
            QGroupBox {
                background-color: rgba(86,0,0,0.46);
                border: 1px solid rgba(255,205,92,0.60);
                border-radius: 18px;
                margin-top: 16px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                top: -2px;
                padding: 2px 10px 3px 10px;
                background-color: rgba(112,0,0,0.48);
                border: 1px solid rgba(255,220,112,0.68);
                border-radius: 10px;
                color: #fff0b8;
                font-weight: 600;
            }
            QLabel { color: #ffe6b0; }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
                background: rgba(74,0,0,0.54);
                color: #ffe6b0;
                border: 1px solid rgba(255,205,92,0.60);
                border-radius: 14px;
                padding: 7px 10px;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid rgba(255,220,112,0.84);
                background: rgba(126,0,0,0.62);
            }
            QPushButton {
                background-color: rgba(112,0,0,0.48);
                color: #ffe6b0;
                border: 1px solid rgba(255,205,92,0.60);
                border-radius: 12px;
                padding: 7px 12px;
            }
            QPushButton:hover {
                background-color: rgba(176,24,12,0.54);
                border-color: rgba(255,232,147,0.94);
            }
        """

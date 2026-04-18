# -*- coding: utf-8 -*-
"""
主题样式管理器
集中管理应用程序的所有主题样式，避免重复代码
"""

class ThemeManager:
    """主题样式管理器"""
    
    def __init__(self):
        """初始化主题管理器"""
        self.themes = {
            "dark_green": {
                "name": "亮绿主题",
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
    
    def _get_dark_green_styles(self):
        """获取亮绿主题样式"""
        return """
            QMainWindow {
                background-color: #0f1d16;
                border: none;
            }

            QMenuBar {
                background: rgba(21, 46, 33, 0.92);
                color: #f3fff5;
                border: none;
                border-bottom: 1px solid rgba(111, 231, 135, 0.18);
            }

            QMenuBar::item {
                padding: 6px 11px;
                margin: 4px 2px;
                border-radius: 8px;
            }

            QMenuBar::item:selected {
                background: rgba(111, 231, 135, 0.16);
            }

            QMenu {
                background: rgba(21, 46, 33, 0.96);
                color: #f3fff5;
                border: 1px solid rgba(111, 231, 135, 0.2);
                border-radius: 12px;
                padding: 6px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 8px;
            }

            QMenu::item:selected {
                background: rgba(111, 231, 135, 0.18);
            }

            QToolBar {
                background-color: rgba(21, 46, 33, 0.9);
                border: none;
                border-bottom: 1px solid rgba(111, 231, 135, 0.14);
                padding: 10px 14px;
                spacing: 12px;
            }

            QToolButton {
                background: rgba(111, 231, 135, 0.08);
                border: 1px solid rgba(111, 231, 135, 0.14);
                padding: 9px 18px;
                border-radius: 12px;
                color: #f3fff5;
                font-weight: 500;
                font-size: 13px;
            }

            QToolButton:hover {
                background: rgba(111, 231, 135, 0.16);
                border: 1px solid rgba(152, 246, 176, 0.24);
            }

            QToolButton:pressed {
                background: rgba(54, 122, 73, 0.72);
            }

            QStatusBar {
                background: rgba(20, 42, 31, 0.92);
                border: none;
                border-top: 1px solid rgba(111, 231, 135, 0.12);
                color: #c6ebcf;
                font-size: 12px;
            }

            QSplitter {
                background-color: #0f1d16;
            }

            QSplitter::handle {
                background: rgba(111, 231, 135, 0.08);
                width: 8px;
                border-radius: 4px;
                margin: 8px 0;
            }

            QSplitter::handle:hover {
                background: rgba(152, 246, 176, 0.2);
            }

            QLineEdit {
                background: rgba(22, 49, 35, 0.82);
                border: 1px solid rgba(111, 231, 135, 0.16);
                border-radius: 12px;
                padding: 9px 14px;
                color: #f3fff5;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid rgba(152, 246, 176, 0.34);
                background: rgba(25, 57, 40, 0.9);
                outline: none;
            }

            QPushButton {
                background: rgba(111, 231, 135, 0.1);
                border: 1px solid rgba(111, 231, 135, 0.16);
                border-radius: 12px;
                padding: 9px 18px;
                color: #f3fff5;
                font-weight: 500;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(111, 231, 135, 0.18);
                border: 1px solid rgba(152, 246, 176, 0.26);
            }

            QPushButton:pressed {
                background: rgba(54, 122, 73, 0.76);
            }

            QPushButton:default {
                border: 1px solid rgba(152, 246, 176, 0.32);
                background: rgba(111, 231, 135, 0.2);
            }

            QGroupBox {
                background: rgba(20, 44, 31, 0.76);
                border: 1px solid rgba(111, 231, 135, 0.14);
                border-radius: 16px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #d5ffe0;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            QLabel {
                color: #ecfff1;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 16px;
                font-weight: 700;
                color: #f4fff6;
            }

            QLabel#contentModeLabel {
                color: #b9d9c1;
                font-size: 12px;
                padding: 4px 10px;
                background: rgba(111, 231, 135, 0.08);
                border: 1px solid rgba(111, 231, 135, 0.14);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: rgba(18, 39, 28, 0.76);
                border: 1px solid rgba(111, 231, 135, 0.12);
                border-radius: 22px;
            }

            QWidget#contentInfoBar {
                background: rgba(25, 54, 38, 0.6);
                border: 1px solid rgba(111, 231, 135, 0.1);
                border-radius: 16px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            QTextEdit {
                background: rgba(18, 49, 36, 0.82);
                border: 1px solid rgba(111, 231, 135, 0.16);
                border-radius: 12px;
                padding: 10px;
                color: #f3fff5;
                font-size: 13px;
            }

            QTextEdit:focus {
                border: 1px solid rgba(152, 246, 176, 0.28);
                background: rgba(24, 64, 44, 0.9);
                outline: none;
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #f3fff5;
                selection-background-color: rgba(111, 231, 135, 0.22);
                selection-color: #f3fff5;
            }

            QComboBox QAbstractItemView {
                background: rgba(21, 46, 33, 0.96);
                color: #f3fff5;
                border: 1px solid rgba(111, 231, 135, 0.18);
            }

            QInputDialog, QDialog, QProgressDialog {
                background-color: #0f1d16;
                color: #f3fff5;
            }"""
    
    def _get_blue_white_styles(self):
        """获取蓝白主题样式"""
        return """
            /* 主窗口样式 */
            QMainWindow {
                background-color: #eef3f8;
                border: none;
            }

            /* 菜单栏样式 */
            QMenuBar {
                background: rgba(255, 255, 255, 0.88);
                color: #334155;
                border: none;
                border-bottom: 1px solid rgba(148, 163, 184, 0.16);
            }

            QMenuBar::item {
                padding: 6px 11px;
                margin: 4px 2px;
                border-radius: 8px;
            }

            QMenuBar::item:selected {
                background: rgba(59, 130, 246, 0.1);
            }

            /* 弹出菜单样式 */
            QMenu {
                background: rgba(255, 255, 255, 0.96);
                color: #334155;
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 12px;
                padding: 6px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 8px;
            }

            QMenu::item:selected {
                background: rgba(59, 130, 246, 0.12);
            }

            /* 工具栏样式 */
            QToolBar {
                background-color: rgba(255, 255, 255, 0.82);
                border: none;
                border-bottom: 1px solid rgba(148, 163, 184, 0.14);
                padding: 8px 12px;
                spacing: 12px;
            }

            /* 工具栏按钮 */
            QToolButton {
                background: rgba(59, 130, 246, 0.06);
                border: 1px solid rgba(59, 130, 246, 0.1);
                padding: 8px 16px;
                border-radius: 12px;
                color: #334155;
                font-weight: 500;
            }

            QToolButton:hover {
                background: rgba(59, 130, 246, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.18);
            }

            QToolButton:pressed {
                background: rgba(59, 130, 246, 0.18);
            }

            /* 状态栏 */
            QStatusBar {
                background: rgba(255, 255, 255, 0.84);
                border: none;
                border-top: 1px solid rgba(148, 163, 184, 0.12);
                color: #475569;
                font-size: 12px;
            }

            /* 分割器 */
            QSplitter {
                background-color: #eef3f8;
            }

            QSplitter::handle {
                background: rgba(148, 163, 184, 0.08);
                width: 8px;
                border-radius: 4px;
                margin: 8px 0;
            }

            QSplitter::handle:hover {
                background: rgba(59, 130, 246, 0.18);
            }

            /* 输入框 */
            QLineEdit {
                background: rgba(255, 255, 255, 0.86);
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 12px;
                padding: 8px 12px;
                color: #334155;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid rgba(59, 130, 246, 0.3);
                background: rgba(255, 255, 255, 0.98);
                outline: none;
            }

            /* 按钮 */
            QPushButton {
                background: rgba(59, 130, 246, 0.08);
                border: 1px solid rgba(59, 130, 246, 0.12);
                border-radius: 12px;
                padding: 8px 16px;
                color: #334155;
                font-weight: 500;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(59, 130, 246, 0.14);
                border: 1px solid rgba(59, 130, 246, 0.2);
            }

            QPushButton:pressed {
                background: rgba(59, 130, 246, 0.2);
            }

            QPushButton:default {
                border: 1px solid rgba(59, 130, 246, 0.24);
            }

            /* 分组框 */
            QGroupBox {
                background: rgba(255, 255, 255, 0.74);
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 16px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #334155;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            /* 标签 */
            QLabel {
                color: #334155;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 16px;
                font-weight: 700;
                color: #1e293b;
            }

            QLabel#contentModeLabel {
                color: #475569;
                font-size: 12px;
                padding: 4px 10px;
                background: rgba(59, 130, 246, 0.08);
                border: 1px solid rgba(59, 130, 246, 0.1);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: rgba(255, 255, 255, 0.64);
                border: 1px solid rgba(148, 163, 184, 0.12);
                border-radius: 22px;
            }

            QWidget#contentInfoBar {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(148, 163, 184, 0.1);
                border-radius: 16px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            /* 文本编辑框 */
            QTextEdit {
                background: rgba(255, 255, 255, 0.82);
                border: 1px solid rgba(148, 163, 184, 0.16);
                border-radius: 12px;
                padding: 10px;
                color: #334155;
                font-size: 13px;
            }

            QTextEdit:focus {
                border: 1px solid rgba(59, 130, 246, 0.24);
                background: rgba(255, 255, 255, 0.96);
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #334155;
                selection-background-color: rgba(59, 130, 246, 0.12);
                selection-color: #1e293b;
            }"""
    
    def _get_dark_green_messagebox_style(self):
        """获取亮绿主题消息框样式"""
        return """
            QMessageBox {
                background: #102117;
                color: #f3fff5;
            }
            QLabel {
                color: #f3fff5;
            }
            QPushButton {
                background-color: rgba(111, 231, 135, 0.14);
                color: #f3fff5;
                border: 1px solid rgba(111, 231, 135, 0.42);
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: rgba(152, 246, 176, 0.24);
            }"""
    
    def _get_blue_white_messagebox_style(self):
        """获取蓝白主题消息框样式"""
        return """
            QMessageBox {
                background: #f6fbff;
                color: #003347;
            }
            QLabel {
                color: #003347;
            }
            QPushButton {
                background-color: rgba(66, 135, 245, 0.06);
                color: #003347;
                border-radius: 6px;
                padding: 6px 10px;
            }"""
    
    def _get_dark_green_toolcard_style(self):
        """获取亮绿主题工具卡片样式"""
        return """
            QFrame {
                background-color: rgba(24, 55, 37, 0.97);
                border: 1px solid rgba(111, 231, 135, 0.42);
                border-radius: 8px;
            }

            QLabel {
                color: #f3fff5;
            }

            QPushButton {
                background-color: rgba(111, 231, 135, 0.14);
                border: 1px solid rgba(111, 231, 135, 0.42);
                border-radius: 4px;
                color: #f3fff5;
            }

            QPushButton:hover {
                background-color: rgba(152, 246, 176, 0.24);
                border: 1px solid rgba(152, 246, 176, 0.58);
            }

            QPushButton:pressed {
                background-color: rgba(54, 122, 73, 0.92);
            }"""
    
    def _get_blue_white_toolcard_style(self):
        """获取蓝白主题工具卡片样式"""
        return """
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
            }
            
            QLabel {
                color: #333333;
            }
            
            QPushButton {
                background-color: rgba(66, 135, 245, 0.1);
                border: 1px solid rgba(66, 135, 245, 0.3);
                border-radius: 4px;
                color: #333333;
            }
            
            QPushButton:hover {
                background-color: rgba(66, 135, 245, 0.2);
                border: 1px solid rgba(66, 135, 245, 0.5);
            }
            
            QPushButton:pressed {
                background-color: rgba(66, 135, 245, 0.3);
            }"""

    def _get_dark_green_category_style(self):
        """获取亮绿主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
            }

            QListWidget::item {
                background: rgba(24, 55, 37, 0.72);
                border: 1px solid rgba(111, 231, 135, 0.14);
                border-radius: 14px;
                padding: 12px 14px;
                margin-bottom: 6px;
                color: #f3fff5;
                font-weight: 500;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(32, 73, 48, 0.84);
                border-color: rgba(152, 246, 176, 0.24);
            }

            QListWidget::item:selected {
                background: rgba(111, 231, 135, 0.18);
                color: #f3fff5;
                border-color: rgba(152, 246, 176, 0.3);
            }
        """

    def _get_blue_white_category_style(self):
        """获取蓝白主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
            }

            QListWidget::item {
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(148, 163, 184, 0.14);
                border-radius: 14px;
                padding: 12px 14px;
                margin-bottom: 6px;
                color: #0369a1;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.9);
                border-color: rgba(59, 130, 246, 0.2);
            }

            QListWidget::item:selected {
                background: rgba(219, 234, 254, 0.86);
                color: #0f172a;
                border-color: rgba(59, 130, 246, 0.3);
            }
        """

    def _get_dark_green_dialog_style(self):
        """获取亮绿主题对话框样式"""
        return """
            QDialog { background-color: #102117; }
            QGroupBox { background-color: rgba(23,55,37,0.84); border: 1px solid rgba(111,231,135,0.32); border-radius: 8px; margin-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #d5ffe0; font-weight:600; }
            QLabel { color: #ecfff1; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background: #143125; color: #f3fff5; border: 1px solid rgba(111,231,135,0.4); border-radius: 6px; padding: 6px; }
            QPushButton { background-color: rgba(111,231,135,0.12); color: #f3fff5; border: 1px solid rgba(111,231,135,0.46); border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background-color: rgba(152,246,176,0.24); }
        """

    def _get_blue_white_dialog_style(self):
        """获取蓝白主题对话框样式"""
        return """
            QDialog { background-color: #f6fbff; }
            QGroupBox { background-color: transparent; border: 1px solid rgba(66,135,245,0.12); border-radius: 8px; margin-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #003366; font-weight:600; }
            QLabel { color: #003347; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background: white; color: #0b2540; border: 1px solid rgba(3,105,161,0.12); border-radius: 6px; padding: 6px; }
            QPushButton { background-color: rgba(66,135,245,0.06); color: #003347; border: 1px solid rgba(66,135,245,0.12); border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background-color: rgba(66,135,245,0.12); }
        """

    def _get_purple_neon_styles(self):
        """获取紫霓（暗紫霓虹）主题样式"""
        return """
            QMainWindow {
                background-color: #131023;
                border: none;
            }

            QMenuBar {
                background: rgba(28, 22, 50, 0.92);
                color: #f3eeff;
                border: none;
                border-bottom: 1px solid rgba(157, 123, 255, 0.16);
            }

            QMenuBar::item {
                padding: 6px 11px;
                margin: 4px 2px;
                border-radius: 8px;
            }

            QMenuBar::item:selected {
                background: rgba(157, 123, 255, 0.14);
            }

            QMenu {
                background: rgba(28, 22, 50, 0.96);
                color: #f3eeff;
                border: 1px solid rgba(157, 123, 255, 0.18);
                border-radius: 12px;
                padding: 6px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 8px;
            }

            QMenu::item:selected {
                background: rgba(157, 123, 255, 0.18);
            }

            QToolBar {
                background-color: rgba(28, 22, 50, 0.88);
                border: none;
                border-bottom: 1px solid rgba(157, 123, 255, 0.14);
                padding: 10px 12px;
                spacing: 12px;
            }

            QToolButton {
                background: rgba(157, 123, 255, 0.08);
                border: 1px solid rgba(157, 123, 255, 0.14);
                padding: 9px 18px;
                border-radius: 12px;
                color: #efe9ff;
                font-weight: 500;
                font-size: 13px;
            }

            QToolButton:hover {
                background: rgba(157, 123, 255, 0.16);
                border-color: rgba(195, 169, 255, 0.24);
            }

            QToolButton:pressed {
                background: rgba(93, 74, 156, 0.72);
            }

            QStatusBar {
                background: rgba(23, 18, 41, 0.92);
                border: none;
                border-top: 1px solid rgba(157, 123, 255, 0.12);
                color: #d6ceef;
                font-size: 12px;
            }

            QSplitter {
                background-color: #131023;
            }

            QSplitter::handle {
                background: rgba(157, 123, 255, 0.08);
                width: 8px;
                border-radius: 4px;
                margin: 8px 0;
            }

            QSplitter::handle:hover {
                background: rgba(195, 169, 255, 0.2);
            }

            QLineEdit {
                background: rgba(24, 19, 46, 0.82);
                border: 1px solid rgba(157, 123, 255, 0.16);
                border-radius: 12px;
                padding: 9px 14px;
                color: #efe9ff;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid rgba(195, 169, 255, 0.32);
                background: rgba(28, 22, 54, 0.9);
                outline: none;
            }

            QPushButton {
                background: rgba(157, 123, 255, 0.1);
                border: 1px solid rgba(157, 123, 255, 0.16);
                border-radius: 12px;
                padding: 9px 18px;
                color: #f3eeff;
                font-weight: 500;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(195, 169, 255, 0.16);
                border-color: rgba(195, 169, 255, 0.24);
            }

            QPushButton:pressed {
                background: rgba(93, 74, 156, 0.76);
            }

            QGroupBox {
                background: rgba(31, 25, 58, 0.76);
                border: 1px solid rgba(157, 123, 255, 0.14);
                border-radius: 16px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #ddceff;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            QLabel {
                color: #efe9ff;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 16px;
                font-weight: 700;
                color: #f3eeff;
            }

            QLabel#contentModeLabel {
                color: #d7cff3;
                font-size: 12px;
                padding: 4px 10px;
                background: rgba(157, 123, 255, 0.08);
                border: 1px solid rgba(157, 123, 255, 0.12);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: rgba(24, 19, 45, 0.74);
                border: 1px solid rgba(157, 123, 255, 0.12);
                border-radius: 22px;
            }

            QWidget#contentInfoBar {
                background: rgba(35, 28, 66, 0.62);
                border: 1px solid rgba(157, 123, 255, 0.1);
                border-radius: 16px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            QTextEdit {
                background: rgba(24, 19, 46, 0.82);
                border: 1px solid rgba(157, 123, 255, 0.16);
                border-radius: 12px;
                padding: 10px;
                color: #efe9ff;
                font-size: 13px;
            }

            QTextEdit:focus {
                border: 1px solid rgba(195, 169, 255, 0.26);
                background: rgba(28, 22, 54, 0.9);
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #efe9ff;
                selection-background-color: rgba(157, 123, 255, 0.2);
                selection-color: #f3eeff;
            }

            QComboBox QAbstractItemView {
                background: rgba(28, 22, 50, 0.96);
                color: #efe9ff;
                border: 1px solid rgba(157, 123, 255, 0.18);
            }
        """

    def _get_purple_neon_messagebox_style(self):
        """获取紫霓主题消息框样式"""
        return """
            QMessageBox {
                background: #141027;
                color: #f3eeff;
            }
            QLabel {
                color: #f3eeff;
            }
            QPushButton {
                background-color: rgba(157, 123, 255, 0.2);
                color: #f3eeff;
                border: 1px solid rgba(157, 123, 255, 0.5);
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: rgba(195, 169, 255, 0.3);
            }
        """

    def _get_purple_neon_toolcard_style(self):
        """获取紫霓主题工具卡片样式"""
        return """
            QFrame {
                background-color: rgba(27, 23, 56, 0.95);
                border: 1px solid rgba(157, 123, 255, 0.48);
                border-radius: 10px;
            }

            QLabel {
                color: #efe9ff;
            }

            QPushButton {
                background-color: rgba(157, 123, 255, 0.16);
                border: 1px solid rgba(157, 123, 255, 0.46);
                border-radius: 6px;
                color: #efe9ff;
            }

            QPushButton:hover {
                background-color: rgba(195, 169, 255, 0.3);
                border-color: rgba(195, 169, 255, 0.62);
            }

            QPushButton:pressed {
                background-color: rgba(93, 74, 156, 0.9);
            }
        """

    def _get_purple_neon_category_style(self):
        """获取紫霓主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
            }

            QListWidget::item {
                background: rgba(34, 28, 63, 0.72);
                border: 1px solid rgba(157, 123, 255, 0.14);
                border-radius: 14px;
                padding: 12px 14px;
                margin-bottom: 6px;
                color: #efe9ff;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(43, 34, 81, 0.84);
                border-color: rgba(195, 169, 255, 0.24);
            }

            QListWidget::item:selected {
                background: rgba(76, 58, 126, 0.8);
                color: #f3eeff;
                border-color: rgba(195, 169, 255, 0.3);
            }
        """

    def _get_purple_neon_dialog_style(self):
        """获取紫霓主题对话框样式"""
        return """
            QDialog { background-color: #141027; }
            QGroupBox { background-color: rgba(27,23,56,0.84); border: 1px solid rgba(157,123,255,0.42); border-radius: 8px; margin-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #ddceff; font-weight:600; }
            QLabel { color: #efe9ff; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background: #171233; color: #efe9ff; border: 1px solid rgba(157,123,255,0.48); border-radius: 6px; padding: 6px; }
            QPushButton { background-color: rgba(157,123,255,0.18); color: #f3eeff; border: 1px solid rgba(157,123,255,0.5); border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background-color: rgba(195,169,255,0.3); }
        """

    def _get_red_orange_styles(self):
        """获取红橙主题样式"""
        return """
            QMainWindow {
                background-color: #17110f;
                border: none;
            }

            QMenuBar {
                background: rgba(36, 26, 22, 0.92);
                color: #fff1e6;
                border: none;
                border-bottom: 1px solid rgba(255, 138, 61, 0.16);
            }

            QMenuBar::item {
                padding: 6px 11px;
                margin: 4px 2px;
                border-radius: 8px;
            }

            QMenuBar::item:selected {
                background: rgba(255, 138, 61, 0.14);
            }

            QMenu {
                background: rgba(36, 26, 22, 0.96);
                color: #fff1e6;
                border: 1px solid rgba(255, 138, 61, 0.18);
                border-radius: 12px;
                padding: 6px;
            }

            QMenu::item {
                padding: 8px 18px;
                border-radius: 8px;
            }

            QMenu::item:selected {
                background: rgba(255, 138, 61, 0.18);
            }

            QToolBar {
                background-color: rgba(36, 26, 22, 0.88);
                border: none;
                border-bottom: 1px solid rgba(255, 138, 61, 0.14);
                padding: 10px 12px;
                spacing: 12px;
            }

            QToolButton {
                background: rgba(255, 138, 61, 0.08);
                border: 1px solid rgba(255, 138, 61, 0.14);
                padding: 9px 18px;
                border-radius: 12px;
                color: #fff1e6;
                font-weight: 500;
                font-size: 13px;
            }

            QToolButton:hover {
                background: rgba(255, 138, 61, 0.16);
                border-color: rgba(255, 176, 103, 0.24);
            }

            QToolButton:pressed {
                background: rgba(123, 64, 40, 0.72);
            }

            QStatusBar {
                background: rgba(31, 23, 19, 0.92);
                border: none;
                border-top: 1px solid rgba(255, 138, 61, 0.12);
                color: #f1c9aa;
                font-size: 12px;
            }

            QSplitter {
                background-color: #17110f;
            }

            QSplitter::handle {
                background: rgba(255, 138, 61, 0.08);
                width: 8px;
                border-radius: 4px;
                margin: 8px 0;
            }

            QSplitter::handle:hover {
                background: rgba(255, 176, 103, 0.2);
            }

            QLineEdit {
                background: rgba(35, 25, 21, 0.82);
                border: 1px solid rgba(255, 138, 61, 0.16);
                border-radius: 12px;
                padding: 9px 14px;
                color: #fff1e6;
                font-size: 13px;
            }

            QLineEdit:focus {
                border: 1px solid rgba(255, 176, 103, 0.32);
                background: rgba(40, 29, 24, 0.9);
                outline: none;
            }

            QPushButton {
                background: rgba(255, 138, 61, 0.1);
                border: 1px solid rgba(255, 138, 61, 0.16);
                border-radius: 12px;
                padding: 9px 18px;
                color: #fff1e6;
                font-weight: 500;
                font-size: 13px;
            }

            QPushButton:hover {
                background: rgba(255, 176, 103, 0.16);
                border-color: rgba(255, 176, 103, 0.24);
            }

            QPushButton:pressed {
                background: rgba(123, 64, 40, 0.76);
            }

            QGroupBox {
                background: rgba(42, 30, 24, 0.76);
                border: 1px solid rgba(255, 138, 61, 0.14);
                border-radius: 16px;
                margin-top: 10px;
                padding: 16px;
            }

            QGroupBox::title {
                background-color: transparent;
                color: #ffd2b2;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }

            QLabel {
                color: #fff1e6;
                font-size: 13px;
            }

            QLabel#contentTitleLabel {
                font-size: 16px;
                font-weight: 700;
                color: #fff3ea;
            }

            QLabel#contentModeLabel {
                color: #f6d2b6;
                font-size: 12px;
                padding: 4px 10px;
                background: rgba(255, 138, 61, 0.08);
                border: 1px solid rgba(255, 138, 61, 0.12);
                border-radius: 999px;
            }

            QWidget#contentPanel {
                background: rgba(35, 25, 21, 0.74);
                border: 1px solid rgba(255, 138, 61, 0.12);
                border-radius: 22px;
            }

            QWidget#contentInfoBar {
                background: rgba(48, 34, 27, 0.62);
                border: 1px solid rgba(255, 138, 61, 0.1);
                border-radius: 16px;
            }

            QStackedWidget#contentStack {
                background: transparent;
                border: none;
            }

            QTextEdit {
                background: rgba(35, 25, 21, 0.82);
                border: 1px solid rgba(255, 138, 61, 0.16);
                border-radius: 12px;
                padding: 10px;
                color: #fff1e6;
                font-size: 13px;
            }

            QTextEdit:focus {
                border: 1px solid rgba(255, 176, 103, 0.26);
                background: rgba(40, 29, 24, 0.9);
            }

            QListView, QTreeView, QTableView, QAbstractItemView {
                background: transparent;
                color: #fff1e6;
                selection-background-color: rgba(255, 138, 61, 0.2);
                selection-color: #fff3ea;
            }

            QComboBox QAbstractItemView {
                background: rgba(36, 26, 22, 0.96);
                color: #fff1e6;
                border: 1px solid rgba(255, 138, 61, 0.18);
            }
        """

    def _get_red_orange_messagebox_style(self):
        """获取红橙主题消息框样式"""
        return """
            QMessageBox {
                background: #1a1412;
                color: #fff1e6;
            }
            QLabel {
                color: #fff1e6;
            }
            QPushButton {
                background-color: rgba(255, 138, 61, 0.18);
                color: #fff1e6;
                border: 1px solid rgba(255, 138, 61, 0.48);
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 176, 103, 0.28);
            }
        """

    def _get_red_orange_toolcard_style(self):
        """获取红橙主题工具卡片样式"""
        return """
            QFrame {
                background-color: rgba(38, 27, 23, 0.95);
                border: 1px solid rgba(255, 138, 61, 0.46);
                border-radius: 10px;
            }

            QLabel {
                color: #fff1e6;
            }

            QPushButton {
                background-color: rgba(255, 138, 61, 0.14);
                border: 1px solid rgba(255, 138, 61, 0.44);
                border-radius: 6px;
                color: #fff1e6;
            }

            QPushButton:hover {
                background-color: rgba(255, 176, 103, 0.22);
                border-color: rgba(255, 176, 103, 0.62);
            }

            QPushButton:pressed {
                background-color: rgba(123, 64, 40, 0.9);
            }
        """

    def _get_red_orange_category_style(self):
        """获取红橙主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 10px;
            }

            QListWidget::item {
                background: rgba(50, 35, 29, 0.72);
                border: 1px solid rgba(255, 138, 61, 0.14);
                border-radius: 14px;
                padding: 12px 14px;
                margin-bottom: 6px;
                color: #fff1e6;
                font-weight: 600;
                font-size: 16px;
            }

            QListWidget::item:hover {
                background: rgba(71, 48, 40, 0.84);
                border-color: rgba(255, 176, 103, 0.24);
            }

            QListWidget::item:selected {
                background: rgba(90, 58, 45, 0.8);
                color: #fff1e6;
                border-color: rgba(255, 176, 103, 0.3);
            }
        """

    def _get_red_orange_dialog_style(self):
        """获取红橙主题对话框样式"""
        return """
            QDialog { background-color: #1a1412; }
            QGroupBox { background-color: rgba(38,27,23,0.86); border: 1px solid rgba(255,138,61,0.38); border-radius: 8px; margin-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #ffd2b2; font-weight:600; }
            QLabel { color: #fff1e6; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background: #201714; color: #fff1e6; border: 1px solid rgba(255,138,61,0.44); border-radius: 6px; padding: 6px; }
            QPushButton { background-color: rgba(255,138,61,0.16); color: #fff1e6; border: 1px solid rgba(255,138,61,0.46); border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background-color: rgba(255,176,103,0.26); }
        """

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
                "name": "深绿主题",
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
        """获取深绿主题样式"""
        return """
            /* 主窗口样式 */
            QMainWindow {
                background-color: #16213e;
                border: none;
            }
            
            /* 菜单栏样式 */
            QMenuBar {
                background: rgba(46, 204, 113, 0.1);
                color: #ffffff;
                border-bottom: 1px solid rgba(46, 204, 113, 0.2);
            }
            
            QMenuBar::item {
                padding: 5px 10px;
            }
            
            QMenuBar::item:selected {
                background: rgba(46, 204, 113, 0.2);
                border-radius: 4px;
            }
            
            /* 弹出菜单样式 */
            QMenu {
                background: rgba(22, 33, 62, 0.95);
                color: #ffffff;
                border: 1px solid rgba(46, 204, 113, 0.2);
                border-radius: 8px;
                padding: 5px;
            }
            
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background: rgba(46, 204, 113, 0.2);
            }
            
            /* 工具栏样式 */
            QToolBar {
                background-color: #0f3460;
                border-bottom: 1px solid rgba(46, 204, 113, 0.3);
                padding: 10px 12px;
                spacing: 15px;
                border-radius: 0;
            }
            
            /* 工具栏按钮 */
            QToolButton {
                background: rgba(46, 204, 113, 0.1);
                border: 1px solid rgba(46, 204, 113, 0.2);
                padding: 9px 18px;
                border-radius: 8px;
                color: #ffffff;
                font-weight: 500;
                font-size: 13px;
            }
            
            QToolButton:hover {
                background: rgba(46, 204, 113, 0.2);
                border: 1px solid rgba(46, 204, 113, 0.5);
            }
            
            QToolButton:pressed {
                background: rgba(46, 204, 113, 0.3);
            }
            
            /* 状态栏 */
            QStatusBar {
                background: rgba(46, 204, 113, 0.05);
                border-top: 1px solid rgba(46, 204, 113, 0.2);
                color: #ffffff;
                font-size: 12px;
            }
            
            /* 分割器 */
            QSplitter {
                background-color: #16213e;
            }
            
            QSplitter::handle {
                background: rgba(46, 204, 113, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            
            QSplitter::handle:hover {
                background: rgba(46, 204, 113, 0.3);
            }
            
            /* 输入框 */
            QLineEdit {
                background: rgba(15, 52, 96, 0.8);
                border: 1px solid rgba(46, 204, 113, 0.2);
                border-radius: 8px;
                padding: 9px 14px;
                color: #ffffff;
                font-size: 13px;
            }
            
            QLineEdit:focus {
                border: 1px solid rgba(46, 204, 113, 0.7);
                background: rgba(15, 52, 96, 0.9);
                outline: none;
            }
            
            /* 按钮 */
            QPushButton {
                background: rgba(46, 204, 113, 0.15);
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 8px;
                padding: 9px 18px;
                color: #ffffff;
                font-weight: 500;
                font-size: 13px;
            }
            
            QPushButton:hover {
                background: rgba(46, 204, 113, 0.25);
                border: 1px solid rgba(46, 204, 113, 0.5);
            }
            
            QPushButton:pressed {
                background: rgba(46, 204, 113, 0.35);
            }
            
            QPushButton:default {
                border: 1px solid rgba(46, 204, 113, 0.5);
                background: rgba(46, 204, 113, 0.2);
            }
            
            /* 分组框 */
            QGroupBox {
                background: rgba(15, 52, 96, 0.5);
                border: 1px solid rgba(46, 204, 113, 0.2);
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
            }
            
            QGroupBox::title {
                background-color: transparent;
                color: #ffffff;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }
            
            /* 标签 */
            QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            
            /* 文本编辑框 */
            QTextEdit {
                background: rgba(15, 52, 96, 0.5);
                border: 1px solid rgba(46, 204, 113, 0.2);
                border-radius: 8px;
                padding: 10px;
                color: #ffffff;
                font-size: 13px;
            }
            
            QTextEdit:focus {
                border: 1px solid rgba(46, 204, 113, 0.5);
                background: rgba(15, 52, 96, 0.6);
                outline: none;
            }

            /* 列表视图与下拉列表弹出样式（修复下拉/选择弹窗可读性） */
            QListView, QTreeView, QTableView, QAbstractItemView {
                background: rgba(22, 33, 62, 0.95);
                color: #ffffff;
                selection-background-color: rgba(46, 204, 113, 0.2);
                selection-color: #ffffff;
            }

            QComboBox QAbstractItemView {
                background: rgba(22, 33, 62, 0.95);
                color: #ffffff;
                border: 1px solid rgba(46, 204, 113, 0.2);
            }

            /* 通用对话框（如 QInputDialog / QProgressDialog）样式调整 */
            QInputDialog, QDialog, QProgressDialog {
                background-color: #16213e;
                color: #ffffff;
            }"""
    
    def _get_blue_white_styles(self):
        """获取蓝白主题样式"""
        return """
            /* 主窗口样式 */
            QMainWindow {
                background-color: #f5f7fa;
                border: none;
            }
            
            /* 菜单栏样式 */
            QMenuBar {
                background: #ffffff;
                color: #333333;
                border-bottom: 1px solid #e0e0e0;
            }
            
            QMenuBar::item {
                padding: 5px 10px;
            }
            
            QMenuBar::item:selected {
                background: #e6f0ff;
                border-radius: 4px;
            }
            
            /* 弹出菜单样式 */
            QMenu {
                background: rgba(255, 255, 255, 0.95);
                color: #333333;
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 5px;
            }
            
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            
            QMenu::item:selected {
                background: rgba(66, 135, 245, 0.1);
            }
            
            /* 工具栏样式 */
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #4287f5;
                padding: 8px;
                spacing: 12px;
            }
            
            /* 工具栏按钮 */
            QToolButton {
                background: rgba(66, 135, 245, 0.05);
                border: 1px solid rgba(66, 135, 245, 0.2);
                padding: 8px 16px;
                border-radius: 8px;
                color: #333333;
                font-weight: 500;
            }
            
            QToolButton:hover {
                background: rgba(66, 135, 245, 0.1);
                border: 1px solid rgba(66, 135, 245, 0.5);
            }
            
            QToolButton:pressed {
                background: rgba(66, 135, 245, 0.2);
            }
            
            /* 状态栏 */
            QStatusBar {
                background: rgba(255, 255, 255, 0.9);
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                color: #333333;
                font-size: 12px;
            }
            
            /* 分割器 */
            QSplitter {
                background-color: #f0f4f8;
            }
            
            QSplitter::handle {
                background: rgba(0, 0, 0, 0.1);
                width: 6px;
                border-radius: 3px;
            }
            
            QSplitter::handle:hover {
                background: rgba(66, 135, 245, 0.3);
            }
            
            /* 输入框 */
            QLineEdit {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 8px 12px;
                color: #333333;
                font-size: 13px;
            }
            
            QLineEdit:focus {
                border: 1px solid rgba(66, 135, 245, 0.5);
                background: rgba(255, 255, 255, 1);
                outline: none;
            }
            
            /* 按钮 */
            QPushButton {
                background: rgba(66, 135, 245, 0.1);
                border: 1px solid rgba(66, 135, 245, 0.3);
                border-radius: 8px;
                padding: 8px 16px;
                color: #333333;
                font-weight: 500;
                font-size: 13px;
            }
            
            QPushButton:hover {
                background: rgba(66, 135, 245, 0.2);
                border: 1px solid rgba(66, 135, 245, 0.5);
            }
            
            QPushButton:pressed {
                background: rgba(66, 135, 245, 0.3);
            }
            
            QPushButton:default {
                border: 1px solid rgba(66, 135, 245, 0.5);
            }
            
            /* 分组框 */
            QGroupBox {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 10px;
                margin-top: 10px;
                padding: 15px;
            }
            
            QGroupBox::title {
                background-color: transparent;
                color: #333333;
                font-weight: 600;
                font-size: 14px;
                padding: 0 10px;
                margin-top: -10px;
            }
            
            /* 标签 */
            QLabel {
                color: #333333;
                font-size: 13px;
            }
            
            /* 文本编辑框 */
            QTextEdit {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 10px;
                color: #333333;
                font-size: 13px;
            }"""
    
    def _get_dark_green_messagebox_style(self):
        """获取深绿主题消息框样式"""
        return """
            QMessageBox {
                background: #16213e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: rgba(46, 204, 113, 0.15);
                color: #ffffff;
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 6px;
                padding: 6px 10px;
            }
            QPushButton:hover {
                background-color: rgba(46, 204, 113, 0.25);
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
        """获取深绿主题工具卡片样式"""
        return """
            QFrame {
                background-color: rgba(15, 52, 96, 0.95);
                border: 1px solid rgba(46, 204, 113, 0.2);
                border-radius: 8px;
            }
            
            QLabel {
                color: #ffffff;
            }
            
            QPushButton {
                background-color: rgba(46, 204, 113, 0.15);
                border: 1px solid rgba(46, 204, 113, 0.3);
                border-radius: 4px;
                color: #ffffff;
            }
            
            QPushButton:hover {
                background-color: rgba(46, 204, 113, 0.25);
                border: 1px solid rgba(46, 204, 113, 0.5);
            }
            
            QPushButton:pressed {
                background-color: rgba(46, 204, 113, 0.35);
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
        """获取深绿主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            
            QListWidget::item {
                background: rgba(32, 33, 54, 0.8);
                border: 1px solid rgba(144, 238, 144, 0.2);
                border-radius: 8px;
                padding: 12px 14px;
                margin-bottom: 4px;
                color: #ffffff;
                font-weight: 500;
                font-size: 16px;
            }
            
            QListWidget::item:hover {
                background: rgba(40, 42, 66, 0.9);
                border-color: rgba(144, 238, 144, 0.5);
            }
            
            QListWidget::item:selected {
                background: rgba(144, 238, 144, 0.2);
                color: #ffffff;
                border-color: rgba(144, 238, 144, 0.7);
            }
        """

    def _get_blue_white_category_style(self):
        """获取蓝白主题分类视图样式"""
        return """
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 8px;
            }
            
            QListWidget::item {
                background: #f0f9ff;
                border: 1px solid #bae6fd;
                border-radius: 10px;
                padding: 12px 14px;
                margin-bottom: 6px;
                color: #0369a1;
                font-weight: 600;
                font-size: 16px;
            }
            
            QListWidget::item:hover {
                background: #e0f2fe;
                border-color: #7dd3fc;
            }
            
            QListWidget::item:selected {
                background: #e0f2fe;
                color: #0369a1;
                border-color: #7dd3fc;
            }
        """

    def _get_dark_green_dialog_style(self):
        """获取深绿主题对话框样式"""
        return """
            QDialog { background-color: #111217; }
            QGroupBox { background-color: rgba(22,24,36,0.6); border: 1px solid rgba(144,238,144,0.12); border-radius: 8px; margin-top: 4px; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #90ee90; font-weight:600; }
            QLabel { color: #dfeee0; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background: rgba(32,33,54,0.9); color: #ffffff; border: 1px solid rgba(144,238,144,0.08); border-radius: 6px; padding: 6px; }
            QPushButton { background-color: rgba(144,238,144,0.06); color: #e8ffea; border: 1px solid rgba(144,238,144,0.16); border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background-color: rgba(144,238,144,0.14); }
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
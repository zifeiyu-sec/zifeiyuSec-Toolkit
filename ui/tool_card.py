import os
import sys
from PyQt5.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QMessageBox, QMenu, QScrollArea, 
                           QWidget, QGridLayout, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor

# 获取资源目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# prefer the project's resources/icons folder for default icons (SVGs)
RESOURCE_ICON_DIR = os.path.join(BASE_DIR, 'resources', 'icons')
ICON_DIR = os.path.join(BASE_DIR, 'assets', 'icons')  # legacy location (may not exist)
# DEFAULT_ICON_PATH: look in resources/icons first, fallback to assets/icons path
DEFAULT_ICON_PATH = os.path.join(RESOURCE_ICON_DIR, 'new_default_icon.svg')
if not os.path.exists(DEFAULT_ICON_PATH):
    DEFAULT_ICON_PATH = os.path.join(RESOURCE_ICON_DIR, 'default_tool_icon.svg')

class ToolCard(QFrame):
    """工具卡片组件，用于显示单个工具的信息和操作按钮"""
    # 信号定义
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    
    def __init__(self, tool_data, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data
        self.current_theme = "dark_green"  # 默认深色主题
        self.process = None  # 用于存储进程引用
        
        # 创建阴影效果
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(8)
        self.shadow.setOffset(0, 3)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(self.shadow)
        
        self.init_ui()
    
    def init_ui(self):
        # 设置布局
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)
        # 固定卡片大小（在工具区保证每行两个卡片时适配宽度）
        # 选择一个在默认工具区宽度下能够显示两列的合理大小
        # Reduce default card size to make layout more compact
        # New size chosen for compact display while keeping readability
        self.setFixedSize(260, 110)
        
        # 图标按钮
        self.icon_button = QPushButton()
        # 卡片图标增大一点，位于左侧
        # Shrink icon to fit compact card
        self.icon_button.setFixedSize(56, 56)
        self.update_icon()
        self.icon_button.clicked.connect(self.on_run_clicked)
        
        # 右侧信息布局
        info_layout = QVBoxLayout()
        # 名称标签
        self.name_label = QLabel(self.tool_data['name'])
        # 保持单行高，超出显示省略
        self.name_label.setFixedHeight(20)
        self.name_label.setStyleSheet('font-weight:700;')
        self.name_label.setAlignment(Qt.AlignLeft)
        # 去掉文本的边框与背景
        self.name_label.setStyleSheet(self.name_label.styleSheet() + "background: transparent; border: none; padding: 0px; margin: 0px;")
        
        # 描述标签
        description = self.tool_data.get('description', '无介绍')
        self.description_label = QLabel(description)
        self.description_label.setAlignment(Qt.AlignLeft)
        self.description_label.setWordWrap(True)
        # 去掉描述的边框与背景
        self.description_label.setStyleSheet("background: transparent; border: none; padding: 0px; margin: 0px;")
        # 限制描述高度，避免卡片高度随内容膨胀
        # smaller description area for compact layout
        self.description_label.setFixedHeight(44)
        self.description_label.setAlignment(Qt.AlignLeft)
        self.description_label.setWordWrap(True)
        
        # 添加标签到布局
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.description_label)
        
        # 以前有收藏和运行按钮；现在删除收藏按钮并保留空白占位
        button_layout = QHBoxLayout()
        button_layout.setSpacing(4)
        # 为保持布局一致性，添加伸缩空间
        button_layout.addStretch(1)
        
        info_layout.addLayout(button_layout)
        
        # 添加到主布局
        main_layout.addWidget(self.icon_button)
        main_layout.addLayout(info_layout)
        
        # 设置右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # 应用主题样式
        self.apply_theme_styles()
    
    # 收藏按钮已移除（UI 简化），保留接口兼容但不再使用
    
    def update_icon(self):
        # 更新工具图标：优先使用 tool_data['icon']（相对 resources/icons 或绝对路径）
        icon_value = self.tool_data.get('icon') or self.tool_data.get('icon_path') or ''

        # Helper to try load a QIcon from a candidate path
        def try_set_icon(candidate):
            if not candidate:
                return False
            # if it's a URL we avoid attempting to fetch remotely here
            if isinstance(candidate, str) and (candidate.startswith('http://') or candidate.startswith('https://')):
                return False
            # absolute path - check exists
            if os.path.isabs(candidate) and os.path.exists(candidate):
                icon = QIcon(candidate)
                if not icon.isNull():
                    self.icon_button.setIcon(icon)
                    self.icon_button.setIconSize(self.icon_button.size())
                    return True
                return False

            # try resource icons folder (relative names)
            candidate_path = os.path.join(RESOURCE_ICON_DIR, candidate)
            if os.path.exists(candidate_path):
                icon = QIcon(candidate_path)
                if not icon.isNull():
                    self.icon_button.setIcon(icon)
                    self.icon_button.setIconSize(self.icon_button.size())
                    return True

            # legacy icons folder
            candidate_path2 = os.path.join(ICON_DIR, candidate)
            if os.path.exists(candidate_path2):
                icon = QIcon(candidate_path2)
                if not icon.isNull():
                    self.icon_button.setIcon(icon)
                    self.icon_button.setIconSize(self.icon_button.size())
                    return True

            return False

        set_ok = False
        if icon_value:
            set_ok = try_set_icon(icon_value)

        # fallback to default resource icon
        if not set_ok and os.path.exists(DEFAULT_ICON_PATH):
            icon = QIcon(DEFAULT_ICON_PATH)
            if not icon.isNull():
                self.icon_button.setIcon(icon)
                self.icon_button.setIconSize(self.icon_button.size())
                set_ok = True

        # if still not set, show text label
        if not set_ok:
            self.icon_button.setText('工具')
    
    def on_run_clicked(self):
        # 运行工具
        self.run_tool.emit(self.tool_data)

    def mousePressEvent(self, event):
        # 左键点击整张卡片触发运行；右键保留原有行为（如上下文菜单）
        try:
            if event.button() == Qt.LeftButton:
                # 只有在左键才触发运行
                self.on_run_clicked()
                return
        except Exception:
            pass

        # 对于其他事件，默认行为交由父类处理（包括右键上下文菜单）
        super().mousePressEvent(event)
    
    # on_favorite_clicked removed — 收藏 UI 已移除
    
    def show_context_menu(self, position):
        # 显示右键菜单
        menu = QMenu(self)
        
        # 运行菜单项
        run_action = menu.addAction("运行工具")
        run_action.triggered.connect(self.on_run_clicked)
        
        # 编辑菜单项
        edit_action = menu.addAction("编辑工具")
        edit_action.triggered.connect(self.on_edit_requested)
        
        # 收藏菜单项
        is_favorite = self.tool_data.get('is_favorite', False)
        favorite_action = menu.addAction("取消收藏" if is_favorite else "添加收藏")
        # 右键菜单收藏项仍然可用——触发 toggle_favorite 信号
        favorite_action.triggered.connect(lambda: self.toggle_favorite.emit(self.tool_data.get('id')))
        
        # 分隔线
        menu.addSeparator()
        
        # 删除菜单项
        delete_action = menu.addAction("删除工具")
        delete_action.triggered.connect(self.on_delete_requested)
        
        # 显示菜单
        menu.exec_(self.mapToGlobal(position))
    
    def on_edit_requested(self):
        # 请求编辑工具
        self.edit_requested.emit(self.tool_data)
    
    def on_delete_requested(self):
        # 请求删除工具 - 使用本地主题样式的提示框
        box = QMessageBox(self)
        box.setWindowTitle('确认删除')
        box.setText(f'确定要删除工具 "{self.tool_data["name"]}" 吗？')
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)

        # local thematic style
        if self.current_theme == 'blue_white':
            box.setStyleSheet('''
                QMessageBox { background: #f6fbff; color: #003347; }
                QLabel { color: #003347; }
                QPushButton { background-color: rgba(66,135,245,0.06); color: #003347; border-radius: 6px; padding: 6px 10px; }
            ''')
        else:
            box.setStyleSheet('''
                QMessageBox { background: #0f1113; color: #e5ffe9; }
                QLabel { color: #e5ffe9; }
                QPushButton { background-color: rgba(144,238,144,0.06); color: #e5ffe9; border-radius: 6px; padding: 6px 10px; }
            ''')

        if box.exec_() == QMessageBox.Yes:
            tool_id = self.tool_data['id']
            self.deleted.emit(tool_id)
    
    def update_data(self, tool_data):
        # 更新工具数据
        self.tool_data = tool_data
        self.name_label.setText(self.tool_data['name'])
        self.description_label.setText(self.tool_data.get('description', '无介绍'))
        self.update_icon()
        # 收藏按钮已移除，界面无需更新收藏状态
    
    def set_theme(self, theme_name):
        # 设置主题
        self.current_theme = theme_name
        self.apply_theme_styles()
        
        # 更新阴影效果
        if self.current_theme == "light":
            self.shadow.setBlurRadius(6)
            self.shadow.setColor(QColor(0, 0, 0, 80))
        else:
            self.shadow.setBlurRadius(8)
            self.shadow.setColor(QColor(0, 0, 0, 100))
        # 在设置主题时也强制卡片尺寸（防止外部布局改变）
        try:
            self.setFixedSize(260, 110)
        except Exception:
            pass
    
    def apply_theme_styles(self):
        # 应用主题样式
        if self.current_theme in ("light", "blue_white"):
            # 浅色主题样式
            self.setStyleSheet("""
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
                }
            """)
        else:
            # 深色主题样式
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(32, 33, 54, 0.95);
                    border: 1px solid rgba(144, 238, 144, 0.2);
                    border-radius: 8px;
                }
                
                QLabel {
                    color: #ffffff;
                }
                
                QPushButton {
                    background-color: rgba(144, 238, 144, 0.1);
                    border: 1px solid rgba(144, 238, 144, 0.3);
                    border-radius: 4px;
                    color: #ffffff;
                }
                
                QPushButton:hover {
                    background-color: rgba(144, 238, 144, 0.2);
                    border: 1px solid rgba(144, 238, 144, 0.5);
                }
                
                QPushButton:pressed {
                    background-color: rgba(144, 238, 144, 0.3);
                }
            """)

class ToolCardContainer(QWidget):
    """工具卡片容器组件，用于显示多个工具卡片，支持滚动和主题切换"""
    # 信号定义
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    new_tool_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "dark_green"  # 默认深色主题
        self.tool_cards = []  # 存储工具卡片
        self.init_ui()
    
    def init_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 创建内容部件
        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        # 确保网格中的卡片默认顶部对齐（即使只有一张卡片也显示在顶部）
        try:
            self.grid_layout.setAlignment(Qt.AlignTop)
        except Exception:
            pass
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(16, 16, 16, 16)
        
        # 设置滚动区域内容
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)
        
        # 应用主题样式
        self.apply_theme_styles()
    
    def set_theme(self, theme_name):
        # 设置主题
        self.current_theme = theme_name
        self.apply_theme_styles()
        
        # 更新所有工具卡片的主题
        for card in self.tool_cards:
            card.set_theme(theme_name)
    
    def apply_theme_styles(self):
        # 应用主题样式
        if self.current_theme in ("light", "blue_white"):
            # 浅色主题样式
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #f0f4f8;
                    border: none;
                }
                
                QScrollArea QWidget {
                    background-color: #f0f4f8;
                }
                
                QScrollBar:vertical {
                    width: 8px;
                    background: rgba(0, 0, 0, 0.05);
                    border-radius: 4px;
                }
                
                QScrollBar::handle:vertical {
                    background: rgba(66, 135, 245, 0.3);
                    border-radius: 4px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background: rgba(66, 135, 245, 0.5);
                }
            """)
        else:
            # 深色主题样式
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    background-color: #1a1a2e;
                    border: none;
                }
                
                QScrollArea QWidget {
                    background-color: #1a1a2e;
                }
                
                QScrollBar:vertical {
                    width: 8px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 4px;
                }
                
                QScrollBar::handle:vertical {
                    background: rgba(144, 238, 144, 0.3);
                    border-radius: 4px;
                }
                
                QScrollBar::handle:vertical:hover {
                    background: rgba(144, 238, 144, 0.5);
                }
            """)
    
    def display_tools(self, tools):
        # 显示工具列表
        # 清除现有卡片
        self.clear_cards()
        
        # 添加新卡片（每行固定两列）
        for tool in tools:
            self.add_tool_card(tool)
    
    def add_tool_card(self, tool_data):
        # 添加工具卡片
        card = ToolCard(tool_data)
        card.set_theme(self.current_theme)
        
        # 连接信号
        card.run_tool.connect(self.run_tool)
        card.edit_requested.connect(self.edit_requested)
        card.deleted.connect(self.deleted)
        card.toggle_favorite.connect(self.toggle_favorite)
        
        # 添加到列表和布局
        self.tool_cards.append(card)
        
        # 强制每行显示 2 列，卡片宽度在 ToolCard 中固定为 300
        columns = 2
        
        # 计算位置（每行两列）
        index = len(self.tool_cards) - 1
        row = index // columns
        col = index % columns
        
        # 将卡片添加到网格，并确保顶部对齐
        self.grid_layout.addWidget(card, row, col, alignment=Qt.AlignTop)

        # 使最后一行下面的行占位可伸缩，从而将所有卡片推到顶部
        # 清理掉下一行的拉伸设置后再设置为可伸缩
        # 把下一行（row+1）设为弹性行
        # 先将所有行的 stretch 清理（保守处理）
        try:
            # 先清理后续行的 stretch
            total_rows = max(1, row + 2)
            for r in range(total_rows + 1):
                self.grid_layout.setRowStretch(r, 0)
            # 让下一行吸收剩余空间
            self.grid_layout.setRowStretch(row + 1, 1)
        except Exception:
            pass
    
    def clear_cards(self):
        # 清除所有卡片
        for card in self.tool_cards:
            self.grid_layout.removeWidget(card)
            card.deleteLater()
        self.tool_cards.clear()
    
    def update_tool(self, tool_id, updated_data):
        # 更新工具卡片数据
        for card in self.tool_cards:
            if card.tool_data['id'] == tool_id:
                card.update_data(updated_data)
                break
    
    def remove_tool(self, tool_id):
        # 移除工具卡片
        for i, card in enumerate(self.tool_cards):
            if card.tool_data['id'] == tool_id:
                self.grid_layout.removeWidget(card)
                card.deleteLater()
                del self.tool_cards[i]
                # 重新排列剩余卡片
                self._rearrange_cards()
                break
    
    def _rearrange_cards(self):
        # 重新排列卡片
        # 保存当前工具数据
        tools_data = [card.tool_data for card in self.tool_cards]
        
        # 清除并重新添加
        self.clear_cards()
        for tool_data in tools_data:
            self.add_tool_card(tool_data)

# 测试代码
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建示例工具数据
    tools = [
        {
            'id': 1,
            'name': 'Nmap 扫描工具',
            'description': '强大的网络扫描和安全评估工具',
            'is_favorite': True
        },
        {
            'id': 2,
            'name': 'SQLmap',
            'description': '自动化SQL注入工具',
            'is_favorite': False
        },
        {
            'id': 3,
            'name': 'Burp Suite',
            'description': 'Web应用安全测试工具',
            'is_favorite': True
        }
    ]
    
    # 创建工具卡片容器
    container = ToolCardContainer()
    container.display_tools(tools)
    
    # 创建窗口
    window = QWidget()
    window.setWindowTitle('工具卡片测试')
    window.resize(1200, 800)
    
    # 添加容器到窗口
    layout = QVBoxLayout(window)
    layout.addWidget(container)
    
    window.show()
    sys.exit(app.exec_())

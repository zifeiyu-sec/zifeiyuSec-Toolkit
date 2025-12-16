import os
from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon

# 图标缓存，减少重复的文件系统操作
category_icon_cache = {}

class CategoryView(QWidget):
    """分类视图，显示一级分类列表"""
    # 信号定义：当分类被选择时发出
    category_selected = pyqtSignal(int)  # 仅发出category_id
    # 右键菜单信号
    new_category_requested = pyqtSignal()
    new_subcategory_requested = pyqtSignal(int)  # 参数为父分类ID
    delete_category_requested = pyqtSignal(int)  # 参数为要删除的分类ID
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_category = None
        self.current_theme = 'dark_green'  # 默认主题
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 分类标题
        self.title_label = QLabel("分类")
        layout.addWidget(self.title_label)
        
        # 创建分类列表控件
        self.category_list = QListWidget()
        # 确保列表有足够宽度显示完整的分类名称
        self.category_list.setMinimumWidth(260)
        self.category_list.setSelectionMode(QListWidget.SingleSelection)
        
        # 应用当前主题样式
        self.apply_theme_styles()
        
        # 连接信号
        self.category_list.itemClicked.connect(self.on_item_clicked)
        # 设置右键菜单
        self.category_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_list.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.category_list)
        
        # 确保组件最小宽度，避免被 splitter 收缩过小
        self.setMinimumWidth(260)

        # 加载分类数据
        self.load_categories()
    
    def load_categories(self):
        """加载分类数据，只显示一级分类"""
        self.category_list.clear()
        
        # 从数据管理器加载分类
        categories = self.data_manager.load_categories()
        
        # 过滤出一级分类
        root_categories = []
        
        for category in categories:
            if isinstance(category, dict):
                # 只处理一级分类，忽略有parent_id的项
                if 'subcategories' in category or ('parent_id' not in category or category['parent_id'] is None):
                    root_categories.append(category)
        
        # 创建分类项
        for category in root_categories:
            # 创建分类项，显示名称和可选图标
            name = category.get('name', '未知分类')
            
            # 优化：先创建列表项，延迟加载图标，避免启动时阻塞
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, {'id': category.get('id', 0)})
            self.category_list.addItem(item)
            
            # 移除图标加载逻辑
            # if 'icon' in category and isinstance(category['icon'], str) and category['icon'] != 'default_icon':
            #     def load_icon_delayed(item_ref, icon_name):
            #         # ... (removed)
            #     from PyQt5.QtCore import QTimer
            #     QTimer.singleShot(200, lambda: load_icon_delayed(item, category['icon']))
        
        # 优化：延迟加载工具，避免启动时阻塞
        # 如果有分类，默认选中第一个分类，但延迟触发加载
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)
            first_item = self.category_list.item(0)
            data = first_item.data(Qt.UserRole)
            self.current_category = data['id']
            # 使用 QTimer 延迟触发，让 UI 先显示（增加延迟时间到300ms）
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(300, lambda: self.category_selected.emit(data['id']))
    
    def on_item_clicked(self, item):
        """处理分类项点击事件"""
        data = item.data(Qt.UserRole)
        self.current_category = data['id']
        self.category_selected.emit(data['id'])
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 添加新建分类菜单项
        new_category_action = QAction("新建分类", self)
        new_category_action.triggered.connect(self.new_category_requested.emit)
        menu.addAction(new_category_action)
        
        # 获取当前选中的分类
        selected_items = self.category_list.selectedItems()
        if selected_items:
            # 添加分隔符
            menu.addSeparator()
            
            # 添加新建子分类菜单项
            new_subcategory_action = QAction("新建子分类", self)
            new_subcategory_action.triggered.connect(lambda: self.new_subcategory_requested.emit(self.current_category))
            menu.addAction(new_subcategory_action)
            
            # 添加删除分类菜单项
            delete_category_action = QAction("删除分类", self)
            delete_category_action.triggered.connect(lambda: self.delete_category_requested.emit(self.current_category))
            menu.addAction(delete_category_action)
        
        # 显示菜单
        menu.exec_(self.category_list.mapToGlobal(position))
    
    def refresh(self):
        """刷新分类列表"""
        self.load_categories()
        
    def set_theme(self, theme):
        """设置当前主题并应用样式"""
        self.current_theme = theme
        self.apply_theme_styles()
        
    def apply_theme_styles(self):
        """根据当前主题应用样式"""
        if self.current_theme == 'blue_white':
            # 蓝白配色主题样式 — 白色背景，黑色标题文字，分类项为淡蓝卡片
            self.title_label.setStyleSheet("font-weight: 600; padding: 12px; border-bottom: 1px solid #e6f2ff; background-color: #ffffff; color: #000000; font-size: 14px;")
            self.category_list.setStyleSheet("""
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
            """)
        else:
            # 默认深色主题样式
            self.title_label.setStyleSheet("font-weight: 600; padding: 12px; border-bottom: 1px solid rgba(144, 238, 144, 0.3); background-color: rgba(26, 28, 43, 1); color: #90ee90; font-size: 14px;")
            self.category_list.setStyleSheet("""
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
                    /* removed: transition not supported in Qt QSS */
                }
                
                QListWidget::item:hover {
                    background: rgba(40, 42, 66, 0.9);
                    border-color: rgba(144, 238, 144, 0.5);
                    /* removed: box-shadow not supported in Qt QSS */
                }
                
                QListWidget::item:selected {
                    background: rgba(144, 238, 144, 0.2);
                    color: #ffffff;
                    border-color: rgba(144, 238, 144, 0.7);
                    /* removed: box-shadow not supported in Qt QSS */
                }
            """)
    
    def select_category(self, category_id):
        """手动选择分类"""
        # 遍历所有项查找匹配的分类
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            data = item.data(Qt.UserRole)
            
            if data['id'] == category_id:
                # 找到了匹配的分类
                self.category_list.setCurrentItem(item)
                self.current_category = category_id
                self.category_selected.emit(category_id)
                return True
        
        return False
    
    def get_selected_category(self):
        """获取当前选中的分类信息"""
        current_item = self.category_list.currentItem()
        if not current_item:
            return None
        
        data = current_item.data(Qt.UserRole)
        return data['id']

if __name__ == "__main__":
    import sys
    import os
    # 添加项目根目录到Python路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from PyQt5.QtWidgets import QApplication
    from core.data_manager import DataManager
    
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建相对于脚本的data目录路径
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    
    app = QApplication(sys.argv)
    
    # 创建数据管理器
    data_manager = DataManager(data_dir)
    
    # 创建分类视图
    category_view = CategoryView(data_manager)
    category_view.setWindowTitle("工具分类")
    category_view.setGeometry(100, 100, 250, 600)
    category_view.show()
    
    sys.exit(app.exec_())

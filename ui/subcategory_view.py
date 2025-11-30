import os
from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon

class SubcategoryView(QWidget):
    """子分类视图，显示指定分类下的子分类列表"""
    # 信号定义：当子分类被选择时发出
    subcategory_selected = pyqtSignal(int, int)  # (category_id, subcategory_id)
    # 右键菜单信号
    new_subcategory_requested = pyqtSignal(int)  # 参数为父分类ID
    delete_subcategory_requested = pyqtSignal(int)  # 参数为要删除的子分类ID
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.current_category = None
        self.current_subcategory = None
        self.current_theme = 'dark_green'  # 默认深色主题
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标题标签
        self.title_label = QLabel("子分类")
        
        # 创建子分类列表
        self.subcategory_list = QListWidget()
        # 给子分类列表设置最小宽度，保证长名称能完整显示
        self.subcategory_list.setMinimumWidth(200)
        self.subcategory_list.itemClicked.connect(self.on_item_clicked)
        # 设置右键菜单
        self.subcategory_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.subcategory_list.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.subcategory_list)

        # 设置子分类视图最小宽度，避免 splitter 缩得太窄
        self.setMinimumWidth(300)
        
        # 应用初始主题样式
        self.apply_theme_styles()
        
    def set_theme(self, theme_name):
        """设置主题"""
        self.current_theme = theme_name
        self.apply_theme_styles()
        
    def apply_theme_styles(self):
        """根据当前主题应用样式"""
        if self.current_theme == 'blue_white':
            # 蓝白主题样式
            self.title_label.setStyleSheet("padding: 10px; background-color: #e6f2ff; font-weight: 600; border-bottom: 1px solid #99ccff; color: #003366; font-size: 14px;")
            
            self.subcategory_list.setStyleSheet("""
                QListWidget {
                    background-color: transparent;
                    border: none;
                    padding: 5px;
                }
                
                QListWidget::item {
                    background: rgba(240, 248, 255, 0.9);
                    border: 1px solid rgba(135, 206, 250, 0.3);
                    border-radius: 10px;
                    padding: 12px;
                    margin-bottom: 5px;
                    color: #000000;
                    font-weight: 500;
                }
                
                QListWidget::item:hover {
                    background: rgba(240, 248, 255, 1);
                    border-color: rgba(65, 105, 225, 0.5);
                }
                
                QListWidget::item:selected {
                    background: rgba(135, 206, 250, 0.2);
                    color: #000000;
                    border-color: rgba(65, 105, 225, 0.5);
                }
            """)
        else:  # dark_green 主题
            # 深色主题样式
            self.title_label.setStyleSheet("padding: 10px; background-color: #2d2d2d; font-weight: 600; border-bottom: 1px solid #2d5016; color: #90ee90; font-size: 14px;")
            
            self.subcategory_list.setStyleSheet("""
                QListWidget {
                    background-color: transparent;
                    border: none;
                    padding: 5px;
                }
                
                QListWidget::item {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                    padding: 12px;
                    margin-bottom: 5px;
                    color: #ffffff;
                    font-weight: 500;
                }
                
                QListWidget::item:hover {
                    background: rgba(255, 255, 255, 0.1);
                    border-color: rgba(103, 232, 249, 0.5);
                }
                
                QListWidget::item:selected {
                    background: rgba(103, 232, 249, 0.15);
                    color: #ffffff;
                    border-color: rgba(103, 232, 249, 0.5);
                }
            """)
    
    def load_subcategories(self, category_id):
        """加载指定分类下的子分类"""
        self.current_category = category_id
        self.current_subcategory = None
        self.subcategory_list.clear()
        
        # 从数据管理器获取子分类数据
        subcategories = self.data_manager.get_subcategories_by_category(category_id)
        
        # 添加子分类项到列表
        for subcategory in subcategories:
            item = QListWidgetItem(subcategory['name'])
            item.setData(Qt.UserRole, {'id': subcategory['id'], 'name': subcategory['name']})
            self.subcategory_list.addItem(item)
    
    def on_item_clicked(self, item):
        """处理子分类项点击事件"""
        data = item.data(Qt.UserRole)
        self.current_subcategory = data['id']
        self.subcategory_selected.emit(self.current_category, data['id'])
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 无论是否有选中项，都可以添加新子分类
        # 添加新建子分类菜单项
        new_subcategory_action = QAction("新建子分类", self)
        new_subcategory_action.triggered.connect(lambda: self.new_subcategory_requested.emit(self.current_category))
        menu.addAction(new_subcategory_action)
        
        # 获取当前选中的子分类
        selected_items = self.subcategory_list.selectedItems()
        if selected_items:
            
            # 添加删除子分类菜单项
            delete_subcategory_action = QAction("删除子分类", self)
            delete_subcategory_action.triggered.connect(lambda: self.delete_subcategory_requested.emit(self.current_subcategory))
            menu.addAction(delete_subcategory_action)
        
        # 显示菜单
        menu.exec_(self.subcategory_list.mapToGlobal(position))
    
    def select_subcategory(self, subcategory_id):
        """手动选择指定ID的子分类"""
        for i in range(self.subcategory_list.count()):
            item = self.subcategory_list.item(i)
            data = item.data(Qt.UserRole)
            if data['id'] == subcategory_id:
                self.subcategory_list.setCurrentItem(item)
                self.current_subcategory = subcategory_id
                self.subcategory_selected.emit(self.current_category, subcategory_id)
                return True
        return False
    
    def get_selected_subcategory(self):
        """获取当前选中的子分类信息"""
        if self.current_subcategory is None:
            return None
        
        for i in range(self.subcategory_list.count()):
            item = self.subcategory_list.item(i)
            data = item.data(Qt.UserRole)
            if data['id'] == self.current_subcategory:
                return data
        return None

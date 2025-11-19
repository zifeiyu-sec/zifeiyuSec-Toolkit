from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
import os

class CategoryView(QWidget):
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
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 分类标题
        title_label = QLabel("分类")
        title_label.setStyleSheet("font-weight: 600; padding: 10px; border-bottom: 1px solid #2d5016; background-color: #2d2d2d; color: #90ee90; font-size: 14px;")
        layout.addWidget(title_label)
        
        # 创建分类列表控件
        self.category_list = QListWidget()
        self.category_list.setSelectionMode(QListWidget.SingleSelection)
        
        # 设置列表控件样式，增加间距和整体美观度
        self.category_list.setStyleSheet("""
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
        
        # 连接信号
        self.category_list.itemClicked.connect(self.on_item_clicked)
        # 设置右键菜单
        self.category_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_list.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.category_list)
        
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
            
            # 处理图标显示
            if 'icon' in category and isinstance(category['icon'], str) and category['icon'] != 'default_icon':
                # 尝试加载图标
                try:
                    # 移除可能的'icons/'前缀
                    icon_name = category['icon']
                    if icon_name.startswith('icons/'):
                        icon_name = icon_name[6:]
                    
                    # 尝试加载图标
                    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'icons', icon_name)
                    if os.path.exists(icon_path):
                        item = QListWidgetItem(name)
                        item.setIcon(QIcon(icon_path))
                        item.setData(Qt.UserRole, {'id': category.get('id', 0)})
                        self.category_list.addItem(item)
                        continue
                except Exception as e:
                    print(f"加载图标失败: {e}")
            
            # 默认显示方式
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, {'id': category.get('id', 0)})
            self.category_list.addItem(item)
        
        # 如果有分类，默认选中第一个分类
        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)
            first_item = self.category_list.item(0)
            data = first_item.data(Qt.UserRole)
            self.current_category = data['id']
            self.category_selected.emit(data['id'])
    
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
    from PyQt5.QtWidgets import QApplication
    from ..core.data_manager import DataManager
    
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
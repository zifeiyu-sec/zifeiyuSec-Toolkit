from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QDropEvent
from core.style_manager import ThemeManager

# 自定义分类列表控件，支持拖拽排序
class DraggableCategoryListWidget(QListWidget):
    # 拖拽完成信号
    order_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setMovement(QListWidget.Snap)
        self.setUniformItemSizes(True)
    
    def dropEvent(self, event: QDropEvent):
        """处理拖拽完成事件"""
        super().dropEvent(event)
        # 使用延迟发射信号，确保列表状态完全稳定
        # 这有助于避免拖拽过程中临时创建的重复项被处理
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.order_changed.emit)

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
        self.setObjectName("subcategoryPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标题标签
        self.title_label = QLabel("子分类")
        
        # 创建子分类列表
        self.subcategory_list = DraggableCategoryListWidget()
        # 给子分类列表设置最小宽度，保证长名称能完整显示
        self.subcategory_list.setMinimumWidth(200)
        self.subcategory_list.itemClicked.connect(self.on_item_clicked)
        # 设置右键菜单
        self.subcategory_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.subcategory_list.customContextMenuRequested.connect(self.show_context_menu)
        # 连接拖拽排序信号
        self.subcategory_list.order_changed.connect(self.on_subcategory_order_changed)
        
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
        # 从 StyleManager 获取样式
        # 注意：子分类视图样式与主分类视图非常相似，这里复用 category_view 样式
        # 如果需要区分，可以在 StyleManager 新增 get_subcategory_view_style
        theme_manager = ThemeManager()
        if self.current_theme == 'blue_white':
            self.setStyleSheet("QWidget#subcategoryPanel { background: rgba(224,247,255,0.34); border: 1px solid rgba(151,213,244,0.56); border-radius: 24px; }")
        elif self.current_theme == 'celadon_mist':
            self.setStyleSheet("QWidget#subcategoryPanel { background: rgba(208,250,250,0.34); border: 1px solid rgba(137,220,223,0.56); border-radius: 24px; }")
        elif self.current_theme == 'dark_green':
            self.setStyleSheet("QWidget#subcategoryPanel { background: rgba(0,10,12,0.28); border: 1px solid rgba(0,229,255,0.42); border-right: 1px solid rgba(255,51,102,0.28); border-bottom: 1px solid rgba(255,51,102,0.18); border-radius: 12px; }")
        elif self.current_theme == 'purple_neon':
            self.setStyleSheet("QWidget#subcategoryPanel { background: rgba(13,2,22,0.32); border: 1px solid rgba(255,207,92,0.54); border-right: 1px solid rgba(189,58,255,0.34); border-bottom: 1px solid rgba(255,207,92,0.38); border-radius: 24px; }")
        elif self.current_theme == 'red_orange':
            self.setStyleSheet("QWidget#subcategoryPanel { background: rgba(102,0,0,0.44); border: 1px solid rgba(255,205,92,0.72); border-right: 1px solid rgba(255,86,48,0.46); border-bottom: 1px solid rgba(255,205,92,0.58); border-radius: 24px; }")
        else:
            self.setStyleSheet("QWidget#subcategoryPanel { background: rgba(24,58,39,0.70); border: 1px solid rgba(111,231,135,0.12); border-radius: 24px; }")
        list_style = theme_manager.get_category_view_style(self.current_theme)
        self.subcategory_list.setStyleSheet(list_style)
        
        # 标题样式暂时保持本地
        if self.current_theme == 'blue_white':
            self.title_label.setStyleSheet("padding: 10px 14px; background-color: rgba(232,249,255,0.60); font-weight: 700; border: 1px solid rgba(151,213,244,0.58); border-radius: 18px; color: #1b547b; font-size: 14px;")
        elif self.current_theme == 'celadon_mist':
            self.title_label.setStyleSheet("padding: 9px 12px 11px 12px; background-color: rgba(226,255,255,0.74); font-weight: 700; border: 1px solid rgba(137,220,223,0.58); border-radius: 16px; color: #0f6970; font-size: 14px;")
        elif self.current_theme == 'dark_green':
            self.title_label.setStyleSheet("padding: 10px 14px; background-color: rgba(0,18,16,0.34); font-weight: 700; border-top: 1px solid rgba(0,255,65,0.76); border-bottom: 1px solid rgba(0,255,65,0.76); border-left: 1px solid rgba(0,229,255,0.42); border-right: 1px solid rgba(255,51,102,0.26); border-radius: 10px; color: #00ff41; font-size: 14px;")
        elif self.current_theme == 'purple_neon':
            self.title_label.setStyleSheet("padding: 10px 14px; background-color: rgba(45,7,67,0.38); font-weight: 700; border-top: 1px solid rgba(255,232,147,0.86); border-bottom: 1px solid rgba(255,207,92,0.72); border-left: 1px solid rgba(189,58,255,0.42); border-right: 1px solid rgba(189,58,255,0.42); border-radius: 18px; color: #fff0b8; font-size: 14px;")
        elif self.current_theme == 'red_orange':
            self.title_label.setStyleSheet("padding: 10px 14px; background-color: rgba(112,0,0,0.54); font-weight: 700; border-top: 1px solid rgba(255,232,147,0.96); border-bottom: 1px solid rgba(255,205,92,0.84); border-left: 1px solid rgba(255,86,48,0.50); border-right: 1px solid rgba(255,86,48,0.50); border-radius: 18px; color: #fff4c7; font-size: 14px;")
        else:
            self.title_label.setStyleSheet("padding: 10px 12px; background-color: rgba(24,58,39,0.68); font-weight: 700; border: 1px solid rgba(111,231,135,0.10); border-radius: 14px; color: #f3fff5; font-size: 14px;")
    
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
        try:
            menu = QMenu(self)
            
            # 无论是否有选中项，都可以添加新子分类
            # 添加新建子分类菜单项
            new_subcategory_action = QAction("新建子分类", self)
            new_subcategory_action.triggered.connect(lambda: self.new_subcategory_requested.emit(self.current_category))
            menu.addAction(new_subcategory_action)
            
            # 获取当前选中的子分类
            selected_items = self.subcategory_list.selectedItems()
            if selected_items:
                # 添加重命名子分类菜单项
                rename_action = QAction("重命名", self)
                rename_action.triggered.connect(self._rename_selected_subcategory)
                menu.addAction(rename_action)

                # 添加删除子分类菜单项
                delete_subcategory_action = QAction("删除子分类", self)
                delete_subcategory_action.triggered.connect(lambda: self.delete_subcategory_requested.emit(self.current_subcategory))
                menu.addAction(delete_subcategory_action)
            
            # 显示菜单
            menu.exec_(self.subcategory_list.mapToGlobal(position))
        except KeyboardInterrupt:
            # 优雅地处理用户中断操作
            pass
    
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
    
    def on_subcategory_order_changed(self):
        """处理子分类拖拽排序事件，更新子分类顺序"""
        if self.current_category is None:
            return
        
        # 获取当前分类数据
        categories = self.data_manager.load_categories()
        parent_category = None
        
        # 查找当前父分类
        for category in categories:
            if category['id'] == self.current_category:
                parent_category = category
                break
        
        if not parent_category:
            return
        current_order = []
        seen_ids = set()
        
        # 从列表中获取当前顺序，去除重复项
        for i in range(self.subcategory_list.count()):
            item = self.subcategory_list.item(i)
            data = item.data(Qt.UserRole)
            subcat_id = data['id']
            
            # 只添加唯一ID，避免重复
            if subcat_id not in seen_ids:
                seen_ids.add(subcat_id)
                current_order.append(subcat_id)
        
        # 获取原始子分类列表
        original_subcategories = parent_category.get('subcategories', [])
        
        # 创建ID到子分类的映射，提高查找效率
        subcat_map = {subcat['id']: subcat for subcat in original_subcategories}
        
        # 重新排序子分类
        new_subcategories = []
        for subcat_id in current_order:
            if subcat_id in subcat_map:
                new_subcategories.append(subcat_map[subcat_id])
        
        # 更新父分类的子分类列表
        parent_category['subcategories'] = new_subcategories
        
        # 保存更新后的分类数据
        self.data_manager.save_categories(categories)

    def _rename_selected_subcategory(self):
        """弹出输入框获取新名称，并调用 DataManager 进行重命名"""
        current_item = self.subcategory_list.currentItem()
        if not current_item:
            return

        data = current_item.data(Qt.UserRole)
        subcategory_id = data['id']
        from PyQt5.QtWidgets import QInputDialog
        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, "重命名子分类", "新的子分类名称:", text=old_name)
        if ok and new_name and new_name.strip() and new_name != old_name:
            try:
                success = self.data_manager.rename_subcategory(subcategory_id, new_name.strip())
            except Exception:
                success = False

            if success:
                # 重新加载并尽量恢复选中
                self.load_subcategories(self.current_category)
                self.select_subcategory(subcategory_id)
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "失败", "重命名子分类失败！")

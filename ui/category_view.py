import os
from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QVBoxLayout, QLabel, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QIcon, QDropEvent, QPixmap, QPainter, QFont
from core.style_manager import ThemeManager
from core.data_manager import DataManager
from core.runtime_paths import resolve_icon_path_value

# 图标缓存，减少重复的文件系统操作
category_icon_cache = {}


def _create_text_icon(text: str) -> QIcon:
    """把 emoji / 短文本渲染成列表图标"""
    safe_text = (text or '').strip()[:2] or '?'
    cache_key = f"text::{safe_text}"
    if cache_key in category_icon_cache:
        return category_icon_cache[cache_key]

    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    font = QFont()
    font.setPixelSize(16)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, safe_text)
    painter.end()

    icon = QIcon(pixmap)
    category_icon_cache[cache_key] = icon
    return icon


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
        self.category_list = DraggableCategoryListWidget()
        # 确保列表有足够宽度显示完整的分类名称
        self.category_list.setMinimumWidth(260)
        
        # 应用当前主题样式
        self.apply_theme_styles()
        
        # 连接信号
        self.category_list.itemClicked.connect(self.on_item_clicked)
        # 设置右键菜单
        self.category_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.category_list.customContextMenuRequested.connect(self.show_context_menu)
        # 连接拖拽排序完成信号
        self.category_list.order_changed.connect(self.on_category_order_changed)
        
        layout.addWidget(self.category_list)
        
        # 确保组件最小宽度，避免被 splitter 收缩过小
        self.setMinimumWidth(260)

        # 加载分类数据
        self.load_categories()
    

    
    def on_category_order_changed(self):
        """处理分类拖拽排序事件，更新分类顺序"""
        # 获取当前分类数据
        categories = self.data_manager.load_categories()
        
        # 获取当前分类顺序，去重处理
        current_order = []
        seen_ids = set()
        
        # 从列表中获取当前顺序，去除重复项
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            data = item.data(Qt.UserRole)
            category_id = data['id']
            
            # 只添加唯一ID，避免重复
            if category_id not in seen_ids:
                seen_ids.add(category_id)
                current_order.append(category_id)
        
        # 创建ID到分类的映射，提高查找效率
        category_map = {cat['id']: cat for cat in categories}
        
        # 重新排序分类列表
        new_order = []
        for category_id in current_order:
            if category_id in category_map:
                new_order.append(category_map[category_id])
        
        # 确保只包含原始分类，避免添加不存在的分类
        # 添加剩余的原始分类（如果有不在current_order中的）
        for category in categories:
            if category['id'] not in seen_ids:
                new_order.append(category)
        
        # 更新并保存分类顺序
        self.data_manager.save_categories(new_order)
        
        # 不默认选中任何分类，让应用程序启动时默认显示收藏页面
        # 只有当用户主动选择分类时，才会触发分类选择信号
    
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
            # 添加重命名操作
            rename_action = QAction("重命名", self)
            rename_action.triggered.connect(self._rename_selected_category)
            menu.addAction(rename_action)
        
        # 显示菜单
        menu.exec_(self.category_list.mapToGlobal(position))

    def _rename_selected_category(self):
        """弹出输入框获取新名称，并调用 DataManager 进行重命名"""
        current_item = self.category_list.currentItem()
        if not current_item:
            return

        data = current_item.data(Qt.UserRole)
        category_id = data['id']
        from PyQt5.QtWidgets import QInputDialog
        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, "重命名分类", "新的分类名称:", text=old_name)
        if ok and new_name and new_name.strip() and new_name != old_name:
            success = self.data_manager.rename_category(category_id, new_name.strip())
            if success:
                # 重新加载并尽量恢复选中
                self.load_categories()
                self.select_category(category_id)
            else:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "失败", "重命名分类失败！")
    
    def set_theme(self, theme):
        """设置当前主题并应用样式"""
        self.current_theme = theme
        self.apply_theme_styles()
        
    def apply_theme_styles(self):
        """根据当前主题应用样式"""
        # 从 StyleManager 获取样式
        theme_manager = ThemeManager()
        list_style = theme_manager.get_category_view_style(self.current_theme)
        self.category_list.setStyleSheet(list_style)
        
        # 标题样式暂时保持本地，或者也可以移入 StyleManager (简单起见这里保留逻辑)
        if self.current_theme == 'blue_white':
            self.title_label.setStyleSheet("font-weight: 700; padding: 12px 14px; border: 1px solid rgba(148,163,184,0.10); border-radius: 14px; background-color: rgba(255,255,255,0.72); color: #1e293b; font-size: 14px;")
        elif self.current_theme == 'purple_neon':
            self.title_label.setStyleSheet("font-weight: 700; padding: 12px 14px; border: 1px solid rgba(157,123,255,0.10); border-radius: 14px; background-color: rgba(30,24,56,0.68); color: #efe9ff; font-size: 14px;")
        elif self.current_theme == 'red_orange':
            self.title_label.setStyleSheet("font-weight: 700; padding: 12px 14px; border: 1px solid rgba(255,138,61,0.10); border-radius: 14px; background-color: rgba(42,30,24,0.68); color: #fff1e6; font-size: 14px;")
        else:
            self.title_label.setStyleSheet("font-weight: 700; padding: 12px 14px; border: 1px solid rgba(111,231,135,0.10); border-radius: 14px; background-color: rgba(24,58,39,0.68); color: #f3fff5; font-size: 14px;")
    
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
    
    def refresh(self):
        """刷新分类列表"""
        # 保存当前选中的分类ID
        current_selection = None
        if self.category_list.currentItem():
            current_selection = self.category_list.currentItem().data(Qt.UserRole)['id']

        # 重新加载分类数据
        self.load_categories()

        # 恢复之前的选中状态
        if current_selection:
            self.select_category(current_selection)

    def _resolve_category_icon(self, icon_value):
        """解析分类图标，兼容资源文件和 emoji/短文本"""
        icon_text = (icon_value or '').strip()
        if not icon_text or icon_text == 'default_icon':
            return QIcon()

        if icon_text in category_icon_cache:
            return category_icon_cache[icon_text]

        candidate_path = resolve_icon_path_value(icon_text)
        if candidate_path is not None:
            icon = QIcon(os.fspath(candidate_path))
            if not icon.isNull():
                category_icon_cache[icon_text] = icon
                return icon

        return _create_text_icon(icon_text)

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
            icon_value = category.get('icon', '')
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, {'id': category.get('id', 0)})

            icon = self._resolve_category_icon(icon_value)
            if not icon.isNull():
                item.setIcon(icon)

            self.category_list.addItem(item)

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
    data_manager = DataManager(data_dir=data_dir)
    
    # 创建分类视图
    category_view = CategoryView(data_manager)
    category_view.setWindowTitle("工具分类")
    category_view.setGeometry(100, 100, 250, 600)
    category_view.show()
    
    sys.exit(app.exec_())

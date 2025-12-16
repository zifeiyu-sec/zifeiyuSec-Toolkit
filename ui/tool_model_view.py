#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Qt Model/View 架构的高性能工具列表组件。
这种实现方式通过虚拟化渲染，可以实现海量数据的毫秒级加载。
"""
import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListView, QStyledItemDelegate, 
                            QAbstractItemView, QMenu, QMessageBox, QStyle)
from PyQt5.QtCore import (Qt, QAbstractListModel, QModelIndex, QSize, pyqtSignal, 
                         QRect, QRectF, QPoint, QThread, QRunnable, QThreadPool, QObject)
from PyQt5.QtGui import (QPainter, QColor, QFont, QIcon, QPen, QBrush, 
                        QFontMetrics, QPixmap, QPainterPath, QImage)

# 获取资源目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCE_ICON_DIR = os.path.join(BASE_DIR, 'resources', 'icons')
DEFAULT_ICON_PATH = os.path.join(RESOURCE_ICON_DIR, 'new_default_icon.ico')
if not os.path.exists(DEFAULT_ICON_PATH):
    DEFAULT_ICON_PATH = os.path.join(RESOURCE_ICON_DIR, 'default_tool_icon.svg')

# 图标缓存
# 异步图标加载器
class LoaderSignals(QObject):
    """信号类，用于Worker线程通信"""
    loaded = pyqtSignal(str, QImage)

class IconWorker(QRunnable):
    """后台加载图片的Worker"""
    def __init__(self, path, signals):
        super().__init__()
        self.path = path
        self.signals = signals

    def run(self):
        # 在后台线程加载图片
        if os.path.exists(self.path):
            img = QImage(self.path)
        else:
            img = QImage() # 空图片表示加载失败
        self.signals.loaded.emit(self.path, img)

class AsyncIconLoader(QObject):
    """单例异步加载器管理器"""
    _instance = None
    icon_ready = pyqtSignal() # 全局信号：有新图标加载好了
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncIconLoader, cls).__new__(cls)
            # 手动初始化
            QObject.__init__(cls._instance)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.cache = {} # path -> QIcon
        self.loading = set() # path
        self.signals = LoaderSignals()
        self.signals.loaded.connect(self._on_loaded)
        self.pool = QThreadPool.globalInstance()
        
        # 延迟加载默认图标，避免在QApplication创建之前加载
        self._default_icon = None

    @property
    def default_icon(self):
        """延迟加载默认图标属性"""
        if self._default_icon is None:
            # 第一次访问时创建默认图标
            self._default_icon = QIcon(DEFAULT_ICON_PATH)
            if self._default_icon.isNull():
                self._default_icon = QIcon() # 空图标
        return self._default_icon

    def get_icon(self, path):
        """获取图标：如果缓存有则返回，没有则触发加载并返回默认图标"""
        if not path:
            return self.default_icon
            
        # 处理相对路径
        full_path = path
        if not os.path.isabs(path):
            full_path = os.path.join(RESOURCE_ICON_DIR, path)

        if full_path in self.cache:
            return self.cache[full_path]
        
        if full_path not in self.loading:
            self.loading.add(full_path)
            worker = IconWorker(full_path, self.signals)
            self.pool.start(worker)
        
        return self.default_icon

    def _on_loaded(self, path, img):
        if not img.isNull():
            # QPixmap 和 QIcon 必须在 GUI 线程创建
            self.cache[path] = QIcon(QPixmap.fromImage(img))
        else:
            # 加载失败，存入默认图标防止反复尝试
            self.cache[path] = self.default_icon
            
        self.loading.discard(path)
        self.icon_ready.emit()
    
    def shutdown(self):
        """清理资源，停止所有任务"""
        try:
            # 停止所有线程池中的任务
            self.pool.clear()
            # 等待所有任务完成，最多等待500毫秒
            self.pool.waitForDone(500)
        except Exception:
            # 忽略任何清理过程中的错误
            pass

# 全局实例
icon_loader = AsyncIconLoader()

class ToolModel(QAbstractListModel):
    """工具数据模型"""
    def __init__(self, tools=None, parent=None):
        super().__init__(parent)
        self._tools = tools or []
        
    def rowCount(self, parent=QModelIndex()):
        return len(self._tools)
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._tools):
            return None
        
        tool = self._tools[index.row()]
        
        if role == Qt.DisplayRole:
            return tool['name']
        elif role == Qt.UserRole:
            return tool  # 返回完整的工具数据
        elif role == Qt.ToolTipRole:
            return tool.get('description', '')
            
        return None

    def update_data(self, tools):
        """全量更新数据"""
        self.beginResetModel()
        self._tools = tools
        self.endResetModel()

    def get_tool(self, index):
        if 0 <= index.row() < len(self._tools):
            return self._tools[index.row()]
        return None

    def remove_tool(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._tools[row]
        self.endRemoveRows()

class ToolDelegate(QStyledItemDelegate):
    """工具卡片绘制代理"""
    def __init__(self, theme="dark_green", parent=None):
        super().__init__(parent)
        self.theme = theme
        # 卡片尺寸
        self.card_size = QSize(320, 80)
        self.padding = 10
        self.icon_size = 48
        
    def sizeHint(self, option, index):
        return self.card_size
        
    def paint(self, painter, option, index):
        """绘制卡片内容"""
        tool = index.data(Qt.UserRole)
        if not tool:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. 确定绘制区域
        rect = option.rect
        # 留一点间隙作为Margin
        card_rect = rect.adjusted(4, 4, -4, -4)
        
        # 2. 获取主题颜色
        is_hover = (option.state & QStyle.State_MouseOver)
        is_selected = (option.state & QStyle.State_Selected)
        
        bg_color = QColor(30, 41, 59)
        border_color = QColor(51, 65, 85, 127)
        text_color = QColor(226, 232, 240)
        desc_color = QColor(148, 163, 184)
        
        if self.theme in ("light", "blue_white"):
            bg_color = QColor(255, 255, 255)
            border_color = QColor(0, 0, 0, 25)
            text_color = QColor(55, 65, 81)
            desc_color = QColor(107, 114, 128)
            
            if is_hover or is_selected:
                bg_color = QColor(248, 250, 252)
                border_color = QColor(59, 130, 246, 127)
        else:
            if is_hover or is_selected:
                border_color = QColor(59, 130, 246, 127)
                # 深色模式下hover背景保持或微调
                
        # 3. 绘制背景
        path = QPainterPath()
        # 修正：addRoundedRect 需要 QRectF
        path.addRoundedRect(QRectF(card_rect), 8, 8)
        
        painter.fillPath(path, bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)
        
        # 4. 绘制图标
        icon_rect = QRect(card_rect.left() + 10, card_rect.top() + (card_rect.height() - 56)//2, 56, 56)
        
        icon_path = tool.get('icon') or tool.get('icon_path')
        # 使用异步加载器
        icon = icon_loader.get_icon(icon_path)
        
        # 绘制图标背景（可选，稍微模仿旧UI的按钮感）
        # icon_bg_rect = icon_rect
        # painter.setBrush(QColor(0,0,0,10))
        # painter.setPen(Qt.NoPen)
        # painter.drawRoundedRect(icon_bg_rect, 8, 8)
        
        # 绘制图标 - 强制缩放
        # 获取最大可用尺寸的 Pixmap
        # 对于 SVG，pixmap(size) 会渲染出指定大小的高清图
        # 对于光栅图，如果原图较小，我们需要加载后手动缩放
        pixmap = icon.pixmap(56, 56)
        
        if not pixmap.isNull():
            # 缩放 Pixmap 以填充 56x56 区域 (保持纵横比)
            # transform=Qt.SmoothTransformation 保证缩放质量
            scaled_pixmap = pixmap.scaled(
                icon_rect.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            
            # 计算居中位置
            x = icon_rect.left() + (icon_rect.width() - scaled_pixmap.width()) // 2
            y = icon_rect.top() + (icon_rect.height() - scaled_pixmap.height()) // 2
            
            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            # 备用绘制逻辑（理论上不应触发，除非icon完全无效）
            icon.paint(painter, icon_rect, Qt.AlignCenter)
        
        # 5. 绘制文本
        text_x = icon_rect.right() + 15
        text_width = card_rect.width() - 56 - 30
        
        name = tool.get('name', 'Process')
        desc = tool.get('description', '')
        if desc:
            desc = ' '.join(desc.split()) # 去除多余空白
            
        # 绘制标题
        title_font = QFont()
        title_font.setBold(True)
        # 如果没有描述，字体变大
        if not desc or desc == '无介绍':
            title_font.setPixelSize(18)
        else:
            title_font.setPixelSize(14)
            
        painter.setFont(title_font)
        painter.setPen(text_color)
        
        # 计算标题位置
        if not desc or desc == '无介绍':
            # 居中垂直
            title_rect = QRect(text_x, card_rect.top(), text_width, card_rect.height())
            painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, name)
        else:
            # 上下分布
            title_rect = QRect(text_x, card_rect.top() + 18, text_width, 20)
            painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, name)
            
            # 绘制描述
            desc_font = QFont()
            desc_font.setPixelSize(12)
            painter.setFont(desc_font)
            painter.setPen(desc_color)
            
            desc_rect = QRect(text_x, title_rect.bottom() + 2, text_width, 20)
            painter.drawText(desc_rect, Qt.AlignLeft | Qt.AlignVCenter,  painter.fontMetrics().elidedText(desc, Qt.ElideRight, text_width))

        # 6. 绘制收藏标记 (星号)
        if tool.get('is_favorite', False):
            star_font = QFont()
            star_font.setPixelSize(16)
            painter.setFont(star_font)
            
            # 根据主题调整颜色
            if self.theme in ("light", "blue_white"):
                painter.setPen(QColor(245, 158, 11)) # 深金色/橙色，在亮色背景更清晰
            else:
                painter.setPen(QColor(255, 215, 0)) # 亮金色，在深色背景更清晰
            
            # 右上角绘制
            star_rect = QRect(card_rect.right() - 25, card_rect.top() + 5, 20, 20)
            painter.drawText(star_rect, Qt.AlignCenter, "★")

        painter.restore()

class ToolCardContainer(QWidget):
    """
    兼容层：对外提供与旧版 ToolCardContainer 一致的接口，
    但内部使用 QListView + Model 实现。
    """
    # 信号定义 (保持兼容)
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    new_tool_requested = pyqtSignal()   # 暂未使用，但保持兼容
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "dark_green"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = QListView()
        self.model = ToolModel()
        self.delegate = ToolDelegate(self.current_theme)
        
        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)
        
        # 关键设置：像图标模式一样布局（网格）
        self.view.setViewMode(QListView.IconMode)
        self.view.setResizeMode(QListView.Adjust)
        self.view.setUniformItemSizes(True) # 性能优化
        self.view.setSpacing(8)
        self.view.setWordWrap(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # 样式设置：去除丑陋的默认选中框，完全靠Delegate绘制
        self.view.setFrameShape(QListView.NoFrame)
        # 设置鼠标追踪以便Delegate可以处理Hover
        self.view.setMouseTracking(True)
        
        layout.addWidget(self.view)
        
        # 信号连接
        self.view.clicked.connect(self.on_item_clicked)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        
        self.apply_theme_styles()
        
        # 连接加载器信号，刷新界面
        icon_loader.icon_ready.connect(self.view.viewport().update)

    def set_theme(self, theme_name):
        self.current_theme = theme_name
        self.delegate.theme = theme_name
        self.apply_theme_styles()
        # 强制重绘
        self.view.viewport().update()
        
    def apply_theme_styles(self):
        if self.current_theme in ("light", "blue_white"):
             self.view.setStyleSheet("""
                QListView {
                    background-color: #f0f4f8;
                    border: none;
                    outline: none;
                }
             """)
        else:
             self.view.setStyleSheet("""
                QListView {
                    background-color: #1a1a2e;
                    border: none;
                    outline: none;
                }
             """)

    def display_tools(self, tools_data):
        """显示工具列表"""
        # Model/View 模式下，直接给 Model 数据，Qt 负责极速渲染
        self.model.update_data(tools_data)
        
    def on_item_clicked(self, index):
        """点击运行"""
        tool = self.model.get_tool(index)
        if tool:
            self.run_tool.emit(tool)

    def show_context_menu(self, pos):
        index = self.view.indexAt(pos)
        if not index.isValid():
            return
            
        tool = self.model.get_tool(index)
        if not tool:
            return
            
        menu = QMenu(self)
        
        run_action = menu.addAction("运行工具")
        run_action.triggered.connect(lambda: self.run_tool.emit(tool))
        
        edit_action = menu.addAction("编辑工具")
        edit_action.triggered.connect(lambda: self.edit_requested.emit(tool))
        
        is_fav = tool.get('is_favorite', False)
        fav_text = "取消收藏" if is_fav else "添加收藏"
        fav_action = menu.addAction(fav_text)
        fav_action.triggered.connect(lambda: self.toggle_favorite.emit(tool['id']))
        
        menu.addSeparator()
        
        del_action = menu.addAction("删除工具")
        del_action.triggered.connect(lambda: self.confirm_delete(tool))
        
        menu.exec_(self.view.mapToGlobal(pos))
        
    def confirm_delete(self, tool):
        # 简单确认框，为了减少依赖不引用外部样式，使用原生
        reply = QMessageBox.question(self, '确认删除', 
                                   f"确定要删除工具 \"{tool['name']}\" 吗？",
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.deleted.emit(tool['id'])

    def get_tool_count(self):
        return self.model.rowCount()

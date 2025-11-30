import os
import datetime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QFileDialog, QScrollArea, QWidget, QMessageBox, QApplication
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

class ImageSelectorDialog(QDialog):
    """图片选择对话框，用于选择工具卡片的背景图片"""
    def __init__(self, image_manager, current_image=None, parent=None):
        super().__init__(parent)
        self.image_manager = image_manager
        self.selected_image = current_image
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("选择背景图片")
        self.setGeometry(100, 100, 600, 400)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("选择背景图片或上传新图片:")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(title_label)
        
        # 当前图片预览
        preview_layout = QHBoxLayout()
        preview_label = QLabel("当前图片:")
        self.current_preview = QLabel()
        self.current_preview.setFixedSize(100, 75)
        self.current_preview.setAlignment(Qt.AlignCenter)
        
        # 显示当前图片
        if self.selected_image:
            self._update_preview(self.selected_image)
        else:
            self.current_preview.setText("无")
        
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.current_preview)
        preview_layout.addStretch()
        main_layout.addLayout(preview_layout)
        
        # 分隔线
        separator = QLabel()
        separator.setStyleSheet("background-color: #CCCCCC; height: 2px;")
        main_layout.addWidget(separator)
        
        # 图片网格
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        grid_widget = QWidget()
        self.image_grid = QGridLayout(grid_widget)
        self.image_grid.setAlignment(Qt.AlignTop)
        self.image_grid.setSpacing(10)
        
        scroll_area.setWidget(grid_widget)
        main_layout.addWidget(scroll_area, 1)
        
        # 底部按钮
        buttons_layout = QHBoxLayout()
        
        # 上传新图片按钮
        upload_button = QPushButton("上传新图片")
        upload_button.clicked.connect(self.on_upload_clicked)
        buttons_layout.addWidget(upload_button)
        
        # 移除背景按钮
        remove_button = QPushButton("移除背景")
        remove_button.clicked.connect(self.on_remove_clicked)
        buttons_layout.addWidget(remove_button)
        
        buttons_layout.addStretch()
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        
        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_button)
        
        main_layout.addLayout(buttons_layout)
        
        # 加载可用图片
        self.load_images()
    
    def load_images(self):
        """加载所有可用的图片"""
        # 清除现有内容
        while self.image_grid.count() > 0:
            item = self.image_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 获取所有图片
        images = self.image_manager.list_images()
        
        # 计算网格布局
        row = 0
        col = 0
        max_cols = 5
        
        for image_name in images:
            # 创建图片项
            image_item = self._create_image_item(image_name)
            self.image_grid.addWidget(image_item, row, col)
            
            # 更新行列索引
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def _create_image_item(self, image_name):
        """创建单个图片选择项"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 图片预览
        image_label = QLabel()
        image_label.setFixedSize(100, 75)
        image_label.setAlignment(Qt.AlignCenter)
        
        # 获取缩略图
        thumbnail = self.image_manager.create_thumbnail(image_name, (100, 75))
        if thumbnail:
            image_label.setPixmap(thumbnail)
        else:
            image_label.setText("加载失败")
        
        # 图片名称
        name_label = QLabel(image_name)
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setStyleSheet("font-size: 10px;")
        name_label.setWordWrap(True)
        
        layout.addWidget(image_label)
        layout.addWidget(name_label)
        
        # 设置选中效果
        if self.selected_image == image_name:
            widget.setStyleSheet("background-color: #E0E0FF; border: 2px solid #0000FF;")
        
        # 点击事件
        widget.mousePressEvent = lambda event, img=image_name, w=widget: self.on_image_clicked(img, w)
        
        return widget
    
    def on_image_clicked(self, image_name, widget):
        """处理图片点击事件"""
        # 更新选中状态
        self.selected_image = image_name
        self._update_preview(image_name)
        
        # 更新UI中的选中效果
        for i in range(self.image_grid.count()):
            item = self.image_grid.itemAt(i)
            if item:
                child_widget = item.widget()
                if child_widget:
                    if child_widget == widget:
                        child_widget.setStyleSheet("background-color: #E0E0FF; border: 2px solid #0000FF;")
                    else:
                        child_widget.setStyleSheet("")
    
    def _update_preview(self, image_name):
        """更新预览图片"""
        thumbnail = self.image_manager.create_thumbnail(image_name, (100, 75))
        if thumbnail:
            self.current_preview.setPixmap(thumbnail)
        else:
            self.current_preview.setText("加载失败")
    
    def on_upload_clicked(self):
        """处理上传新图片按钮点击事件"""
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)"
        )
        
        if file_path:
            # 验证图片有效性
            if not self.image_manager.validate_image(file_path):
                QMessageBox.warning(self, "无效图片", "请选择有效的图片文件！")
                return
            
            # 生成文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = os.path.splitext(file_path)[1]
            image_name = f"bg_{timestamp}{file_ext}"
            
            # 保存图片
            saved_name = self.image_manager.save_image(file_path, image_name)
            if saved_name:
                # 刷新图片列表并选中新上传的图片
                self.load_images()
                self.selected_image = saved_name
                self._update_preview(saved_name)
                QMessageBox.information(self, "上传成功", "图片已成功上传！")
            else:
                QMessageBox.warning(self, "上传失败", "图片上传失败，请重试！")
    
    def on_remove_clicked(self):
        """处理移除背景按钮点击事件"""
        self.selected_image = ""
        self.current_preview.setText("无")
        
        # 清除所有选中效果
        for i in range(self.image_grid.count()):
            item = self.image_grid.itemAt(i)
            if item:
                child_widget = item.widget()
                if child_widget:
                    child_widget.setStyleSheet("")
    
    def get_selected_image(self):
        """获取选中的图片
        
        Returns:
            选中的图片名称，如果未选中返回空字符串
        """
        return self.selected_image

if __name__ == "__main__":
    import sys
    # 添加项目根目录到Python路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from PyQt5.QtWidgets import QApplication
    from core.image_manager import ImageManager
    
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建相对于脚本的images目录路径
    images_dir = os.path.join(os.path.dirname(script_dir), "images")
    
    app = QApplication(sys.argv)
    
    # 创建图片管理器
    image_manager = ImageManager(images_dir)
    # 创建默认背景图片
    image_manager.create_default_backgrounds()
    
    # 创建对话框
    dialog = ImageSelectorDialog(image_manager)
    if dialog.exec_():
        selected_image = dialog.get_selected_image()
        print(f"选中的图片: {selected_image}")
    
    sys.exit()
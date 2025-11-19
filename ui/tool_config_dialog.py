from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                            QTextEdit, QPushButton, QComboBox, QCheckBox, QGroupBox, 
                            QGridLayout, QSpinBox, QFileDialog, QMessageBox)    
from PyQt5.QtGui import QPixmap, QIcon
import shutil
import hashlib
from PyQt5.QtCore import Qt
import os

class ToolConfigDialog(QDialog):
    def __init__(self, tool_data=None, categories=None, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data or self._create_empty_tool()
        self.categories = categories or []
        self.init_ui()
    
    def _create_empty_tool(self):
        """创建一个空的工具数据字典"""
        return {
            "id": None,
            "name": "",
            "path": "",
            "description": "",
            "category_id": None,
            "subcategory_id": None,
            "background_image": "",
            "icon": "",  # 工具图标路径
            "tags": [],
            "priority": 0,
            "is_favorite": False,
            "arguments": "",  # 命令行参数
            "working_directory": "",  # 工作目录
            "run_in_terminal": False,  # 是否在终端中运行
            "is_web_tool": False  # 是否为网页工具
        }
    
    def init_ui(self):
        """初始化对话框界面"""
        self.setWindowTitle("编辑工具配置" if self.tool_data["id"] else "新建工具")
        self.setMinimumSize(500, 450)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QGridLayout()
        
        # 工具类型
        basic_layout.addWidget(QLabel("工具类型:"), 0, 0)
        self.tool_type_combo = QComboBox()
        self.tool_type_combo.addItem("本地工具", False)
        self.tool_type_combo.addItem("网页工具", True)
        if self.tool_data.get("is_web_tool", False):
            self.tool_type_combo.setCurrentIndex(1)
        self.tool_type_combo.currentIndexChanged.connect(self.on_tool_type_changed)
        basic_layout.addWidget(self.tool_type_combo, 0, 1)
        
        # 工具名称
        basic_layout.addWidget(QLabel("名称:"), 1, 0)
        self.name_edit = QLineEdit(self.tool_data["name"])
        basic_layout.addWidget(self.name_edit, 1, 1)
        
        # 工具位置/URL
        self.path_label = QLabel("工具位置:")
        basic_layout.addWidget(self.path_label, 2, 0)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(self.tool_data["path"])
        path_layout.addWidget(self.path_edit, 1)
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self.on_browse_path)
        path_layout.addWidget(self.browse_button)
        basic_layout.addLayout(path_layout, 2, 1)
        
        # 工具介绍（原预览区域）
        basic_layout.addWidget(QLabel("工具介绍:"), 3, 0, alignment=Qt.AlignTop)
        self.description_edit = QTextEdit(self.tool_data["description"])
        self.description_edit.setMinimumHeight(100)
        basic_layout.addWidget(self.description_edit, 3, 1)
        
        # 一级分类（原路径字段位置）
        if self.categories:
            basic_layout.addWidget(QLabel("一级分类:"), 4, 0)
            self.category_combo = QComboBox()
            self.category_map = {}
            
            # 填充分类列表
            for category in self.categories:
                self.category_combo.addItem(category["name"], category["id"])
                self.category_map[category["id"]] = category
            
            # 设置当前选中的分类
            if self.tool_data["category_id"] and self.tool_data["category_id"] in self.category_map:
                index = self.category_combo.findData(self.tool_data["category_id"])
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            
            self.category_combo.currentIndexChanged.connect(self.on_category_changed)
            basic_layout.addWidget(self.category_combo, 4, 1)
            
            # 二级分类（原子分类位置）
            basic_layout.addWidget(QLabel("二级分类:"), 5, 0)
            self.subcategory_combo = QComboBox()
            # 添加一个默认的"无"选项
            self.subcategory_combo.addItem("无", None)
            basic_layout.addWidget(self.subcategory_combo, 5, 1)
            
            # 初始加载子分类
            self.on_category_changed(self.category_combo.currentIndex())
        
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # 运行配置组
        run_group = QGroupBox("运行配置")
        run_layout = QGridLayout()
        
        # 命令行参数
        run_layout.addWidget(QLabel("命令行参数:"), 0, 0)
        self.args_edit = QLineEdit(self.tool_data.get("arguments", ""))
        self.args_edit.setPlaceholderText("例如: -h, --verbose 等")
        run_layout.addWidget(self.args_edit, 0, 1)
        
        run_group.setLayout(run_layout)
        main_layout.addWidget(run_group)
        
        # 优先级和标签组
        tags_group = QGroupBox("其他设置")
        tags_layout = QGridLayout()
        
        # 优先级
        tags_layout.addWidget(QLabel("优先级:"), 0, 0)
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(0, 5)
        self.priority_spin.setValue(self.tool_data["priority"])
        tags_layout.addWidget(self.priority_spin, 0, 1)
        
        # 收藏
        self.favorite_check = QCheckBox("添加到收藏")
        self.favorite_check.setChecked(self.tool_data["is_favorite"])
        tags_layout.addWidget(self.favorite_check, 1, 1, alignment=Qt.AlignLeft)
        
        tags_group.setLayout(tags_layout)
        main_layout.addWidget(tags_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("保存")
        save_button.setDefault(True)
        save_button.clicked.connect(self.on_save)
        button_layout.addWidget(save_button)
        
        main_layout.addLayout(button_layout)
    
    def on_tool_type_changed(self, index):
        """处理工具类型变更事件"""
        is_web_tool = self.tool_type_combo.itemData(index)
        if is_web_tool:
            self.path_label.setText("URL地址:")
            self.browse_button.setText("验证")
        else:
            self.path_label.setText("工具位置:")
            self.browse_button.setText("浏览")
    
    def on_browse_path(self):
        """浏览工具路径或验证URL"""
        is_web_tool = self.tool_type_combo.currentData()
        
        if is_web_tool:
            # 验证URL
            url = self.path_edit.text().strip()
            if not url:
                QMessageBox.warning(self, "警告", "请输入URL地址！")
                return
            
            # 简单验证URL格式
            if not (url.startswith("http://") or url.startswith("https://")):
                QMessageBox.warning(self, "警告", "URL地址必须以http://或https://开头！")
                return
            
            QMessageBox.information(self, "信息", "URL格式验证通过！")
        else:
            # 浏览本地文件
            # 根据操作系统选择适当的文件类型过滤器
            if os.name == 'nt':  # Windows
                file_filter = "可执行文件 (*.exe);;所有文件 (*.*)"
            else:  # Linux/Mac
                file_filter = "可执行文件 (*);;所有文件 (*.*)"
            
            file_path, _ = QFileDialog.getOpenFileName(self, "选择工具", 
                                                       os.path.dirname(self.path_edit.text()) or ".",
                                                       file_filter)
            
            if file_path:
                self.path_edit.setText(file_path)
    

    

    
    def on_category_changed(self, index):
        """处理分类变更事件"""
        # 清空子分类列表
        self.subcategory_combo.clear()
        self.subcategory_combo.addItem("无", None)
        
        # 获取当前分类
        if index >= 0:
            category_id = self.category_combo.itemData(index)
            if category_id and category_id in self.category_map:
                category = self.category_map[category_id]
                # 添加子分类
                for subcategory in category.get("subcategories", []):
                    self.subcategory_combo.addItem(subcategory["name"], subcategory["id"])
                
                # 设置当前子分类
                if self.tool_data["subcategory_id"]:
                    sub_index = self.subcategory_combo.findData(self.tool_data["subcategory_id"])
                    if sub_index >= 0:
                        self.subcategory_combo.setCurrentIndex(sub_index)
    
    def on_save(self):
        """保存工具配置"""
        # 验证必填字段
        name = self.name_edit.text().strip()
        path = self.path_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "警告", "请输入工具名称！")
            return
        
        if not path:
            QMessageBox.warning(self, "警告", "请输入工具路径或URL！")
            return
        
        is_web_tool = self.tool_type_combo.currentData()
        working_directory = ""
        
        if not is_web_tool:
            # 验证本地工具路径
            if not os.path.exists(path):
                QMessageBox.warning(self, "警告", "工具路径不存在！")
                return
            # 自动设置工作目录为工具所在目录
            working_directory = os.path.dirname(os.path.abspath(path))
        else:
            # 验证网页工具URL格式
            if not (path.startswith("http://") or path.startswith("https://")):
                QMessageBox.warning(self, "警告", "URL地址必须以http://或https://开头！")
                return
        
        # 更新工具数据
        self.tool_data.update({
            "name": name,
            "path": path,
            "description": self.description_edit.toPlainText(),
            "category_id": self.category_combo.currentData() if self.categories else None,
            "subcategory_id": self.subcategory_combo.currentData() if self.categories else None,
            "priority": self.priority_spin.value(),
            "is_favorite": self.favorite_check.isChecked(),
            "tags": [],  # 移除标签功能
            "icon": path,  # 图标路径使用工具路径或URL
            "arguments": self.args_edit.text(),
            "working_directory": working_directory,  # 自动设置工作目录
            "run_in_terminal": False,  # 移除在终端中运行选项
            "is_web_tool": is_web_tool  # 设置工具类型
        })
        
        self.accept()
    
    def get_tool_data(self):
        """获取工具数据"""
        return self.tool_data

# 示例用法
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 示例工具数据
    sample_tool = {
        "id": 1,
        "name": "Nmap",
        "path": "C:\\Program Files\\Nmap\\nmap.exe",
        "description": "网络扫描和安全评估工具",
        "category_id": 1,
        "subcategory_id": 101,
        "background_image": "",
        "priority": 3,
        "tags": ["扫描", "网络", "端口"],
        "is_favorite": True
    }
    
    # 示例分类数据
    sample_categories = [
        {
            "id": 1,
            "name": "网络扫描工具",
            "icon": "network_scan.png",
            "subcategories": [
                {"id": 101, "name": "端口扫描"},
                {"id": 102, "name": "服务探测"}
            ]
        },
        {
            "id": 2,
            "name": "Web安全工具",
            "icon": "web_security.png",
            "subcategories": [
                {"id": 201, "name": "代理工具"},
                {"id": 202, "name": "漏洞扫描"}
            ]
        }
    ]
    
    dialog = ToolConfigDialog(sample_tool, sample_categories)
    if dialog.exec_():
        updated_tool = dialog.get_tool_data()
        print("更新后的工具数据:")
        print(updated_tool)
    
    sys.exit(app.exec_())
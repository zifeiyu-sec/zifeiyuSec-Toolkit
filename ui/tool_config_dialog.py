import os
import re
import socket
from urllib.parse import urlparse
import urllib.request
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QCheckBox,
    QGroupBox,
    QGridLayout,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QApplication
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

class ToolConfigDialog(QDialog):
    """工具配置对话框，用于添加或编辑工具信息"""
    def __init__(self, tool_data=None, categories=None, parent=None, theme_name=None):
        super().__init__(parent)
        # 支持主题传入，默认深色主题
        self.current_theme = theme_name or 'dark_green'
        self.tool_data = tool_data or self._create_empty_tool()
        self.categories = categories or []
        self.icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "icons")
        self.default_icon_name = "default_tool.svg"
        self.selected_icon_name = self._normalize_icon_name(self.tool_data.get("icon"))
        self.init_ui()
        # 在 UI 建立后应用主题样式
        try:
            self.apply_theme_styles()
        except Exception:
            pass
    
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
        basic_layout = QVBoxLayout()
        
        # 顶部布局：左侧表单 + 右侧图标
        top_layout = QHBoxLayout()
        form_layout = QGridLayout()
        form_layout.setColumnStretch(1, 1)
        
        # 工具类型
        form_layout.addWidget(QLabel("工具类型:"), 0, 0)
        self.tool_type_combo = QComboBox()
        self.tool_type_combo.addItem("本地工具", False)
        self.tool_type_combo.addItem("网页工具", True)
        if self.tool_data.get("is_web_tool", False):
            self.tool_type_combo.setCurrentIndex(1)
        self.tool_type_combo.currentIndexChanged.connect(self.on_tool_type_changed)
        form_layout.addWidget(self.tool_type_combo, 0, 1)
        
        # 工具名称
        form_layout.addWidget(QLabel("名称:"), 1, 0)
        self.name_edit = QLineEdit(self.tool_data["name"])
        form_layout.addWidget(self.name_edit, 1, 1)
        
        # 工具位置/URL
        self.path_label = QLabel("工具位置:")
        form_layout.addWidget(self.path_label, 2, 0)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit(self.tool_data["path"])
        path_layout.addWidget(self.path_edit, 1)
        self.browse_button = QPushButton("浏览")
        self.browse_button.clicked.connect(self.on_browse_path)
        path_layout.addWidget(self.browse_button)
        form_layout.addLayout(path_layout, 2, 1)
        
        top_layout.addLayout(form_layout, 1)
        
        icon_container = QVBoxLayout()
        icon_container.setAlignment(Qt.AlignTop)
        icon_label = QLabel("工具图标:")
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(60, 60)
        self.icon_preview.setStyleSheet("border: 1px solid rgba(255,255,255,0.15); border-radius: 12px;")
        self._update_icon_preview()
        self.icon_button = QPushButton("选择图标")
        self.icon_button.clicked.connect(self.on_select_icon)
        icon_container.addWidget(icon_label)
        icon_container.addWidget(self.icon_preview)
        icon_container.addWidget(self.icon_button)
        icon_container.addStretch()
        top_layout.addLayout(icon_container)
        
        basic_layout.addLayout(top_layout)
        
        # 工具介绍
        desc_label = QLabel("工具介绍:")
        self.description_edit = QTextEdit(self.tool_data["description"])
        self.description_edit.setFixedHeight(80)
        basic_layout.addWidget(desc_label)
        basic_layout.addWidget(self.description_edit)
        
        # 一级分类（原路径字段位置）
        if self.categories:
            category_layout = QGridLayout()
            category_layout.setColumnStretch(1, 1)
            
            category_layout.addWidget(QLabel("一级分类:"), 0, 0)
            self.category_combo = QComboBox()
            self.category_map = {}
            for category in self.categories:
                self.category_combo.addItem(category["name"], category["id"])
                self.category_map[category["id"]] = category
            if self.tool_data["category_id"] and self.tool_data["category_id"] in self.category_map:
                index = self.category_combo.findData(self.tool_data["category_id"])
                if index >= 0:
                    self.category_combo.setCurrentIndex(index)
            self.category_combo.currentIndexChanged.connect(self.on_category_changed)
            category_layout.addWidget(self.category_combo, 0, 1)
            
            category_layout.addWidget(QLabel("二级分类:"), 1, 0)
            self.subcategory_combo = QComboBox()
            self.subcategory_combo.addItem("无", None)
            category_layout.addWidget(self.subcategory_combo, 1, 1)
            
            basic_layout.addLayout(category_layout)
            self.on_category_changed(self.category_combo.currentIndex())
        
        basic_group.setLayout(basic_layout)
        main_layout.addWidget(basic_group)
        
        # 运行配置组
        run_group = QGroupBox("运行配置")
        run_layout = QGridLayout()
        
        # 命令行参数
        run_layout.addWidget(QLabel("命令行参数:"), 0, 0)
        arguments_value = self.tool_data.get("arguments", "")
        if isinstance(arguments_value, list):
            arguments_value = " ".join(str(arg) for arg in arguments_value)
        self.args_edit = QLineEdit(arguments_value)
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

    def set_theme(self, theme_name: str):
        """外部调用用于切换对话框主题"""
        self.current_theme = theme_name or 'dark_green'
        self.apply_theme_styles()

    def apply_theme_styles(self):
        """根据当前主题应用 QSS 样式（仅影响本对话框内控件）"""
        # 基于两个主题单独调整控件样式，避免全局冲突
        if self.current_theme == 'blue_white':
            # 淡雅浅蓝 & 白底
            self.setStyleSheet('''
                QDialog { background-color: #f6fbff; }
                QGroupBox { background-color: transparent; border: 1px solid rgba(66,135,245,0.12); border-radius: 8px; margin-top: 4px; }
                QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #003366; font-weight:600; }
                QLabel { color: #003347; }
                QLineEdit, QTextEdit, QComboBox, QSpinBox { background: white; color: #0b2540; border: 1px solid rgba(3,105,161,0.12); border-radius: 6px; padding: 6px; }
                QPushButton { background-color: rgba(66,135,245,0.06); color: #003347; border: 1px solid rgba(66,135,245,0.12); border-radius: 6px; padding: 6px 10px; }
                QPushButton:hover { background-color: rgba(66,135,245,0.12); }
            ''')
            # icon preview border subtle
            self.icon_preview.setStyleSheet('border: 1px solid rgba(3,105,161,0.12); border-radius: 12px;')
        else:
            # 深色主题
            self.setStyleSheet('''
                QDialog { background-color: #111217; }
                QGroupBox { background-color: rgba(22,24,36,0.6); border: 1px solid rgba(144,238,144,0.12); border-radius: 8px; margin-top: 4px; }
                QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #90ee90; font-weight:600; }
                QLabel { color: #dfeee0; }
                QLineEdit, QTextEdit, QComboBox, QSpinBox { background: rgba(32,33,54,0.9); color: #ffffff; border: 1px solid rgba(144,238,144,0.08); border-radius: 6px; padding: 6px; }
                QPushButton { background-color: rgba(144,238,144,0.06); color: #e8ffea; border: 1px solid rgba(144,238,144,0.16); border-radius: 6px; padding: 6px 10px; }
                QPushButton:hover { background-color: rgba(144,238,144,0.14); }
            ''')
            self.icon_preview.setStyleSheet('border: 1px solid rgba(255,255,255,0.12); border-radius: 12px;')
    
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
            # 尝试抓取网站 favicon 并显示为图标预览（非阻塞）
            try:
                favicon_name = self._download_favicon(url)
                if favicon_name:
                    # 选中该图标名称并更新预览
                    self.selected_icon_name = favicon_name
                    self._update_icon_preview()
                else:
                    # 给用户提示：未能自动下载 favicon（但不阻止继续操作）
                    QMessageBox.information(self, "图标未获取", "未能自动获取网站图标，已使用默认图标或请手动选择。")
            except Exception:
                # 忽略 favicon 下载错误，但告知用户可手动选择
                QMessageBox.information(self, "图标获取异常", "尝试获取站点图标时发生错误，已使用默认或可手动选择图标。")
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

    def on_select_icon(self):
        """选择工具图标"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图标",
            self.icon_dir,
            "图标文件 (*.png *.jpg *.jpeg *.svg *.ico);;所有文件 (*.*)",
        )
        if file_path:
            # 允许选择任意目录下的图标文件
            self.selected_icon_name = file_path
            self._update_icon_preview()

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
        
        # 若为网页工具且未选择图标，尝试在保存前抓取favicon
        if is_web_tool and not self.selected_icon_name:
            try:
                favicon_name = self._download_favicon(path)
                if favicon_name:
                    self.selected_icon_name = favicon_name
            except Exception:
                # 保存前尝试抓取失败，告知用户（但仍允许保存使用默认图标）
                QMessageBox.information(self, "图标获取失败", "保存前尝试获取站点图标失败，工具将使用默认图标或您选择的图标。")
        # 若为本地工具且未选择图标，尝试使用工具根目录的favicon.ico
        elif not is_web_tool and not self.selected_icon_name:
            try:
                # 获取工具根目录
                tool_dir = os.path.dirname(os.path.abspath(path))
                # 检查工具根目录是否存在favicon.ico
                favicon_path = os.path.join(tool_dir, "favicon.ico")
                if os.path.exists(favicon_path):
                    # 使用工具根目录的favicon.ico
                    self.selected_icon_name = favicon_path
            except Exception:
                # 忽略错误，使用默认图标
                pass

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
            "icon": self.selected_icon_name or self.default_icon_name,
            "arguments": self.args_edit.text(),
            "working_directory": working_directory,  # 自动设置工作目录
            "run_in_terminal": False,  # 移除在终端中运行选项
            "is_web_tool": is_web_tool  # 设置工具类型
        })
        
        self.accept()
    
    def get_tool_data(self):
        """获取工具数据"""
        return self.tool_data

    def _normalize_icon_name(self, value):
        if not value:
            return ""
        # 支持绝对路径和相对路径
        if os.path.isabs(value):
            # 如果是绝对路径且文件存在，直接返回
            if os.path.exists(value):
                return value
            return ""
        # value 可能是相对路径
        candidate = os.path.join(self.icon_dir, value)
        if os.path.exists(candidate):
            return value
        # 检查相对路径是否存在
        if os.path.exists(value):
            return value
        return ""

    def _download_favicon(self, url: str, timeout: float = 5.0) -> str:
        """尝试从目标站点抓取 favicon 并保存到 resources/icons 目录。

        返回保存的文件名（相对 resources/icons），失败返回空字符串。
        """
        if not url:
            return ""

        parsed = urlparse(url)
        if not parsed.scheme:
            return ""

        domain = parsed.netloc
        base = f"{parsed.scheme}://{domain}"

        # Try common locations and public icon services
        candidates = [
            f"{base}/favicon.ico",
            f"https://{domain}/favicon.ico",
            f"http://{domain}/favicon.ico",
            f"https://www.google.com/s2/favicons?sz=64&domain={domain}",
            f"https://icons.duckduckgo.com/ip3/{domain}.ico"
        ]

        # Ensure icon_dir exists
        try:
            os.makedirs(self.icon_dir, exist_ok=True)
        except Exception:
            # cannot write to icon dir
            return ""

        for candidate in candidates:
            try:
                # small timeout
                req = urllib.request.Request(candidate, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = resp.read()
                    if not data:
                        continue

                    # determine extension
                    content_type = resp.headers.get('Content-Type', '') or ''
                    ext = '.ico'
                    if 'png' in content_type:
                        ext = '.png'
                    elif 'svg' in content_type:
                        ext = '.svg'
                    elif 'jpeg' in content_type or 'jpg' in content_type:
                        ext = '.jpg'

                    # create unique filename
                    safe_domain = domain.replace(':', '_').replace('/', '_')
                    filename = f"{safe_domain}_favicon{ext}"
                    path = os.path.join(self.icon_dir, filename)
                    # if exists, append counter
                    counter = 1
                    while os.path.exists(path):
                        filename = f"{safe_domain}_favicon_{counter}{ext}"
                        path = os.path.join(self.icon_dir, filename)
                        counter += 1

                    try:
                        with open(path, 'wb') as f:
                            f.write(data)
                    except Exception:
                        # cannot save
                        return ""

                    # success
                    return filename
            except (urllib.error.URLError, socket.timeout, Exception):
                continue

        # As a last attempt, try to fetch the homepage and parse for link rel icons
        try:
            homepage = f"{parsed.scheme}://{domain}/"
            req = urllib.request.Request(homepage, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                # naive parse for common link rel patterns
                matches = re.findall(r'<link[^>]+rel=[\'\"](?:icon|shortcut icon|apple-touch-icon)[\'\"][^>]*>', html, flags=re.I)
                for tag in matches:
                    # find href
                    m = re.search(r'href=[\'\"]([^\'\"]+)[\'\"]', tag)
                    if m:
                        href = m.group(1)
                        # resolve relative urls
                        if href.startswith('//'):
                            href = f"{parsed.scheme}:{href}"
                        elif href.startswith('/'):
                            href = f"{parsed.scheme}://{domain}{href}"
                        # try download this href
                        try:
                            req2 = urllib.request.Request(href, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(req2, timeout=timeout) as r2:
                                data = r2.read()
                                if data:
                                    ext = '.ico'
                                    ct = r2.headers.get('Content-Type','')
                                    if 'png' in ct:
                                        ext = '.png'
                                    elif 'svg' in ct:
                                        ext = '.svg'
                                    filename = f"{domain}_favicon_homepage{ext}"
                                    path = os.path.join(self.icon_dir, filename)
                                    with open(path, 'wb') as f:
                                        f.write(data)
                                    return filename
                        except Exception:
                            continue
        except Exception:
            pass

        return ""

    def _update_icon_preview(self):
        icon_name = self.selected_icon_name or self.default_icon_name
        # 处理绝对路径和相对路径
        if os.path.isabs(icon_name):
            icon_path = icon_name
        else:
            icon_path = os.path.join(self.icon_dir, icon_name)
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            self.icon_preview.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))

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
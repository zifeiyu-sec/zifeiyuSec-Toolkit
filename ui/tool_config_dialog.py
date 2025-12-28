#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具配置对话框模块，用于添加和编辑工具配置信息。"""
import os
import re
import socket
import shutil
import hashlib
from urllib.parse import urlparse
import urllib.request

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtWidgets import QLineEdit, QTextEdit, QPushButton, QComboBox
from PyQt5.QtWidgets import QCheckBox, QGroupBox, QGridLayout, QSpinBox
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QFileInfo
from PyQt5.QtWidgets import QFileIconProvider
from core.style_manager import ThemeManager

class ToolConfigDialog(QDialog):
    """工具配置对话框，用于添加或编辑工具信息"""
    def __init__(self, tool_data=None, categories=None, parent=None, theme_name=None):
        super().__init__(parent)
        # 支持主题传入，默认深色主题
        self.current_theme = theme_name or 'dark_green'
        self.tool_data = tool_data or self._create_empty_tool()
        self.categories = categories or []
        self.icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "icons")
        self.default_icon_name = "favicon.ico"
        self.selected_icon_name = self._normalize_icon_name(self.tool_data.get("icon"))
        self.downloader = None  # 初始化下载器属性
        self.init_ui()
        # 在 UI 建立后应用主题样式
        try:
            self.apply_theme_styles()
        except (RuntimeError, TypeError, AttributeError):
            pass
    
    class FaviconDownloader(QThread):
        """后台下载favicon的线程"""
        download_finished = pyqtSignal(str)
        
        def __init__(self, parent, url, icon_dir):
            super().__init__(parent)
            self.url = url
            self.icon_dir = icon_dir
        
        def run(self):
            """线程运行方法"""
            try:
                # 移动下载逻辑到线程内部，避免调用主线程方法
                favicon_name = self._download_favicon_logic(self.url)
                self.download_finished.emit(favicon_name)
            except Exception:
                self.download_finished.emit("")

        def _download_favicon_logic(self, url: str, timeout: float = 3.0) -> str:
            """实际的 favicon 下载逻辑（线程安全）"""
            if not url:
                return ""

            try:
                parsed = urlparse(url)
                if not parsed.scheme:
                    return ""

                domain = parsed.netloc
                base = f"{parsed.scheme}://{domain}"
            except Exception:
                return ""

            # 尝试常见位置（减少尝试次数，加快失败返回）
            candidates = [
                f"{base}/favicon.ico",
                f"{base}/favicon.png",
                f"{base}/apple-touch-icon.png"
            ]
            
            # 使用简单的 User-Agent
            headers = {"User-Agent": "Mozilla/5.0"}
            
            # 确保图标目录存在
            try:
                os.makedirs(self.icon_dir, exist_ok=True)
            except OSError:
                return ""

            # 1. 尝试直接下载候选地址
            for candidate in candidates:
                try:
                    req = urllib.request.Request(candidate, headers=headers)
                    # 缩短超时时间，避免长时间阻塞
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        data = resp.read()
                        if not data or len(data) < 10: continue
                        
                        # 简单的扩展名检测
                        ext = '.ico'
                        ct = resp.headers.get('Content-Type', '').lower()
                        if 'png' in ct: ext = '.png'
                        elif 'svg' in ct: ext = '.svg'
                        elif 'jpg' in ct or 'jpeg' in ct: ext = '.jpg'
                        
                        return self._save_icon(data, domain, ext)
                except Exception as e:
                    # 任何下载错误都直接跳过，尝试下一个候选地址
                    continue

            # 下载失败，返回空字符串，使用默认图标
            return ""

        def _save_icon(self, data, domain, ext):
            """保存图标文件（线程安全）"""
            safe_domain = domain.replace(':', '_').replace('/', '_')
            filename = f"{safe_domain}_favicon{ext}"
            path = os.path.join(self.icon_dir, filename)
            
            # 简单的防重名逻辑
            counter = 1
            while os.path.exists(path):
                filename = f"{safe_domain}_favicon_{counter}{ext}"
                path = os.path.join(self.icon_dir, filename)
                counter += 1
                
            try:
                with open(path, 'wb') as f:
                    f.write(data)
                return filename
            except Exception:
                return ""
    
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
        # 添加信号连接，当URL输入完成后自动尝试下载favicon
        self.path_edit.textChanged.connect(self.on_url_text_changed)
        self.path_edit.editingFinished.connect(self.on_url_editing_finished)
        # 创建延迟计时器
        self.favicon_timer = QTimer()
        self.favicon_timer.setSingleShot(True)
        self.favicon_timer.setInterval(500)  # 延迟500毫秒
        self.favicon_timer.timeout.connect(self.on_favicon_timer_timeout)
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
        
        # 在终端中运行选项
        self.run_in_terminal_check = QCheckBox("在终端中运行")
        self.run_in_terminal_check.setChecked(self.tool_data.get("run_in_terminal", False))
        run_layout.addWidget(self.run_in_terminal_check, 1, 1, alignment=Qt.AlignLeft)
        
        run_group.setLayout(run_layout)
        main_layout.addWidget(run_group)
        
        # 优先级和标签组
        tags_group = QGroupBox("其他设置")
        tags_layout = QGridLayout()
        
        # 收藏
        self.favorite_check = QCheckBox("添加到收藏")
        self.favorite_check.setChecked(self.tool_data.get("is_favorite", False))
        tags_layout.addWidget(self.favorite_check, 0, 1, alignment=Qt.AlignLeft)
        
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
            # 如果已经输入了URL，尝试自动下载favicon
            url = self.path_edit.text().strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                # 使用延迟计时器和后台线程，避免切换时卡死
                self.on_favicon_timer_timeout()
        else:
            self.path_label.setText("工具位置:")
            self.browse_button.setText("浏览")
            # 清除可能的计时器
            self.favicon_timer.stop()

    def set_theme(self, theme_name: str):
        """外部调用用于切换对话框主题"""
        self.current_theme = theme_name or 'dark_green'
        self.apply_theme_styles()

    def apply_theme_styles(self):
        """根据当前主题应用 QSS 样式（仅影响本对话框内控件）"""
        theme_manager = ThemeManager()
        style = theme_manager.get_dialog_style(self.current_theme)
        self.setStyleSheet(style)

        # 单独处理 Icon preview
        if self.current_theme == 'blue_white':
            self.icon_preview.setStyleSheet('border: 1px solid rgba(3,105,161,0.12); border-radius: 12px;')
        else:
            self.icon_preview.setStyleSheet('border: 1px solid rgba(255,255,255,0.12); border-radius: 12px;')
    
    def on_url_text_changed(self, text):
        """当URL文本改变时，重置计时器"""
        is_web_tool = self.tool_type_combo.currentData()
        if is_web_tool and text.strip():
            # 重置计时器
            self.favicon_timer.start()
        else:
            # 如果不是网页工具或文本为空，停止计时器
            self.favicon_timer.stop()
    
    def on_favicon_timer_timeout(self):
        """当计时器超时后，执行favicon下载"""
        is_web_tool = self.tool_type_combo.currentData()
        if is_web_tool:
            url = self.path_edit.text().strip()
            if url and (url.startswith("http://") or url.startswith("https://")):
                # 检查并清理之前的下载线程
                if hasattr(self, 'downloader') and self.downloader is not None:
                    if self.downloader.isRunning():
                        # 尝试优雅地终止旧线程
                        self.downloader.quit()
                        self.downloader.wait(500)  # 等待500毫秒
                    # 断开信号连接
                    try:
                        self.downloader.download_finished.disconnect()
                    except TypeError:
                        # 可能已经断开连接，忽略此错误
                        pass
                    self.downloader = None
                
                # 创建并启动新的下载线程
                self.downloader = self.FaviconDownloader(self, url, self.icon_dir)
                self.downloader.download_finished.connect(self.on_favicon_download_finished)
                self.downloader.start()
    
    def on_favicon_download_finished(self, favicon_name):
        """处理favicon下载完成事件"""
        try:
            if favicon_name and isinstance(favicon_name, str):
                # 验证文件名格式是否有效
                if not any(favicon_name.endswith(ext) for ext in ['.ico', '.png', '.svg', '.jpg', '.jpeg']):
                    # 无效的图标文件扩展名，不使用该图标
                    return
                
                # 验证文件是否真正存在
                icon_path = os.path.join(self.icon_dir, favicon_name)
                if not os.path.exists(icon_path) or not os.path.isfile(icon_path):
                    # 文件不存在或不是有效文件，不使用该图标
                    return
                
                # 选中该图标名称并更新预览
                self.selected_icon_name = favicon_name
                self._update_icon_preview()
        except Exception as e:
            # 捕获所有异常，防止因favicon处理问题导致崩溃
            pass
    
    def on_url_editing_finished(self):
        """当URL输入完成后自动尝试下载favicon"""
        # 不再直接调用，改为由计时器处理
    
    def _async_download_favicon(self, url):
        """异步下载favicon并更新图标预览"""
        try:
            # 检查是否需要下载favicon
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                return
            
            # 检查并清理之前的下载线程
            if hasattr(self, 'downloader') and self.downloader is not None:
                if self.downloader.isRunning():
                    self.downloader.quit()
                    self.downloader.wait(500)
                try:
                    self.downloader.download_finished.disconnect()
                except TypeError:
                    pass
                self.downloader = None
            
            # 启动一个新线程来下载favicon，避免阻塞UI
            self.downloader = self.FaviconDownloader(self, url, self.icon_dir)
            self.downloader.download_finished.connect(self.on_favicon_download_finished)
            self.downloader.start()
        except Exception as e:
            # 捕获所有异常，确保不会影响主线程
            pass
    
    def validate_url(self, url):
        """验证URL格式是否正确"""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc]) and parsed.scheme in ['http', 'https']
        except (ValueError, AttributeError):
            return False
    
    def on_browse_path(self):
        """浏览工具路径或验证URL"""
        try:
            is_web_tool = self.tool_type_combo.currentData()
            
            if is_web_tool:
                # 验证URL
                url = self.path_edit.text().strip()
                if not url:
                    QMessageBox.warning(self, "警告", "请输入URL地址！")
                    return
                
                # 严格验证URL格式
                if not (url.startswith("http://") or url.startswith("https://")):
                    QMessageBox.warning(self, "警告", "URL地址必须以http://或https://开头！")
                    return
                
                if not self.validate_url(url):
                    QMessageBox.warning(self, "警告", "URL格式不正确，请检查地址是否完整！")
                    return
                
                QMessageBox.information(self, "信息", "URL格式验证通过！")
                # 尝试抓取网站 favicon 并显示为图标预览
                # 使用现有的异步下载方法
                self._async_download_favicon(url)
            else:
                # 浏览本地文件或目录
                # 允许用户选择文件或目录
                path, _ = QFileDialog.getOpenFileName(
                    self, "选择工具或目录", 
                    os.path.dirname(self.path_edit.text()) or ".",
                    "可执行文件 (*.exe *.bat *.cmd *.py);;所有文件 (*.*)"
                )
                
                # 如果没有选择文件，尝试选择目录
                if not path:
                    path = QFileDialog.getExistingDirectory(
                        self, "选择目录", 
                        os.path.dirname(self.path_edit.text()) or "."
                    )
                
                if path:
                    self.path_edit.setText(path)
        except Exception as e:
            # 捕获所有异常，防止因浏览路径或验证URL过程中的问题导致崩溃
            QMessageBox.warning(self, "错误", f"操作失败: {e}")

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
    
    def _async_download_favicon(self, url):
        """异步下载favicon图标"""


        self.downloader = self.FaviconDownloader(self, url, self.icon_dir)
        self.downloader.download_finished.connect(self._on_favicon_downloaded)
        self.downloader.start()
        
    def _on_favicon_downloaded(self, favicon_name):
        """处理异步下载完成的回调"""
        if favicon_name and self.parent():
            try:
                # 更新工具数据中的图标路径
                if hasattr(self.parent(), 'update_tool_icon'):
                    tool_data = self.get_tool_data()
                    self.parent().update_tool_icon(tool_data['id'], favicon_name)
                # 更新本地图标预览
                self.selected_icon_name = favicon_name
                self._update_icon_preview()
            except (AttributeError, TypeError, ValueError):
                pass
        
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
            
            # 检查文件是否可执行（对于Windows可执行文件）
            if os.path.isfile(path) and not path.lower().endswith(('.exe', '.bat', '.cmd', '.py', '.ps1')):
                reply = QMessageBox.question(self, "询问", 
                                           f"所选文件 '{os.path.basename(path)}' 可能不是可执行文件，是否继续？",
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return
            
            # 自动设置工作目录为工具所在目录
            working_directory = os.path.dirname(os.path.abspath(path))
        else:
            # 验证网页工具URL格式
            if not (path.startswith("http://") or path.startswith("https://")):
                QMessageBox.warning(self, "警告", "URL地址必须以http://或https://开头！")
                return
                
            if not self.validate_url(path):
                QMessageBox.warning(self, "警告", "URL格式不正确，请检查地址是否完整！")
                return
        
        # 若为网页工具且未选择图标，直接使用默认图标，不等待favicon下载
        # 保存后会自动后台下载favicon，下次打开时会显示
        if is_web_tool and not self.selected_icon_name:
            # 直接使用默认图标，不阻塞保存操作
            pass
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
            except (FileNotFoundError, PermissionError, OSError):
                # 忽略错误，使用默认图标
                pass
            
            # 如果仍然没有图标，且是本地可执行文件，尝试提取系统图标
            if not self.selected_icon_name and os.path.isfile(path):
                try:
                    # 使用 QFileIconProvider 提取图标
                    file_info = QFileInfo(path)
                    provider = QFileIconProvider()
                    icon = provider.icon(file_info)
                    
                    if not icon.isNull():
                        # 获取最大可用尺寸
                        sizes = icon.availableSizes()
                        if sizes:
                            # 找最大的尺寸，或者至少 48x48
                            max_size = sizes[-1] # 通常最后一个是最大的
                            if max_size.width() < 48:
                                max_size = Qt.QSize(48, 48)
                        else:
                            max_size = Qt.QSize(48, 48)
                            
                        # 转换为 Pixmap
                        pixmap = icon.pixmap(max_size)
                        
                        # 生成保存路径
                        tool_name_safe = re.sub(r'[\\/:*?"<>|]', '_', name)
                        icon_filename = f"{tool_name_safe}_icon.png"
                        target_path = os.path.join(self.icon_dir, icon_filename)
                        
                        # 确保不覆盖现有文件
                        counter = 1
                        base_name, ext = os.path.splitext(icon_filename)
                        while os.path.exists(target_path):
                            icon_filename = f"{base_name}_{counter}{ext}"
                            target_path = os.path.join(self.icon_dir, icon_filename)
                            counter += 1
                        
                        # 确保目录存在
                        os.makedirs(self.icon_dir, exist_ok=True)
                        
                        # 保存图标
                        if pixmap.save(target_path, "PNG"):
                            self.selected_icon_name = target_path
                except Exception as e:
                    print(f"提取图标失败: {e}")
                    pass

        # 处理图标文件路径，统一保存到resources/icons目录
        final_icon_name = None
        try:
            # 先检查是否有正在运行的下载线程，如果有，直接使用默认图标，不等待下载完成
            if hasattr(self, 'downloader') and self.downloader is not None and self.downloader.isRunning():
                # 有正在运行的下载线程，直接使用默认图标
                final_icon_name = self.default_icon_name
            elif self.selected_icon_name:
                if os.path.isabs(self.selected_icon_name):
                    # 如果是绝对路径，复制到resources/icons目录
                    # 先检查文件是否存在且是有效文件
                    if not os.path.exists(self.selected_icon_name) or not os.path.isfile(self.selected_icon_name):
                        # 文件不存在或无效，使用默认图标
                        final_icon_name = self.default_icon_name
                    else:
                        try:
                            # 首先检查是否已存在相同内容的图标
                            existing_icon = self._find_existing_icon_by_hash(self.selected_icon_name)
                            if existing_icon:
                                # 找到相同图标，直接使用现有的
                                final_icon_name = existing_icon
                            else:
                                # 没有找到相同图标，需要复制新文件
                                icon_name = os.path.basename(self.selected_icon_name)
                                # 确保文件名唯一（仅当文件名冲突时）
                                base_name, ext = os.path.splitext(icon_name)
                                counter = 1
                                target_path = os.path.join(self.icon_dir, icon_name)
                                while os.path.exists(target_path):
                                    icon_name = f"{base_name}_{counter}{ext}"
                                    target_path = os.path.join(self.icon_dir, icon_name)
                                    counter += 1
                                # 复制文件
                                shutil.copy2(self.selected_icon_name, target_path)
                                final_icon_name = icon_name
                        except (FileNotFoundError, PermissionError, IOError, shutil.Error, OSError) as e:
                            # 复制失败，使用默认图标
                            final_icon_name = self.default_icon_name
                else:
                    # 相对路径，检查文件是否存在
                    icon_path = os.path.join(self.icon_dir, self.selected_icon_name)
                    if os.path.exists(icon_path) and os.path.isfile(icon_path):
                        final_icon_name = self.selected_icon_name
                    else:
                        # 文件不存在，使用默认图标
                        final_icon_name = self.default_icon_name
            else:
                final_icon_name = self.default_icon_name
        except Exception as e:
            # 捕获所有异常，确保工具添加操作能继续完成
            final_icon_name = self.default_icon_name

        # 更新工具数据
        self.tool_data.update({
            "name": name,
            "path": path,
            "description": self.description_edit.toPlainText(),
            "category_id": self.category_combo.currentData() if self.categories else None,
            "subcategory_id": self.subcategory_combo.currentData() if self.categories else None,
            "is_favorite": self.favorite_check.isChecked(),
            "tags": [],  # 移除标签功能
            "icon": final_icon_name,
            "arguments": self.args_edit.text(),
            "working_directory": working_directory,  # 自动设置工作目录
            "run_in_terminal": self.run_in_terminal_check.isChecked(),  # 保存是否在终端中运行的设置
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

    def _calculate_file_hash(self, file_path):
        """计算文件的SHA256哈希值"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            print(f"计算文件哈希失败: {e}")
            return None

    def _find_existing_icon_by_hash(self, source_path):
        """根据文件哈希值查找已存在的相同图标"""
        try:
            source_hash = self._calculate_file_hash(source_path)
            if not source_hash:
                return None

            # 遍历图标目录，查找相同哈希值的文件
            if os.path.exists(self.icon_dir):
                for filename in os.listdir(self.icon_dir):
                    file_path = os.path.join(self.icon_dir, filename)
                    if os.path.isfile(file_path):
                        file_hash = self._calculate_file_hash(file_path)
                        if file_hash == source_hash:
                            return filename
            return None
        except Exception as e:
            print(f"查找重复图标失败: {e}")
            return None

    def _download_favicon(self, url: str, timeout: float = 8.0) -> str:
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

        # 尝试常见位置和公共图标服务
        # 增加更多可能的图标位置
        candidates = [
            f"{base}/favicon.ico",
            f"{base}/favicon.png",
            f"{base}/apple-touch-icon.png",
            f"{base}/favicon.svg",
            f"{base}/apple-touch-icon-precomposed.png",
            f"{base}/favicon.jpg",
            f"{base}/favicon.jpeg",
            f"https://{domain}/favicon.ico",
            f"http://{domain}/favicon.ico"
        ]

        # 添加公共图标服务作为备选
        # 注意：这些服务可能会超时，所以放在后面尝试
        candidates.extend([
            f"https://www.google.com/s2/favicons?sz=64&domain={domain}",
            f"https://icons.duckduckgo.com/ip3/{domain}.ico"
        ])

        # 确保图标目录存在
        try:
            os.makedirs(self.icon_dir, exist_ok=True)
        except (FileNotFoundError, PermissionError, OSError):
            # 无法写入图标目录，尝试创建目录
            return ""

        for candidate in candidates:
            try:
                # 增加超时时间，使用更完整的 User-Agent
                req = urllib.request.Request(
                    candidate, 
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = resp.read()
                    # 检查响应数据是否为空
                    if not data or len(data) < 10:  # 过滤过小的响应
                        continue

                    # 确定文件扩展名
                    content_type = resp.headers.get('Content-Type', '') or ''
                    ext = '.ico'
                    if 'png' in content_type.lower():
                        ext = '.png'
                    elif 'svg' in content_type.lower():
                        ext = '.svg'
                    elif 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                        ext = '.jpg'
                    # 如果没有 Content-Type，尝试从 URL 路径猜测扩展名
                    elif '.' in candidate.rsplit('/', maxsplit=1)[-1]:
                        guessed_ext = candidate.rsplit('.', maxsplit=1)[-1].lower()
                        if guessed_ext in ['ico', 'png', 'svg', 'jpg', 'jpeg']:
                            ext = f'.{guessed_ext}'

                    # 创建唯一文件名
                    safe_domain = domain.replace(':', '_').replace('/', '_')
                    filename = f"{safe_domain}_favicon{ext}"
                    path = os.path.join(self.icon_dir, filename)
                    # 如果存在，添加计数器
                    counter = 1
                    while os.path.exists(path):
                        filename = f"{safe_domain}_favicon_{counter}{ext}"
                        path = os.path.join(self.icon_dir, filename)
                        counter += 1

                    # 确保目录存在（再次检查）
                    if not os.path.exists(self.icon_dir):
                        try:
                            os.makedirs(self.icon_dir, exist_ok=True)
                        except (FileNotFoundError, PermissionError, OSError):
                            continue
                            
                    try:
                        with open(path, 'wb') as f:
                            f.write(data)
                        # 验证文件是否成功保存
                        if os.path.exists(path) and os.path.getsize(path) > 0:
                            return filename
                    except (FileNotFoundError, PermissionError, IOError, OSError):
                        # 无法保存，继续尝试其他候选位置
                        continue

            except (urllib.error.URLError, socket.timeout, urllib.error.HTTPError, ValueError, IOError):
                # 忽略所有可能的错误，继续尝试下一个候选位置
                continue

        # 作为最后的尝试，尝试获取完整URL对应的页面并解析link rel图标
        try:
            # 首先尝试获取用户提供的完整URL对应的页面
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                # 增强正则表达式，支持更多rel属性值和格式
                matches = re.findall(r'<link[^>]+rel=[\'\"](?:icon|shortcut icon|apple-touch-icon|apple-touch-icon-precomposed|mask-icon|fluid-icon)[\'\"][^>]*>', html, flags=re.I)
                for tag in matches:
                    # 查找href
                    m = re.search(r'href=[\'\"]([^\'\"]+)[\'\"]', tag)
                    if m:
                        href = m.group(1)
                        # 解析相对URL
                        if href.startswith('//'):
                            href = f"{parsed.scheme}:{href}"
                        elif href.startswith('/'):
                            href = f"{parsed.scheme}://{domain}{href}"
                        elif not href.startswith(('http://', 'https://')):
                            # 处理相对路径，如 "favicon.ico", "images/favicon.png" 等
                            # 获取当前URL的目录路径
                            current_path = '/'.join(url.split('/')[:-1]) + '/' if '/' in url else url + '/'
                            href = f"{current_path}{href}"
                        # 尝试下载此href
                        try:
                            req2 = urllib.request.Request(href, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(req2, timeout=timeout) as r2:
                                data = r2.read()
                                if data:
                                    ext = '.ico'
                                    ct = r2.headers.get('Content-Type','')
                                    if 'png' in ct.lower():
                                        ext = '.png'
                                    elif 'svg' in ct.lower():
                                        ext = '.svg'
                                    elif 'jpeg' in ct.lower() or 'jpg' in ct.lower():
                                        ext = '.jpg'
                                    filename = f"{domain}_favicon_html{ext}"
                                    path = os.path.join(self.icon_dir, filename)
                                    with open(path, 'wb') as f:
                                        f.write(data)
                                    return filename
                        except (urllib.error.URLError, socket.timeout, IOError):
                            continue
        except (urllib.error.URLError, socket.timeout, ValueError):
            # 如果获取完整URL失败，尝试获取主页
            try:
                homepage = f"{parsed.scheme}://{domain}/"
                req = urllib.request.Request(homepage, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
                    # 增强正则表达式，支持更多rel属性值和格式
                    matches = re.findall(r'<link[^>]+rel=[\'\"](?:icon|shortcut icon|apple-touch-icon|apple-touch-icon-precomposed|mask-icon|fluid-icon)[\'\"][^>]*>', html, flags=re.I)
                    for tag in matches:
                        # 查找href
                        m = re.search(r'href=[\'\"]([^\'\"]+)[\'\"]', tag)
                        if m:
                            href = m.group(1)
                            # 解析相对URL
                            if href.startswith('//'):
                                href = f"{parsed.scheme}:{href}"
                            elif href.startswith('/'):
                                href = f"{parsed.scheme}://{domain}{href}"
                            # 尝试下载此href
                            try:
                                req2 = urllib.request.Request(href, headers={"User-Agent": "Mozilla/5.0"})
                                with urllib.request.urlopen(req2, timeout=timeout) as r2:
                                    data = r2.read()
                                    if data:
                                        ext = '.ico'
                                        ct = r2.headers.get('Content-Type','')
                                        if 'png' in ct.lower():
                                            ext = '.png'
                                        elif 'svg' in ct.lower():
                                            ext = '.svg'
                                        elif 'jpeg' in ct.lower() or 'jpg' in ct.lower():
                                            ext = '.jpg'
                                        filename = f"{domain}_favicon_homepage{ext}"
                                        path = os.path.join(self.icon_dir, filename)
                                        with open(path, 'wb') as f:
                                            f.write(data)
                                        return filename
                            except (urllib.error.URLError, socket.timeout, IOError):
                                continue
            except (urllib.error.URLError, socket.timeout, ValueError):
                pass

        return ""

    def closeEvent(self, event):
        """当对话框关闭时，清理资源"""
        try:
            # 停止favicon计时器
            if hasattr(self, 'favicon_timer') and self.favicon_timer is not None:
                self.favicon_timer.stop()
            
            # 停止并清理下载线程
            if hasattr(self, 'downloader') and self.downloader is not None:
                if self.downloader.isRunning():
                    # 尝试优雅地终止线程
                    self.downloader.quit()
                    # 等待线程终止，最多等待1秒
                    self.downloader.wait(1000)
                # 断开所有信号连接
                self.downloader.download_finished.disconnect()
                # 清理引用，允许垃圾回收
                self.downloader = None
        except Exception as e:
            # 捕获所有异常，防止清理过程中出错
            pass
        
        # 调用父类的closeEvent
        super().closeEvent(event)
    
    def _update_icon_preview(self):
        try:
            # 处理图标文件路径
            icon_name = self.selected_icon_name or self.default_icon_name
            
            # 处理绝对路径和相对路径
            if os.path.isabs(icon_name):
                icon_path = icon_name
            else:
                icon_path = os.path.join(self.icon_dir, icon_name)
            
            # 检查文件是否存在
            if not os.path.exists(icon_path) or not os.path.isfile(icon_path):
                # 如果文件不存在或不是文件，使用默认图标
                icon_path = os.path.join(self.icon_dir, self.default_icon_name)
            
            # 确保默认图标路径有效
            if not os.path.exists(icon_path) or not os.path.isfile(icon_path):
                # 如果默认图标也不存在，直接返回
                return
            
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self.icon_preview.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                # 如果图标文件损坏，也使用默认图标
                default_icon_path = os.path.join(self.icon_dir, self.default_icon_name)
                if os.path.exists(default_icon_path) and os.path.isfile(default_icon_path):
                    pixmap = QPixmap(default_icon_path)
                    if not pixmap.isNull():
                        self.icon_preview.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            # 捕获所有异常，防止因图标问题导致崩溃
            pass

# 示例用法
if __name__ == "__main__":
    import sys
    
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

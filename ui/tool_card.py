import os
import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout, QScrollArea, QMessageBox, QMenu, QAction
from PyQt5.QtCore import pyqtSignal, Qt, QProcess, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QBrush, QColor

class ToolCard(QFrame):
    # 信号定义
    run_tool = pyqtSignal(dict)  # 运行工具信号
    edit_requested = pyqtSignal(dict)  # 编辑请求信号
    deleted = pyqtSignal(int)  # 删除信号
    toggle_favorite = pyqtSignal(int)  # 切换收藏状态信号
    
    def __init__(self, tool_data, parent=None):
        super().__init__(parent)
        self.tool_data = tool_data
        self.process = None  # 用于运行外部工具的进程
        self.init_ui()
    
    def init_ui(self):
        """初始化工具卡片界面"""
        # 设置卡片样式
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setMinimumHeight(120)  # 固定高度
        self.setMinimumWidth(200)   # 设置最小宽度
        self.setMaximumHeight(120)  # 固定最大高度
        # 移除固定最大宽度限制，允许卡片根据容器宽度自适应
        
        # 设置卡片样式为玻璃主题
        self.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(103, 232, 249, 0.3);
                border-radius: 6px;
                color: #ffffff;
                padding: 6px 12px;
                margin: 2px;
                font-size: 12px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background: rgba(103, 232, 249, 0.15);
                border-color: rgba(103, 232, 249, 0.5);
            }
            
            QPushButton:pressed {
                background: rgba(103, 232, 249, 0.25);
            }
        """)
        
        # 设置右键菜单支持
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # 设置布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)  # 调整边距
        main_layout.setAlignment(Qt.AlignTop)  # 顶部对齐
        main_layout.setSpacing(8)  # 设置元素间距
        
        # 工具名称
        self.name_label = QLabel(self.tool_data['name'])
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("""
            QLabel {
                font-weight: 600;
                font-size: 14px;
                color: #90ee90;
                margin: 3px 0;
                text-align: center;
            }
        """)
        self.name_label.setWordWrap(True)  # 允许名称换行
        self.name_label.setMaximumHeight(35)  # 限制名称高度
        
        # 工具介绍
        self.description_label = QLabel(self.tool_data.get('description', '无介绍'))
        self.description_label.setAlignment(Qt.AlignLeft)
        self.description_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #81c784;
                margin: 3px 0;
                text-align: left;
            }
        """)
        self.description_label.setWordWrap(True)  # 允许描述换行
        self.description_label.setMaximumHeight(45)  # 限制描述高度
        
        # 按钮区域（包含运行和打开文件夹按钮）
        buttons_container = QWidget()
        buttons_layout = QGridLayout(buttons_container)
        buttons_layout.setAlignment(Qt.AlignCenter)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(6)  # 按钮间距
        
        # 运行按钮
        self.run_button = QPushButton("运行")
        self.run_button.setFixedHeight(26)  # 按钮高度
        self.run_button.setFixedWidth(50)   # 按钮宽度
        # 美化按钮样式：添加渐变和圆角
        self.run_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #4caf50, stop:1 #388e3c);
                color: #ffffff;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 13px;
                font-size: 11px;
                border: 1px solid #388e3c;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #388e3c, stop:1 #2e7d32);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #2e7d32, stop:1 #1b5e20);
            }
        """)
        self.run_button.clicked.connect(self.on_run_clicked)
        buttons_layout.addWidget(self.run_button, 0, 0)
        
        # 打开文件夹按钮 - 仅本地工具显示
        self.open_folder_button = QPushButton("打开文件夹")
        self.open_folder_button.setFixedHeight(26)  # 按钮高度
        self.open_folder_button.setFixedWidth(80)   # 按钮宽度
        # 美化按钮样式
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #2d5016, stop:1 #4caf50);
                color: #ffffff;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 13px;
                font-size: 11px;
                border: 1px solid #4caf50;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #4caf50, stop:1 #66bb6a);
                color: #ffffff;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                          stop:0 #1b5e20, stop:1 #2d5016);
                color: #ffffff;
            }
        """)
        self.open_folder_button.clicked.connect(self.on_open_folder_clicked)
        
        # 只有本地工具才显示打开文件夹按钮
        if not self.tool_data.get('is_web_tool', False):
            buttons_layout.addWidget(self.open_folder_button, 0, 1)
        
        # 将所有元素添加到主布局
        main_layout.addWidget(self.name_label)
        main_layout.addWidget(self.description_label)
        main_layout.addWidget(buttons_container)
        main_layout.addStretch(1)  # 添加弹性空间
    
    def update_favorite_icon(self):
        """更新收藏图标"""
        # 实现收藏图标的更新逻辑
        if self.tool_data.get('is_favorite', False):
            # 设置收藏图标
            pass
        else:
            # 设置非收藏图标
            pass
        
    def update_tool_icon(self):
        """更新工具图标"""
        icon_path = self.tool_data.get('icon', '')
        if icon_path and os.path.exists(icon_path):
            # 加载用户上传的图标
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                self.icon_label.setPixmap(pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.icon_label.setText("")
                self.icon_label.setStyleSheet("border: 1px solid #CCCCCC; border-radius: 6px;")
                return
        # 默认显示图标文字
        self.icon_label.setText("图标")
        self.icon_label.setStyleSheet("background-color: #F0F0F0; border: 1px solid #CCCCCC; border-radius: 6px; color: #666666; font-size: 16px; font-weight: bold;")
    

    
    def on_run_clicked(self):
        """处理运行按钮点击事件"""
        tool_path = self.tool_data.get('path', '')
        if not tool_path:
            QMessageBox.warning(self, "错误", "工具路径未设置！")
            return
        
        # 检查是否为网页工具
        is_web_tool = self.tool_data.get('is_web_tool', False)
        
        if is_web_tool:
            # 网页工具，使用默认浏览器打开
            try:
                import webbrowser
                webbrowser.open(tool_path)
                self.run_tool.emit(self.tool_data)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"打开网页工具失败: {str(e)}")
        else:
            # 本地工具，按照原逻辑处理
            # 检查路径是否存在
            if not os.path.exists(tool_path):
                # 尝试在PATH中查找
                import shutil
                found_path = shutil.which(tool_path)
                if not found_path:
                    QMessageBox.warning(self, "错误", f"找不到工具: {tool_path}")
                    return
                else:
                    tool_path = found_path
            
            try:
                # 启动外部进程
                self.process = QProcess()
                
                # 设置工作目录（如果有）
                working_directory = self.tool_data.get('working_directory', '')
                if working_directory and os.path.exists(working_directory):
                    self.process.setWorkingDirectory(working_directory)
                
                # 获取命令行参数
                arguments = self.tool_data.get('arguments', '')
                
                # 检查是否为Windows批处理文件
                is_bat_file = tool_path.lower().endswith('.bat') and sys.platform == 'win32'
                
                # 根据操作系统、文件类型和设置启动进程
                if self.tool_data.get('run_in_terminal', False) or is_bat_file:
                    # 在终端中运行，对于.bat文件强制使用终端
                    if sys.platform == 'win32':
                        # Windows下使用cmd运行，特别优化批处理文件的执行
                        if is_bat_file:
                            # 对于.bat文件，使用cmd直接执行并保持窗口打开
                            cmd_command = f'start cmd.exe /k "call \"{tool_path}\" {arguments}"'
                            self.process.startDetached('cmd.exe', ['/c', cmd_command])
                            # 对于批处理文件，我们不设置finished信号，因为它是在新窗口中运行的
                            self.process = None
                            return
                        else:
                            # 其他文件类型使用常规方式
                            cmd_command = f'start cmd.exe /k "\"{tool_path}\" {arguments}"'
                            self.process.start('cmd.exe', ['/c', cmd_command])
                    else:
                        # Linux/Mac下使用终端模拟器
                        terminal_commands = ['x-terminal-emulator', 'gnome-terminal', 'konsole', 'xterm']
                        terminal = None
                        
                        for term in terminal_commands:
                            if shutil.which(term):
                                terminal = term
                                break
                        
                        if terminal:
                            if terminal == 'x-terminal-emulator':
                                self.process.start(terminal, ['-e', f'{tool_path} {arguments}'])
                            elif terminal == 'gnome-terminal':
                                self.process.start(terminal, ['--', 'sh', '-c', f'{tool_path} {arguments}; read -p "按Enter键继续..."'])
                            else:
                                self.process.start(terminal, ['-e', f'{tool_path} {arguments}'])
                        else:
                            QMessageBox.warning(self, "错误", "找不到可用的终端模拟器！")
                            return
                else:
                    # 直接运行进程
                    if arguments:
                        # 分割参数（简单处理，不考虑引号内的空格）
                        args_list = []
                        import shlex
                        try:
                            args_list = shlex.split(arguments)
                        except:
                            # 如果分割失败，简单按空格分割
                            args_list = arguments.split()
                        
                        # 启动进程，注意这里tool_path已经是命令，不需要再次添加
                        self.process.start(tool_path, args_list)
                    else:
                        # 没有参数时直接运行
                        self.process.start(tool_path)
                
                # 只有当进程不为None时才设置信号（批处理文件情况已返回）
                if self.process:
                    # 设置进程完成信号
                    self.process.finished.connect(self.on_process_finished)
                    self.process.errorOccurred.connect(self.on_process_error)
                    
                    self.run_tool.emit(self.tool_data)
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"运行工具失败: {str(e)}")
    
    def on_process_finished(self, exit_code, exit_status):
        """处理进程完成事件"""
        self.process = None
        
    def on_process_error(self, error):
        """处理进程错误事件"""
        error_messages = {
            QProcess.FailedToStart: "无法启动进程",
            QProcess.Crashed: "进程崩溃",
            QProcess.Timedout: "进程超时",
            QProcess.WriteError: "写入错误",
            QProcess.ReadError: "读取错误",
            QProcess.UnknownError: "未知错误"
        }
        
        error_msg = error_messages.get(error, "未知错误")
        QMessageBox.warning(self, "进程错误", f"运行工具时发生错误: {error_msg}")
        self.process = None
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 运行菜单项
        run_action = QAction("运行", self)
        run_action.triggered.connect(self.on_run_clicked)
        
        # 编辑菜单项
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self.on_edit_requested)
        
        # 删除菜单项
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.on_delete_requested)
        
        # 添加菜单项
        menu.addAction(run_action)
        menu.addSeparator()
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.mapToGlobal(position))
    
    def on_edit_requested(self):
        """处理编辑请求"""
        self.edit_requested.emit(self.tool_data)
    
    def on_delete_requested(self):
        """处理删除请求"""
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除工具 "{self.tool_data["name"]}" 吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.deleted.emit(self.tool_data['id'])
    
    def on_open_folder_clicked(self):
        """处理打开文件夹按钮点击事件"""
        tool_path = self.tool_data.get('path', '')
        if not tool_path:
            QMessageBox.warning(self, "错误", "工具路径未设置！")
            return
        
        # 获取文件夹路径
        import os
        folder_path = os.path.dirname(os.path.abspath(tool_path))
        
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "错误", f"文件夹不存在: {folder_path}")
            return
        
        try:
            # 使用操作系统默认方式打开文件夹
            import webbrowser
            webbrowser.open(folder_path)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件夹失败: {str(e)}")
    

    
    def update_data(self, tool_data):
        """更新工具卡片数据"""
        self.tool_data = tool_data
        
        # 更新UI元素
        self.name_label.setText(tool_data['name'])
        self.description_label.setText(tool_data.get('description', '无介绍'))

class ToolCardContainer(QWidget):
    # 信号定义
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    new_tool_requested = pyqtSignal()  # 右键菜单新建工具信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tool_cards = {}
        self.current_tools = []  # 保存当前显示的工具列表
        self.view_type = "grid"  # 只保留网格视图
        self.init_ui()
    
    def resizeEvent(self, event):
        """窗口大小变化时重新计算和布局工具卡片"""
        super().resizeEvent(event)
        # 延迟重新布局，避免频繁计算
        self.layout_timer = QTimer.singleShot(100, self._delayed_layout)
    
    def _delayed_layout(self):
        """延迟执行布局更新，优化性能"""
        # 只有在网格视图且有工具时才重新布局
        if self.view_type == "grid" and hasattr(self, 'current_tools') and self.current_tools:
            self.display_tools(self.current_tools)
    
    def init_ui(self):
        """初始化容器界面"""
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: #1a1a1a;")
        
        # 创建内容窗口
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background-color: #1a1a1a;")
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)  # 水平居中，垂直置顶
        self.grid_layout.setSpacing(10)  # 调整间距为合适大小
        self.grid_layout.setContentsMargins(10, 10, 10, 10)  # 调整边距为合适大小
        
        self.scroll_area.setWidget(self.content_widget)
        
        # 设置主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 减少外部边距
        main_layout.addWidget(self.scroll_area)
        
        # 设置右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def display_tools(self, tools):
        """显示工具列表（仅网格视图）"""
        # 保存当前工具列表
        self.current_tools = tools
        
        # 清除现有卡片
        self.clear_cards()
        
        # 仅使用网格视图显示工具
        self._display_tools_grid(tools)
    
    def _display_tools_grid(self, tools):
        """以网格视图显示工具，根据容器宽度自动调整列数"""
        # 根据容器宽度计算每行可以显示的列数
        container_width = self.scroll_area.width() - 40  # 减去边距
        max_cols = 3  # 固定显示3列
        
        # 计算卡片宽度，考虑间距（grid_layout.setSpacing(10)）
        spacing = 10
        card_width = (container_width - (max_cols - 1) * spacing) // max_cols
        
        row = 0
        col = 0
        
        for tool in tools:
            tool_card = ToolCard(tool)
            self._setup_tool_card_connections(tool_card)
            
            # 设置卡片宽度
            tool_card.setMinimumWidth(card_width)
            tool_card.setMaximumWidth(card_width)
            
            self.grid_layout.addWidget(tool_card, row, col)
            self.tool_cards[tool['id']] = tool_card
            
            # 更新行列索引
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    

    
    def _setup_tool_card_connections(self, tool_card):
        """设置工具卡片的信号连接"""
        tool_card.run_tool.connect(self.run_tool.emit)
        tool_card.edit_requested.connect(self.edit_requested.emit)
        tool_card.deleted.connect(self.deleted.emit)
        tool_card.toggle_favorite.connect(self.toggle_favorite.emit)
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 添加新建工具菜单项
        new_tool_action = QAction("新建工具", self)
        new_tool_action.triggered.connect(self.new_tool_requested.emit)
        menu.addAction(new_tool_action)
        
        # 显示菜单
        menu.exec_(self.mapToGlobal(position))
    
    def clear_cards(self):
        """清除所有工具卡片"""
        # 删除所有布局中的项目
        while self.grid_layout.count() > 0:
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # 清空卡片字典
        self.tool_cards.clear()
    
    def update_tool(self, tool_id, tool_data):
        """更新指定工具的卡片"""
        if tool_id in self.tool_cards:
            self.tool_cards[tool_id].update_data(tool_data)
    
    def remove_tool(self, tool_id):
        """移除指定工具的卡片"""
        if tool_id in self.tool_cards:
            widget = self.tool_cards[tool_id]
            self.grid_layout.removeWidget(widget)
            widget.deleteLater()
            del self.tool_cards[tool_id]

if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 创建示例工具数据
    sample_tools = [
        {
            "id": 1,
            "name": "Nmap",
            "description": "网络扫描和安全评估工具",
            "path": "C:\\Program Files\\Nmap\\nmap.exe",
            "category_id": 1,
            "subcategory_id": 101,
            "icon": "nmap.png",
            "background_image": "",
            "priority": 3,
            "tags": ["扫描", "网络", "端口"],
            "is_favorite": True
        },
        {
            "id": 2,
            "name": "Burp Suite",
            "description": "Web应用安全测试工具",
            "path": "C:\\Program Files\\BurpSuite\\BurpSuiteCommunity.exe",
            "category_id": 7,
            "subcategory_id": 701,
            "icon": "burp.png",
            "background_image": "",
            "priority": 5,
            "tags": ["代理", "Web安全", "渗透"],
            "is_favorite": True
        }
    ]
    
    # 创建工具卡片容器
    container = ToolCardContainer()
    container.setWindowTitle("工具卡片示例")
    container.setGeometry(100, 100, 900, 600)
    container.display_tools(sample_tools)
    container.show()
    
    sys.exit(app.exec_())
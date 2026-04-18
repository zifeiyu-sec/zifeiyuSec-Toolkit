#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Qt Model/View 架构的高性能工具列表组件。
这种实现方式通过虚拟化渲染，可以实现海量数据的毫秒级加载。
"""
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListView, QStyledItemDelegate,
                            QAbstractItemView, QMenu, QMessageBox, QStyle)
from PyQt5.QtCore import (Qt, QAbstractListModel, QModelIndex, QSize, pyqtSignal,
                         QRect, QRectF, QPoint, QEvent)
from PyQt5.QtGui import (QPainter, QColor, QFont, QIcon, QPen, QBrush,
                         QFontMetrics, QPixmap, QPainterPath, QImage)
from core.runtime_paths import get_runtime_state_root
# 本地笔记对话框（右键笔记功能）
try:
    from ui.markdown_note_dialog import MarkdownNoteDialog
except Exception:
    # 在运行时 app.py 会把项目根加入 sys.path，导入应当正常；
    # 这里捕获异常以避免静态分析/编辑器报错
    MarkdownNoteDialog = None

from ui.icon_loader import icon_loader
from ui.tool_card_actions_mixin import ToolCardActionsMixin


class ToolModel(QAbstractListModel):
    """工具数据模型"""

    orderChanged = pyqtSignal(list)

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

    def flags(self, index):
        """设置项的标志，支持拖放"""
        if not index.isValid():
            return Qt.NoItemFlags
        return super().flags(index) | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

    def supportedDropActions(self):
        """支持的拖放动作"""
        return Qt.MoveAction

    def mimeTypes(self):
        """支持的MIME类型"""
        return ['application/vnd.tool.item']

    def mimeData(self, indexes):
        """返回拖放的数据"""
        mime_data = super().mimeData(indexes)
        if not indexes or not mime_data:
            return mime_data

        # 获取第一个选中项的索引
        index = indexes[0]
        if index.isValid():
            # 将行索引作为MIME数据
            mime_data.setData('application/vnd.tool.item', str(index.row()).encode())
        return mime_data

    def canDropMimeData(self, mime_data, action, row, column, parent):
        """仅允许把卡片拖到另一张卡片上，忽略空白区域和插入型落点"""
        if action != Qt.MoveAction:
            return False
        if not mime_data.hasFormat('application/vnd.tool.item'):
            return False
        if not parent.isValid():
            return False

        try:
            source_row = int(mime_data.data('application/vnd.tool.item').data().decode())
        except (TypeError, ValueError):
            return False

        target_row = parent.row()
        return (
            0 <= source_row < len(self._tools)
            and 0 <= target_row < len(self._tools)
            and source_row != target_row
        )

    def dropMimeData(self, mime_data, action, row, column, parent):
        """处理拖放操作：仅在落到另一张卡片上时交换位置"""
        if not self.canDropMimeData(mime_data, action, row, column, parent):
            return False

        source_row = int(mime_data.data('application/vnd.tool.item').data().decode())
        target_row = parent.row()

        self.beginResetModel()
        self._tools[source_row], self._tools[target_row] = self._tools[target_row], self._tools[source_row]
        self.endResetModel()

        self.orderChanged.emit([tool.get('id') for tool in self._tools if tool.get('id') is not None])
        return True

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

    def tools(self):
        """返回工具列表"""
        return self._tools


class ToolDelegate(QStyledItemDelegate):
    """工具卡片绘制代理"""

    buttonClicked = pyqtSignal(QModelIndex, int)

    def __init__(self, theme="dark_green", parent=None):
        super().__init__(parent)
        self.theme = theme
        # 卡片尺寸
        self.card_size = QSize(320, 110)
        self.padding = 10
        self.icon_size = 48
        # 存储每一行对应的按钮区域，用于点击命中测试
        self._button_rects = {}
        # 缓存图标亮度，避免反复采样带来的绘制开销
        self._icon_luminance_cache = {}

    def sizeHint(self, option, index):
        return self.card_size

    def _get_secondary_action_button_colors(self):
        if self.theme in ("light", "blue_white"):
            return (
                QColor(255, 255, 255, 230),
                QColor(203, 213, 225, 180),
                QColor(71, 85, 105),
            )
        if self.theme == "dark_green":
            return (
                QColor(33, 65, 48, 220),
                QColor(111, 231, 135, 92),
                QColor(236, 255, 241),
            )
        if self.theme == "purple_neon":
            return (
                QColor(46, 36, 82, 220),
                QColor(157, 123, 255, 96),
                QColor(244, 239, 255),
            )
        if self.theme == "red_orange":
            return (
                QColor(63, 41, 30, 220),
                QColor(255, 138, 61, 96),
                QColor(255, 243, 234),
            )
        return (
            QColor(15, 23, 42, 228),
            QColor(71, 85, 105, 180),
            QColor(226, 232, 240),
        )

    def _get_primary_action_button_colors(self):
        if self.theme in ("light", "blue_white"):
            return (
                QColor(59, 130, 246),
                QColor(37, 99, 235),
                QColor(255, 255, 255),
            )
        if self.theme == "dark_green":
            return (
                QColor(74, 222, 128),
                QColor(22, 163, 74),
                QColor(10, 31, 18),
            )
        if self.theme == "purple_neon":
            return (
                QColor(195, 169, 255),
                QColor(157, 123, 255),
                QColor(27, 23, 56),
            )
        if self.theme == "red_orange":
            return (
                QColor(255, 176, 103),
                QColor(255, 138, 61),
                QColor(58, 31, 22),
            )
        return (
            QColor(129, 140, 248),
            QColor(99, 102, 241),
            QColor(15, 23, 42),
        )

    def _build_tinted_icon_pixmap(self, icon, size, color):
        base_pixmap = icon.pixmap(size, size)
        if base_pixmap.isNull():
            return QPixmap()

        tinted = QPixmap(base_pixmap.size())
        tinted.fill(Qt.transparent)

        icon_painter = QPainter(tinted)
        icon_painter.drawPixmap(0, 0, base_pixmap)
        icon_painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        icon_painter.fillRect(tinted.rect(), color)
        icon_painter.end()
        return tinted

    def _is_dark_theme(self):
        return self.theme in ("dark_green", "purple_neon", "red_orange")

    def _color_luminance(self, color):
        return (
            0.2126 * color.redF()
            + 0.7152 * color.greenF()
            + 0.0722 * color.blueF()
        )

    def _estimate_pixmap_luminance(self, pixmap):
        if pixmap.isNull():
            return 1.0

        cache_key = int(pixmap.cacheKey())
        cached_value = self._icon_luminance_cache.get(cache_key)
        if cached_value is not None:
            return cached_value

        image = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        width = image.width()
        height = image.height()
        if width <= 0 or height <= 0:
            return 1.0

        step = max(1, min(width, height) // 16)
        weighted_luminance_sum = 0.0
        alpha_weight_sum = 0.0

        for y in range(0, height, step):
            for x in range(0, width, step):
                pixel = image.pixelColor(x, y)
                alpha = pixel.alphaF()
                if alpha <= 0.05:
                    continue

                luminance = self._color_luminance(pixel)
                weighted_luminance_sum += luminance * alpha
                alpha_weight_sum += alpha

        if alpha_weight_sum <= 0.0:
            result = 1.0
        else:
            result = weighted_luminance_sum / alpha_weight_sum

        # 限制缓存大小，避免在极端场景持续增长
        if len(self._icon_luminance_cache) > 4096:
            self._icon_luminance_cache.clear()
        self._icon_luminance_cache[cache_key] = result
        return result

    def _needs_icon_contrast_boost(self, pixmap, background_color):
        if not self._is_dark_theme() or pixmap.isNull():
            return False

        icon_luminance = self._estimate_pixmap_luminance(pixmap)
        background_luminance = self._color_luminance(background_color)
        contrast_delta = abs(icon_luminance - background_luminance)

        return icon_luminance < 0.48 and contrast_delta < 0.38

    def _draw_icon_boost_background(self, painter, icon_rect):
        if self.theme == "purple_neon":
            fill_color = QColor(255, 255, 255, 40)
            border_color = QColor(195, 169, 255, 150)
        elif self.theme == "red_orange":
            fill_color = QColor(255, 255, 255, 36)
            border_color = QColor(255, 176, 103, 150)
        else:
            fill_color = QColor(255, 255, 255, 34)
            border_color = QColor(152, 246, 176, 150)

        plate_rect = icon_rect.adjusted(2, 2, -2, -2)
        painter.save()
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(QRectF(plate_rect), 10, 10)
        painter.restore()

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
        hover_progress = 1.0 if (is_hover or is_selected) else 0.0
        if hover_progress:
            card_rect = card_rect.adjusted(-1, -1, 1, 1)

        bg_color = QColor(30, 41, 59)

        if self.theme in ("light", "blue_white"):
            bg_color = QColor(255, 255, 255)
            border_color = QColor(0, 0, 0, 25)
            text_color = QColor(55, 65, 81)
            desc_color = QColor(107, 114, 128)

            if is_hover or is_selected:
                bg_color = QColor(248, 250, 252)
                border_color = QColor(59, 130, 246, 127)
        elif self.theme == "dark_green":
            bg_color = QColor(23, 55, 37)
            border_color = QColor(111, 231, 135, 145)
            text_color = QColor(243, 255, 245)
            desc_color = QColor(183, 220, 192)

            if is_hover or is_selected:
                bg_color = QColor(33, 75, 49)
                border_color = QColor(152, 246, 176, 215)
        elif self.theme == "purple_neon":
            bg_color = QColor(27, 23, 56)
            border_color = QColor(157, 123, 255, 150)
            text_color = QColor(239, 233, 255)
            desc_color = QColor(197, 183, 235)

            if is_hover or is_selected:
                bg_color = QColor(35, 30, 71)
                border_color = QColor(195, 169, 255, 205)
        elif self.theme == "red_orange":
            bg_color = QColor(38, 27, 23)
            border_color = QColor(255, 138, 61, 145)
            text_color = QColor(255, 241, 230)
            desc_color = QColor(236, 186, 151)

            if is_hover or is_selected:
                bg_color = QColor(49, 35, 29)
                border_color = QColor(255, 176, 103, 205)
        else:
            if is_hover or is_selected:
                border_color = QColor(129, 140, 248, 190)

        # 3. 绘制背景
        path = QPainterPath()
        path.addRoundedRect(QRectF(card_rect), 8, 8)

        painter.fillPath(path, bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)

        # 4. 绘制图标
        icon_rect = QRect(card_rect.left() + 12, card_rect.top() + 16, 56, 56)

        icon = icon_loader.get_icon(tool, theme_name=self.theme)

        pixmap = icon.pixmap(56, 56)

        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                icon_rect.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )

            x = icon_rect.left() + (icon_rect.width() - scaled_pixmap.width()) // 2
            y = icon_rect.top() + (icon_rect.height() - scaled_pixmap.height()) // 2

            if self._needs_icon_contrast_boost(scaled_pixmap, bg_color):
                self._draw_icon_boost_background(painter, icon_rect)

            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            icon.paint(painter, icon_rect, Qt.AlignCenter)

        # 5. 绘制文本
        text_x = icon_rect.right() + 15
        text_right_margin = 136  # 右下角操作按钮预留宽度
        text_width = max(60, card_rect.right() - text_right_margin - text_x)

        name = tool.get('_display_name') or tool.get('name', 'Process')
        desc = (tool.get('_display_description') or tool.get('description') or '').strip()
        if desc:
            desc = ' '.join(desc.split())

        title_font = QFont()
        title_font.setBold(True)
        title_font.setPixelSize(14)

        painter.setFont(title_font)
        painter.setPen(text_color)

        has_desc = bool(desc and desc != '无介绍')
        if not has_desc:
            # 无介绍：名称字体放大，占据两行高度但只绘制一行文字
            display_name = str(name or '')
            line_height = 24
            total_height = line_height * 2 + 4
            big_font = QFont()
            big_font.setBold(True)
            big_font.setPixelSize(18)
            painter.setFont(big_font)

            combined_rect = QRect(text_x, card_rect.top() + 18, text_width, total_height)
            painter.drawText(combined_rect, Qt.AlignLeft | Qt.AlignVCenter, display_name)
        else:
            # 有介绍：第一行名称，第二行简介
            title_rect = QRect(text_x, card_rect.top() + 14, text_width, 22)
            painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, name)

            desc_font = QFont()
            desc_font.setPixelSize(12)
            painter.setFont(desc_font)
            painter.setPen(desc_color)

            desc_rect = QRect(text_x, title_rect.bottom() + 4, text_width, 22)
            painter.drawText(
                desc_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                painter.fontMetrics().elidedText(desc, Qt.ElideRight, text_width),
            )

        # 6. 绘制工具类型文本（图标下方的小字）
        type_label = self._get_tool_type_label(tool)
        if type_label:
            type_font = QFont()
            type_font.setPixelSize(11)
            painter.setFont(type_font)

            text_color_type, border_color_type, bg_color_type = self._get_type_style(type_label)

            tag_width = icon_rect.width() + 8
            type_rect = QRect(
                icon_rect.center().x() - tag_width // 2,
                icon_rect.bottom() + 4,
                tag_width,
                18,
            )

            painter.setPen(QPen(border_color_type, 1))
            painter.setBrush(QBrush(bg_color_type))
            painter.drawRoundedRect(type_rect, 8, 8)

            painter.setPen(text_color_type)
            painter.drawText(type_rect, Qt.AlignCenter, type_label)

        # 7. 绘制收藏标记 (星号)
        if tool.get('is_favorite', False):
            star_font = QFont()
            star_font.setPixelSize(16)
            painter.setFont(star_font)

            if self.theme in ("light", "blue_white"):
                painter.setPen(QColor(245, 158, 11))
            elif self.theme == "dark_green":
                painter.setPen(QColor(134, 239, 172))
            elif self.theme == "purple_neon":
                painter.setPen(QColor(195, 169, 255))
            elif self.theme == "red_orange":
                painter.setPen(QColor(255, 176, 103))
            else:
                painter.setPen(QColor(251, 191, 36))

            star_rect = QRect(card_rect.right() - 25, card_rect.top() + 5, 20, 20)
            painter.drawText(star_rect, Qt.AlignCenter, "★")

        # 7.5 工具可用性状态点（全部工具显示绿/红点）
        try:
            path_str = (tool.get('path') or '').strip()
        except Exception:
            path_str = ""

        status_color = QColor(220, 38, 38)
        is_web_tool_flag = bool(tool.get('is_web_tool', False))
        is_url = path_str.startswith('http://') or path_str.startswith('https://')

        if is_web_tool_flag or is_url:
            if path_str:
                status_color = QColor(34, 197, 94)
        elif path_str:
            full_path = path_str
            if not os.path.isabs(full_path):
                full_path = os.path.abspath(full_path)
            try:
                if os.path.exists(full_path):
                    status_color = QColor(34, 197, 94)
            except Exception:
                status_color = QColor(220, 38, 38)

        dot_radius = 5
        dot_center = QPoint(card_rect.right() - 12, card_rect.top() + 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(status_color)
        painter.drawEllipse(dot_center, dot_radius, dot_radius)

        # 8. 底部操作按钮：三个操作按钮常驻显示
        is_web_tool = bool(tool.get('is_web_tool', False))
        if not is_web_tool:
            try:
                inferred_type_label = self._get_tool_type_label(tool)
            except Exception:
                inferred_type_label = ""
            if inferred_type_label == "网页":
                is_web_tool = True

        buttons_margin = 10
        buttons_height = 30
        buttons_top = card_rect.bottom() - buttons_height - buttons_margin
        primary_button_width = 52 if not is_web_tool else 58
        secondary_button_width = 32
        secondary_spacing = 6
        menu_gap = 8
        button_icon_size = 18

        button_rects_for_row = []
        secondary_count = 0 if is_web_tool else 2
        secondary_total_width = secondary_count * secondary_button_width + max(0, secondary_count - 1) * secondary_spacing
        total_buttons_width = primary_button_width + (menu_gap + secondary_total_width if secondary_count else 0)
        buttons_right = card_rect.right() - buttons_margin
        base_x = buttons_right - total_buttons_width
        base_y = buttons_top

        style = option.widget.style() if option.widget else None
        if style is not None:
            icons = {
                0: style.standardIcon(QStyle.SP_MediaPlay),
                1: style.standardIcon(QStyle.SP_ComputerIcon),
                2: style.standardIcon(QStyle.SP_DirIcon),
            }
        else:
            icons = {}

        primary_bg_color, primary_border_color, primary_icon_color = self._get_primary_action_button_colors()
        secondary_bg_color, secondary_border_color, secondary_icon_color = self._get_secondary_action_button_colors()

        run_rect = QRect(base_x, base_y, primary_button_width, buttons_height)
        button_rects_for_row.append((0, run_rect))
        painter.setPen(QPen(primary_border_color, 1))
        painter.setBrush(QBrush(primary_bg_color))
        painter.drawRoundedRect(run_rect, 10, 10)

        run_icon = icons.get(0)
        if run_icon is not None:
            run_pix = self._build_tinted_icon_pixmap(run_icon, button_icon_size, primary_icon_color)
            if not run_pix.isNull():
                icon_x = run_rect.x() + (run_rect.width() - button_icon_size) // 2
                icon_y = run_rect.y() + (run_rect.height() - button_icon_size) // 2
                painter.drawPixmap(icon_x, icon_y, button_icon_size, button_icon_size, run_pix)

        if secondary_count:
            secondary_x = run_rect.right() + 1 + menu_gap
            for button_index in (1, 2):
                rect = QRect(secondary_x, base_y, secondary_button_width, buttons_height)
                button_rects_for_row.append((button_index, rect))
                painter.setPen(QPen(secondary_border_color, 1))
                painter.setBrush(QBrush(secondary_bg_color))
                painter.drawRoundedRect(rect, 10, 10)

                icon = icons.get(button_index)
                if icon is not None:
                    pix = self._build_tinted_icon_pixmap(icon, 16, secondary_icon_color)
                    if not pix.isNull():
                        icon_x = rect.x() + (rect.width() - 16) // 2
                        icon_y = rect.y() + (rect.height() - 16) // 2
                        painter.drawPixmap(icon_x, icon_y, 16, 16, pix)
                secondary_x += secondary_button_width + secondary_spacing

        row = index.row()
        self._button_rects[row] = button_rects_for_row

        painter.restore()

    def _get_type_style(self, type_label: str):
        """根据类型返回文本色、边框色和背景色，用于图标下方的小标签"""
        # 浅色主题：整体颜色更浅
        if self.theme in ("light", "blue_white"):
            text = QColor(107, 114, 128)
            border = QColor(209, 213, 219)
            bg = QColor(248, 250, 252)

            if type_label == "网页":
                text = QColor(37, 99, 235)  # 深蓝
                border = QColor(59, 130, 246)
                bg = QColor(239, 246, 255)
            elif type_label == "终端":
                text = QColor(22, 101, 52)  # 绿色
                border = QColor(34, 197, 94)
                bg = QColor(220, 252, 231)
            elif type_label == "目录":
                text = QColor(180, 83, 9)  # 橙色
                border = QColor(245, 158, 11)
                bg = QColor(255, 247, 237)
            elif type_label == "文档":
                text = QColor(109, 40, 217)  # 紫色
                border = QColor(168, 85, 247)
                bg = QColor(245, 243, 255)
            elif type_label == "应用":
                text = QColor(8, 47, 73)  # 青色系文字
                border = QColor(34, 211, 238)
                bg = QColor(224, 242, 254)
        elif self.theme == "dark_green":
            text = QColor(191, 228, 200)
            border = QColor(82, 165, 103)
            bg = QColor(28, 60, 41)

            if type_label == "网页":
                text = QColor(157, 248, 182)
                border = QColor(96, 220, 128)
                bg = QColor(31, 73, 45)
            elif type_label == "终端":
                text = QColor(187, 255, 204)
                border = QColor(74, 222, 128)
                bg = QColor(22, 64, 38)
            elif type_label == "目录":
                text = QColor(255, 210, 155)
                border = QColor(251, 146, 60)
                bg = QColor(58, 38, 24)
            elif type_label == "文档":
                text = QColor(208, 240, 255)
                border = QColor(56, 189, 248)
                bg = QColor(18, 49, 66)
            elif type_label == "应用":
                text = QColor(211, 248, 219)
                border = QColor(111, 231, 135)
                bg = QColor(27, 65, 43)
        elif self.theme == "purple_neon":
            text = QColor(200, 187, 239)
            border = QColor(90, 74, 141)
            bg = QColor(34, 28, 63)

            if type_label == "网页":
                text = QColor(166, 213, 255)
                border = QColor(96, 165, 250)
                bg = QColor(31, 39, 69)
            elif type_label == "终端":
                text = QColor(139, 240, 199)
                border = QColor(52, 211, 153)
                bg = QColor(23, 48, 42)
            elif type_label == "目录":
                text = QColor(255, 214, 171)
                border = QColor(251, 146, 60)
                bg = QColor(61, 38, 25)
            elif type_label == "文档":
                text = QColor(232, 210, 255)
                border = QColor(192, 132, 252)
                bg = QColor(52, 33, 73)
            elif type_label == "应用":
                text = QColor(210, 204, 255)
                border = QColor(167, 139, 250)
                bg = QColor(44, 36, 80)
        elif self.theme == "red_orange":
            text = QColor(255, 229, 210)
            border = QColor(172, 90, 52)
            bg = QColor(42, 30, 24)

            if type_label == "网页":
                text = QColor(255, 214, 176)
                border = QColor(255, 138, 61)
                bg = QColor(63, 38, 25)
            elif type_label == "终端":
                text = QColor(255, 209, 209)
                border = QColor(239, 68, 68)
                bg = QColor(70, 28, 28)
            elif type_label == "目录":
                text = QColor(255, 210, 143)
                border = QColor(245, 158, 11)
                bg = QColor(67, 43, 27)
            elif type_label == "文档":
                text = QColor(255, 227, 196)
                border = QColor(255, 176, 103)
                bg = QColor(66, 38, 25)
            elif type_label == "应用":
                text = QColor(255, 229, 210)
                border = QColor(255, 138, 61)
                bg = QColor(58, 36, 26)
        else:
            # 深色主题：底色偏深，文字更亮
            text = QColor(148, 163, 184)
            border = QColor(55, 65, 81)
            bg = QColor(15, 23, 42)

            if type_label == "网页":
                text = QColor(96, 165, 250)
                border = QColor(59, 130, 246)
                bg = QColor(15, 23, 42)
            elif type_label == "终端":
                text = QColor(74, 222, 128)
                border = QColor(34, 197, 94)
                bg = QColor(5, 46, 22)
            elif type_label == "目录":
                text = QColor(251, 191, 36)
                border = QColor(245, 158, 11)
                bg = QColor(69, 26, 3)
            elif type_label == "文档":
                text = QColor(196, 181, 253)
                border = QColor(168, 85, 247)
                bg = QColor(46, 16, 101)
            elif type_label == "应用":
                text = QColor(103, 232, 249)
                border = QColor(34, 211, 238)
                bg = QColor(8, 51, 68)

        # 文件 / 其他 使用默认灰色系即可
        return text, border, bg

    def _get_tool_type_label(self, tool: dict) -> str:
        """根据工具配置推断工具类型标签（网页/图形应用/终端/目录/文件/文档/其他）"""
        # 如果配置了自定义类型标签，则优先使用
        custom_label = (tool.get('type_label') or '').strip()
        if custom_label:
            return custom_label

        path = (tool.get('path') or '').strip()
        is_web = tool.get('is_web_tool', False)
        run_in_terminal = tool.get('run_in_terminal', False)

        # 网页类工具：显式标记或 URL
        if is_web or path.startswith('http://') or path.startswith('https://'):
            return "网页"

        if not path:
            return "其他"

        # 粗略判断目录：显式以分隔符结尾
        if path.endswith('/') or path.endswith('\\'):
            return "目录"

        _, ext = os.path.splitext(path)
        ext = ext.lower()

        # 常见文档类型
        doc_exts = ('.txt', '.md', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx')
        if ext in doc_exts:
            return "文档"

        # 常见终端脚本/命令行工具（含脚本语言、批处理、VBS 等）
        terminal_exts = ('.bat', '.cmd', '.ps1', '.sh', '.py', '.vbs')
        if run_in_terminal or ext in terminal_exts:
            return "终端"

        # 常见图形化可执行文件
        if ext in ('.exe', '.lnk', '.jar', '.app'):
            return "应用"

        # 其他落入通用文件类型
        return "文件"

    def editorEvent(self, event, model, option, index):
        """处理按钮点击事件：区分三种按钮

        0: 启动工具
        1: 在此处打开命令行
        2: 在此处打开目录
        """
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            pos = event.pos()
            row = index.row()

            # 如果没有缓存按钮区域，直接走默认逻辑
            button_rects = self._button_rects.get(row) if hasattr(self, "_button_rects") else None
            if not button_rects:
                return super().editorEvent(event, model, option, index)

            for button_index, rect in button_rects:
                if rect.contains(pos):
                    self.buttonClicked.emit(index, button_index)
                    return True

        return super().editorEvent(event, model, option, index)


class ToolListView(QListView):
    """只允许拖到实际卡片上的列表视图"""

    def dragMoveEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            super().dragMoveEvent(event)
        else:
            event.ignore()

    def dropEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            super().dropEvent(event)
        else:
            event.ignore()


class ToolCardContainer(ToolCardActionsMixin, QWidget):
    """
    兼容层：对外提供与旧版 ToolCardContainer 一致的接口，
    但内部使用 QListView + Model 实现。
    """

    # 信号定义 (保持兼容)
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    tool_order_changed = pyqtSignal(list)
    new_tool_requested = pyqtSignal()   # 暂未使用，但保持兼容

    LAYOUT_PRESETS = {
        "main": {
            "preferred_columns": 2,
            "max_columns": 3,
            "min_card_width": 300,
            "max_card_width": 430,
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = "dark_green"
        self.layout_mode = "main"
        self.card_height = 110
        self._last_layout_signature = None
        self._viewport_horizontal_margin = 0
        self._layout_update_in_progress = False
        # 防止底部按钮点击后 QListView 再触发一次 clicked
        self._suppress_next_click = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = ToolListView()
        self.model = ToolModel()
        self.delegate = ToolDelegate(self.current_theme)

        self.view.setModel(self.model)
        self.view.setItemDelegate(self.delegate)

        # 关键设置：像图标模式一样布局（网格）
        self.view.setViewMode(QListView.IconMode)
        self.view.setResizeMode(QListView.Adjust)
        self.view.setUniformItemSizes(True)  # 性能优化
        self.view.setSpacing(8)
        self.view.setWordWrap(True)
        self.view.setSelectionMode(QAbstractItemView.SingleSelection)
        # 移动方式：拖动时仍然贴合网格，不允许停在随意位置
        self.view.setMovement(QListView.Snap)

        # 启用拖放功能
        self.view.setDragEnabled(True)
        self.view.setAcceptDrops(True)
        self.view.setDropIndicatorShown(True)
        self.view.setDragDropMode(QAbstractItemView.InternalMove)

        # 样式设置：去除丑陋的默认选中框，完全靠Delegate绘制
        self.view.setFrameShape(QListView.NoFrame)
        # 设置鼠标追踪以便Delegate可以处理Hover
        self.view.setMouseTracking(True)
        self.view.viewport().installEventFilter(self)

        layout.addWidget(self.view)

        # 信号连接
        self.view.clicked.connect(self.on_item_clicked)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)

        self.apply_theme_styles()
        self.set_layout_mode(self.layout_mode)
        self.update_card_layout(force=True)

        # 连接加载器信号，刷新界面
        icon_loader.icon_ready.connect(self.view.viewport().update)

        # 底部按钮点击：由 Delegate 发出精确按钮索引，再在这里分发动作
        self.delegate.buttonClicked.connect(self.on_button_clicked)
        self.model.orderChanged.connect(self.tool_order_changed.emit)

    def set_layout_mode(self, layout_mode):
        """切换卡片布局模式。"""
        layout_mode = layout_mode if layout_mode in self.LAYOUT_PRESETS else "main"
        if self.layout_mode == layout_mode:
            self.update_card_layout()
            return

        self.layout_mode = layout_mode
        self.view.setViewMode(QListView.IconMode)
        self.view.setFlow(QListView.LeftToRight)
        self.view.setWrapping(True)
        self.view.setResizeMode(QListView.Adjust)
        self.view.setMovement(QListView.Snap)
        self.view.setSpacing(8)
        self.update_card_layout(force=True)

    def eventFilter(self, watched, event):
        if watched is self.view.viewport() and event.type() == QEvent.Resize:
            if self._layout_update_in_progress:
                return super().eventFilter(watched, event)
            self.update_card_layout()
        return super().eventFilter(watched, event)

    def _get_layout_preset(self):
        return self.LAYOUT_PRESETS.get(self.layout_mode, self.LAYOUT_PRESETS["main"])

    def _calculate_card_width_for_columns(self, viewport_width, columns, spacing):
        columns = max(1, int(columns))
        return max(1, (max(0, int(viewport_width)) // columns) - max(0, int(spacing)))

    def _resolve_columns(self, viewport_width, spacing, preset):
        preferred_columns = max(1, preset["preferred_columns"])
        max_columns = max(preferred_columns, preset.get("max_columns", preferred_columns))
        min_card_width = preset["min_card_width"]
        max_card_width = preset["max_card_width"]

        columns = preferred_columns
        while columns > 1:
            candidate_width = self._calculate_card_width_for_columns(viewport_width, columns, spacing)
            if candidate_width >= min_card_width:
                break
            columns -= 1

        while columns < max_columns:
            current_width = self._calculate_card_width_for_columns(viewport_width, columns, spacing)
            next_columns = columns + 1
            next_width = self._calculate_card_width_for_columns(viewport_width, next_columns, spacing)
            if current_width <= max_card_width or next_width < min_card_width:
                break
            columns = next_columns

        return max(1, columns)

    def _set_horizontal_viewport_margin(self, margin):
        margin = max(0, int(margin))
        if margin == self._viewport_horizontal_margin:
            return
        self._viewport_horizontal_margin = margin
        self.view.setViewportMargins(margin, 0, margin, 0)

    def update_card_layout(self, force=False):
        if self._layout_update_in_progress:
            return

        self._layout_update_in_progress = True
        try:
            preset = self._get_layout_preset()
            spacing = max(0, self.view.spacing())
            min_card_width = preset["min_card_width"]
            max_card_width = preset.get("max_card_width")
            viewport_width = max(0, self.view.viewport().width())
            self._set_horizontal_viewport_margin(0)
            viewport_width = max(0, self.view.viewport().width())
            if viewport_width <= 0:
                columns = preset["preferred_columns"]
                card_width = min_card_width if max_card_width is None else max(min_card_width, max_card_width)
            else:
                columns = self._resolve_columns(viewport_width, spacing, preset)
                candidate_width = self._calculate_card_width_for_columns(viewport_width, columns, spacing)
                if max_card_width is None:
                    card_width = max(min_card_width, candidate_width)
                else:
                    card_width = max(min_card_width, min(max_card_width, candidate_width))
                card_width = min(card_width, max(min_card_width, viewport_width))

            card_size = QSize(card_width, self.card_height)
            grid_size = QSize(card_width + spacing, self.card_height + spacing)
            signature = (
                self.layout_mode,
                viewport_width,
                columns,
                card_size.width(),
                grid_size.width(),
                self._viewport_horizontal_margin,
            )
            if not force and signature == self._last_layout_signature:
                return

            self._last_layout_signature = signature
            self.delegate.card_size = card_size
            self.view.setGridSize(grid_size)
            self.view.setIconSize(QSize(56, 56))
            self.view.doItemsLayout()
            self.view.viewport().update()
        finally:
            self._layout_update_in_progress = False

    def set_theme(self, theme_name):
        self.current_theme = theme_name
        self.delegate.theme = theme_name
        self.apply_theme_styles()
        self.update_card_layout(force=True)
        # 强制重绘
        self.view.viewport().update()

    def apply_theme_styles(self):
        if self.current_theme in ("light", "blue_white"):
            self.view.setStyleSheet(
                """
                QListView {
                    background-color: #f0f4f8;
                    border: none;
                    outline: none;
                }
                """
            )
        elif self.current_theme == "dark_green":
            self.view.setStyleSheet(
                """
                QListView {
                    background-color: #102117;
                    border: none;
                    outline: none;
                }
                """
            )
        elif self.current_theme == "purple_neon":
            self.view.setStyleSheet(
                """
                QListView {
                    background-color: #141027;
                    border: none;
                    outline: none;
                }
                """
            )
        elif self.current_theme == "red_orange":
            self.view.setStyleSheet(
                """
                QListView {
                    background-color: #1a1412;
                    border: none;
                    outline: none;
                }
                """
            )
        else:
            self.view.setStyleSheet(
                """
                QListView {
                    background-color: #1a1a2e;
                    border: none;
                    outline: none;
                }
                """
            )

    def display_tools(self, tools_data):
        """显示工具列表"""
        # Model/View 模式下，直接给 Model 数据，Qt 负责极速渲染
        self.model.update_data(tools_data)
        self.update_card_layout(force=True)

    def on_item_clicked(self, index):
        """点击运行

        注意：底部按钮点击在 editorEvent 中已经被截获并单独处理，
        这里只处理普通卡片区域的点击（整体运行工具）。
        """
        if getattr(self, "_suppress_next_click", False):
            # 清除一次性标记，不再向外发送 run_tool
            self._suppress_next_click = False
            return

        tool = self.model.get_tool(index)
        if tool:
            self.run_tool.emit(tool)

    def on_button_clicked(self, index, button_index: int):
        """处理底部按钮点击，根据按钮类型分发操作"""
        tool = self.model.get_tool(index)
        if not tool:
            return

        # 标记：本次点击已经有专门处理，防止 QListView 再触发一次 clicked 信号
        self._suppress_next_click = True

        # 0: 启动工具（与点击整卡片一致）
        if button_index == 0:
            self.run_tool.emit(tool)
            return

        # 下面两个按钮需要推断一个“目标目录”
        target_dir = self.resolve_tool_target_dir(tool)

        if not target_dir:
            if button_index == 1 or button_index == 2:
                self.warn_missing_tool_target_dir(tool)
            return

        if button_index == 1:
            # 在此处打开命令行
            self.open_command_line(target_dir, tool_data=tool)
        elif button_index == 2:
            # 在此处打开目录
            self.open_directory(target_dir)

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

        # 打开笔记（基于工具名自动加载/保存 notes 文件）
        if MarkdownNoteDialog is not None:
            notes_action = menu.addAction("打开笔记")
            notes_action.triggered.connect(lambda: self._open_notes_for_tool(tool))
            menu.addSeparator()

        potential_target_dir = self.resolve_tool_target_dir(tool)

        if potential_target_dir:
            # 添加"在此处打开命令行"选项
            cmd_action = menu.addAction("在此处打开命令行")
            cmd_action.triggered.connect(lambda: self.open_command_line(potential_target_dir, tool_data=tool))

            # 添加"在此处打开目录"选项
            dir_action = menu.addAction("在此处打开目录")
            dir_action.triggered.connect(lambda: self.open_directory(potential_target_dir))

            menu.addSeparator()

        del_action = menu.addAction("删除工具")
        del_action.triggered.connect(lambda: self.confirm_delete(tool))

        menu.exec_(self.view.mapToGlobal(pos))

    def _open_notes_for_tool(self, tool):
        """打开笔记对话框，基于工具名进行保存与加载"""
        if MarkdownNoteDialog is None:
            QMessageBox.warning(self, "未安装", "笔记功能未能加载。")
            return

        # 尝试推断项目根路径，Notes dialog 接受 repo_root
        repo_root = getattr(self.window(), 'config_dir', None) or os.fspath(get_runtime_state_root())
        dialog = MarkdownNoteDialog(
            tool_id=tool.get('id'),
            tool_name=tool.get('name', 'untitled'),
            repo_root=repo_root,
            parent=self,
            theme_name=getattr(self, 'current_theme', None),
        )
        dialog.exec_()
        window = self.window()
        if hasattr(window, 'refresh_current_view'):
            window.refresh_current_view()

    def confirm_delete(self, tool):
        # 简单确认框，为了减少依赖不引用外部样式，使用原生
        reply = QMessageBox.question(
            self,
            '确认删除',
            f"确定要删除工具 \"{tool['name']}\" 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            self.deleted.emit(tool['id'])

    def get_tool_count(self):
        return self.model.rowCount()

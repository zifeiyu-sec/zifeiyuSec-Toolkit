#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于 Qt Model/View 架构的高性能工具列表组件。
这种实现方式通过虚拟化渲染，可以实现海量数据的毫秒级加载。
"""
import os
from time import monotonic
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QListView, QStyledItemDelegate,
                            QAbstractItemView, QMenu, QMessageBox, QStyle)
from PyQt5.QtCore import (Qt, QAbstractListModel, QModelIndex, QSize, pyqtSignal,
                         QRect, QRectF, QPoint, QEvent, QTimer)
from PyQt5.QtGui import (QPainter, QColor, QFont, QIcon, QPen, QBrush,
                         QFontMetrics, QPixmap, QPainterPath, QImage, QLinearGradient, QPalette)
from core.auto_icon_resolver import get_tool_icon_identity
from core.path_status_service import (
    PathStatus,
    PathStatusResult,
    PathStatusService,
    build_path_status_cache_key,
)
from core.runtime_paths import get_runtime_state_root
from core.tool_metadata import infer_display_tool_type_label
# 本地笔记对话框（右键笔记功能）
try:
    from ui.markdown_note_dialog import MarkdownNoteDialog
except Exception:
    # 在运行时 app.py 会把项目根加入 sys.path，导入应当正常；
    # 这里捕获异常以避免静态分析/编辑器报错
    MarkdownNoteDialog = None

from ui.icon_loader import get_icon_cache_key, icon_loader
from core.style_manager import ThemeManager
from ui.tool_card_action_icons import (
    ACTION_BUTTON_OPEN_DIRECTORY,
    ACTION_BUTTON_OPEN_NOTES,
    ACTION_BUTTON_OPEN_TERMINAL,
    ACTION_BUTTON_RUN,
    ACTION_BUTTON_TOGGLE_FAVORITE,
    ACTION_ICON_FAVORITE,
    ACTION_ICON_NOTES,
    load_tool_card_action_icon,
)
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
        prepared_tools = []
        for tool in tools or []:
            if isinstance(tool, dict):
                prepared_tool = dict(tool)
                prepared_tool["_display_type_label"] = (
                    prepared_tool.get("_display_type_label")
                    or infer_display_tool_type_label(prepared_tool)
                )
                prepared_tools.append(prepared_tool)
            else:
                prepared_tools.append(tool)
        self._tools = prepared_tools
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
        self._icon_contrast_cache = {}
        self._action_icon_cache = {}
        self._tinted_icon_pixmap_cache = {}
        self._icon_pixmap_cache = {}
        self.performance_mode = True

    def sizeHint(self, option, index):
        return self.card_size

    def _get_secondary_action_button_colors(self):
        if self.theme == "celadon_mist":
            return (
                QColor(226, 255, 255, 218),
                QColor(135, 218, 222, 198),
                QColor(20, 86, 92),
            )
        if self.theme == "blue_white":
            return (
                QColor(255, 255, 255, 214),
                QColor(201, 224, 241, 180),
                QColor(64, 88, 113),
            )
        if self.theme == "light":
            return (
                QColor(255, 255, 255, 230),
                QColor(203, 213, 225, 180),
                QColor(71, 85, 105),
            )
        if self.theme == "dark_green":
            return (
                QColor(17, 24, 24, 224),
                QColor(30, 58, 63, 220),
                QColor(0, 229, 255),
            )
        if self.theme == "purple_neon":
            return (
                QColor(22, 3, 34, 232),
                QColor(255, 207, 92, 172),
                QColor(255, 230, 163),
            )
        if self.theme == "red_orange":
            return (
                QColor(112, 0, 0, 232),
                QColor(255, 220, 112, 204),
                QColor(255, 244, 204),
            )
        return (
            QColor(15, 23, 42, 228),
            QColor(71, 85, 105, 180),
            QColor(226, 232, 240),
        )

    def _get_primary_action_button_colors(self):
        if self.theme == "celadon_mist":
            return (
                QColor(16, 142, 150),
                QColor(69, 190, 192),
                QColor(255, 255, 255),
            )
        if self.theme == "blue_white":
            return (
                QColor(72, 145, 244),
                QColor(104, 186, 252),
                QColor(255, 255, 255),
            )
        if self.theme == "light":
            return (
                QColor(59, 130, 246),
                QColor(37, 99, 235),
                QColor(255, 255, 255),
            )
        if self.theme == "dark_green":
            return (
                QColor(0, 255, 65),
                QColor(0, 188, 58),
                QColor(3, 10, 8),
            )
        if self.theme == "purple_neon":
            return (
                QColor(255, 207, 92),
                QColor(255, 232, 147),
                QColor(12, 2, 20),
            )
        if self.theme == "red_orange":
            return (
                QColor(255, 232, 147),
                QColor(255, 126, 58),
                QColor(48, 0, 0),
            )
        return (
            QColor(129, 140, 248),
            QColor(99, 102, 241),
            QColor(15, 23, 42),
        )

    def _build_tinted_icon_pixmap(self, icon, size, color):
        try:
            icon_key = int(icon.cacheKey())
        except Exception:
            icon_key = id(icon)
        cache_key = (icon_key, int(size), int(color.rgba()))
        cached = self._tinted_icon_pixmap_cache.get(cache_key)
        if cached is not None:
            return cached

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
        if len(self._tinted_icon_pixmap_cache) > 128:
            self._tinted_icon_pixmap_cache.clear()
        self._tinted_icon_pixmap_cache[cache_key] = tinted
        return tinted

    def _get_icon_pixmap(self, tool, icon, size):
        try:
            icon_key = int(icon.cacheKey())
        except Exception:
            icon_key = id(icon)
        cache_key = (
            str((tool or {}).get("_icon_cache_key") or ""),
            str(self.theme or ""),
            int(size),
            icon_key,
        )
        cached = self._icon_pixmap_cache.get(cache_key)
        if cached is not None:
            return cached

        pixmap = icon.pixmap(size, size)
        if len(self._icon_pixmap_cache) > 512:
            self._icon_pixmap_cache.clear()
        self._icon_pixmap_cache[cache_key] = pixmap
        return pixmap

    def _get_action_icons(self, style):
        style_key = id(style) if style is not None else 0
        cached = self._action_icon_cache.get(style_key)
        if cached is not None:
            return cached

        icons = {
            ACTION_BUTTON_RUN: load_tool_card_action_icon(style, fallback_icon_type=QStyle.SP_MediaPlay),
            ACTION_BUTTON_TOGGLE_FAVORITE: load_tool_card_action_icon(style, ACTION_ICON_FAVORITE, QStyle.SP_DialogYesButton),
            ACTION_BUTTON_OPEN_NOTES: load_tool_card_action_icon(style, ACTION_ICON_NOTES, QStyle.SP_FileDialogContentsView),
            ACTION_BUTTON_OPEN_TERMINAL: load_tool_card_action_icon(style, fallback_icon_type=QStyle.SP_ComputerIcon),
            ACTION_BUTTON_OPEN_DIRECTORY: load_tool_card_action_icon(style, fallback_icon_type=QStyle.SP_DirIcon),
        }
        if len(self._action_icon_cache) > 8:
            self._action_icon_cache.clear()
        self._action_icon_cache[style_key] = icons
        return icons

    def _is_dark_theme(self):
        return self.theme in ("dark_green", "purple_neon", "red_orange")

    def _fast_palette(self):
        if self.theme == "celadon_mist":
            return QColor(232, 255, 255, 172), QColor(137, 220, 223, 194), QColor(16, 76, 82), QColor(68, 108, 112)
        if self.theme == "blue_white":
            return QColor(238, 251, 255, 184), QColor(151, 213, 244, 190), QColor(24, 49, 73), QColor(90, 113, 136)
        if self.theme == "light":
            return QColor(255, 255, 255), QColor(0, 0, 0, 25), QColor(55, 65, 81), QColor(107, 114, 128)
        if self.theme == "purple_neon":
            return QColor(12, 2, 20, 170), QColor(255, 207, 92, 176), QColor(255, 232, 147), QColor(210, 176, 221)
        if self.theme == "red_orange":
            return QColor(110, 0, 0, 196), QColor(255, 210, 96, 214), QColor(255, 244, 204), QColor(255, 198, 150)
        return QColor(0, 16, 18, 118), QColor(0, 229, 255, 150), QColor(0, 255, 65), QColor(124, 195, 139)

    def _is_web_tool(self, tool):
        tool_path = (tool.get('path') or '').strip()
        is_web_tool = bool(tool.get('is_web_tool', False)) or tool_path.startswith(('http://', 'https://'))
        if not is_web_tool:
            try:
                is_web_tool = self._get_tool_type_label(tool) == "网页"
            except Exception:
                is_web_tool = False
        return is_web_tool

    def _draw_fast_action_buttons(self, painter, option, tool, card_rect, is_web_tool, row):
        buttons_margin = 10
        buttons_height = 30
        buttons_top = card_rect.bottom() - buttons_height - buttons_margin
        primary_button_width = 52 if not is_web_tool else 58
        secondary_button_width = 32
        secondary_spacing = 6
        menu_gap = 8
        button_icon_size = 18

        secondary_indices = [ACTION_BUTTON_TOGGLE_FAVORITE, ACTION_BUTTON_OPEN_NOTES]
        if not is_web_tool:
            secondary_indices.extend([ACTION_BUTTON_OPEN_TERMINAL, ACTION_BUTTON_OPEN_DIRECTORY])

        secondary_count = len(secondary_indices)
        secondary_total_width = secondary_count * secondary_button_width + max(0, secondary_count - 1) * secondary_spacing
        total_width = primary_button_width + menu_gap + secondary_total_width
        start_x = card_rect.right() - total_width - 12

        button_rects_for_row = []
        action_icons = self._get_action_icons(option.widget.style() if option.widget else None)
        primary_bg, primary_border, primary_text = self._get_primary_action_button_colors()
        secondary_bg, secondary_border, secondary_text = self._get_secondary_action_button_colors()

        def draw_button(rect, action_index, bg, border, icon_color):
            painter.setPen(QPen(border, 1))
            painter.setBrush(QBrush(bg))
            painter.drawRoundedRect(QRectF(rect), 8, 8)
            icon = action_icons.get(action_index, QIcon())
            if not icon.isNull():
                pixmap = self._build_tinted_icon_pixmap(icon, button_icon_size, icon_color)
                if not pixmap.isNull():
                    x = rect.left() + (rect.width() - pixmap.width()) // 2
                    y = rect.top() + (rect.height() - pixmap.height()) // 2
                    painter.drawPixmap(x, y, pixmap)

        run_rect = QRect(start_x, buttons_top, primary_button_width, buttons_height)
        draw_button(run_rect, ACTION_BUTTON_RUN, primary_bg, primary_border, primary_text)
        button_rects_for_row.append((ACTION_BUTTON_RUN, run_rect))

        x = run_rect.right() + menu_gap
        for action_index in secondary_indices:
            rect = QRect(x, buttons_top, secondary_button_width, buttons_height)
            draw_button(rect, action_index, secondary_bg, secondary_border, secondary_text)
            button_rects_for_row.append((action_index, rect))
            x += secondary_button_width + secondary_spacing

        self._button_rects[row] = button_rects_for_row
        return button_rects_for_row

    def _paint_fast(self, painter, option, index):
        tool = index.data(Qt.UserRole)
        if not tool:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, False)
        rect = option.rect
        card_rect = rect.adjusted(4, 4, -4, -4)
        bg_color, border_color, text_color, desc_color = self._fast_palette()

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(QRectF(card_rect), 8, 8)

        icon_rect = QRect(card_rect.left() + 12, card_rect.top() + 16, 56, 56)
        icon = icon_loader.get_icon(tool, theme_name=self.theme)
        pixmap = self._get_icon_pixmap(tool, icon, 56)
        if not pixmap.isNull():
            x = icon_rect.left() + (icon_rect.width() - pixmap.width()) // 2
            y = icon_rect.top() + (icon_rect.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
        else:
            icon.paint(painter, icon_rect, Qt.AlignCenter)

        text_x = icon_rect.right() + 15
        text_width = max(80, card_rect.right() - 42 - text_x)
        name = str(tool.get('_display_name') or tool.get('name', 'Process') or '')
        desc = (tool.get('_display_description') or tool.get('description') or '').strip()
        if desc:
            desc = ' '.join(desc.split())

        title_font = QFont()
        title_font.setBold(True)
        title_font.setPixelSize(14)
        painter.setFont(title_font)
        painter.setPen(text_color)
        title_metrics = QFontMetrics(title_font)
        painter.drawText(
            QRect(text_x, card_rect.top() + 16, text_width, 22),
            Qt.AlignLeft | Qt.AlignVCenter,
            title_metrics.elidedText(name, Qt.ElideRight, text_width),
        )

        desc_font = QFont()
        desc_font.setPixelSize(11)
        painter.setFont(desc_font)
        painter.setPen(desc_color)
        desc_metrics = QFontMetrics(desc_font)
        painter.drawText(
            QRect(text_x, card_rect.top() + 42, text_width, 18),
            Qt.AlignLeft | Qt.AlignVCenter,
            desc_metrics.elidedText(desc, Qt.ElideRight, text_width),
        )

        if tool.get("is_favorite", False):
            painter.setPen(QColor(251, 191, 36))
            painter.drawText(QRect(card_rect.right() - 25, card_rect.top() + 5, 20, 20), Qt.AlignCenter, "*")

        dot_radius = 5
        dot_center = QPoint(card_rect.right() - 12, card_rect.top() + 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._get_status_color(tool, option))
        painter.drawEllipse(dot_center, dot_radius, dot_radius)

        self._draw_fast_action_buttons(painter, option, tool, card_rect, self._is_web_tool(tool), index.row())
        painter.restore()

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

    def _needs_icon_contrast_boost(self, pixmap, background_color, cache_key=None):
        if not self._is_dark_theme() or pixmap.isNull():
            return False

        contrast_cache_key = None
        if cache_key:
            contrast_cache_key = (str(cache_key), int(background_color.rgba()), self.theme)
            cached = self._icon_contrast_cache.get(contrast_cache_key)
            if cached is not None:
                return cached

        icon_luminance = self._estimate_pixmap_luminance(pixmap)
        background_luminance = self._color_luminance(background_color)
        contrast_delta = abs(icon_luminance - background_luminance)

        result = icon_luminance < 0.48 and contrast_delta < 0.38
        if contrast_cache_key:
            if len(self._icon_contrast_cache) > 4096:
                self._icon_contrast_cache.clear()
            self._icon_contrast_cache[contrast_cache_key] = result
        return result

    def _draw_icon_boost_background(self, painter, icon_rect):
        if self.theme == "purple_neon":
            fill_color = QColor(45, 7, 67, 72)
            border_color = QColor(255, 207, 92, 166)
        elif self.theme == "red_orange":
            fill_color = QColor(120, 0, 0, 88)
            border_color = QColor(255, 220, 112, 188)
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

        if self.performance_mode and not (option.state & (QStyle.State_MouseOver | QStyle.State_Selected)):
            self._paint_fast(painter, option, index)
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
        bg_secondary_color = None
        card_radius = 20 if self.theme in ("blue_white", "dark_green", "purple_neon", "red_orange") else 8

        if self.theme == "celadon_mist":
            bg_color = QColor(232, 255, 255, 172)
            bg_secondary_color = QColor(150, 229, 232, 122)
            border_color = QColor(137, 220, 223, 194)
            text_color = QColor(16, 76, 82)
            desc_color = QColor(68, 108, 112)
            card_radius = 22

            if is_hover or is_selected:
                bg_color = QColor(224, 255, 255, 208)
                bg_secondary_color = QColor(132, 224, 228, 158)
                border_color = QColor(18, 150, 158, 188)
        elif self.theme == "blue_white":
            bg_color = QColor(238, 251, 255, 184)
            bg_secondary_color = QColor(184, 230, 252, 150)
            border_color = QColor(151, 213, 244, 190)
            text_color = QColor(24, 49, 73)
            desc_color = QColor(90, 113, 136)

            if is_hover or is_selected:
                bg_color = QColor(236, 251, 255, 224)
                bg_secondary_color = QColor(167, 224, 251, 188)
                border_color = QColor(83, 190, 238, 206)
        elif self.theme == "light":
            bg_color = QColor(255, 255, 255)
            border_color = QColor(0, 0, 0, 25)
            text_color = QColor(55, 65, 81)
            desc_color = QColor(107, 114, 128)

            if is_hover or is_selected:
                bg_color = QColor(248, 250, 252)
                border_color = QColor(59, 130, 246, 127)
        elif self.theme == "dark_green":
            bg_color = QColor(0, 16, 18, 118)
            bg_secondary_color = QColor(0, 34, 28, 92)
            border_color = QColor(0, 229, 255, 150)
            text_color = QColor(0, 255, 65)
            desc_color = QColor(124, 195, 139)

            if is_hover or is_selected:
                bg_color = QColor(0, 32, 25, 150)
                bg_secondary_color = QColor(0, 78, 44, 112)
                border_color = QColor(0, 255, 65, 220)
        elif self.theme == "purple_neon":
            bg_color = QColor(12, 2, 20, 170)
            bg_secondary_color = QColor(78, 10, 112, 132)
            border_color = QColor(255, 207, 92, 176)
            text_color = QColor(255, 232, 147)
            desc_color = QColor(210, 176, 221)

            if is_hover or is_selected:
                bg_color = QColor(22, 3, 34, 204)
                bg_secondary_color = QColor(105, 16, 148, 168)
                border_color = QColor(255, 232, 147, 236)
        elif self.theme == "red_orange":
            bg_color = QColor(110, 0, 0, 196)
            bg_secondary_color = QColor(190, 24, 10, 150)
            border_color = QColor(255, 210, 96, 214)
            text_color = QColor(255, 244, 204)
            desc_color = QColor(255, 198, 150)

            if is_hover or is_selected:
                bg_color = QColor(150, 0, 0, 228)
                bg_secondary_color = QColor(226, 54, 24, 188)
                border_color = QColor(255, 232, 147, 248)
        else:
            if is_hover or is_selected:
                border_color = QColor(129, 140, 248, 190)

        # 3. 绘制背景
        path = QPainterPath()
        path.addRoundedRect(QRectF(card_rect), card_radius, card_radius)

        if self.theme == "celadon_mist":
            if hover_progress:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(QRectF(card_rect.adjusted(-2, -2, 2, 2)), card_radius + 1, card_radius + 1)
                painter.fillPath(glow_path, QColor(16, 142, 150, 34))

            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(QRectF(card_rect.translated(0, 5)), card_radius, card_radius)
            painter.fillPath(shadow_path, QColor(28, 104, 110, 16 if not hover_progress else 26))

            card_gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
            card_gradient.setColorAt(0.0, bg_color)
            card_gradient.setColorAt(0.60, bg_secondary_color or bg_color)
            card_gradient.setColorAt(1.0, QColor(212, 250, 250, 158 if hover_progress else 122))
            painter.fillPath(path, QBrush(card_gradient))
            painter.setPen(QPen(border_color, 1))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(240, 255, 255, 230 if hover_progress else 188), 1))
            painter.drawLine(card_rect.left() + 18, card_rect.top() + 1, card_rect.right() - 18, card_rect.top() + 1)

            mist_pen = QPen(QColor(18, 139, 148, 30 if hover_progress else 20), 2)
            painter.setPen(mist_pen)
            painter.drawArc(QRectF(card_rect.left() + 26, card_rect.bottom() - 36, 110, 34), 0, 180 * 16)
            painter.drawArc(QRectF(card_rect.left() + 68, card_rect.bottom() - 28, 128, 26), 18 * 16, 156 * 16)
            painter.drawArc(QRectF(card_rect.right() - 176, card_rect.bottom() - 34, 132, 30), 0, 180 * 16)

            mountain_path = QPainterPath()
            mountain_path.moveTo(card_rect.right() - 168, card_rect.bottom() - 10)
            mountain_path.quadTo(card_rect.right() - 136, card_rect.bottom() - 30, card_rect.right() - 104, card_rect.bottom() - 14)
            mountain_path.quadTo(card_rect.right() - 78, card_rect.bottom() - 4, card_rect.right() - 40, card_rect.bottom() - 14)
            mountain_path.lineTo(card_rect.right() - 40, card_rect.bottom() - 2)
            mountain_path.lineTo(card_rect.right() - 168, card_rect.bottom() - 2)
            mountain_path.closeSubpath()
            painter.fillPath(mountain_path, QColor(17, 132, 140, 24 if hover_progress else 18))
        elif self.theme == "blue_white":
            if hover_progress:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(QRectF(card_rect.adjusted(-2, -2, 2, 2)), card_radius + 1, card_radius + 1)
                painter.fillPath(glow_path, QColor(92, 205, 234, 34))

            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(QRectF(card_rect.translated(0, 5)), card_radius, card_radius)
            painter.fillPath(shadow_path, QColor(64, 132, 170, 24 if not hover_progress else 38))

            card_gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
            card_gradient.setColorAt(0.0, bg_color)
            card_gradient.setColorAt(0.62, bg_secondary_color or bg_color)
            card_gradient.setColorAt(1.0, QColor(230, 248, 255, 194 if hover_progress else 156))
            painter.fillPath(path, QBrush(card_gradient))
            painter.setPen(QPen(border_color, 1))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(248, 253, 255, 218 if hover_progress else 162), 1))
            painter.drawLine(card_rect.left() + 18, card_rect.top() + 1, card_rect.right() - 18, card_rect.top() + 1)
        elif self.theme == "dark_green":
            if hover_progress:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(QRectF(card_rect.adjusted(-2, -2, 2, 2)), card_radius + 1, card_radius + 1)
                painter.fillPath(glow_path, QColor(0, 255, 65, 38))

            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(QRectF(card_rect.translated(0, 5)), card_radius, card_radius)
            painter.fillPath(shadow_path, QColor(0, 0, 0, 34 if not hover_progress else 50))

            card_gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
            card_gradient.setColorAt(0.0, bg_color)
            card_gradient.setColorAt(0.62, bg_secondary_color or bg_color)
            card_gradient.setColorAt(1.0, QColor(0, 255, 65, 22 if hover_progress else 8))
            painter.fillPath(path, QBrush(card_gradient))
            painter.setPen(QPen(border_color, 1))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(0, 229, 255, 150 if hover_progress else 96), 1))
            painter.drawLine(card_rect.left() + 18, card_rect.top() + 1, card_rect.right() - 18, card_rect.top() + 1)
            painter.setPen(QPen(QColor(0, 255, 65, 86 if hover_progress else 48), 1))
            painter.drawLine(card_rect.left() + 10, card_rect.bottom() - 2, card_rect.right() - 16, card_rect.bottom() - 2)
            corner_pen = QPen(QColor(0, 255, 65, 230 if hover_progress else 168), 1)
            painter.setPen(corner_pen)
            corner = 14
            painter.drawLine(card_rect.left() + 6, card_rect.top() + 6, card_rect.left() + corner + 6, card_rect.top() + 6)
            painter.drawLine(card_rect.left() + 6, card_rect.top() + 6, card_rect.left() + 6, card_rect.top() + corner + 6)
            painter.drawLine(card_rect.right() - 6, card_rect.top() + 6, card_rect.right() - corner - 6, card_rect.top() + 6)
            painter.drawLine(card_rect.right() - 6, card_rect.top() + 6, card_rect.right() - 6, card_rect.top() + corner + 6)
            painter.drawLine(card_rect.left() + 6, card_rect.bottom() - 6, card_rect.left() + corner + 6, card_rect.bottom() - 6)
            painter.drawLine(card_rect.left() + 6, card_rect.bottom() - 6, card_rect.left() + 6, card_rect.bottom() - corner - 6)
            painter.drawLine(card_rect.right() - 6, card_rect.bottom() - 6, card_rect.right() - corner - 6, card_rect.bottom() - 6)
            painter.drawLine(card_rect.right() - 6, card_rect.bottom() - 6, card_rect.right() - 6, card_rect.bottom() - corner - 6)
            painter.setPen(QPen(QColor(255, 51, 102, 184), 1))
            painter.drawLine(card_rect.right() - 28, card_rect.top() + 6, card_rect.right() - 8, card_rect.top() + 6)
            painter.drawLine(card_rect.right() - 8, card_rect.top() + 6, card_rect.right() - 8, card_rect.top() + 26)
            painter.setPen(QPen(QColor(255, 51, 102, 78 if hover_progress else 42), 1))
            painter.drawLine(card_rect.left() + 10, card_rect.bottom() - 6, card_rect.left() + 34, card_rect.bottom() - 6)
            painter.drawLine(card_rect.left() + 10, card_rect.bottom() - 6, card_rect.left() + 10, card_rect.bottom() - 28)
            painter.drawLine(card_rect.right() - 34, card_rect.bottom() - 6, card_rect.right() - 10, card_rect.bottom() - 6)
            painter.drawLine(card_rect.right() - 10, card_rect.bottom() - 6, card_rect.right() - 10, card_rect.bottom() - 28)
        elif self.theme == "purple_neon":
            if hover_progress:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(QRectF(card_rect.adjusted(-2, -2, 2, 2)), card_radius + 1, card_radius + 1)
                painter.fillPath(glow_path, QColor(189, 58, 255, 50))

            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(QRectF(card_rect.translated(0, 5)), card_radius, card_radius)
            painter.fillPath(shadow_path, QColor(4, 0, 9, 46 if not hover_progress else 66))

            card_gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
            card_gradient.setColorAt(0.0, bg_color)
            card_gradient.setColorAt(0.62, bg_secondary_color or bg_color)
            card_gradient.setColorAt(1.0, QColor(255, 207, 92, 58 if hover_progress else 30))
            painter.fillPath(path, QBrush(card_gradient))
            painter.setPen(QPen(border_color, 1))
            painter.drawPath(path)
            painter.setPen(QPen(QColor(255, 232, 147, 194 if hover_progress else 126), 1))
            painter.drawLine(card_rect.left() + 18, card_rect.top() + 1, card_rect.right() - 18, card_rect.top() + 1)

            corner_pen = QPen(QColor(255, 232, 147, 232 if hover_progress else 168), 1)
            painter.setPen(corner_pen)
            corner = 16
            painter.drawLine(card_rect.left() + 8, card_rect.top() + 8, card_rect.left() + corner + 8, card_rect.top() + 8)
            painter.drawLine(card_rect.left() + 8, card_rect.top() + 8, card_rect.left() + 8, card_rect.top() + corner + 8)
            painter.drawLine(card_rect.right() - 8, card_rect.top() + 8, card_rect.right() - corner - 8, card_rect.top() + 8)
            painter.drawLine(card_rect.right() - 8, card_rect.top() + 8, card_rect.right() - 8, card_rect.top() + corner + 8)

            painter.setPen(QPen(QColor(189, 58, 255, 118 if hover_progress else 66), 1))
            painter.drawLine(card_rect.left() + 28, card_rect.bottom() - 3, card_rect.right() - 28, card_rect.bottom() - 3)
            painter.drawLine(card_rect.right() - 34, card_rect.top() + 11, card_rect.right() - 14, card_rect.top() + 11)
            painter.drawLine(card_rect.right() - 14, card_rect.top() + 11, card_rect.right() - 14, card_rect.top() + 31)

            crown_path = QPainterPath()
            crown_left = card_rect.right() - 46
            crown_top = card_rect.top() + 9
            crown_path.moveTo(crown_left, crown_top + 12)
            crown_path.lineTo(crown_left + 6, crown_top + 4)
            crown_path.lineTo(crown_left + 13, crown_top + 11)
            crown_path.lineTo(crown_left + 20, crown_top + 2)
            crown_path.lineTo(crown_left + 27, crown_top + 11)
            crown_path.lineTo(crown_left + 34, crown_top + 4)
            crown_path.lineTo(crown_left + 40, crown_top + 12)
            painter.setPen(QPen(QColor(255, 232, 147, 170 if hover_progress else 104), 1))
            painter.drawPath(crown_path)
        elif self.theme == "red_orange":
            if hover_progress:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(QRectF(card_rect.adjusted(-2, -2, 2, 2)), card_radius + 1, card_radius + 1)
                painter.fillPath(glow_path, QColor(255, 160, 64, 62))

            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(QRectF(card_rect.translated(0, 5)), card_radius, card_radius)
            painter.fillPath(shadow_path, QColor(34, 0, 0, 30 if not hover_progress else 46))

            card_gradient = QLinearGradient(card_rect.topLeft(), card_rect.bottomRight())
            card_gradient.setColorAt(0.0, bg_color)
            card_gradient.setColorAt(0.62, bg_secondary_color or bg_color)
            card_gradient.setColorAt(1.0, QColor(255, 220, 112, 74 if hover_progress else 38))
            painter.fillPath(path, QBrush(card_gradient))
            painter.setPen(QPen(border_color, 1))
            painter.drawPath(path)
            inner_path = QPainterPath()
            inner_path.addRoundedRect(QRectF(card_rect.adjusted(1, 1, -1, -1)), card_radius - 1, card_radius - 1)
            painter.setPen(QPen(QColor(255, 232, 147, 138 if hover_progress else 88), 1))
            painter.drawPath(inner_path)
            painter.setPen(QPen(QColor(255, 240, 170, 224 if hover_progress else 158), 1))
            painter.drawLine(card_rect.left() + 18, card_rect.top() + 1, card_rect.right() - 18, card_rect.top() + 1)
            painter.setPen(QPen(QColor(255, 112, 56, 150 if hover_progress else 86), 1))
            painter.drawLine(card_rect.left() + 28, card_rect.bottom() - 3, card_rect.right() - 28, card_rect.bottom() - 3)
            corner_pen = QPen(QColor(255, 232, 147, 240 if hover_progress else 188), 1)
            painter.setPen(corner_pen)
            corner = 15
            painter.drawLine(card_rect.left() + 8, card_rect.top() + 8, card_rect.left() + corner + 8, card_rect.top() + 8)
            painter.drawLine(card_rect.left() + 8, card_rect.top() + 8, card_rect.left() + 8, card_rect.top() + corner + 8)
            painter.drawLine(card_rect.right() - 8, card_rect.top() + 8, card_rect.right() - corner - 8, card_rect.top() + 8)
            painter.drawLine(card_rect.right() - 8, card_rect.top() + 8, card_rect.right() - 8, card_rect.top() + corner + 8)
            painter.drawLine(card_rect.left() + 8, card_rect.bottom() - 8, card_rect.left() + corner + 8, card_rect.bottom() - 8)
            painter.drawLine(card_rect.left() + 8, card_rect.bottom() - 8, card_rect.left() + 8, card_rect.bottom() - corner - 8)
            painter.drawLine(card_rect.right() - 8, card_rect.bottom() - 8, card_rect.right() - corner - 8, card_rect.bottom() - 8)
            painter.drawLine(card_rect.right() - 8, card_rect.bottom() - 8, card_rect.right() - 8, card_rect.bottom() - corner - 8)
            star_font = QFont()
            star_font.setPixelSize(16)
            painter.setFont(star_font)
            painter.setPen(QPen(QColor(255, 232, 147, 166 if hover_progress else 104), 1))
            painter.drawText(QRect(card_rect.right() - 40, card_rect.top() + 15, 18, 18), Qt.AlignCenter, "*")
        else:
            painter.fillPath(path, bg_color)
            painter.setPen(QPen(border_color, 1))
            painter.drawPath(path)

        # 4. 绘制图标
        icon_rect = QRect(card_rect.left() + 12, card_rect.top() + 16, 56, 56)

        icon = icon_loader.get_icon(tool, theme_name=self.theme)

        pixmap = self._get_icon_pixmap(tool, icon, 56)

        if not pixmap.isNull():
            if self.theme == "celadon_mist":
                icon_plate_rect = QRectF(icon_rect.adjusted(2, 2, -2, -2))
                painter.setPen(QPen(QColor(255, 255, 255, 178), 1))
                painter.setBrush(QBrush(QColor(255, 255, 255, 188)))
                painter.drawRoundedRect(icon_plate_rect, 14, 14)
            elif self.theme == "blue_white":
                icon_plate_rect = QRectF(icon_rect.adjusted(1, 1, -1, -1))
                painter.setPen(QPen(QColor(255, 255, 255, 190), 1))
                painter.setBrush(QBrush(QColor(255, 255, 255, 130)))
                painter.drawRoundedRect(icon_plate_rect, 14, 14)
            elif self.theme == "dark_green":
                icon_plate_rect = QRectF(icon_rect.adjusted(1, 1, -1, -1))
                painter.setPen(QPen(QColor(0, 229, 255, 92), 1))
                painter.setBrush(QBrush(QColor(0, 229, 255, 22)))
                painter.drawRoundedRect(icon_plate_rect, 14, 14)
            elif self.theme == "purple_neon":
                icon_plate_rect = QRectF(icon_rect.adjusted(1, 1, -1, -1))
                painter.setPen(QPen(QColor(255, 207, 92, 158), 1))
                painter.setBrush(QBrush(QColor(45, 7, 67, 70)))
                painter.drawRoundedRect(icon_plate_rect, 14, 14)
            elif self.theme == "red_orange":
                icon_plate_rect = QRectF(icon_rect.adjusted(1, 1, -1, -1))
                painter.setPen(QPen(QColor(255, 220, 112, 172), 1))
                painter.setBrush(QBrush(QColor(120, 0, 0, 76)))
                painter.drawRoundedRect(icon_plate_rect, 14, 14)

            scaled_pixmap = pixmap
            x = icon_rect.left() + (icon_rect.width() - scaled_pixmap.width()) // 2
            y = icon_rect.top() + (icon_rect.height() - scaled_pixmap.height()) // 2

            if self._needs_icon_contrast_boost(scaled_pixmap, bg_color, tool.get("_icon_cache_key")):
                self._draw_icon_boost_background(painter, icon_rect)

            painter.drawPixmap(x, y, scaled_pixmap)
        else:
            icon.paint(painter, icon_rect, Qt.AlignCenter)

        # 5. 绘制文本
        text_x = icon_rect.right() + 15
        tool_path = (tool.get('path') or '').strip()
        is_web_tool = bool(tool.get('is_web_tool', False)) or tool_path.startswith(('http://', 'https://'))
        if not is_web_tool:
            try:
                is_web_tool = self._get_tool_type_label(tool) == "网页"
            except Exception:
                is_web_tool = False
        text_width = max(80, card_rect.right() - 42 - text_x)

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
            if self.theme == "red_orange":
                painter.setPen(QColor(255, 220, 112, 72))
                painter.drawText(combined_rect.translated(1, 1), Qt.AlignLeft | Qt.AlignVCenter, display_name)
                painter.setPen(text_color)
            painter.drawText(combined_rect, Qt.AlignLeft | Qt.AlignVCenter, display_name)
        else:
            # 有介绍：第一行名称，第二行简介
            title_rect = QRect(text_x, card_rect.top() + 14, text_width, 22)
            if self.theme == "red_orange":
                painter.setPen(QColor(255, 220, 112, 68))
                painter.drawText(title_rect.translated(1, 1), Qt.AlignLeft | Qt.AlignVCenter, name)
                painter.setPen(text_color)
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

        dot_radius = 5
        dot_center = QPoint(card_rect.right() - 12, card_rect.top() + 12)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._get_status_color(tool, option))
        painter.drawEllipse(dot_center, dot_radius, dot_radius)

        buttons_margin = 10
        buttons_height = 30
        buttons_top = card_rect.bottom() - buttons_height - buttons_margin
        primary_button_width = 52 if not is_web_tool else 58
        secondary_button_width = 32
        secondary_spacing = 6
        menu_gap = 8
        button_icon_size = 18

        secondary_indices = [ACTION_BUTTON_TOGGLE_FAVORITE, ACTION_BUTTON_OPEN_NOTES]
        if not is_web_tool:
            secondary_indices.extend([ACTION_BUTTON_OPEN_TERMINAL, ACTION_BUTTON_OPEN_DIRECTORY])

        button_rects_for_row = []
        secondary_count = len(secondary_indices)
        secondary_total_width = secondary_count * secondary_button_width + max(0, secondary_count - 1) * secondary_spacing
        total_buttons_width = primary_button_width + (menu_gap + secondary_total_width if secondary_count else 0)
        buttons_right = card_rect.right() - buttons_margin
        base_x = buttons_right - total_buttons_width
        base_y = buttons_top
        style = option.widget.style() if option.widget else None
        icons = self._get_action_icons(style)

        primary_bg_color, primary_border_color, primary_icon_color = self._get_primary_action_button_colors()
        secondary_bg_color, secondary_border_color, secondary_icon_color = self._get_secondary_action_button_colors()

        run_rect = QRect(base_x, base_y, primary_button_width, buttons_height)
        button_rects_for_row.append((ACTION_BUTTON_RUN, run_rect))
        painter.setPen(QPen(primary_border_color, 1))
        if self.theme in ("celadon_mist", "blue_white", "dark_green", "purple_neon", "red_orange"):
            primary_gradient = QLinearGradient(run_rect.topLeft(), run_rect.bottomRight())
            if self.theme == "celadon_mist":
                primary_gradient.setColorAt(0.0, QColor(58, 196, 197))
            elif self.theme == "blue_white":
                primary_gradient.setColorAt(0.0, QColor(113, 205, 255))
            elif self.theme == "purple_neon":
                primary_gradient.setColorAt(0.0, QColor(255, 232, 147))
            elif self.theme == "red_orange":
                primary_gradient.setColorAt(0.0, QColor(255, 220, 112))
            else:
                primary_gradient.setColorAt(0.0, QColor(0, 255, 65))
            primary_gradient.setColorAt(1.0, primary_bg_color)
            painter.setBrush(QBrush(primary_gradient))
        else:
            painter.setBrush(QBrush(primary_bg_color))
        painter.drawRoundedRect(run_rect, 10, 10)

        run_icon = icons.get(ACTION_BUTTON_RUN)
        if run_icon is not None:
            run_pix = self._build_tinted_icon_pixmap(run_icon, button_icon_size, primary_icon_color)
            if not run_pix.isNull():
                icon_x = run_rect.x() + (run_rect.width() - button_icon_size) // 2
                icon_y = run_rect.y() + (run_rect.height() - button_icon_size) // 2
                painter.drawPixmap(icon_x, icon_y, button_icon_size, button_icon_size, run_pix)

        if secondary_count:
            secondary_x = run_rect.right() + 1 + menu_gap
            for button_index in secondary_indices:
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
        if self.theme == "celadon_mist":
            text = QColor(42, 102, 105)
            border = QColor(124, 207, 209, 190)
            bg = QColor(246, 255, 254, 220)

            if type_label == "网页":
                text = QColor(24, 127, 137)
                border = QColor(108, 203, 215, 210)
                bg = QColor(239, 253, 254, 224)
            elif type_label == "终端":
                text = QColor(31, 127, 110)
                border = QColor(118, 214, 197, 210)
                bg = QColor(239, 253, 249, 224)
            elif type_label == "目录":
                text = QColor(159, 118, 80)
                border = QColor(232, 205, 168, 194)
                bg = QColor(252, 247, 240, 214)
            elif type_label == "文档":
                text = QColor(123, 111, 159)
                border = QColor(208, 198, 232, 194)
                bg = QColor(247, 244, 252, 214)
            elif type_label == "应用":
                text = QColor(79, 132, 128)
                border = QColor(171, 220, 217, 194)
                bg = QColor(239, 249, 248, 214)
        elif self.theme == "blue_white":
            text = QColor(86, 107, 128)
            border = QColor(188, 214, 236)
            bg = QColor(255, 255, 255, 210)

            if type_label == "网页":
                text = QColor(45, 116, 206)
                border = QColor(132, 190, 250)
                bg = QColor(239, 249, 255, 226)
            elif type_label == "终端":
                text = QColor(23, 132, 78)
                border = QColor(116, 215, 167)
                bg = QColor(231, 250, 239, 226)
            elif type_label == "目录":
                text = QColor(75, 111, 160)
                border = QColor(172, 205, 236)
                bg = QColor(239, 248, 254, 226)
            elif type_label == "文档":
                text = QColor(111, 89, 162)
                border = QColor(198, 185, 235)
                bg = QColor(246, 243, 253, 226)
            elif type_label == "应用":
                text = QColor(43, 122, 155)
                border = QColor(146, 207, 232)
                bg = QColor(235, 248, 252, 226)
        elif self.theme == "light":
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
            text = QColor(0, 229, 255)
            border = QColor(0, 229, 255, 210)
            bg = QColor(15, 42, 47, 222)

            if type_label == "网页":
                text = QColor(0, 229, 255)
                border = QColor(0, 229, 255)
                bg = QColor(15, 42, 47, 224)
            elif type_label == "终端":
                text = QColor(0, 255, 65)
                border = QColor(0, 255, 65)
                bg = QColor(10, 46, 42, 224)
            elif type_label == "目录":
                text = QColor(255, 140, 0)
                border = QColor(255, 140, 0, 220)
                bg = QColor(42, 32, 15, 224)
            elif type_label == "文档":
                text = QColor(0, 229, 255)
                border = QColor(0, 229, 255, 220)
                bg = QColor(12, 39, 48, 224)
            elif type_label == "应用":
                text = QColor(174, 234, 0)
                border = QColor(0, 255, 65, 220)
                bg = QColor(10, 46, 42, 224)
        elif self.theme == "purple_neon":
            text = QColor(255, 230, 163)
            border = QColor(255, 207, 92)
            bg = QColor(24, 3, 38, 226)

            if type_label == "网页":
                text = QColor(255, 232, 147)
                border = QColor(255, 207, 92)
                bg = QColor(50, 9, 72, 226)
            elif type_label == "终端":
                text = QColor(255, 211, 106)
                border = QColor(189, 58, 255)
                bg = QColor(52, 7, 76, 226)
            elif type_label == "目录":
                text = QColor(255, 232, 147)
                border = QColor(255, 211, 106)
                bg = QColor(82, 43, 12, 226)
            elif type_label == "文档":
                text = QColor(255, 230, 163)
                border = QColor(189, 58, 255)
                bg = QColor(70, 11, 100, 226)
            elif type_label == "应用":
                text = QColor(255, 232, 147)
                border = QColor(255, 207, 92)
                bg = QColor(56, 8, 82, 226)
        elif self.theme == "red_orange":
            text = QColor(255, 230, 176)
            border = QColor(255, 220, 112)
            bg = QColor(112, 0, 0, 232)

            if type_label == "网页":
                text = QColor(255, 236, 190)
                border = QColor(255, 220, 112)
                bg = QColor(128, 12, 0, 232)
            elif type_label == "终端":
                text = QColor(255, 205, 160)
                border = QColor(255, 105, 48)
                bg = QColor(138, 12, 0, 232)
            elif type_label == "目录":
                text = QColor(255, 236, 190)
                border = QColor(255, 220, 112)
                bg = QColor(122, 48, 0, 232)
            elif type_label == "文档":
                text = QColor(255, 230, 176)
                border = QColor(255, 220, 112)
                bg = QColor(120, 14, 12, 232)
            elif type_label == "应用":
                text = QColor(255, 236, 190)
                border = QColor(255, 220, 112)
                bg = QColor(132, 8, 0, 232)
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
        cached_label = str(tool.get("_display_type_label", "") or "").strip()
        if cached_label:
            return cached_label

        base_dir = os.fspath(get_runtime_state_root())
        widget = getattr(self, "window", None)
        window = widget() if callable(widget) else None
        if window is not None:
            base_dir = getattr(window, "config_dir", None) or base_dir
        return infer_display_tool_type_label(tool, base_dir=base_dir)

    def _get_status_color(self, tool: dict, option) -> QColor:
        status_name = str(tool.get("_path_status") or "").strip()
        if status_name in {PathStatus.UNKNOWN, PathStatus.LOADING}:
            return QColor(245, 158, 11)
        if status_name in {PathStatus.WEB, PathStatus.AVAILABLE}:
            return QColor(34, 197, 94)
        if status_name == PathStatus.UNCONFIGURED:
            return QColor(148, 163, 184)
        if status_name in {PathStatus.MISSING, PathStatus.TIMEOUT, PathStatus.CANCELLED}:
            return QColor(220, 38, 38)

        if "_is_path_available" in tool:
            status = tool.get("_is_path_available")
            if status is None:
                return QColor(245, 158, 11)
            return QColor(34, 197, 94) if status else QColor(220, 38, 38)
        return QColor(220, 38, 38)

    def editorEvent(self, event, model, option, index):
        """处理按钮点击事件：区分三种按钮

        0: 启动工具
        1: 在此处打开命令行
        2: 在此处打开目录
        3: 收藏/取消收藏
        4: 打开笔记
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
            "max_columns": 4,
            "min_card_width": 300,
            "max_card_width": None,
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
        self._metadata_cache_ttl_seconds = 30.0
        self._type_label_cache = {}
        self._icon_key_cache = {}
        self._path_status_generation = 0
        self._async_path_status_enabled = True
        self.path_status_service = PathStatusService(self, ttl_seconds=self._metadata_cache_ttl_seconds)
        self.path_status_service.status_resolved.connect(self._on_path_status_result)
        self._path_status_request_timer = QTimer(self)
        self._path_status_request_timer.setSingleShot(True)
        self._path_status_request_timer.setInterval(180)
        self._path_status_request_timer.timeout.connect(self._schedule_path_status_warmup)
        self._icon_warmup_queue = []
        self._icon_warmup_seen = set()
        self._icon_warmup_timer = QTimer(self)
        self._icon_warmup_timer.setInterval(120)
        self._icon_warmup_timer.timeout.connect(self._process_icon_warmup_queue)
        self._icon_warmup_request_timer = QTimer(self)
        self._icon_warmup_request_timer.setSingleShot(True)
        self._icon_warmup_request_timer.setInterval(250)
        self._icon_warmup_request_timer.timeout.connect(self._schedule_icon_warmup)
        # 防止底部按钮点击后 QListView 再触发一次 clicked
        self._suppress_next_click = False
        self.init_ui()

    @property
    def _path_status_queue(self):
        base_dir = self._resolve_metadata_base_dir()
        viewport = self.view.viewport() if hasattr(self, "view") else None
        viewport_rect = viewport.rect() if viewport is not None else QRect()
        visible_tools = []
        fallback_tools = []
        seen = set()
        tools = self.model.tools() if hasattr(self, "model") else []
        for row_idx, tool in enumerate(tools):
            if not isinstance(tool, dict):
                continue
            if tool.get("_path_status") not in (None, PathStatus.UNKNOWN, PathStatus.LOADING):
                continue
            cache_key = self._path_status_cache_key(tool, base_dir)
            if cache_key in seen:
                continue
            seen.add(cache_key)
            try:
                rect = self.view.visualRect(self.model.index(row_idx, 0))
            except Exception:
                rect = QRect()
            if rect.isValid() and viewport_rect.intersects(rect):
                visible_tools.append(cache_key)
            elif not visible_tools and len(fallback_tools) < 8:
                fallback_tools.append(cache_key)
        return visible_tools if visible_tools else fallback_tools

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
        self.view.setLayoutMode(QListView.Batched)
        self.view.setBatchSize(80)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
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
        self.view.verticalScrollBar().valueChanged.connect(
            lambda _value: (self._request_icon_warmup(), self._request_path_status_warmup())
        )

        layout.addWidget(self.view)

        # 信号连接
        self.view.clicked.connect(self.on_item_clicked)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)

        self.apply_theme_styles()
        self.set_layout_mode(self.layout_mode)
        self.update_card_layout(force=True)

        # 连接加载器信号，刷新界面
        icon_loader.icon_path_ready.connect(self._update_rows_for_icon_path)
        icon_loader.auto_icon_ready.connect(self._update_rows_for_auto_icon)

        # 底部按钮点击：由 Delegate 发出精确按钮索引，再在这里分发动作
        self.delegate.buttonClicked.connect(self.on_button_clicked)
        self.model.orderChanged.connect(self.tool_order_changed.emit)

    def set_layout_mode(self, layout_mode):
        """切换卡片布局模式。"""
        layout_mode = layout_mode if layout_mode in self.LAYOUT_PRESETS else "main"
        self.view.setViewMode(QListView.IconMode)
        self.view.setLayoutMode(QListView.Batched)
        self.view.setBatchSize(80)
        self.view.setFlow(QListView.LeftToRight)
        self.view.setWrapping(True)
        self.view.setResizeMode(QListView.Adjust)
        self.view.setMovement(QListView.Snap)
        self.view.setSpacing(8)
        if self.layout_mode == layout_mode:
            self.update_card_layout()
            return

        self.layout_mode = layout_mode
        self.update_card_layout()

    def eventFilter(self, watched, event):
        if watched is self.view.viewport() and event.type() == QEvent.Resize:
            if self._layout_update_in_progress:
                return super().eventFilter(watched, event)
            self.update_card_layout()
            self._request_icon_warmup()
            self._request_path_status_warmup()
        return super().eventFilter(watched, event)

    def _get_layout_preset(self):
        return self.LAYOUT_PRESETS.get(self.layout_mode, self.LAYOUT_PRESETS["main"])

    def _calculate_card_width_for_columns(self, viewport_width, columns, spacing):
        columns = max(1, int(columns))
        spacing = max(0, int(spacing))
        available_width = max(0, int(viewport_width) - spacing * 2)
        return max(1, (available_width // columns) - spacing)

    def _resolve_columns(self, viewport_width, spacing, preset):
        preferred_columns = max(1, preset.get("preferred_columns", 1))
        max_columns = max(1, preset.get("max_columns", preferred_columns))
        min_card_width = preset["min_card_width"]

        for columns in range(max_columns, 1, -1):
            candidate_width = self._calculate_card_width_for_columns(viewport_width, columns, spacing)
            if candidate_width >= min_card_width:
                return columns
        return 1

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
        self.delegate._tinted_icon_pixmap_cache.clear()
        self.delegate._icon_contrast_cache.clear()
        self.delegate._icon_pixmap_cache.clear()
        self.apply_theme_styles()
        self.update_card_layout(force=True)
        # 强制重绘
        self.view.viewport().update()

    def apply_theme_styles(self):
        known_themes = {
            "celadon_mist",
            "light",
            "blue_white",
            "dark_green",
            "purple_neon",
            "red_orange",
        }
        background = "transparent" if self.current_theme in known_themes else "#1a1a2e"
        self.view.setStyleSheet(
            f"""
            QListView {{
                background-color: {background};
                border: none;
                outline: none;
            }}
            QListView::viewport {{
                background-color: {background};
            }}
            """
        )
        viewport = self.view.viewport()
        viewport.setAutoFillBackground(True)
        viewport_palette = viewport.palette()
        try:
            rgb = QColor(background)
        except Exception:
            rgb = QColor("#1a1a2e")
        viewport_palette.setColor(QPalette.Window, rgb)
        viewport_palette.setColor(QPalette.Base, rgb)
        viewport.setPalette(viewport_palette)

    def display_tools(self, tools_data):
        """显示工具列表"""
        # Model/View 模式下，直接给 Model 数据，Qt 负责极速渲染
        self.model.update_data(self._prepare_tools_for_display(tools_data))
        self.delegate._button_rects.clear()
        self.update_card_layout()
        self._schedule_path_status_warmup()
        self._request_icon_warmup()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_path_status_warmup()
        self._request_icon_warmup()

    def _resolve_metadata_base_dir(self):
        base_dir = os.fspath(get_runtime_state_root())
        try:
            window = self.window()
            base_dir = getattr(window, "config_dir", None) or base_dir
        except Exception:
            pass
        return os.fspath(base_dir)

    def _get_cached_metadata_value(self, cache, key, loader, default):
        now = monotonic()
        cached = cache.get(key)
        if cached is not None:
            cached_at, cached_value = cached
            if now - cached_at <= self._metadata_cache_ttl_seconds:
                return cached_value

        try:
            value = loader()
        except Exception:
            value = default

        if len(cache) > 2048:
            cache.clear()
        cache[key] = (now, value)
        return value

    def _get_fresh_cached_metadata_value(self, cache, key):
        cached = cache.get(key)
        if cached is None:
            return False, None
        cached_at, cached_value = cached
        if monotonic() - cached_at > self._metadata_cache_ttl_seconds:
            return False, None
        return True, cached_value

    def _path_status_cache_key(self, tool, base_dir):
        return build_path_status_cache_key(tool, base_dir)

    def _type_label_cache_key(self, tool, base_dir):
        return (
            os.path.normcase(os.fspath(base_dir or "")),
            str(tool.get("path") or "").strip(),
            bool(tool.get("is_web_tool", False)),
            bool(tool.get("run_in_terminal", False)),
            str(tool.get("type_label") or "").strip(),
        )

    def _icon_key_cache_key(self, tool):
        return (
            str(self.current_theme or ""),
            str(tool.get("path") or "").strip(),
            bool(tool.get("is_web_tool", False)),
            str(tool.get("icon") or "").strip(),
            str(tool.get("icon_path") or "").strip(),
        )

    def _queue_path_status_check(self, cache_key, tool, base_dir):
        if not self._async_path_status_enabled:
            return
        if self.path_status_service.cache_key(tool, base_dir) != cache_key:
            tool = dict(tool or {})
        self.path_status_service.request(
            tool,
            base_dir=base_dir,
            request_id=self._path_status_generation,
        )

    def _process_path_status_queue(self):
        # Compatibility hook for older tests/extensions. Resolution now runs in
        # PathStatusService workers instead of a main-thread timer queue.
        self._schedule_path_status_warmup()

    def _on_path_status_resolved(self, cache_key, available):
        status = PathStatus.AVAILABLE if available else PathStatus.MISSING
        result = PathStatusResult(
            cache_key=cache_key,
            status=status,
            available=bool(available),
            request_id=self._path_status_generation,
        )
        self._apply_path_status_result(result)

    def _on_path_status_result(self, result):
        if not isinstance(result, PathStatusResult):
            return
        if result.request_id and result.request_id != self._path_status_generation:
            return
        self._apply_path_status_result(result)

    def _apply_path_status_result(self, result):
        cache_key = result.cache_key
        base_dir = self._resolve_metadata_base_dir()
        viewport = self.view.viewport()
        for row, tool in enumerate(self.model.tools()):
            if not isinstance(tool, dict):
                continue
            if self._path_status_cache_key(tool, base_dir) != cache_key:
                continue
            if tool.get("_path_status") == result.status and tool.get("_is_path_available") == result.available:
                continue
            tool["_path_status"] = result.status
            tool["_is_path_available"] = result.available
            index = self.model.index(row, 0)
            self.model.dataChanged.emit(index, index, [Qt.UserRole])
            rect = self.view.visualRect(index)
            if rect.isValid() and rect.intersects(viewport.rect()):
                viewport.update(rect)

    def _prepare_tools_for_display(self, tools_data):
        base_dir = self._resolve_metadata_base_dir()
        self._path_status_generation += 1
        self.path_status_service.cancel_generation(self._path_status_generation - 1)

        prepared_tools = []
        for tool in tools_data or []:
            if not isinstance(tool, dict):
                prepared_tools.append(tool)
                continue
            prepared_tool = dict(tool)
            prepared_tool["_display_type_label"] = self._get_cached_metadata_value(
                self._type_label_cache,
                self._type_label_cache_key(prepared_tool, base_dir),
                lambda tool=prepared_tool: infer_display_tool_type_label(tool),
                str(prepared_tool.get("_display_type_label") or ""),
            )
            path_status_key = self._path_status_cache_key(prepared_tool, base_dir)
            cached_result = self.path_status_service.get_cached(path_status_key)
            if cached_result is not None:
                prepared_tool["_path_status"] = cached_result.status
                prepared_tool["_is_path_available"] = cached_result.available
            elif not self._async_path_status_enabled:
                resolved = self.path_status_service.resolve_now(
                    prepared_tool,
                    base_dir=base_dir,
                    request_id=self._path_status_generation,
                )
                prepared_tool["_path_status"] = resolved.status
                prepared_tool["_is_path_available"] = resolved.available
            else:
                prepared_tool["_path_status"] = PathStatus.LOADING
                prepared_tool["_is_path_available"] = None
            prepared_tool["_icon_cache_key"] = self._get_cached_metadata_value(
                self._icon_key_cache,
                self._icon_key_cache_key(prepared_tool),
                lambda tool=prepared_tool: get_icon_cache_key(tool, theme_name=self.current_theme),
                "",
            )
            prepared_tool["_icon_cache_theme"] = self.current_theme
            prepared_tools.append(prepared_tool)
        return prepared_tools

    def _request_path_status_warmup(self):
        self._path_status_request_timer.start()

    def _schedule_path_status_warmup(self):
        base_dir = self._resolve_metadata_base_dir()
        viewport = self.view.viewport()
        viewport_rect = viewport.rect() if viewport is not None else QRect()
        visible_tools = []
        fallback_tools = []
        seen_keys = set()

        for row, tool in enumerate(self.model.tools()):
            if not isinstance(tool, dict):
                continue
            if tool.get("_path_status") not in (None, PathStatus.UNKNOWN, PathStatus.LOADING):
                continue

            cache_key = self._path_status_cache_key(tool, base_dir)
            if cache_key in seen_keys:
                continue
            seen_keys.add(cache_key)

            index = self.model.index(row, 0)
            rect = self.view.visualRect(index)
            tool_payload = (cache_key, dict(tool or {}), base_dir)
            if rect.isValid() and viewport_rect.intersects(rect):
                visible_tools.append(tool_payload)
            elif not visible_tools and len(fallback_tools) < 8:
                fallback_tools.append(tool_payload)

        queued_tools = visible_tools if visible_tools else fallback_tools
        for cache_key, tool, resolved_base_dir in queued_tools:
            self._queue_path_status_check(cache_key, tool, resolved_base_dir)

    def _request_icon_warmup(self):
        self._icon_warmup_request_timer.start()

    def _schedule_icon_warmup(self):
        self._icon_warmup_queue.clear()
        self._icon_warmup_seen.clear()

        viewport = self.view.viewport()
        viewport_rect = viewport.rect() if viewport is not None else QRect()
        visible_tools = []
        fallback_tools = []
        for row, tool in enumerate(self.model.tools()):
            if not isinstance(tool, dict):
                continue
            cache_key = self._icon_key_cache_key(tool)
            if cache_key in self._icon_warmup_seen:
                continue
            self._icon_warmup_seen.add(cache_key)
            index = self.model.index(row, 0)
            rect = self.view.visualRect(index)
            if rect.isValid() and viewport_rect.intersects(rect):
                visible_tools.append(dict(tool))
            elif row < 32:
                fallback_tools.append(dict(tool))

        if visible_tools:
            self._icon_warmup_queue.extend(visible_tools)
        elif fallback_tools:
            self._icon_warmup_queue.extend(fallback_tools[:24])

        if self._icon_warmup_queue and not self._icon_warmup_timer.isActive():
            self._icon_warmup_timer.start()

    def _process_icon_warmup_queue(self):
        if not self._icon_warmup_queue:
            self._icon_warmup_timer.stop()
            return

        tool = self._icon_warmup_queue.pop(0)
        try:
            icon_loader.warm_tool_icon(tool, theme_name=self.current_theme)
        except Exception:
            pass

        if not self._icon_warmup_queue:
            self._icon_warmup_timer.stop()

    def _update_rows_for_icon_path(self, icon_path):
        target_path = os.fspath(icon_path or "")
        if not target_path:
            return

        viewport = self.view.viewport()
        for row, tool in enumerate(self.model.tools()):
            if not isinstance(tool, dict):
                continue
            current_icon_key = os.fspath(tool.get("_icon_cache_key") or "")
            if current_icon_key != target_path:
                continue
            index = self.model.index(row, 0)
            self.model.dataChanged.emit(index, index, [Qt.UserRole])
            rect = self.view.visualRect(index)
            if rect.isValid() and rect.intersects(viewport.rect()):
                viewport.update(rect)

    def _update_rows_for_auto_icon(self, icon_path, source_tool):
        target_path = os.fspath(icon_path or "")
        if not target_path or not isinstance(source_tool, dict):
            return

        source_identity = get_tool_icon_identity(source_tool)
        if not source_identity:
            return

        viewport = self.view.viewport()
        for row, tool in enumerate(self.model.tools()):
            if not isinstance(tool, dict):
                continue
            if get_tool_icon_identity(tool) != source_identity:
                continue
            tool["_icon_cache_key"] = target_path
            tool["_icon_cache_theme"] = self.current_theme
            if len(self._icon_key_cache) > 2048:
                self._icon_key_cache.clear()
            self._icon_key_cache[self._icon_key_cache_key(tool)] = (monotonic(), target_path)
            index = self.model.index(row, 0)
            self.model.dataChanged.emit(index, index, [Qt.UserRole])
            rect = self.view.visualRect(index)
            if rect.isValid() and rect.intersects(viewport.rect()):
                viewport.update(rect)

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
        if button_index == ACTION_BUTTON_RUN:
            self.run_tool.emit(tool)
            return

        if button_index == ACTION_BUTTON_TOGGLE_FAVORITE:
            tool_id = tool.get("id")
            if tool_id is not None:
                self.toggle_favorite.emit(tool_id)
            return

        if button_index == ACTION_BUTTON_OPEN_NOTES:
            self._open_notes_for_tool(tool)
            return

        # 下面两个按钮需要推断一个“目标目录”
        target_dir = self.resolve_tool_target_dir(tool)

        if not target_dir:
            if button_index in (ACTION_BUTTON_OPEN_TERMINAL, ACTION_BUTTON_OPEN_DIRECTORY):
                self.warn_missing_tool_target_dir(tool)
            return

        if button_index == ACTION_BUTTON_OPEN_TERMINAL:
            # 在此处打开命令行
            self.open_command_line(target_dir, tool_data=tool)
        elif button_index == ACTION_BUTTON_OPEN_DIRECTORY:
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
        menu.setStyleSheet(ThemeManager().get_context_menu_style(self.current_theme))

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

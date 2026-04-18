#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立的收藏页网格视图。"""
import os

from PyQt5.QtCore import Qt, QSize, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QImage, QPen
from PyQt5.QtWidgets import (
    QAbstractButton,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from core.runtime_paths import get_runtime_state_root

try:
    from ui.markdown_note_dialog import MarkdownNoteDialog
except Exception:
    MarkdownNoteDialog = None

from ui.icon_loader import get_icon_cache_key, icon_loader
from ui.tool_card_actions_mixin import ToolCardActionsMixin


class FavoriteToolCard(QFrame):
    clicked = pyqtSignal(dict)
    button_clicked = pyqtSignal(dict, int)
    context_menu_requested = pyqtSignal(dict, QPoint)
    CARD_HEIGHT = 116
    ICON_SIZE = 46

    def __init__(self, tool, theme_name='dark_green', parent=None):
        super().__init__(parent)
        self.tool = tool or {}
        self.theme_name = theme_name or 'dark_green'
        self._theme_palette = {}
        self._icon_luminance_cache = {}
        self._hover_active = False
        self._build_ui()
        self.set_theme(self.theme_name)

    def _build_ui(self):
        self.setObjectName("favoriteToolCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.context_menu_requested.emit(self.tool, self.mapToGlobal(pos))
        )
        self.setFixedHeight(self.CARD_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(2)
        top_row.addStretch()

        self.status_label = QLabel("●", self)
        self.status_label.setObjectName("favoriteStatusDot")
        top_row.addWidget(self.status_label, 0, Qt.AlignRight)

        self.star_label = QLabel("★", self)
        self.star_label.setObjectName("favoriteStar")
        top_row.addWidget(self.star_label, 0, Qt.AlignRight)
        root.addLayout(top_row)

        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(8)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self.icon_label.setAlignment(Qt.AlignCenter)
        body_row.addWidget(self.icon_label, 0, Qt.AlignVCenter)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        self.name_label = QLabel(self.tool.get('name', '未命名工具'), self)
        self.name_label.setObjectName("favoriteToolName")
        self.name_label.setWordWrap(False)
        self.name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPixelSize(13)
        self.name_label.setFont(name_font)
        text_col.addWidget(self.name_label)

        desc_text = (self.tool.get('_display_description') or self.tool.get('description') or '').strip()
        self.desc_label = QLabel(desc_text, self)
        self.desc_label.setObjectName("favoriteToolDesc")
        self.desc_label.setWordWrap(True)
        self.desc_label.setMaximumHeight(16)
        self.desc_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.desc_label.setVisible(bool(desc_text))
        text_col.addWidget(self.desc_label)
        text_col.addStretch()

        body_row.addLayout(text_col, 1)
        root.addLayout(body_row)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 0, 0, 0)
        footer_row.setSpacing(4)

        self.type_badge = QLabel(self)
        self.type_badge.setObjectName("favoriteTypeBadge")
        self.type_badge.setAlignment(Qt.AlignCenter)
        self.type_badge.setMinimumWidth(50)
        self.type_badge.setMaximumWidth(78)
        footer_row.addWidget(self.type_badge, 0, Qt.AlignLeft)
        footer_row.addStretch()

        self.run_button = self._create_action_button(QStyle.SP_MediaPlay, 0, primary=False)
        footer_row.addWidget(self.run_button)

        self.terminal_button = self._create_action_button(QStyle.SP_ComputerIcon, 1)
        footer_row.addWidget(self.terminal_button)

        self.directory_button = self._create_action_button(QStyle.SP_DirIcon, 2)
        footer_row.addWidget(self.directory_button)

        root.addLayout(footer_row)

    def _create_action_button(self, icon_type, button_index, primary=False):
        button = QToolButton(self)
        button.setObjectName("favoriteCardAction")
        button.setCursor(Qt.PointingHandCursor)
        button.setProperty("icon_type", int(icon_type))
        button.setProperty("is_primary", bool(primary))
        button.setIcon(self.style().standardIcon(icon_type))
        button.setIconSize(QSize(14, 14))
        button.setFixedSize(30, 26)
        button.clicked.connect(lambda: self.button_clicked.emit(self.tool, button_index))
        return button

    def _secondary_action_buttons(self):
        return (self.terminal_button, self.directory_button)

    def _build_tinted_icon(self, icon_type, color):
        base_icon = self.style().standardIcon(icon_type)
        base_pixmap = base_icon.pixmap(16, 16)
        if base_pixmap.isNull():
            return base_icon

        tinted = QPixmap(base_pixmap.size())
        tinted.fill(Qt.transparent)

        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, base_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()

        return QIcon(tinted)

    def _update_action_button_icons(self, icon_color):
        for button in (self.run_button, self.terminal_button, self.directory_button):
            icon_type = button.property("icon_type")
            if icon_type is None:
                continue
            button.setIcon(self._build_tinted_icon(int(icon_type), icon_color))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if child is None or not isinstance(child, QAbstractButton):
                self.clicked.emit(self.tool)
        super().mouseReleaseEvent(event)

    def set_theme(self, theme_name, palette=None, type_style=None, status_color=None):
        self.theme_name = theme_name or 'dark_green'
        palette = palette or {}
        self._theme_palette = dict(palette)
        type_style = type_style or {}
        status_color = status_color or QColor(220, 38, 38)

        bg = palette.get('card_bg', '#ffffff')
        border = palette.get('card_border', '#d1d5db')
        hover = palette.get('card_hover', '#f8fafc')
        title = palette.get('title', '#1f2937')
        desc = palette.get('desc', '#6b7280')
        button_bg = palette.get('button_bg', '#ffffff')
        button_border = palette.get('button_border', '#d1d5db')
        button_icon = palette.get('button_icon', title)
        button_hover = palette.get('button_hover', '#eff6ff')
        button_hover_border = palette.get('button_hover_border', button_border)
        star = palette.get('star', '#f59e0b')

        self.setStyleSheet(
            f"""
            QFrame#favoriteToolCard {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            QFrame#favoriteToolCard:hover {{
                background: {hover};
            }}
            QLabel#favoriteToolName {{
                color: {title};
                border: none;
                background: transparent;
            }}
            QLabel#favoriteToolDesc {{
                color: {desc};
                border: none;
                background: transparent;
            }}
            QLabel#favoriteStar {{
                color: {star};
                border: none;
                background: transparent;
                font-size: 13px;
            }}
            QLabel#favoriteStatusDot {{
                border: none;
                background: transparent;
                font-size: 11px;
            }}
            QToolButton#favoriteCardAction {{
                background: {button_bg};
                border: 1px solid {button_border};
                border-radius: 9px;
                padding: 2px;
            }}
            QToolButton#favoriteCardAction:hover {{
                background: {button_hover};
                border-color: {button_hover_border};
            }}
            QToolButton#favoriteCardAction:pressed {{
                background: {button_hover};
                border-color: {button_hover_border};
            }}
            """
        )


        self.status_label.setStyleSheet(f"color: {status_color.name()}; border: none; background: transparent;")
        self.star_label.setVisible(bool(self.tool.get('is_favorite', False)))
        self._update_action_button_icons(QColor(button_icon))
        self._update_action_buttons_visibility()

        type_bg = type_style.get('bg', '#f8fafc')
        type_border = type_style.get('border', '#d1d5db')
        type_text = type_style.get('text', '#6b7280')
        self.type_badge.setText(type_style.get('label', '其他'))
        self.type_badge.setStyleSheet(
            f"""
            QLabel#favoriteTypeBadge {{
                color: {type_text};
                background: {type_bg};
                border: 1px solid {type_border};
                border-radius: 10px;
                padding: 1px 8px;
                font-size: 9px;
            }}
            """
        )

        QTimer.singleShot(0, self._refresh_action_buttons_after_polish)

    def _refresh_action_buttons_after_polish(self):
        icon_color = QColor(self._theme_palette.get('button_icon', '#f4fff6'))
        self._update_action_button_icons(icon_color)
        for button in (self.run_button, *self._secondary_action_buttons()):
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _is_dark_theme(self):
        return self.theme_name in ("dark_green", "purple_neon", "red_orange")

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

        if len(self._icon_luminance_cache) > 1024:
            self._icon_luminance_cache.clear()
        self._icon_luminance_cache[cache_key] = result
        return result

    def _needs_icon_contrast_boost(self, pixmap):
        if not self._is_dark_theme() or pixmap.isNull():
            return False

        background_color = QColor(self._theme_palette.get('card_bg', '#173725'))
        if not background_color.isValid():
            background_color = QColor('#173725')

        icon_luminance = self._estimate_pixmap_luminance(pixmap)
        background_luminance = self._color_luminance(background_color)
        contrast_delta = abs(icon_luminance - background_luminance)

        return icon_luminance < 0.48 and contrast_delta < 0.38

    def _compose_boosted_icon_pixmap(self, scaled_pixmap):
        canvas = QPixmap(self.ICON_SIZE, self.ICON_SIZE)
        canvas.fill(Qt.transparent)

        if self.theme_name == "purple_neon":
            fill_color = QColor(255, 255, 255, 40)
            border_color = QColor(195, 169, 255, 150)
        elif self.theme_name == "red_orange":
            fill_color = QColor(255, 255, 255, 36)
            border_color = QColor(255, 176, 103, 150)
        else:
            fill_color = QColor(255, 255, 255, 34)
            border_color = QColor(152, 246, 176, 150)

        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(2, 2, self.ICON_SIZE - 4, self.ICON_SIZE - 4, 9, 9)

        x = (self.ICON_SIZE - scaled_pixmap.width()) // 2
        y = (self.ICON_SIZE - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()
        return canvas

    def refresh_icon(self):
        icon = icon_loader.get_icon(self.tool, theme_name=self.theme_name)
        pixmap = icon.pixmap(self.ICON_SIZE, self.ICON_SIZE)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                self.ICON_SIZE,
                self.ICON_SIZE,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            if self._needs_icon_contrast_boost(scaled_pixmap):
                scaled_pixmap = self._compose_boosted_icon_pixmap(scaled_pixmap)
            self.icon_label.setPixmap(scaled_pixmap)
        else:
            self.icon_label.clear()

        desc_text = (self.tool.get('_display_description') or self.tool.get('description') or '').strip()
        self.desc_label.setText(desc_text)
        self.desc_label.setVisible(bool(desc_text))

    def update_tool(self, tool):
        self.tool = tool or {}
        self.name_label.setText(self.tool.get('name', '未命名工具'))
        desc_text = (self.tool.get('_display_description') or self.tool.get('description') or '').strip()
        self.desc_label.setText(desc_text)
        self.desc_label.setVisible(bool(desc_text))
        self._update_action_buttons_visibility()

    def get_icon_cache_key(self):
        return get_icon_cache_key(self.tool, theme_name=self.theme_name)

    def _update_action_buttons_visibility(self):
        path = (self.tool.get('path') or '').strip()
        is_web = bool(self.tool.get('is_web_tool', False)) or path.startswith('http://') or path.startswith('https://')
        self.terminal_button.setVisible(not is_web)
        self.directory_button.setVisible(not is_web)


class FavoritesGridContainer(ToolCardActionsMixin, QWidget):
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    tool_order_changed = pyqtSignal(list)
    new_tool_requested = pyqtSignal()

    COLUMN_COUNT = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_theme = 'dark_green'
        self._tools = []
        self._cards = []
        self._cards_by_icon_key = {}
        self._spacer_widget = None
        self._last_stretch_row = -1
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget(self.scroll)
        self.content.setObjectName("favoritesContent")
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(12, 12, 12, 12)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        for column in range(self.COLUMN_COUNT):
            self.grid.setColumnStretch(column, 1)

        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll)

        self.empty_label = QLabel("暂无收藏工具", self.content)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()

        icon_loader.icon_path_ready.connect(self._refresh_cards_for_icon)
        self.apply_theme_styles()

    def _get_theme_palette(self):
        if self.current_theme in ("light", "blue_white"):
            return {
                'page_bg': '#f0f4f8',
                'card_bg': '#ffffff',
                'card_hover': '#f8fafc',
                'card_border': '#d7dee8',
                'title': '#334155',
                'desc': '#64748b',
                'button_bg': '#ffffff',
                'button_border': '#cbd5e1',
                'button_icon': '#475569',
                'button_hover': '#eff6ff',
                'button_hover_border': '#60a5fa',
                'star': '#f59e0b',
            }
        if self.current_theme == "purple_neon":
            return {
                'page_bg': '#141027',
                'card_bg': '#1d1638',
                'card_hover': '#241d45',
                'card_border': '#6f54b0',
                'title': '#efe9ff',
                'desc': '#c5b7eb',
                'button_bg': '#2a204d',
                'button_border': '#8b74cb',
                'button_icon': '#f4efff',
                'button_hover': '#312754',
                'button_hover_border': '#c3a9ff',
                'star': '#c3a9ff',
            }
        if self.current_theme == "red_orange":
            return {
                'page_bg': '#1a1412',
                'card_bg': '#241914',
                'card_hover': '#2d1f18',
                'card_border': '#b36236',
                'title': '#fff1e6',
                'desc': '#e8b39a',
                'button_bg': '#33211a',
                'button_border': '#c77c4a',
                'button_icon': '#fff3ea',
                'button_hover': '#38241b',
                'button_hover_border': '#ffb067',
                'star': '#ffb067',
            }
        return {
            'page_bg': '#102117',
            'card_bg': '#173725',
            'card_hover': '#21432f',
            'card_border': '#6fe787',
            'title': '#f3fff5',
            'desc': '#b7dcc0',
            'button_bg': '#224432',
            'button_border': '#79db8c',
            'button_icon': '#f4fff6',
            'button_hover': '#29503a',
            'button_hover_border': '#98f6b0',
            'star': '#86efac',
        }

    def _get_type_style(self, type_label):
        label = type_label or '其他'
        if self.current_theme in ("light", "blue_white"):
            style = {'text': '#6b7280', 'border': '#d1d5db', 'bg': '#f8fafc'}
            if label == "网页":
                style = {'text': '#2563eb', 'border': '#60a5fa', 'bg': '#eff6ff'}
            elif label == "终端":
                style = {'text': '#166534', 'border': '#4ade80', 'bg': '#dcfce7'}
            elif label == "目录":
                style = {'text': '#b45309', 'border': '#f59e0b', 'bg': '#fff7ed'}
            elif label == "文档":
                style = {'text': '#7c3aed', 'border': '#c084fc', 'bg': '#f5f3ff'}
            elif label == "应用":
                style = {'text': '#155e75', 'border': '#22d3ee', 'bg': '#ecfeff'}
        elif self.current_theme == "purple_neon":
            style = {'text': '#d2ccff', 'border': '#8b74cb', 'bg': '#2b2251'}
            if label == "网页":
                style = {'text': '#bedcff', 'border': '#60a5fa', 'bg': '#26355d'}
            elif label == "终端":
                style = {'text': '#a7f3d0', 'border': '#34d399', 'bg': '#203f3a'}
            elif label == "目录":
                style = {'text': '#fed7aa', 'border': '#fb923c', 'bg': '#4c2f20'}
            elif label == "文档":
                style = {'text': '#e9d5ff', 'border': '#c084fc', 'bg': '#4b2963'}
            elif label == "应用":
                style = {'text': '#ddd6fe', 'border': '#a78bfa', 'bg': '#372c61'}
        elif self.current_theme == "red_orange":
            style = {'text': '#ffe5d2', 'border': '#b36236', 'bg': '#3d261b'}
            if label == "网页":
                style = {'text': '#ffd8b4', 'border': '#ff8a3d', 'bg': '#512f1e'}
            elif label == "终端":
                style = {'text': '#fecaca', 'border': '#f87171', 'bg': '#572424'}
            elif label == "目录":
                style = {'text': '#fde68a', 'border': '#f59e0b', 'bg': '#553623'}
            elif label == "文档":
                style = {'text': '#ffedd5', 'border': '#fdba74', 'bg': '#573321'}
            elif label == "应用":
                style = {'text': '#ffedd5', 'border': '#fb923c', 'bg': '#4e2d1f'}
        else:
            style = {'text': '#bfe4c8', 'border': '#52a567', 'bg': '#1c3c29'}
            if label == "网页":
                style = {'text': '#9df8b6', 'border': '#60dc80', 'bg': '#1f492d'}
            elif label == "终端":
                style = {'text': '#bbffcc', 'border': '#4ade80', 'bg': '#164026'}
            elif label == "目录":
                style = {'text': '#fed7aa', 'border': '#fb923c', 'bg': '#3a261c'}
            elif label == "文档":
                style = {'text': '#dbeafe', 'border': '#38bdf8', 'bg': '#183848'}
            elif label == "应用":
                style = {'text': '#d3f8db', 'border': '#6fe787', 'bg': '#1b412b'}
        style['label'] = label
        return style

    def _get_tool_type_label(self, tool):
        custom_label = (tool.get('type_label') or '').strip()
        if custom_label:
            return custom_label

        path = (tool.get('path') or '').strip()
        is_web = tool.get('is_web_tool', False)
        run_in_terminal = tool.get('run_in_terminal', False)

        if is_web or path.startswith('http://') or path.startswith('https://'):
            return "网页"
        if not path:
            return "其他"
        if path.endswith('/') or path.endswith('\\'):
            return "目录"

        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if ext in ('.txt', '.md', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'):
            return "文档"
        if run_in_terminal or ext in ('.bat', '.cmd', '.ps1', '.sh', '.py', '.vbs'):
            return "终端"
        if ext in ('.exe', '.lnk', '.jar', '.app'):
            return "应用"
        return "文件"

    def _get_status_color(self, tool):
        path_value = (tool.get('path') or '').strip()
        is_web_tool = bool(tool.get('is_web_tool', False))
        if is_web_tool or path_value.startswith('http://') or path_value.startswith('https://'):
            return QColor(34, 197, 94) if path_value else QColor(220, 38, 38)
        if not path_value:
            return QColor(220, 38, 38)
        full_path = path_value if os.path.isabs(path_value) else os.path.abspath(path_value)
        return QColor(34, 197, 94) if os.path.exists(full_path) else QColor(220, 38, 38)

    def _clear_grid(self):
        if self._last_stretch_row >= 0:
            self.grid.setRowStretch(self._last_stretch_row, 0)
            self._last_stretch_row = -1
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if widget is self.empty_label:
                    self.empty_label.hide()
                    continue
                self._unregister_card(widget)
                widget.deleteLater()
        self._cards = []
        self._cards_by_icon_key = {}
        self._spacer_widget = None

    def _rebuild_grid(self):
        self._clear_grid()
        if not self._tools:
            self.empty_label.show()
            self.grid.addWidget(self.empty_label, 0, 0, 1, self.COLUMN_COUNT)
            self.grid.setRowStretch(1, 1)
            self._last_stretch_row = 1
            return

        self.empty_label.hide()
        for index, tool in enumerate(self._tools):
            card = FavoriteToolCard(tool, theme_name=self.current_theme, parent=self.content)
            card.clicked.connect(self.run_tool.emit)
            card.button_clicked.connect(self._handle_tool_button_click)
            card.context_menu_requested.connect(self._show_tool_context_menu)
            self._apply_card_theme(card)

            row = index // self.COLUMN_COUNT
            col = index % self.COLUMN_COUNT
            self.grid.addWidget(card, row, col)
            self._cards.append(card)
            self._register_card(card)

        spacer_row = (len(self._tools) + self.COLUMN_COUNT - 1) // self.COLUMN_COUNT
        self._spacer_widget = QWidget(self.content)
        self._spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid.addWidget(self._spacer_widget, spacer_row, 0, 1, self.COLUMN_COUNT)
        self.grid.setRowStretch(spacer_row, 1)
        self._last_stretch_row = spacer_row

    def _apply_card_theme(self, card):
        type_label = self._get_tool_type_label(card.tool)
        card.set_theme(
            self.current_theme,
            palette=self._get_theme_palette(),
            type_style=self._get_type_style(type_label),
            status_color=self._get_status_color(card.tool),
        )
        card.refresh_icon()

    def _register_card(self, card):
        icon_key = card.get_icon_cache_key()
        if not icon_key:
            return
        cards = self._cards_by_icon_key.setdefault(icon_key, [])
        if card not in cards:
            cards.append(card)

    def _unregister_card(self, card, icon_key=None):
        resolved_icon_key = icon_key if icon_key is not None else getattr(card, "get_icon_cache_key", lambda: None)()
        if not resolved_icon_key:
            return
        cards = self._cards_by_icon_key.get(resolved_icon_key, [])
        if card in cards:
            cards.remove(card)
        if not cards and resolved_icon_key in self._cards_by_icon_key:
            self._cards_by_icon_key.pop(resolved_icon_key, None)

    def _reindex_card_icon(self, card, previous_icon_key=None):
        self._unregister_card(card, previous_icon_key)
        self._register_card(card)

    def _refresh_cards_for_icon(self, icon_key):
        for card in list(self._cards_by_icon_key.get(icon_key, [])):
            try:
                card.refresh_icon()
            except Exception:
                continue

    def _update_cards_in_place(self, tools_data):
        for card, tool in zip(self._cards, tools_data):
            previous_icon_key = card.get_icon_cache_key()
            card.update_tool(tool)
            self._apply_card_theme(card)
            self._reindex_card_icon(card, previous_icon_key)

    def _handle_tool_button_click(self, tool, button_index):
        if not tool:
            return

        if button_index == 0:
            self.run_tool.emit(tool)
            return

        if tool.get('is_web_tool', False):
            return

        target_dir = self.resolve_tool_target_dir(tool)

        if not target_dir:
            self.warn_missing_tool_target_dir(tool)
            return

        if button_index == 1:
            self.open_command_line(target_dir, tool_data=tool)
        elif button_index == 2:
            self.open_directory(target_dir)

    def _show_tool_context_menu(self, tool, global_pos):
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

        if MarkdownNoteDialog is not None:
            notes_action = menu.addAction("打开笔记")
            notes_action.triggered.connect(lambda: self._open_notes_for_tool(tool))
            menu.addSeparator()

        potential_target_dir = self.resolve_tool_target_dir(tool)

        if potential_target_dir:
            cmd_action = menu.addAction("在此处打开命令行")
            cmd_action.triggered.connect(lambda: self.open_command_line(potential_target_dir, tool_data=tool))

            dir_action = menu.addAction("在此处打开目录")
            dir_action.triggered.connect(lambda: self.open_directory(potential_target_dir))
            menu.addSeparator()

        del_action = menu.addAction("删除工具")
        del_action.triggered.connect(lambda: self.confirm_delete(tool))

        menu.exec_(global_pos)

    def _open_notes_for_tool(self, tool):
        if MarkdownNoteDialog is None:
            QMessageBox.warning(self, "未安装", "笔记功能未能加载。")
            return

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
        reply = QMessageBox.question(
            self,
            '确认删除',
            f"确定要删除工具 \"{tool['name']}\" 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.deleted.emit(tool['id'])

    def set_theme(self, theme_name):
        self.current_theme = theme_name or 'dark_green'
        self.apply_theme_styles()
        for card in self._cards:
            previous_icon_key = card.get_icon_cache_key()
            self._apply_card_theme(card)
            self._reindex_card_icon(card, previous_icon_key)

    def apply_theme_styles(self):
        palette = self._get_theme_palette()
        page_bg = palette.get('page_bg', '#102117')
        self.scroll.setStyleSheet(
            f"""
            QScrollArea {{
                background: {page_bg};
                border: none;
            }}
            QWidget#favoritesContent {{
                background: {page_bg};
            }}
            """
        )
        self.empty_label.setStyleSheet(
            f"color: {palette.get('desc', '#94a3b8')}; background: transparent; border: none; font-size: 14px;"
        )

    def display_tools(self, tools_data):
        next_tools = list(tools_data or [])
        next_ids = [tool.get('id') for tool in next_tools]
        current_ids = [tool.get('id') for tool in self._tools]

        if next_tools and current_ids == next_ids and len(self._cards) == len(next_tools):
            self._tools = next_tools
            self._update_cards_in_place(next_tools)
            return

        self._tools = next_tools
        self._rebuild_grid()

    def get_tool_count(self):
        return len(self._tools)

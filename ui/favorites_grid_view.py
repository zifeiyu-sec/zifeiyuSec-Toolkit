#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""独立的收藏页网格视图。"""
import os
from time import monotonic

from PyQt5.QtCore import Qt, QSize, QPoint, pyqtSignal, QEvent, QTimer, QMimeData
from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap, QImage, QPen, QDrag
from PyQt5.QtWidgets import (
    QAbstractButton,
    QApplication,
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
from core.tool_metadata import infer_display_tool_type_label

try:
    from ui.markdown_note_dialog import MarkdownNoteDialog
except Exception:
    MarkdownNoteDialog = None

from ui.icon_loader import get_icon_cache_key, icon_loader
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


FAVORITE_TOOL_MIME_TYPE = "application/vnd.zifeiyu.favorite-tool-id"


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
        self._drag_start_pos = None
        self._drag_started = False
        self._build_ui()
        self.set_theme(self.theme_name)

    def _build_ui(self):
        self.setObjectName("favoriteToolCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setAcceptDrops(True)
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

        self.run_button = self._create_action_button(
            ACTION_BUTTON_RUN,
            fallback_icon_type=QStyle.SP_MediaPlay,
            primary=True,
            role="primary",
            tooltip="运行工具",
        )
        footer_row.addWidget(self.run_button)

        self.favorite_button = self._create_action_button(
            ACTION_BUTTON_TOGGLE_FAVORITE,
            icon_name=ACTION_ICON_FAVORITE,
            fallback_icon_type=QStyle.SP_DialogYesButton,
            role="favorite",
            tooltip="收藏或取消收藏",
        )
        footer_row.addWidget(self.favorite_button)

        self.notes_button = self._create_action_button(
            ACTION_BUTTON_OPEN_NOTES,
            icon_name=ACTION_ICON_NOTES,
            fallback_icon_type=QStyle.SP_FileDialogContentsView,
            tooltip="打开笔记",
        )
        footer_row.addWidget(self.notes_button)

        self.terminal_button = self._create_action_button(
            ACTION_BUTTON_OPEN_TERMINAL,
            fallback_icon_type=QStyle.SP_ComputerIcon,
            tooltip="在此处打开命令行",
        )
        footer_row.addWidget(self.terminal_button)

        self.directory_button = self._create_action_button(
            ACTION_BUTTON_OPEN_DIRECTORY,
            fallback_icon_type=QStyle.SP_DirIcon,
            tooltip="在此处打开目录",
        )
        footer_row.addWidget(self.directory_button)

        root.addLayout(footer_row)

    def _create_action_button(
        self,
        button_index,
        icon_name=None,
        fallback_icon_type=None,
        primary=False,
        role="secondary",
        tooltip="",
    ):
        button = QToolButton(self)
        button.setObjectName("favoriteCardAction")
        button.setCursor(Qt.PointingHandCursor)
        button.setProperty("icon_name", icon_name or "")
        button.setProperty("fallback_icon_type", int(fallback_icon_type) if fallback_icon_type is not None else -1)
        button.setProperty("is_primary", bool(primary))
        button.setProperty("button_role", role)
        if tooltip:
            button.setToolTip(tooltip)
        button.setIcon(self._resolve_action_button_icon(button))
        button.setIconSize(QSize(14, 14))
        button.setFixedSize(30, 26)
        button.clicked.connect(lambda: self.button_clicked.emit(self.tool, button_index))
        return button

    def _secondary_action_buttons(self):
        return (self.favorite_button, self.notes_button, self.terminal_button, self.directory_button)

    def _resolve_action_button_icon(self, button):
        icon_name = str(button.property("icon_name") or "").strip() or None
        fallback_icon_type = button.property("fallback_icon_type")
        try:
            fallback_icon_type = int(fallback_icon_type)
        except (TypeError, ValueError):
            fallback_icon_type = -1
        if fallback_icon_type < 0:
            fallback_icon_type = None
        return load_tool_card_action_icon(self.style(), icon_name=icon_name, fallback_icon_type=fallback_icon_type)

    def _build_tinted_icon(self, icon, color):
        base_icon = icon if isinstance(icon, QIcon) else QIcon()
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
        for button in (self.run_button, self.favorite_button, self.notes_button, self.terminal_button, self.directory_button):
            base_icon = self._resolve_action_button_icon(button)
            if base_icon.isNull():
                continue
            resolved_color = icon_color
            if bool(button.property("is_primary")):
                resolved_color = QColor(self._theme_palette.get('primary_button_icon', icon_color.name()))
            elif str(button.property("button_role") or "") == "favorite":
                resolved_color = QColor(self._theme_palette.get('star', icon_color.name()))
            button.setIcon(self._build_tinted_icon(base_icon, resolved_color))

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
        button_pressed = palette.get('button_pressed', button_hover)
        primary_button_bg = palette.get('primary_button_bg', button_bg)
        primary_button_border = palette.get('primary_button_border', button_border)
        primary_button_hover = palette.get('primary_button_hover', button_hover)
        hover_border = palette.get('card_hover_border', border)
        star = palette.get('star', '#f59e0b')
        self.name_label.setStyleSheet(f"color: {title}; border: none; background: transparent;")
        self.desc_label.setStyleSheet(f"color: {desc}; border: none; background: transparent;")

        self.setStyleSheet(
            f"""
            QFrame#favoriteToolCard {{
                background: {bg};
                border: 1px solid {border};
                border-radius: 16px;
            }}
            QFrame#favoriteToolCard:hover {{
                background: {hover};
                border-color: {hover_border};
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
                background: {button_pressed};
                border-color: {button_hover_border};
            }}
            QToolButton#favoriteCardAction[is_primary="true"] {{
                background: {primary_button_bg};
                border-color: {primary_button_border};
            }}
            QToolButton#favoriteCardAction[is_primary="true"]:hover {{
                background: {primary_button_hover};
                border-color: {primary_button_border};
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
            fill_color = QColor(45, 7, 67, 72)
            border_color = QColor(255, 207, 92, 166)
        elif self.theme_name == "red_orange":
            fill_color = QColor(255, 255, 255, 32)
            border_color = QColor(255, 218, 228, 104)
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
        cached_theme = str(self.tool.get("_icon_cache_theme", "") or "").strip()
        cached_key = str(self.tool.get("_icon_cache_key", "") or "").strip()
        if cached_key and cached_theme == str(self.theme_name or "").strip():
            return cached_key
        return get_icon_cache_key(self.tool, theme_name=self.theme_name)

    def _update_action_buttons_visibility(self):
        path = (self.tool.get('path') or '').strip()
        is_web = bool(self.tool.get('is_web_tool', False)) or path.startswith('http://') or path.startswith('https://')
        self.favorite_button.setVisible(True)
        self.notes_button.setVisible(True)
        self.terminal_button.setVisible(not is_web)
        self.directory_button.setVisible(not is_web)

    def _child_at_is_action_button(self, pos):
        child = self.childAt(pos)
        return child is not None and isinstance(child, QAbstractButton)

    def _favorite_container(self):
        widget = self.parentWidget()
        while widget is not None:
            if hasattr(widget, "_move_favorite_tool_to_target"):
                return widget
            widget = widget.parentWidget()
        return None

    def _drag_payload_tool_id(self, event):
        mime_data = event.mimeData()
        if mime_data is None or not mime_data.hasFormat(FAVORITE_TOOL_MIME_TYPE):
            return None
        try:
            return bytes(mime_data.data(FAVORITE_TOOL_MIME_TYPE)).decode("utf-8")
        except (TypeError, UnicodeDecodeError):
            return None

    def _can_accept_favorite_drop(self, event):
        source_tool_id = self._drag_payload_tool_id(event)
        target_tool_id = self.tool.get("id")
        return (
            source_tool_id not in (None, "")
            and target_tool_id is not None
            and str(source_tool_id) != str(target_tool_id)
            and self._favorite_container() is not None
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._child_at_is_action_button(event.pos()):
            self._drag_start_pos = QPoint(event.pos())
            self._drag_started = False
        else:
            self._drag_start_pos = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        tool_id = self.tool.get("id")
        if (
            tool_id is None
            or self._drag_start_pos is None
            or not (event.buttons() & Qt.LeftButton)
            or (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance()
        ):
            super().mouseMoveEvent(event)
            return

        self._drag_started = True
        mime_data = QMimeData()
        mime_data.setData(FAVORITE_TOOL_MIME_TYPE, str(tool_id).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        pixmap = self.grab()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
        drag.exec_(Qt.MoveAction)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_started:
            self._drag_started = False
            self._drag_start_pos = None
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            if not self._child_at_is_action_button(event.pos()):
                self.clicked.emit(self.tool)
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        if self._can_accept_favorite_drop(event):
            event.acceptProposedAction()
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if self._can_accept_favorite_drop(event):
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event):
        if not self._can_accept_favorite_drop(event):
            event.ignore()
            return

        container = self._favorite_container()
        source_tool_id = self._drag_payload_tool_id(event)
        if container._move_favorite_tool_to_target(source_tool_id, self.tool.get("id")):
            event.acceptProposedAction()
            return
        event.ignore()


class LegacyFavoritesGridContainer(ToolCardActionsMixin, QWidget):
    run_tool = pyqtSignal(dict)
    edit_requested = pyqtSignal(dict)
    deleted = pyqtSignal(int)
    toggle_favorite = pyqtSignal(int)
    tool_order_changed = pyqtSignal(list)
    new_tool_requested = pyqtSignal()

    MAX_COLUMNS = 4
    MIN_CARD_WIDTH = 250

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.current_theme = 'dark_green'
        self._tools = []
        self._cards = []
        self._cards_by_icon_key = {}
        self._spacer_widget = None
        self._last_stretch_row = -1
        self._current_column_count = self.MAX_COLUMNS
        self._metadata_cache_ttl_seconds = 30.0
        self._path_status_cache = {}
        self._type_label_cache = {}
        self._icon_key_cache = {}
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self)
        self.scroll.setAcceptDrops(True)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget(self.scroll)
        self.content.setAcceptDrops(True)
        self.content.setObjectName("favoritesContent")
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(12, 12, 12, 12)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        self._set_grid_column_stretch(self._current_column_count)

        self.scroll.setWidget(self.content)
        self.scroll.viewport().setAcceptDrops(True)
        self.scroll.viewport().installEventFilter(self)
        self.content.installEventFilter(self)
        root.addWidget(self.scroll)

        self.empty_label = QLabel("暂无收藏工具", self.content)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()

        icon_loader.icon_path_ready.connect(self._refresh_cards_for_icon)
        self.apply_theme_styles()

    def _get_theme_palette(self):
        if self.current_theme == "celadon_mist":
            return {
                'page_bg': 'transparent',
                'card_bg': 'rgba(224,255,255,0.58)',
                'card_hover': 'rgba(204,250,250,0.76)',
                'card_border': 'rgba(137,220,223,0.62)',
                'card_hover_border': 'rgba(17,142,150,0.58)',
                'title': '#104c52',
                'desc': '#446c70',
                'button_bg': 'rgba(226,255,255,0.64)',
                'button_border': 'rgba(135,218,222,0.72)',
                'button_icon': '#14565c',
                'button_hover': 'rgba(206,250,250,0.84)',
                'button_hover_border': 'rgba(17,142,150,0.48)',
                'button_pressed': 'rgba(17,142,150,0.28)',
                'primary_button_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #3ac4c5, stop:1 #108e96)',
                'primary_button_border': 'rgba(69,190,192,0.86)',
                'primary_button_hover': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #54d5d5, stop:1 #129aa2)',
                'primary_button_icon': '#ffffff',
                'star': '#0f8f98',
            }
        if self.current_theme == "blue_white":
            return {
                'page_bg': 'transparent',
                'card_bg': 'rgba(232,249,255,0.62)',
                'card_hover': 'rgba(218,245,255,0.84)',
                'card_border': 'rgba(151,213,244,0.62)',
                'card_hover_border': 'rgba(83,190,238,0.82)',
                'title': '#183149',
                'desc': '#5a7188',
                'button_bg': 'rgba(234,249,255,0.78)',
                'button_border': 'rgba(151,213,244,0.66)',
                'button_icon': '#405871',
                'button_hover': 'rgba(226,247,255,0.98)',
                'button_hover_border': 'rgba(83,190,238,0.82)',
                'button_pressed': 'rgba(224,239,252,0.94)',
                'primary_button_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #71cdff, stop:1 #3f95ea)',
                'primary_button_border': 'rgba(104,206,239,0.86)',
                'primary_button_hover': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #91ddff, stop:1 #4ca5f4)',
                'primary_button_icon': '#ffffff',
                'star': '#f6b74a',
            }
        if self.current_theme == "light":
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
                'page_bg': 'transparent',
                'card_bg': 'rgba(12,2,20,0.70)',
                'card_hover': 'rgba(45,7,67,0.82)',
                'card_border': 'rgba(255,207,92,0.52)',
                'card_hover_border': 'rgba(255,232,147,0.86)',
                'title': '#fff0b8',
                'desc': '#d2b0dd',
                'button_bg': 'rgba(22,3,34,0.70)',
                'button_border': 'rgba(255,207,92,0.48)',
                'button_icon': '#ffe6a3',
                'button_hover': 'rgba(189,58,255,0.30)',
                'button_hover_border': 'rgba(255,232,147,0.86)',
                'button_pressed': 'rgba(255,207,92,0.28)',
                'primary_button_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fff0b8, stop:0.52 #ffcf5c, stop:1 #b6791f)',
                'primary_button_border': 'rgba(255,232,147,0.92)',
                'primary_button_hover': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fff7d6, stop:1 #ffd36a)',
                'primary_button_icon': '#0c0214',
                'star': '#fff0b8',
            }
        if self.current_theme == "red_orange":
            return {
                'page_bg': 'transparent',
                'card_bg': 'rgba(112,0,0,0.74)',
                'card_hover': 'rgba(156,16,8,0.88)',
                'card_border': 'rgba(255,205,92,0.72)',
                'card_hover_border': 'rgba(255,232,147,0.96)',
                'title': '#fff0b8',
                'desc': '#ffc696',
                'button_bg': 'rgba(104,0,0,0.72)',
                'button_border': 'rgba(255,205,92,0.68)',
                'button_icon': '#ffe6b0',
                'button_hover': 'rgba(176,24,12,0.56)',
                'button_hover_border': 'rgba(255,232,147,0.96)',
                'button_pressed': 'rgba(255,205,92,0.34)',
                'primary_button_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fff0b8, stop:0.42 #ffcf5c, stop:0.72 #ff6930, stop:1 #c91f16)',
                'primary_button_border': 'rgba(255,232,147,0.98)',
                'primary_button_hover': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fff0b8, stop:1 #ff7b38)',
                'primary_button_icon': '#240000',
                'star': '#ffdc70',
            }
        return {
            'page_bg': 'transparent',
            'card_bg': 'rgba(0,16,18,0.46)',
            'card_hover': 'rgba(0,32,25,0.62)',
            'card_border': 'rgba(0,229,255,0.52)',
            'card_hover_border': 'rgba(255,51,102,0.42)',
            'title': '#00ff41',
            'desc': '#7cc38b',
            'button_bg': 'rgba(0,18,20,0.58)',
            'button_border': 'rgba(0,229,255,0.46)',
            'button_icon': '#00e5ff',
            'button_hover': 'rgba(0,45,27,0.68)',
            'button_hover_border': 'rgba(0,255,65,0.88)',
            'button_pressed': 'rgba(0,255,65,0.16)',
            'primary_button_bg': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00ff41, stop:1 #00bc3a)',
            'primary_button_border': 'rgba(0,255,65,0.78)',
            'primary_button_hover': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6dff8a, stop:1 #00ff41)',
            'primary_button_icon': '#030a08',
            'star': '#b700ff',
        }

    def _get_type_style(self, type_label):
        label = type_label or '其他'
        if self.current_theme == "celadon_mist":
            style = {'text': '#5f6f6b', 'border': 'rgba(255,255,255,0.58)', 'bg': 'rgba(255,255,255,0.62)'}
            if label == "网页":
                style = {'text': '#4d81a6', 'border': 'rgba(171,213,236,0.88)', 'bg': 'rgba(241,249,252,0.86)'}
            elif label == "终端":
                style = {'text': '#4b7d71', 'border': 'rgba(154,208,198,0.88)', 'bg': 'rgba(240,249,245,0.88)'}
            elif label == "目录":
                style = {'text': '#9f7650', 'border': 'rgba(232,205,168,0.88)', 'bg': 'rgba(252,247,240,0.88)'}
            elif label == "文档":
                style = {'text': '#7b6f9f', 'border': 'rgba(208,198,232,0.88)', 'bg': 'rgba(247,244,252,0.88)'}
            elif label == "应用":
                style = {'text': '#4f8480', 'border': 'rgba(171,220,217,0.88)', 'bg': 'rgba(239,249,248,0.88)'}
        elif self.current_theme == "blue_white":
            style = {'text': '#566b80', 'border': 'rgba(188,214,236,0.92)', 'bg': 'rgba(255,255,255,0.82)'}
            if label == "网页":
                style = {'text': '#2d74ce', 'border': 'rgba(132,190,250,0.92)', 'bg': 'rgba(239,249,255,0.88)'}
            elif label == "终端":
                style = {'text': '#17844e', 'border': 'rgba(116,215,167,0.92)', 'bg': 'rgba(231,250,239,0.88)'}
            elif label == "目录":
                style = {'text': '#4b6fa0', 'border': 'rgba(172,205,236,0.92)', 'bg': 'rgba(239,248,254,0.88)'}
            elif label == "文档":
                style = {'text': '#6f59a2', 'border': 'rgba(198,185,235,0.92)', 'bg': 'rgba(246,243,253,0.88)'}
            elif label == "应用":
                style = {'text': '#2b7a9b', 'border': 'rgba(146,207,232,0.92)', 'bg': 'rgba(235,248,252,0.88)'}
        elif self.current_theme == "light":
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
            style = {'text': '#ffe6a3', 'border': 'rgba(255,207,92,0.96)', 'bg': 'rgba(24,3,38,0.88)'}
            if label == "网页":
                style = {'text': '#fff0b8', 'border': 'rgba(255,207,92,0.96)', 'bg': 'rgba(50,9,72,0.88)'}
            elif label == "终端":
                style = {'text': '#ffd36a', 'border': 'rgba(189,58,255,0.96)', 'bg': 'rgba(52,7,76,0.88)'}
            elif label == "目录":
                style = {'text': '#fff0b8', 'border': 'rgba(255,211,106,0.96)', 'bg': 'rgba(82,43,12,0.88)'}
            elif label == "文档":
                style = {'text': '#ffe6a3', 'border': 'rgba(189,58,255,0.96)', 'bg': 'rgba(70,11,100,0.88)'}
            elif label == "应用":
                style = {'text': '#fff0b8', 'border': 'rgba(255,207,92,0.96)', 'bg': 'rgba(56,8,82,0.88)'}
        elif self.current_theme == "red_orange":
            style = {'text': '#ffe6b0', 'border': 'rgba(255,198,72,0.96)', 'bg': 'rgba(82,0,0,0.88)'}
            if label == "网页":
                style = {'text': '#fff0b8', 'border': 'rgba(255,198,72,0.96)', 'bg': 'rgba(98,6,0,0.88)'}
            elif label == "终端":
                style = {'text': '#ffcd9a', 'border': 'rgba(255,105,48,0.96)', 'bg': 'rgba(105,8,0,0.88)'}
            elif label == "目录":
                style = {'text': '#fff0b8', 'border': 'rgba(255,220,112,0.96)', 'bg': 'rgba(94,36,0,0.88)'}
            elif label == "文档":
                style = {'text': '#ffe6b0', 'border': 'rgba(255,198,72,0.96)', 'bg': 'rgba(92,10,10,0.88)'}
            elif label == "应用":
                style = {'text': '#fff0b8', 'border': 'rgba(255,198,72,0.96)', 'bg': 'rgba(102,4,0,0.88)'}
        else:
            style = {'text': '#00e5ff', 'border': 'rgba(0,229,255,0.92)', 'bg': 'rgba(15,42,47,0.88)'}
            if label == "网页":
                style = {'text': '#00e5ff', 'border': 'rgba(0,229,255,0.92)', 'bg': 'rgba(15,42,47,0.88)'}
            elif label == "终端":
                style = {'text': '#00ff41', 'border': 'rgba(0,255,65,0.92)', 'bg': 'rgba(10,46,42,0.88)'}
            elif label == "目录":
                style = {'text': '#ff8c00', 'border': 'rgba(255,140,0,0.92)', 'bg': 'rgba(42,32,15,0.88)'}
            elif label == "文档":
                style = {'text': '#00e5ff', 'border': 'rgba(0,229,255,0.92)', 'bg': 'rgba(12,39,48,0.88)'}
            elif label == "应用":
                style = {'text': '#aeea00', 'border': 'rgba(0,255,65,0.92)', 'bg': 'rgba(10,46,42,0.88)'}
        style['label'] = label
        return style

    def _resolve_metadata_base_dir(self):
        base_dir = os.fspath(get_runtime_state_root())
        window = self.window() if hasattr(self, "window") else None
        if window is not None:
            base_dir = getattr(window, "config_dir", None) or base_dir
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

    def _path_status_cache_key(self, tool, base_dir):
        return (
            os.path.normcase(os.fspath(base_dir or "")),
            str(tool.get("path") or "").strip(),
            bool(tool.get("is_web_tool", False)),
        )

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

    def _prepare_tool_for_display(self, tool, base_dir):
        if not isinstance(tool, dict):
            return tool

        prepared_tool = dict(tool)
        prepared_tool["_display_type_label"] = self._get_cached_metadata_value(
            self._type_label_cache,
            self._type_label_cache_key(prepared_tool, base_dir),
            lambda tool=prepared_tool: infer_display_tool_type_label(tool, base_dir=base_dir),
            str(prepared_tool.get("_display_type_label") or ""),
        )
        prepared_tool["_is_path_available"] = None
        prepared_tool["_icon_cache_key"] = self._get_cached_metadata_value(
            self._icon_key_cache,
            self._icon_key_cache_key(prepared_tool),
            lambda tool=prepared_tool: get_icon_cache_key(tool, theme_name=self.current_theme),
            "",
        )
        prepared_tool["_icon_cache_theme"] = self.current_theme
        return prepared_tool

    def _prepare_tools_for_display(self, tools_data):
        base_dir = self._resolve_metadata_base_dir()
        return [self._prepare_tool_for_display(tool, base_dir) for tool in (tools_data or [])]

    def _get_tool_type_label(self, tool):
        cached_label = str((tool or {}).get("_display_type_label", "") or "").strip()
        if cached_label:
            return cached_label

        base_dir = os.fspath(get_runtime_state_root())
        window = self.window() if hasattr(self, "window") else None
        if window is not None:
            base_dir = getattr(window, "config_dir", None) or base_dir
        return infer_display_tool_type_label(tool, base_dir=base_dir)

    def _get_status_color(self, tool):
        if "_is_path_available" in (tool or {}):
            status = tool.get("_is_path_available")
            if status is None:
                return QColor(245, 158, 11)
            return QColor(34, 197, 94) if status else QColor(220, 38, 38)
        return QColor(220, 38, 38)

    def eventFilter(self, watched, event):
        if watched is self.scroll.viewport() and event.type() == QEvent.Resize:
            QTimer.singleShot(0, self._update_grid_layout_for_width)
            return super().eventFilter(watched, event)
        if watched in (self.scroll.viewport(), self.content) and event.type() in (
            QEvent.DragEnter,
            QEvent.DragMove,
        ):
            if self._can_accept_container_drop(event):
                event.acceptProposedAction()
                return True
            event.ignore()
            return True
        if watched in (self.scroll.viewport(), self.content) and event.type() == QEvent.Drop:
            if self._handle_container_drop(event):
                return True
            event.ignore()
            return True
        return super().eventFilter(watched, event)

    def _grid_horizontal_spacing(self):
        spacing = self.grid.horizontalSpacing()
        return self.grid.spacing() if spacing < 0 else spacing

    def _available_grid_width(self, viewport_width=None):
        if viewport_width is None:
            viewport_width = self.scroll.viewport().width()
        margins = self.grid.contentsMargins()
        return max(1, int(viewport_width) - margins.left() - margins.right())

    def _resolve_column_count(self, viewport_width=None):
        available_width = self._available_grid_width(viewport_width)
        spacing = self._grid_horizontal_spacing()
        for columns in range(self.MAX_COLUMNS, 1, -1):
            usable_width = available_width - (columns - 1) * spacing
            if usable_width // columns >= self.MIN_CARD_WIDTH:
                return columns
        return 1

    def _set_grid_column_stretch(self, column_count):
        active_columns = max(1, int(column_count))
        for column in range(self.MAX_COLUMNS):
            self.grid.setColumnStretch(column, 1 if column < active_columns else 0)
            self.grid.setColumnMinimumWidth(column, 0)

    def _update_grid_layout_for_width(self, force=False):
        next_columns = self._resolve_column_count()
        if not force and next_columns == self._current_column_count:
            return
        self._current_column_count = next_columns
        self._layout_current_cards()

    def _clear_grid(self, delete_cards=True):
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
                if widget is self._spacer_widget:
                    widget.deleteLater()
                    continue
                if delete_cards:
                    self._unregister_card(widget)
                    widget.deleteLater()
        if delete_cards:
            self._cards = []
            self._cards_by_icon_key = {}
        self._spacer_widget = None

    def _rebuild_grid(self):
        self._clear_grid()
        for index, tool in enumerate(self._tools):
            card = FavoriteToolCard(tool, theme_name=self.current_theme, parent=self.content)
            card.clicked.connect(self.run_tool.emit)
            card.button_clicked.connect(self._handle_tool_button_click)
            card.context_menu_requested.connect(self._show_tool_context_menu)
            self._apply_card_theme(card)
            self._cards.append(card)
            self._register_card(card)

        self._update_grid_layout_for_width(force=True)

    def _tool_id_key(self, tool_id):
        return str(tool_id) if tool_id is not None else ""

    def _find_tool_index_by_id(self, tool_id):
        target_key = self._tool_id_key(tool_id)
        if not target_key:
            return -1
        for index, tool in enumerate(self._tools):
            if self._tool_id_key(tool.get("id")) == target_key:
                return index
        return -1

    def _ordered_tool_ids(self):
        return [tool.get("id") for tool in self._tools if tool.get("id") is not None]

    def _drag_payload_tool_id(self, event):
        mime_data = event.mimeData()
        if mime_data is None or not mime_data.hasFormat(FAVORITE_TOOL_MIME_TYPE):
            return None
        try:
            return bytes(mime_data.data(FAVORITE_TOOL_MIME_TYPE)).decode("utf-8")
        except (TypeError, UnicodeDecodeError):
            return None

    def _can_accept_container_drop(self, event):
        source_tool_id = self._drag_payload_tool_id(event)
        return source_tool_id not in (None, "") and self._find_tool_index_by_id(source_tool_id) >= 0

    def _handle_container_drop(self, event):
        if not self._can_accept_container_drop(event):
            return False
        source_tool_id = self._drag_payload_tool_id(event)
        if self._move_favorite_tool_to_end(source_tool_id):
            event.acceptProposedAction()
            return True
        return False

    def _move_favorite_tool(self, source_index, insert_index):
        if source_index < 0 or source_index >= len(self._tools):
            return False

        tool = self._tools.pop(source_index)
        insert_index = max(0, min(int(insert_index), len(self._tools)))
        self._tools.insert(insert_index, tool)

        if len(self._cards) == len(self._tools):
            card = self._cards.pop(source_index)
            self._cards.insert(min(insert_index, len(self._cards)), card)
            self._layout_current_cards()
        else:
            self._rebuild_grid()

        self.tool_order_changed.emit(self._ordered_tool_ids())
        return True

    def _move_favorite_tool_to_target(self, source_tool_id, target_tool_id):
        source_index = self._find_tool_index_by_id(source_tool_id)
        target_index = self._find_tool_index_by_id(target_tool_id)
        if source_index < 0 or target_index < 0 or source_index == target_index:
            return False
        return self._move_favorite_tool(source_index, target_index)

    def _move_favorite_tool_to_end(self, source_tool_id):
        source_index = self._find_tool_index_by_id(source_tool_id)
        if source_index < 0 or source_index == len(self._tools) - 1:
            return False
        return self._move_favorite_tool(source_index, len(self._tools) - 1)

    def _layout_current_cards(self):
        self._clear_grid(delete_cards=False)
        column_count = self._resolve_column_count()
        self._current_column_count = column_count
        self._set_grid_column_stretch(column_count)

        if not self._cards:
            self.empty_label.show()
            self.grid.addWidget(self.empty_label, 0, 0, 1, column_count)
            self.grid.setRowStretch(1, 1)
            self._last_stretch_row = 1
            return

        self.empty_label.hide()
        for index, card in enumerate(self._cards):
            row = index // column_count
            col = index % column_count
            self.grid.addWidget(card, row, col)

        spacer_row = (len(self._cards) + column_count - 1) // column_count
        self._spacer_widget = QWidget(self.content)
        self._spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.grid.addWidget(self._spacer_widget, spacer_row, 0, 1, column_count)
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

        if button_index == ACTION_BUTTON_RUN:
            self.run_tool.emit(tool)
            return

        if button_index == ACTION_BUTTON_TOGGLE_FAVORITE:
            tool_id = tool.get('id')
            if tool_id is not None:
                self.toggle_favorite.emit(tool_id)
            return

        if button_index == ACTION_BUTTON_OPEN_NOTES:
            self._open_notes_for_tool(tool)
            return

        if tool.get('is_web_tool', False):
            return

        target_dir = self.resolve_tool_target_dir(tool)

        if not target_dir:
            self.warn_missing_tool_target_dir(tool)
            return

        if button_index == ACTION_BUTTON_OPEN_TERMINAL:
            self.open_command_line(target_dir, tool_data=tool)
        elif button_index == ACTION_BUTTON_OPEN_DIRECTORY:
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
        next_tools = self._prepare_tools_for_display(tools_data)
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


from ui.tool_model_view import ToolCardContainer


class FavoritesGridContainer(ToolCardContainer):
    """Virtualized favorites grid backed by QListView/Delegate."""

    MAX_COLUMNS = 4
    MIN_CARD_WIDTH = 250
    LAYOUT_PRESETS = {
        "main": {
            "preferred_columns": 4,
            "max_columns": MAX_COLUMNS,
            "min_card_width": MIN_CARD_WIDTH,
            "max_card_width": None,
        },
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.card_height = 116
        self._tools = self.model.tools()
        self._cards = []
        self.update_card_layout(force=True)

    def _resolve_column_count(self, viewport_width=None):
        if viewport_width is None:
            viewport_width = self.view.viewport().width()
        return self._resolve_columns(
            viewport_width,
            self.view.spacing(),
            self._get_layout_preset(),
        )

    def display_tools(self, tools_data):
        super().display_tools(tools_data)
        self._tools = self.model.tools()
        self._cards = []

    def get_tool_count(self):
        return len(self.model.tools())

    def set_theme(self, theme_name):
        super().set_theme(theme_name or "dark_green")

    def _tool_id_key(self, tool_id):
        return str(tool_id) if tool_id is not None else ""

    def _find_tool_index_by_id(self, tool_id):
        target_key = self._tool_id_key(tool_id)
        if not target_key:
            return -1
        for index, tool in enumerate(self.model.tools()):
            if self._tool_id_key(tool.get("id")) == target_key:
                return index
        return -1

    def _ordered_tool_ids(self):
        return [tool.get("id") for tool in self.model.tools() if tool.get("id") is not None]

    def _replace_model_tools(self, tools):
        self.model.beginResetModel()
        self.model._tools = list(tools or [])
        self.model.endResetModel()
        self._tools = self.model.tools()
        self.view.viewport().update()

    def _move_favorite_tool(self, source_index, insert_index):
        tools = list(self.model.tools())
        if source_index < 0 or source_index >= len(tools):
            return False

        tool = tools.pop(source_index)
        insert_index = max(0, min(int(insert_index), len(tools)))
        tools.insert(insert_index, tool)
        self._replace_model_tools(tools)
        self.tool_order_changed.emit(self._ordered_tool_ids())
        return True

    def _move_favorite_tool_to_target(self, source_tool_id, target_tool_id):
        source_index = self._find_tool_index_by_id(source_tool_id)
        target_index = self._find_tool_index_by_id(target_tool_id)
        if source_index < 0 or target_index < 0 or source_index == target_index:
            return False
        return self._move_favorite_tool(source_index, target_index)

    def _move_favorite_tool_to_end(self, source_tool_id):
        source_index = self._find_tool_index_by_id(source_tool_id)
        if source_index < 0 or source_index == len(self.model.tools()) - 1:
            return False
        return self._move_favorite_tool(source_index, len(self.model.tools()) - 1)

    def _handle_tool_button_click(self, tool, button_index):
        if not tool:
            return

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

        path = (tool.get("path") or "").strip()
        if bool(tool.get("is_web_tool", False)) or path.startswith(("http://", "https://")):
            return

        target_dir = self.resolve_tool_target_dir(tool)
        if not target_dir:
            self.warn_missing_tool_target_dir(tool)
            return

        if button_index == ACTION_BUTTON_OPEN_TERMINAL:
            self.open_command_line(target_dir, tool_data=tool)
        elif button_index == ACTION_BUTTON_OPEN_DIRECTORY:
            self.open_directory(target_dir)

    def _apply_card_theme(self, card):
        palette = {
            "card_bg": "rgba(0,16,18,0.46)",
            "card_hover": "rgba(0,32,25,0.62)",
            "card_border": "rgba(0,229,255,0.52)",
            "card_hover_border": "rgba(255,51,102,0.42)",
            "title": "#00ff41",
            "desc": "#7cc38b",
            "button_bg": "rgba(0,18,20,0.58)",
            "button_border": "rgba(0,229,255,0.46)",
            "button_icon": "#00e5ff",
            "button_hover": "rgba(0,45,27,0.68)",
            "button_hover_border": "rgba(0,255,65,0.88)",
            "button_pressed": "rgba(0,255,65,0.16)",
            "primary_button_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00ff41, stop:1 #00bc3a)",
            "primary_button_border": "rgba(0,255,65,0.78)",
            "primary_button_hover": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #6dff8a, stop:1 #00ff41)",
            "primary_button_icon": "#030a08",
            "star": "#b700ff",
        }
        card.set_theme(
            self.current_theme,
            palette=palette,
            type_style={"label": "应用"},
            status_color=QColor(245, 158, 11),
        )
        card.refresh_icon()

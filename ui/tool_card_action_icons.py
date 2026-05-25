import os

from PyQt5.QtGui import QIcon

from core.runtime_paths import resolve_icon_path_value


ACTION_BUTTON_RUN = 0
ACTION_BUTTON_OPEN_TERMINAL = 1
ACTION_BUTTON_OPEN_DIRECTORY = 2
ACTION_BUTTON_TOGGLE_FAVORITE = 3
ACTION_BUTTON_OPEN_NOTES = 4

ACTION_ICON_FAVORITE = "tool_favorite.svg"
ACTION_ICON_NOTES = "tool_notes.svg"

_ACTION_ICON_CACHE = {}


def load_tool_card_action_icon(style=None, icon_name=None, fallback_icon_type=None):
    if icon_name:
        icon_path = resolve_icon_path_value(icon_name)
        if icon_path is not None:
            cache_key = os.fspath(icon_path)
            icon = _ACTION_ICON_CACHE.get(cache_key)
            if icon is None:
                icon = QIcon(cache_key)
                if not icon.isNull():
                    _ACTION_ICON_CACHE[cache_key] = icon
            if not icon.isNull():
                return icon

    if style is not None and fallback_icon_type is not None:
        return style.standardIcon(fallback_icon_type)

    return QIcon()

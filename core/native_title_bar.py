from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36


TITLE_BAR_COLORS = {
    "dark_green": {
        "caption": "#07100f",
        "text": "#00ff41",
        "border": "#00e5ff",
        "dark": True,
    },
    "blue_white": {
        "caption": "#d8f4fb",
        "text": "#183149",
        "border": "#97d5f4",
        "dark": False,
    },
    "celadon_mist": {
        "caption": "#cceeee",
        "text": "#104c52",
        "border": "#89dcdf",
        "dark": False,
    },
    "purple_neon": {
        "caption": "#160322",
        "text": "#ffe893",
        "border": "#ffcf5c",
        "dark": True,
    },
    "red_orange": {
        "caption": "#700000",
        "text": "#fff4cc",
        "border": "#ffd260",
        "dark": True,
    },
    "light": {
        "caption": "#f0f4f8",
        "text": "#334155",
        "border": "#cbd5e1",
        "dark": False,
    },
}


def _hex_to_colorref(value: str) -> int:
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"Invalid color value: {value!r}")
    red = int(text[0:2], 16)
    green = int(text[2:4], 16)
    blue = int(text[4:6], 16)
    return red | (green << 8) | (blue << 16)


def _set_dwm_attribute(hwnd: int, attribute: int, value: int) -> bool:
    data = ctypes.c_int(value)
    result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
        wintypes.HWND(hwnd),
        wintypes.DWORD(attribute),
        ctypes.byref(data),
        ctypes.sizeof(data),
    )
    return result == 0


def resolve_title_bar_colors(theme_name: str | None) -> dict:
    return dict(TITLE_BAR_COLORS.get(theme_name, TITLE_BAR_COLORS["dark_green"]))


def apply_native_title_bar_theme(window, theme_name: str | None) -> bool:
    """Apply theme colors to the native Windows title bar when DWM supports it."""
    if not sys.platform.startswith("win"):
        return False
    if window is None:
        return False

    try:
        hwnd = int(window.winId())
    except Exception:
        return False
    if not hwnd:
        return False

    colors = resolve_title_bar_colors(theme_name)
    applied = False

    try:
        dark_value = 1 if colors.get("dark") else 0
        applied = _set_dwm_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, dark_value) or applied
    except Exception:
        pass

    for attribute, color_key in (
        (DWMWA_CAPTION_COLOR, "caption"),
        (DWMWA_TEXT_COLOR, "text"),
        (DWMWA_BORDER_COLOR, "border"),
    ):
        try:
            colorref = _hex_to_colorref(colors[color_key])
            applied = _set_dwm_attribute(hwnd, attribute, colorref) or applied
        except Exception:
            continue

    return applied

from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication, QWidget


BASE_DESIGN_WIDTH = 1536
BASE_DESIGN_HEIGHT = 864
BASE_DIALOG_WIDTH = 760
BASE_DIALOG_HEIGHT = 720
MIN_SCALE = 0.85
MAX_SCALE = 1.25


@dataclass(frozen=True)
class UiScaleMetrics:
    scale: float
    width: int
    height: int


def clamp_scale(scale: float) -> float:
    return max(MIN_SCALE, min(MAX_SCALE, float(scale)))


def _available_screen_geometry(widget: QWidget | None = None):
    app = QApplication.instance()
    if app is None:
        return None

    screen = None
    if widget is not None:
        window_handle = widget.windowHandle() if hasattr(widget, "windowHandle") else None
        if window_handle is not None:
            screen = window_handle.screen()
        if screen is None:
            screen = widget.screen() if hasattr(widget, "screen") else None
    if screen is None:
        screen = app.primaryScreen()
    if screen is None:
        return None
    return screen.availableGeometry()


def metrics_for_geometry(width: int, height: int, base_width: int = BASE_DESIGN_WIDTH, base_height: int = BASE_DESIGN_HEIGHT) -> UiScaleMetrics:
    safe_width = max(1, int(width))
    safe_height = max(1, int(height))
    scale = clamp_scale(min(safe_width / max(1, base_width), safe_height / max(1, base_height)))
    return UiScaleMetrics(scale=scale, width=safe_width, height=safe_height)


def metrics_for_widget(widget: QWidget | None = None, base_width: int = BASE_DESIGN_WIDTH, base_height: int = BASE_DESIGN_HEIGHT) -> UiScaleMetrics:
    geometry = _available_screen_geometry(widget)
    if geometry is None:
        return UiScaleMetrics(scale=1.0, width=base_width, height=base_height)
    return metrics_for_geometry(geometry.width(), geometry.height(), base_width=base_width, base_height=base_height)


def scaled(value: int | float, scale: float) -> int:
    return max(1, int(round(float(value) * float(scale))))


def scaled_size(width: int | float, height: int | float, scale: float) -> QSize:
    return QSize(scaled(width, scale), scaled(height, scale))


def preferred_main_window_geometry(widget: QWidget | None = None, width_ratio: float = 0.8, height_ratio: float = 0.8):
    geometry = _available_screen_geometry(widget)
    if geometry is None:
        fallback_width = int(BASE_DESIGN_WIDTH * width_ratio)
        fallback_height = int(BASE_DESIGN_HEIGHT * height_ratio)
        return 0, 0, fallback_width, fallback_height

    width = max(scaled(1100, MIN_SCALE), int(geometry.width() * width_ratio))
    height = max(scaled(700, MIN_SCALE), int(geometry.height() * height_ratio))
    width = min(width, geometry.width())
    height = min(height, geometry.height())
    x = geometry.x() + max(0, (geometry.width() - width) // 2)
    y = geometry.y() + max(0, (geometry.height() - height) // 2)
    return x, y, width, height


def preferred_dialog_size(widget: QWidget | None = None, base_width: int = BASE_DIALOG_WIDTH, base_height: int = BASE_DIALOG_HEIGHT) -> QSize:
    metrics = metrics_for_widget(widget, base_width=BASE_DESIGN_WIDTH, base_height=BASE_DESIGN_HEIGHT)
    return scaled_size(base_width, base_height, metrics.scale)

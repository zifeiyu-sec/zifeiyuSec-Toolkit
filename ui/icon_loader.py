import hashlib
import os
from pathlib import Path

from PyQt5.QtCore import QFileInfo, QObject, QRunnable, QSize, QThreadPool, pyqtSignal
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtWidgets import QFileIconProvider

from core.runtime_paths import ensure_runtime_dir, resolve_icon_path_value


LIGHT_DEFAULT_ICON_NAME = 'write-github.svg'
DARK_DEFAULT_ICON_NAME = 'black-github.png'
LEGACY_DEFAULT_ICON_NAME = 'github_1_1_1.svg'
DEFAULT_ICON_NAME = LIGHT_DEFAULT_ICON_NAME
EXECUTABLE_ICON_SUFFIXES = {'.exe'}
THEME_DARK_SET = {'dark_green', 'purple_neon', 'red_orange'}
ADAPTIVE_DEFAULT_ICON_ALIASES = {
    '',
    'default_icon',
    LEGACY_DEFAULT_ICON_NAME,
    'github_1_1_1',
}
EXECUTABLE_ICON_FALLBACK_NAMES = ADAPTIVE_DEFAULT_ICON_ALIASES.union({
    LIGHT_DEFAULT_ICON_NAME,
    'write-github',
    'white-github.svg',
    'white-github',
    DARK_DEFAULT_ICON_NAME,
    'black-github',
    'favicon.ico',
    'fox.ico',
})


def _normalize_icon_alias_key(value):
    text = str(value or '').strip().casefold().replace('\\', '/')
    if not text:
        return ''
    return os.path.basename(text)


def _is_adaptive_default_icon_value(value):
    normalized = _normalize_icon_alias_key(value)
    if normalized in ADAPTIVE_DEFAULT_ICON_ALIASES:
        return True
    return str(value or '').strip().casefold() in ADAPTIVE_DEFAULT_ICON_ALIASES


def _resolve_theme_default_icon_name(theme_name=None):
    theme = str(theme_name or '').strip().casefold()
    return DARK_DEFAULT_ICON_NAME if theme in THEME_DARK_SET else LIGHT_DEFAULT_ICON_NAME


def _resolve_theme_default_icon_path(theme_name=None):
    preferred_name = _resolve_theme_default_icon_name(theme_name)
    preferred_path = resolve_icon_path(preferred_name)
    if preferred_path:
        return preferred_path

    fallback_name = LIGHT_DEFAULT_ICON_NAME if preferred_name == DARK_DEFAULT_ICON_NAME else DARK_DEFAULT_ICON_NAME
    fallback_path = resolve_icon_path(fallback_name)
    if fallback_path:
        return fallback_path

    legacy_path = resolve_icon_path(LEGACY_DEFAULT_ICON_NAME)
    if legacy_path:
        return legacy_path
    return resolve_icon_path('favicon.ico')


def resolve_icon_path(path):
    """Resolve icon path across runtime resources and absolute paths."""
    if not path:
        return None

    icon_text = str(path).strip()
    if not icon_text:
        return None

    resolved = resolve_icon_path_value(icon_text)
    return os.fspath(resolved) if resolved else None


def _normalize_tool_icon_value(tool):
    if not isinstance(tool, dict):
        return ""
    return str(tool.get('icon') or tool.get('icon_path') or '').strip()


def _resolve_tool_executable_path(tool):
    if not isinstance(tool, dict):
        return None
    if bool(tool.get('is_web_tool', False)):
        return None

    path_text = str(tool.get('path') or '').strip()
    if not path_text or path_text.startswith(('http://', 'https://')):
        return None

    executable_path = os.path.abspath(path_text)
    if not os.path.isfile(executable_path):
        return None
    if Path(executable_path).suffix.casefold() not in EXECUTABLE_ICON_SUFFIXES:
        return None

    return executable_path


def _should_prioritize_executable_icon(tool):
    executable_path = _resolve_tool_executable_path(tool)
    if not executable_path:
        return False

    icon_value = _normalize_tool_icon_value(tool)
    if not icon_value:
        return True
    if icon_value.casefold() in EXECUTABLE_ICON_FALLBACK_NAMES:
        return True
    return resolve_icon_path(icon_value) is None


def _build_executable_icon_cache_path(executable_path):
    try:
        stat = os.stat(executable_path)
    except OSError:
        return None

    digest = hashlib.sha1(os.path.normcase(executable_path).encode('utf-8', errors='ignore')).hexdigest()[:16]
    cache_dir = ensure_runtime_dir('resources', 'icons', 'exe_cache')
    return os.fspath(cache_dir / f"exe_{digest}_{stat.st_size}_{stat.st_mtime_ns}.png")


def _resolve_tool_icon_cache_key(tool, theme_name=None):
    executable_path = _resolve_tool_executable_path(tool)
    if executable_path and _should_prioritize_executable_icon(tool):
        cache_path = _build_executable_icon_cache_path(executable_path)
        if cache_path:
            return cache_path

    icon_value = _normalize_tool_icon_value(tool)
    if _is_adaptive_default_icon_value(icon_value):
        return _resolve_theme_default_icon_path(theme_name)

    explicit_icon = resolve_icon_path(icon_value)
    if explicit_icon:
        return explicit_icon

    if not icon_value:
        return _resolve_theme_default_icon_path(theme_name)
    return explicit_icon


def get_icon_cache_key(path, theme_name=None):
    """Return a normalized cache key for icon lookups."""
    if isinstance(path, dict):
        return _resolve_tool_icon_cache_key(path, theme_name=theme_name)

    if _is_adaptive_default_icon_value(path):
        return _resolve_theme_default_icon_path(theme_name)
    return resolve_icon_path(path)


class LoaderSignals(QObject):
    """Signals used by worker threads."""

    loaded = pyqtSignal(str, QImage)


class IconWorker(QRunnable):
    """Background worker for image loading."""

    def __init__(self, path, signals):
        super().__init__()
        self.path = path
        self.signals = signals

    def run(self):
        if os.path.exists(self.path):
            image = QImage(self.path)
        else:
            image = QImage()
        self.signals.loaded.emit(self.path, image)


class AsyncIconLoader(QObject):
    """Singleton async icon loader."""

    _instance = None
    icon_ready = pyqtSignal()
    icon_path_ready = pyqtSignal(str)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncIconLoader, cls).__new__(cls)
            QObject.__init__(cls._instance)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.cache = {}
        self.loading = set()
        self.signals = LoaderSignals()
        self.signals.loaded.connect(self._on_loaded)
        self.pool = QThreadPool.globalInstance()
        self._default_icon = None
        self._dynamic_failures = set()
        self._file_icon_provider = QFileIconProvider()

    @property
    def default_icon(self):
        if self._default_icon is None:
            self._default_icon = QIcon(_resolve_theme_default_icon_path(None) or "")
            if self._default_icon.isNull():
                # Fallback for environments where SVG loading fails.
                self._default_icon = QIcon(resolve_icon_path('favicon.ico') or "")
            if self._default_icon.isNull():
                self._default_icon = QIcon()
        return self._default_icon

    def get_icon(self, path, theme_name=None):
        if isinstance(path, dict):
            dynamic_icon_key = get_icon_cache_key(path, theme_name=theme_name)
            if dynamic_icon_key and _should_prioritize_executable_icon(path):
                if dynamic_icon_key in self.cache:
                    return self.cache[dynamic_icon_key]
                if os.path.exists(dynamic_icon_key):
                    return self._get_icon_from_path(dynamic_icon_key)

                extracted_icon = self._extract_executable_icon(path, dynamic_icon_key)
                if extracted_icon is not None:
                    return extracted_icon

                explicit_icon_path = resolve_icon_path(_normalize_tool_icon_value(path))
                return self._get_icon_from_path(explicit_icon_path)

            return self._get_icon_from_path(dynamic_icon_key)

        return self._get_icon_from_path(get_icon_cache_key(path, theme_name=theme_name))

    def _get_icon_from_path(self, full_path):
        if not full_path:
            return self.default_icon

        if full_path in self.cache:
            return self.cache[full_path]

        if full_path not in self.loading:
            self.loading.add(full_path)
            self.pool.start(IconWorker(full_path, self.signals))

        return self.default_icon

    def _extract_executable_icon(self, tool, target_path):
        if not target_path or target_path in self._dynamic_failures:
            return None

        executable_path = _resolve_tool_executable_path(tool)
        if not executable_path:
            return None

        try:
            icon = self._file_icon_provider.icon(QFileInfo(executable_path))
            if icon.isNull():
                self._dynamic_failures.add(target_path)
                return None

            sizes = icon.availableSizes()
            if sizes:
                best_size = max(
                    sizes,
                    key=lambda size: (size.width() * size.height(), size.width(), size.height()),
                )
            else:
                best_size = QSize(64, 64)

            width = max(48, best_size.width())
            height = max(48, best_size.height())
            pixmap = icon.pixmap(QSize(width, height))
            if pixmap.isNull():
                self._dynamic_failures.add(target_path)
                return None

            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            if not pixmap.save(target_path, "PNG"):
                self._dynamic_failures.add(target_path)
                return None

            extracted_icon = QIcon(pixmap)
            self.cache[target_path] = extracted_icon
            self.icon_path_ready.emit(target_path)
            self.icon_ready.emit()
            return extracted_icon
        except Exception:
            self._dynamic_failures.add(target_path)
            return None

    def _on_loaded(self, path, image):
        if not image.isNull():
            self.cache[path] = QIcon(QPixmap.fromImage(image))
        else:
            self.cache[path] = self.default_icon

        self.loading.discard(path)
        self.icon_path_ready.emit(path)
        self.icon_ready.emit()

    def shutdown(self):
        try:
            self.pool.clear()
            self.pool.waitForDone(500)
        except Exception:
            pass


icon_loader = AsyncIconLoader()

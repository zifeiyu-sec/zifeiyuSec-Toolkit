import hashlib
import os
from pathlib import Path

from PyQt5.QtCore import QFileInfo, QObject, QRunnable, QSize, QThreadPool, QTimer, QCoreApplication, pyqtSignal
from PyQt5.QtGui import QIcon, QImage, QPixmap
from PyQt5.QtWidgets import QFileIconProvider

from core.auto_icon_resolver import (
    clear_auto_icon_index_cache,
    get_tool_icon_identity,
    get_web_icon_download_request,
    mark_auto_icon_failure,
    flush_auto_icon_index,
    record_auto_icon_path,
    resolve_cached_auto_icon_path,
    resolve_known_tool_icon_path,
    resolve_local_sidecar_icon_path,
)
from core.icon_resolution_service import IconSource, icon_resolution_service
from core.runtime_paths import ensure_runtime_dir, resolve_icon_path_value
from ui.favicon_downloader import FaviconDownloader


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
    LIGHT_DEFAULT_ICON_NAME,
    'write-github',
    'white-github.svg',
    'white-github',
    DARK_DEFAULT_ICON_NAME,
    'black-github',
    'github.com_favicon.ico',
    'github.com_favicon',
}
EXECUTABLE_ICON_FALLBACK_NAMES = ADAPTIVE_DEFAULT_ICON_ALIASES.union({
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
    return icon_resolution_service.default_icon_path(theme_name)


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
    if Path(path_text).suffix.casefold() not in EXECUTABLE_ICON_SUFFIXES:
        return None

    executable_path = os.path.abspath(path_text)
    if not os.path.isfile(executable_path):
        return None

    return executable_path


def _looks_like_executable_tool_path(tool):
    if not isinstance(tool, dict):
        return False
    if bool(tool.get('is_web_tool', False)):
        return False

    path_text = str(tool.get('path') or '').strip()
    if not path_text or path_text.startswith(('http://', 'https://', '\\\\', '//')):
        return False
    return Path(path_text).suffix.casefold() in EXECUTABLE_ICON_SUFFIXES


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


def _should_prioritize_executable_icon_value(tool):
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


def _build_executable_icon_cache_path_from_text(path_text):
    text = str(path_text or "").strip()
    if not text:
        return None
    digest = hashlib.sha1(os.path.normcase(os.path.abspath(text)).encode('utf-8', errors='ignore')).hexdigest()[:16]
    cache_dir = ensure_runtime_dir('resources', 'icons', 'exe_cache')
    return os.fspath(cache_dir / f"exe_{digest}.png")


def _get_precomputed_icon_cache_key(tool, theme_name=None):
    if not isinstance(tool, dict):
        return ""

    cached_theme = str(tool.get("_icon_cache_theme", "") or "").strip()
    if cached_theme and cached_theme != str(theme_name or "").strip():
        return ""

    cached_key = str(tool.get("_icon_cache_key", "") or "").strip()
    return cached_key


def _looks_like_executable_icon_cache_path(path):
    text = str(path or "").strip()
    if not text:
        return False

    normalized = text.replace("\\", "/").casefold()
    return "/exe_cache/exe_" in normalized and normalized.endswith(".png")


def _resolve_tool_fallback_icon_path(tool, theme_name=None):
    icon_value = _normalize_tool_icon_value(tool)
    if _is_adaptive_default_icon_value(icon_value):
        return _resolve_theme_default_icon_path(theme_name)

    explicit_icon = resolve_icon_path(icon_value)
    if explicit_icon:
        return explicit_icon

    return _resolve_theme_default_icon_path(theme_name)


def _resolve_tool_icon_cache_key(tool, theme_name=None):
    if _looks_like_executable_tool_path(tool) and _should_prioritize_executable_icon_value(tool):
        cache_path = _build_executable_icon_cache_path_from_text(tool.get("path"))
        if cache_path:
            return cache_path

    resolution = icon_resolution_service.resolve(tool, theme_name=theme_name)
    if resolution.source != IconSource.FAILED and resolution.path:
        return resolution.path
    return _resolve_theme_default_icon_path(theme_name)


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
    auto_resolved = pyqtSignal(str, str, object, str)
    auto_failed = pyqtSignal(str, object, str)


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


class WebIconWorker(QRunnable):
    """Background worker for downloading and caching web favicons."""

    def __init__(self, request, tool, signals):
        super().__init__()
        self.request = dict(request or {})
        self.tool = dict(tool or {})
        self.signals = signals

    def run(self):
        request_key = str(self.request.get("request_key") or "")
        url = str(self.request.get("url") or "")
        icon_dir = str(self.request.get("icon_dir") or "")
        if not request_key or not url or not icon_dir:
            self.signals.auto_failed.emit(request_key, self.tool, "web")
            return

        try:
            downloader = FaviconDownloader(None, url, icon_dir)
            favicon_name = downloader._download_favicon_logic(url, timeout=3.0)
            if not favicon_name:
                self.signals.auto_failed.emit(request_key, self.tool, "web")
                return

            icon_path = os.path.join(icon_dir, favicon_name)
            if not os.path.isfile(icon_path):
                self.signals.auto_failed.emit(request_key, self.tool, "web")
                return

            self.signals.auto_resolved.emit(request_key, icon_path, self.tool, "web")
        except Exception:
            self.signals.auto_failed.emit(request_key, self.tool, "web")


class LocalSidecarIconWorker(QRunnable):
    """Background worker for scanning icons beside local tools."""

    def __init__(self, request_key, tool, signals):
        super().__init__()
        self.request_key = str(request_key or "")
        self.tool = dict(tool or {})
        self.signals = signals

    def run(self):
        if not self.request_key:
            self.signals.auto_failed.emit(self.request_key, self.tool, "local")
            return

        try:
            icon_path = resolve_local_sidecar_icon_path(self.tool)
            if icon_path and os.path.isfile(icon_path):
                self.signals.auto_resolved.emit(self.request_key, icon_path, self.tool, "local")
            else:
                self.signals.auto_failed.emit(self.request_key, self.tool, "local")
        except Exception:
            self.signals.auto_failed.emit(self.request_key, self.tool, "local")


class AsyncIconLoader(QObject):
    """Singleton async icon loader."""

    _instance = None
    icon_ready = pyqtSignal()
    icon_path_ready = pyqtSignal(str)
    auto_icon_ready = pyqtSignal(str, object)

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
        self.signals.auto_resolved.connect(self._on_auto_resolved)
        self.signals.auto_failed.connect(self._on_auto_failed)
        self.pool = QThreadPool.globalInstance()
        self._default_icon = None
        self._theme_default_icons = {}
        self._dynamic_failures = set()
        self._auto_icon_loading = set()
        self._exe_icon_queue = []
        self._exe_icon_timer = QTimer(self)
        self._exe_icon_timer.setInterval(400)
        self._exe_icon_timer.timeout.connect(self._process_exe_icon_queue)
        self._web_icon_queue = []
        self._web_icon_active_count = 0
        self._max_web_icon_active_count = 1
        self._web_icon_timer = QTimer(self)
        self._web_icon_timer.setInterval(500)
        self._web_icon_timer.timeout.connect(self._process_web_icon_queue)
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

    def _get_default_icon(self, theme_name=None):
        theme_key = str(theme_name or "").strip().casefold()
        if not theme_key:
            return self.default_icon

        cached_icon = self._theme_default_icons.get(theme_key)
        if cached_icon is not None:
            return cached_icon

        icon = QIcon(_resolve_theme_default_icon_path(theme_name) or "")
        if icon.isNull():
            icon = self.default_icon
        self._theme_default_icons[theme_key] = icon
        return icon

    def get_icon(self, path, theme_name=None):
        if isinstance(path, dict):
            dynamic_icon_key = _get_precomputed_icon_cache_key(path, theme_name=theme_name)
            if not dynamic_icon_key:
                dynamic_icon_key = get_icon_cache_key(path, theme_name=theme_name)

            if _looks_like_executable_icon_cache_path(dynamic_icon_key) and not os.path.exists(dynamic_icon_key):
                return self._get_icon_from_path(
                    _resolve_tool_fallback_icon_path(path, theme_name=theme_name),
                    theme_name=theme_name,
                )

            return self._get_icon_from_path(dynamic_icon_key, theme_name=theme_name)

        return self._get_icon_from_path(get_icon_cache_key(path, theme_name=theme_name), theme_name=theme_name)

    def warm_tool_icon(self, tool, theme_name=None):
        if not isinstance(tool, dict):
            return

        icon_key = _get_precomputed_icon_cache_key(tool, theme_name=theme_name)
        if not icon_key:
            icon_key = get_icon_cache_key(tool, theme_name=theme_name)
        self._queue_auto_icon_resolution(tool, icon_key)

    def _queue_auto_icon_resolution(self, tool, icon_key):
        if not isinstance(tool, dict):
            return

        if _looks_like_executable_icon_cache_path(icon_key) and not os.path.exists(icon_key):
            if icon_key not in self._dynamic_failures and icon_key not in self._auto_icon_loading:
                self._auto_icon_loading.add(icon_key)
                self._exe_icon_queue.append((icon_key, dict(tool or {})))
                if QCoreApplication.instance() is not None and not self._exe_icon_timer.isActive():
                    self._exe_icon_timer.start()
            return

        if self._should_queue_local_sidecar_icon(tool, icon_key):
            identity = get_tool_icon_identity(tool)
            request_key = f"local:{identity}" if identity else ""
            if request_key and request_key not in self._auto_icon_loading and request_key not in self._dynamic_failures:
                self._auto_icon_loading.add(request_key)
                self.pool.start(LocalSidecarIconWorker(request_key, tool, self.signals))
            return

        request = get_web_icon_download_request(tool)
        request_key = str(request.get("request_key") or "")
        if request_key and request_key not in self._auto_icon_loading and request_key not in self._dynamic_failures:
            self._auto_icon_loading.add(request_key)
            self._web_icon_queue.append((request_key, request, dict(tool or {})))
            if QCoreApplication.instance() is not None and not self._web_icon_timer.isActive():
                self._web_icon_timer.start()

    def _should_queue_local_sidecar_icon(self, tool, icon_key):
        if bool(tool.get("is_web_tool", False)):
            return False
        path_text = str(tool.get("path") or "").strip()
        if not path_text or path_text.startswith(("http://", "https://")):
            return False
        normalized_icon_key = os.fspath(icon_key or "")
        if not normalized_icon_key:
            return True
        default_paths = {
            os.fspath(_resolve_theme_default_icon_path(None) or ""),
            os.fspath(_resolve_theme_default_icon_path("light") or ""),
            os.fspath(_resolve_theme_default_icon_path("dark_green") or ""),
        }
        return normalized_icon_key in default_paths

    def _process_exe_icon_queue(self):
        if not self._exe_icon_queue:
            self._exe_icon_timer.stop()
            return

        target_path, tool = self._exe_icon_queue.pop(0)
        icon = self._extract_executable_icon(tool, target_path)
        self._auto_icon_loading.discard(target_path)
        if icon is None:
            self._on_auto_failed(target_path, tool, "exe")
        else:
            record_auto_icon_path(tool, target_path, "exe")

        if not self._exe_icon_queue:
            self._exe_icon_timer.stop()

    def _process_web_icon_queue(self):
        if self._web_icon_active_count >= self._max_web_icon_active_count:
            self._web_icon_timer.stop()
            return

        if not self._web_icon_queue:
            self._web_icon_timer.stop()
            return

        request_key, request, tool = self._web_icon_queue.pop(0)
        self._web_icon_active_count += 1
        self.pool.start(WebIconWorker(request, tool, self.signals))

        if not self._web_icon_queue:
            self._web_icon_timer.stop()

    def _get_icon_from_path(self, full_path, theme_name=None):
        if not full_path:
            return self._get_default_icon(theme_name)

        if not os.path.exists(full_path):
            return self._get_default_icon(theme_name)

        if full_path in self.cache:
            cached_icon = self.cache[full_path]
            return cached_icon if cached_icon is not None else self._get_default_icon(theme_name)

        if full_path not in self.loading:
            self.loading.add(full_path)
            self.pool.start(IconWorker(full_path, self.signals))

        return self._get_default_icon(theme_name)

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
            self.cache[path] = None

        self.loading.discard(path)
        self.icon_path_ready.emit(path)
        self.icon_ready.emit()

    def _on_auto_resolved(self, request_key, icon_path, tool, source):
        request_key = str(request_key or "")
        icon_path = os.fspath(icon_path or "")
        self._auto_icon_loading.discard(request_key)
        if not icon_path or not os.path.exists(icon_path):
            self._on_auto_failed(request_key, tool, source)
            return

        if source == "web":
            record_auto_icon_path(tool, icon_path, "web")
            self._web_icon_active_count = max(0, self._web_icon_active_count - 1)
        elif source == "exe":
            record_auto_icon_path(tool, icon_path, "exe")
        elif source == "local":
            record_auto_icon_path(tool, icon_path, "local")

        self._dynamic_failures.discard(request_key)
        icon = QIcon(icon_path)
        self.cache[icon_path] = icon if not icon.isNull() else None
        self.icon_path_ready.emit(icon_path)
        self.auto_icon_ready.emit(icon_path, tool)
        self.icon_ready.emit()
        if self._web_icon_queue and not self._web_icon_timer.isActive():
            self._web_icon_timer.start()

    def _on_auto_failed(self, request_key, tool, source):
        request_key = str(request_key or "")
        self._auto_icon_loading.discard(request_key)
        if request_key:
            self._dynamic_failures.add(request_key)
        if source == "web":
            self._web_icon_active_count = max(0, self._web_icon_active_count - 1)
        mark_auto_icon_failure(tool, source)
        if self._web_icon_queue and not self._web_icon_timer.isActive():
            self._web_icon_timer.start()

    def clear_cache(self):
        self.cache.clear()
        self.loading.clear()
        self._dynamic_failures.clear()
        self._auto_icon_loading.clear()
        self._exe_icon_queue.clear()
        self._exe_icon_timer.stop()
        self._web_icon_queue.clear()
        self._web_icon_active_count = 0
        self._web_icon_timer.stop()
        self._default_icon = None
        self._theme_default_icons.clear()
        clear_auto_icon_index_cache()

    def shutdown(self):
        try:
            flush_auto_icon_index()
            self.pool.clear()
            self.pool.waitForDone(500)
        except Exception:
            pass


icon_loader = AsyncIconLoader()

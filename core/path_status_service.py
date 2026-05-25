from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from core.runtime_paths import resolve_accessible_path_value


class PathStatus:
    UNKNOWN = "unknown"
    LOADING = "loading"
    AVAILABLE = "available"
    MISSING = "missing"
    UNCONFIGURED = "unconfigured"
    WEB = "web"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class PathStatusResult:
    cache_key: tuple
    status: str
    available: bool | None
    resolved_path: str = ""
    error: str = ""
    checked_at: float = 0.0
    request_id: int = 0

    @property
    def is_final(self) -> bool:
        return self.status not in {PathStatus.UNKNOWN, PathStatus.LOADING}


def is_placeholder_path(value) -> bool:
    text = str(value or "").strip()
    return bool(text and text.upper().startswith("CHANGE_ME"))


def is_web_tool_path(tool: Mapping | None) -> bool:
    tool = tool or {}
    path = str(tool.get("path") or "").strip()
    return bool(tool.get("is_web_tool", False)) or path.startswith(("http://", "https://"))


def build_path_status_cache_key(tool: Mapping | None, base_dir=None) -> tuple:
    tool = tool or {}
    return (
        os.path.normcase(os.fspath(base_dir or "")),
        str(tool.get("path") or "").strip(),
        bool(tool.get("is_web_tool", False)),
    )


def _is_unc_path(path_text: str) -> bool:
    return path_text.startswith(("\\\\", "//"))


def resolve_path_status(
    tool: Mapping | None,
    base_dir=None,
    timeout_seconds: float = 0.25,
    request_id: int = 0,
    path_resolver: Callable | None = None,
    clock: Callable[[], float] | None = None,
) -> PathStatusResult:
    tool = tool or {}
    path = str(tool.get("path") or "").strip()
    cache_key = build_path_status_cache_key(tool, base_dir)
    now = clock or time.monotonic
    started_at = now()

    def finish(status: str, available: bool | None, resolved_path: str = "", error: str = ""):
        return PathStatusResult(
            cache_key=cache_key,
            status=status,
            available=available,
            resolved_path=os.fspath(resolved_path or ""),
            error=str(error or ""),
            checked_at=time.time(),
            request_id=request_id,
        )

    if is_web_tool_path(tool):
        return finish(PathStatus.WEB, bool(path), path)
    if not path:
        return finish(PathStatus.UNCONFIGURED, None, "", "empty path")
    if is_placeholder_path(path):
        return finish(PathStatus.UNCONFIGURED, None, "", "placeholder path")

    if _is_unc_path(path):
        # Avoid cold UI stalls from unavailable network shares. Users can still run
        # the tool; this status is advisory and refreshed only from the worker.
        return finish(PathStatus.MISSING, False, path, "network path deferred")

    resolver = path_resolver or resolve_accessible_path_value
    try:
        resolved = resolver(path, base_dir=base_dir)
    except (OSError, ValueError) as exc:
        return finish(PathStatus.MISSING, False, "", str(exc))
    except Exception as exc:
        return finish(PathStatus.MISSING, False, "", str(exc))

    elapsed = now() - started_at
    if timeout_seconds is not None and timeout_seconds >= 0 and elapsed > timeout_seconds:
        return finish(PathStatus.TIMEOUT, None, os.fspath(resolved or ""), f"{elapsed:.3f}s")

    if resolved is None:
        return finish(PathStatus.MISSING, False)

    try:
        exists = Path(resolved).exists()
    except OSError as exc:
        return finish(PathStatus.MISSING, False, os.fspath(resolved), str(exc))

    return finish(
        PathStatus.AVAILABLE if exists else PathStatus.MISSING,
        bool(exists),
        os.fspath(resolved),
    )


class _PathStatusSignals(QObject):
    resolved = pyqtSignal(object)


class _PathStatusWorker(QRunnable):
    def __init__(self, tool, base_dir, request_id, timeout_seconds, signals):
        super().__init__()
        self.tool = dict(tool or {})
        self.base_dir = base_dir
        self.request_id = int(request_id)
        self.timeout_seconds = timeout_seconds
        self.signals = signals

    def run(self):
        result = resolve_path_status(
            self.tool,
            base_dir=self.base_dir,
            timeout_seconds=self.timeout_seconds,
            request_id=self.request_id,
        )
        self.signals.resolved.emit(result)


class PathStatusService(QObject):
    status_resolved = pyqtSignal(object)

    def __init__(
        self,
        parent=None,
        ttl_seconds: float = 30.0,
        timeout_seconds: float = 0.25,
        max_cache_entries: int = 2048,
        pool=None,
    ):
        super().__init__(parent)
        self.ttl_seconds = float(ttl_seconds)
        self.timeout_seconds = float(timeout_seconds)
        self.max_cache_entries = int(max_cache_entries)
        self._cache = {}
        self._loading = set()
        self._cancelled_requests = set()
        self._pool = pool or QThreadPool.globalInstance()
        self._signals = _PathStatusSignals()
        self._signals.resolved.connect(self._on_worker_resolved)

    def cache_key(self, tool, base_dir=None) -> tuple:
        return build_path_status_cache_key(tool, base_dir)

    def get_cached(self, cache_key):
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        cached_at, result = cached
        if time.monotonic() - cached_at > self.ttl_seconds:
            self._cache.pop(cache_key, None)
            return None
        return result

    def set_cached(self, result: PathStatusResult):
        if len(self._cache) > self.max_cache_entries:
            self._cache.clear()
        self._cache[result.cache_key] = (time.monotonic(), result)

    def resolve_now(self, tool, base_dir=None, request_id: int = 0) -> PathStatusResult:
        result = resolve_path_status(
            tool,
            base_dir=base_dir,
            timeout_seconds=self.timeout_seconds,
            request_id=request_id,
        )
        self.set_cached(result)
        return result

    def request(self, tool, base_dir=None, request_id: int = 0):
        cache_key = self.cache_key(tool, base_dir)
        cached = self.get_cached(cache_key)
        if cached is not None:
            self.status_resolved.emit(cached)
            return cached
        if cache_key in self._loading:
            return None

        self._loading.add(cache_key)
        worker = _PathStatusWorker(
            tool=tool,
            base_dir=base_dir,
            request_id=request_id,
            timeout_seconds=self.timeout_seconds,
            signals=self._signals,
        )
        self._pool.start(worker)
        return None

    def cancel_generation(self, request_id: int):
        self._cancelled_requests.add(int(request_id))
        if len(self._cancelled_requests) > 64:
            self._cancelled_requests = set(sorted(self._cancelled_requests)[-32:])

    def clear_cache(self):
        self._cache.clear()
        self._loading.clear()

    def shutdown(self):
        self._loading.clear()

    def _on_worker_resolved(self, result):
        if not isinstance(result, PathStatusResult):
            return
        self._loading.discard(result.cache_key)
        if result.request_id in self._cancelled_requests:
            return
        self.set_cached(result)
        self.status_resolved.emit(result)

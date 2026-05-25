from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

from core.runtime_paths import ensure_runtime_dir, resolve_icon_path_value

try:
    from core.tianhu_icon_registry import iter_tianhu_icon_names
except Exception:
    iter_tianhu_icon_names = None


LOCAL_ICON_FILENAMES = (
    "favicon.ico",
    "icon.ico",
    "icon.png",
    "icon.svg",
    "logo.ico",
    "logo.png",
    "logo.svg",
    "app.ico",
    "app.png",
)
LOCAL_ICON_EXTENSIONS = {".ico", ".png", ".svg", ".jpg", ".jpeg"}
MAX_LOCAL_ICON_SCAN = 24
AUTO_ICON_INDEX_VERSION = 1
WEB_FAILURE_RETRY_SECONDS = 24 * 60 * 60

_AUTO_ICON_INDEX = None
_AUTO_ICON_INDEX_DIRTY = False
_LOCAL_SIDECAR_CACHE = {}


def _normalize_path_text(value) -> str:
    return str(value or "").strip()


def is_web_tool(tool) -> bool:
    if not isinstance(tool, dict):
        return False
    path = _normalize_path_text(tool.get("path"))
    url = _normalize_path_text(tool.get("url"))
    return (
        bool(tool.get("is_web_tool", False))
        or path.startswith(("http://", "https://"))
        or url.startswith(("http://", "https://"))
    )


def get_tool_url(tool) -> str:
    if not isinstance(tool, dict):
        return ""

    for field_name in ("path", "url"):
        value = _normalize_path_text(tool.get(field_name))
        if value.startswith(("http://", "https://")):
            return value
    return ""


def get_web_domain(tool) -> str:
    url = get_tool_url(tool)
    if not url:
        return ""
    try:
        return urlparse(url).netloc.casefold()
    except Exception:
        return ""


def _safe_domain(domain: str) -> str:
    text = str(domain or "").strip().casefold()
    text = re.sub(r"[^a-z0-9._-]+", "_", text)
    return text.strip("._-")


def get_auto_web_icon_dir() -> Path:
    return ensure_runtime_dir("resources", "icons", "auto_cache", "web")


def get_auto_icon_index_path() -> Path:
    return ensure_runtime_dir("resources", "icons", "auto_cache") / "index.json"


def clear_auto_icon_index_cache() -> None:
    global _AUTO_ICON_INDEX, _AUTO_ICON_INDEX_DIRTY
    flush_auto_icon_index()
    _AUTO_ICON_INDEX = None
    _AUTO_ICON_INDEX_DIRTY = False
    _LOCAL_SIDECAR_CACHE.clear()


def _load_index() -> dict:
    global _AUTO_ICON_INDEX
    if _AUTO_ICON_INDEX is not None:
        return _AUTO_ICON_INDEX

    index = {"version": AUTO_ICON_INDEX_VERSION, "tools": {}, "web": {}, "failures": {}}
    path = get_auto_icon_index_path()
    try:
        if path.is_file():
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                index.update(loaded)
    except Exception:
        pass

    index.setdefault("version", AUTO_ICON_INDEX_VERSION)
    index.setdefault("tools", {})
    index.setdefault("web", {})
    index.setdefault("failures", {})
    _AUTO_ICON_INDEX = index
    return _AUTO_ICON_INDEX


def _save_index(index: dict) -> None:
    try:
        path = get_auto_icon_index_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True)
        path.write_text(payload, encoding="utf-8")
    except Exception:
        pass


def _mark_index_dirty() -> None:
    global _AUTO_ICON_INDEX_DIRTY
    _AUTO_ICON_INDEX_DIRTY = True


def flush_auto_icon_index() -> None:
    global _AUTO_ICON_INDEX_DIRTY
    if not _AUTO_ICON_INDEX_DIRTY or _AUTO_ICON_INDEX is None:
        return
    _save_index(_AUTO_ICON_INDEX)
    _AUTO_ICON_INDEX_DIRTY = False


def get_tool_icon_identity(tool) -> str:
    if not isinstance(tool, dict):
        return ""
    parts = (
        _normalize_path_text(tool.get("name")).casefold(),
        _normalize_path_text(tool.get("path")),
        _normalize_path_text(tool.get("url")),
        str(bool(tool.get("is_web_tool", False))),
    )
    digest = hashlib.sha1("\n".join(parts).encode("utf-8", errors="ignore")).hexdigest()
    return digest


def _existing_file(path_text) -> str:
    text = _normalize_path_text(path_text)
    if not text:
        return ""
    try:
        path = Path(text)
        if path.is_file():
            return os.fspath(path)
    except Exception:
        return ""
    return ""


def resolve_cached_auto_icon_path(tool) -> str:
    if not isinstance(tool, dict):
        return ""

    index = _load_index()
    identity = get_tool_icon_identity(tool)
    if identity:
        entry = index.get("tools", {}).get(identity, {})
        if isinstance(entry, dict):
            icon_path = _existing_file(entry.get("path"))
            if icon_path:
                return icon_path

    domain = get_web_domain(tool)
    if domain:
        entry = index.get("web", {}).get(domain, {})
        if isinstance(entry, dict):
            icon_path = _existing_file(entry.get("path"))
            if icon_path:
                return icon_path

    return ""


def record_auto_icon_path(tool, icon_path, source: str) -> str:
    resolved = _existing_file(icon_path)
    if not isinstance(tool, dict) or not resolved:
        return ""

    index = _load_index()
    now = time.time()
    identity = get_tool_icon_identity(tool)
    if identity:
        index.setdefault("tools", {})[identity] = {
            "path": resolved,
            "source": str(source or "auto"),
            "updated_at": now,
        }

    domain = get_web_domain(tool)
    if domain and str(source or "").casefold() == "web":
        index.setdefault("web", {})[domain] = {
            "path": resolved,
            "source": "web",
            "updated_at": now,
        }
        index.setdefault("failures", {}).pop(f"web:{domain}", None)

    _mark_index_dirty()
    return resolved


def mark_auto_icon_failure(tool, source: str) -> None:
    if not isinstance(tool, dict):
        return
    source_key = str(source or "auto").casefold()
    if source_key == "web":
        domain = get_web_domain(tool)
        if not domain:
            return
        key = f"web:{domain}"
    else:
        identity = get_tool_icon_identity(tool)
        if not identity:
            return
        key = f"{source_key}:{identity}"

    index = _load_index()
    index.setdefault("failures", {})[key] = time.time()
    _mark_index_dirty()


def _recent_failure(key: str, retry_seconds: int) -> bool:
    if not key:
        return False
    index = _load_index()
    failed_at = index.get("failures", {}).get(key)
    try:
        return time.time() - float(failed_at) < retry_seconds
    except Exception:
        return False


def get_web_icon_download_request(tool) -> dict:
    if not is_web_tool(tool):
        return {}

    url = get_tool_url(tool)
    domain = get_web_domain(tool)
    if not url or not domain:
        return {}

    if resolve_cached_auto_icon_path(tool):
        return {}

    failure_key = f"web:{domain}"
    if _recent_failure(failure_key, WEB_FAILURE_RETRY_SECONDS):
        return {}

    return {
        "url": url,
        "domain": domain,
        "safe_domain": _safe_domain(domain),
        "icon_dir": os.fspath(get_auto_web_icon_dir()),
        "request_key": failure_key,
    }


def _resolve_local_path(path_text: str) -> Path | None:
    text = _normalize_path_text(path_text)
    if not text or text.startswith(("http://", "https://")):
        return None
    if text.upper().startswith("CHANGE_ME"):
        return None

    try:
        candidate = Path(text).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        return candidate
    except Exception:
        return None


def resolve_local_sidecar_icon_path(tool) -> str:
    if not isinstance(tool, dict) or is_web_tool(tool):
        return ""

    candidate = _resolve_local_path(tool.get("path"))
    if candidate is None:
        return ""

    try:
        if candidate.is_file():
            base_dir = candidate.parent
        elif candidate.is_dir():
            base_dir = candidate
        else:
            return ""
    except Exception:
        return ""

    try:
        stat = base_dir.stat()
        cache_key = (os.path.normcase(os.fspath(base_dir)), stat.st_mtime_ns)
    except Exception:
        cache_key = (os.path.normcase(os.fspath(base_dir)), 0)

    if cache_key in _LOCAL_SIDECAR_CACHE:
        cached = _LOCAL_SIDECAR_CACHE[cache_key]
        return cached if _existing_file(cached) else ""

    for file_name in LOCAL_ICON_FILENAMES:
        icon_path = base_dir / file_name
        if icon_path.is_file():
            resolved = os.fspath(icon_path)
            _LOCAL_SIDECAR_CACHE[cache_key] = resolved
            return resolved

    try:
        scanned = 0
        for child in base_dir.iterdir():
            if scanned >= MAX_LOCAL_ICON_SCAN:
                break
            scanned += 1
            if child.is_file() and child.suffix.casefold() in LOCAL_ICON_EXTENSIONS:
                resolved = os.fspath(child)
                _LOCAL_SIDECAR_CACHE[cache_key] = resolved
                return resolved
    except Exception:
        pass

    _LOCAL_SIDECAR_CACHE[cache_key] = ""
    return ""


def resolve_known_tool_icon_path(tool) -> str:
    if not isinstance(tool, dict) or iter_tianhu_icon_names is None:
        return ""

    seen = set()
    for icon_name in iter_tianhu_icon_names(tool):
        candidates = [icon_name]
        normalized = str(icon_name or "").strip().replace("\\", "/")
        if normalized and "/" not in normalized:
            candidates.extend(
                [
                    f"tianhu/common/{normalized}",
                    f"tianhu/3.0/{normalized}",
                    f"tianhu/2.0/{normalized}",
                ]
            )
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            resolved = resolve_icon_path_value(candidate)
            if resolved and resolved.is_file():
                return os.fspath(resolved)
    return ""

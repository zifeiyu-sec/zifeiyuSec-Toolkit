from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from core.auto_icon_resolver import (
    get_web_icon_download_request,
    record_auto_icon_path,
    resolve_cached_auto_icon_path,
    resolve_known_tool_icon_path,
    resolve_local_sidecar_icon_path,
)
from core.runtime_paths import ensure_runtime_dir, resolve_icon_path_value


class IconSource:
    DEFAULT = "default"
    CUSTOM = "custom"
    EXE_CACHE = "exe_cache"
    WEB_FAVICON = "web_favicon"
    KNOWN_REGISTRY = "known_registry"
    SIDECAR = "sidecar"
    FAILED = "failed"


@dataclass(frozen=True)
class IconResolution:
    source: str
    path: str = ""
    reason: str = ""
    pinned: bool = False


DEFAULT_LIGHT_ICON = "write-github.svg"
DEFAULT_DARK_ICON = "black-github.png"
DARK_THEMES = {"dark_green", "purple_neon", "red_orange"}


def _text(value) -> str:
    return str(value or "").strip()


def _is_default_icon_value(value) -> bool:
    name = os.path.basename(_text(value).replace("\\", "/")).casefold()
    return name in {
        "",
        "default_icon",
        "github_1_1_1.svg",
        "github_1_1_1",
        DEFAULT_LIGHT_ICON,
        "write-github",
        DEFAULT_DARK_ICON,
        "black-github",
        "white-github.svg",
        "white-github",
        "favicon.ico",
        "github.com_favicon.ico",
        "github.com_favicon",
        "fox.ico",
    }


class IconResolutionService:
    def __init__(self, default_light_icon=DEFAULT_LIGHT_ICON, default_dark_icon=DEFAULT_DARK_ICON):
        self.default_light_icon = default_light_icon
        self.default_dark_icon = default_dark_icon

    def default_icon_path(self, theme_name=None) -> str:
        preferred = self.default_dark_icon if _text(theme_name).casefold() in DARK_THEMES else self.default_light_icon
        for candidate in (preferred, self.default_light_icon, self.default_dark_icon, "github_1_1_1.svg", "favicon.ico"):
            resolved = resolve_icon_path_value(candidate)
            if resolved:
                return os.fspath(resolved)
        return ""

    def resolve(self, tool, theme_name=None) -> IconResolution:
        if not isinstance(tool, dict):
            return self._default_resolution(theme_name, "non-dict tool")

        pinned = bool(tool.get("icon_pinned", False))
        icon_value = _text(tool.get("icon") or tool.get("icon_path"))

        if icon_value and not _is_default_icon_value(icon_value):
            resolved = resolve_icon_path_value(icon_value)
            if resolved:
                return IconResolution(IconSource.CUSTOM, os.fspath(resolved), pinned=pinned)
            if pinned:
                return IconResolution(IconSource.FAILED, "", "pinned icon is missing", pinned=True)

        cached_auto = resolve_cached_auto_icon_path(tool)
        if cached_auto:
            if "/web/" in cached_auto.replace("\\", "/").casefold():
                return IconResolution(IconSource.WEB_FAVICON, cached_auto, pinned=pinned)
            if "/exe_cache/" in cached_auto.replace("\\", "/").casefold():
                return IconResolution(IconSource.EXE_CACHE, cached_auto, pinned=pinned)
            return IconResolution(IconSource.SIDECAR, cached_auto, pinned=pinned)

        known_icon = resolve_known_tool_icon_path(tool)
        if known_icon:
            return IconResolution(IconSource.KNOWN_REGISTRY, known_icon, pinned=pinned)

        sidecar_icon = resolve_local_sidecar_icon_path(tool)
        if sidecar_icon:
            return IconResolution(IconSource.SIDECAR, sidecar_icon, pinned=pinned)

        default_path = self.default_icon_path(theme_name)
        if default_path:
            return IconResolution(IconSource.DEFAULT, default_path, pinned=pinned)
        return IconResolution(IconSource.FAILED, "", "default icon is missing", pinned=pinned)

    def clear_cache(self, include_files=False):
        cache_dir = ensure_runtime_dir("resources", "icons", "auto_cache")
        if include_files and cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
            cache_dir.mkdir(parents=True, exist_ok=True)
        return os.fspath(cache_dir)

    def re_resolve(self, tool, theme_name=None) -> IconResolution:
        return self.resolve(tool, theme_name=theme_name)

    def pin_icon(self, tool, icon_path):
        if not isinstance(tool, dict):
            raise TypeError("tool must be a dict")
        resolved = resolve_icon_path_value(icon_path) or Path(icon_path)
        if not Path(resolved).exists():
            raise FileNotFoundError(os.fspath(icon_path))
        tool["icon"] = os.fspath(icon_path)
        tool["icon_pinned"] = True
        return tool

    def fallback_default(self, theme_name=None) -> IconResolution:
        return self._default_resolution(theme_name, "fallback default")

    def web_download_request(self, tool):
        return get_web_icon_download_request(tool)

    def record_resolved_icon(self, tool, icon_path, source):
        return record_auto_icon_path(tool, icon_path, source)

    def _default_resolution(self, theme_name=None, reason="") -> IconResolution:
        path = self.default_icon_path(theme_name)
        source = IconSource.DEFAULT if path else IconSource.FAILED
        return IconResolution(source, path, reason)


icon_resolution_service = IconResolutionService()

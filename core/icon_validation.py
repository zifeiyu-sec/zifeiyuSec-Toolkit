from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse


SUPPORTED_ICON_EXTENSIONS = (".svg", ".png", ".ico", ".jpg", ".jpeg", ".gif")


def _head(data: bytes, limit: int = 512) -> bytes:
    return bytes(data or b"")[:limit].lstrip().lower()


def _looks_like_html(data: bytes) -> bool:
    head = _head(data)
    return head.startswith((b"<!doctype html", b"<html")) or b"<html" in head[:120]


def _looks_like_svg(data: bytes) -> bool:
    head = _head(data, limit=2048)
    return b"<svg" in head and not _looks_like_html(data)


def is_probably_icon_data(data: bytes, source_url: str = "", content_type: str = "") -> bool:
    if not data or _looks_like_html(data):
        return False

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if data.startswith(b"\xff\xd8\xff"):
        return True
    if data.startswith((b"GIF87a", b"GIF89a")):
        return True
    if data[:4] == b"\x00\x00\x01\x00":
        return True
    if _looks_like_svg(data):
        return True

    normalized_content_type = str(content_type or "").lower()
    if any(token in normalized_content_type for token in ("image/", "icon", "svg")):
        return True

    path = urlparse(str(source_url or "")).path.lower()
    return any(path.endswith(ext) for ext in SUPPORTED_ICON_EXTENSIONS)


def detect_icon_extension(source_url: str = "", content_type: str = "", data: bytes = b"") -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if data[:4] == b"\x00\x00\x01\x00":
        return ".ico"
    if _looks_like_svg(data):
        return ".svg"

    normalized_content_type = str(content_type or "").lower()
    if "svg" in normalized_content_type:
        return ".svg"
    if "png" in normalized_content_type:
        return ".png"
    if "gif" in normalized_content_type:
        return ".gif"
    if "jpeg" in normalized_content_type or "jpg" in normalized_content_type:
        return ".jpg"
    if "ico" in normalized_content_type or "icon" in normalized_content_type:
        return ".ico"

    path = urlparse(str(source_url or "")).path.lower()
    for ext in SUPPORTED_ICON_EXTENSIONS:
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".ico"


def is_valid_icon_file(path: str | Path) -> bool:
    try:
        icon_path = Path(path)
        if not icon_path.is_file():
            return False
        data = icon_path.read_bytes()
    except (OSError, ValueError):
        return False
    return is_probably_icon_data(data, source_url=icon_path.name)

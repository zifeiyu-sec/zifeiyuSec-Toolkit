from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.data_manager import DataManager
from core.runtime_paths import resolve_icon_path_value
from core.tianhu_icon_registry import iter_tianhu_icon_names, iter_tianhu_icon_source_urls
from core.tool_config_exchange import ToolConfigExchangeService


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_JSON_TEXT = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TIANHU_ICON_SOURCE", "")
SOURCE_JSON = Path(SOURCE_JSON_TEXT) if SOURCE_JSON_TEXT else None
TIANHU_VERSION = (
    sys.argv[2]
    if len(sys.argv) > 2
    else os.environ.get("TIANHU_ICON_VERSION", "2.0")
).strip()
TARGET_DIR = PROJECT_ROOT / "resources" / "icons" / "tianhu" / TIANHU_VERSION
ENABLE_SEARCH = os.environ.get("TIANHU_ICON_ENABLE_SEARCH", "").strip() == "1"
GITHUB_FALLBACK_ICON = PROJECT_ROOT / "resources" / "icons" / "black-github.png"
DEFAULT_TOOL_ROOTS = [
    Path(item)
    for item in (
        os.environ.get("TIANHU_TOOL_ROOTS", "")
        or os.environ.get("TIANHU_TOOL_ROOT", "")
    ).split(os.pathsep)
    if item.strip()
]
GENERIC_EXTRACTED_ICON_SHA1S = {
    # Generic Java/JAR icon extracted by QFileIconProvider. It renders as a tiny
    # mark in the corner of an otherwise blank icon, so prefer GitHub fallback.
    "c0b2d6b9e38e33abc0fa84a1cb04be87cf462801",
}
STOP_KEYS = {
    "tools",
    "th2",
    "gui",
    "gui_webshell",
    "gui_other",
    "gui_shouji",
    "gui_scan",
    "gui_yjxy",
    "webshell",
    "main",
    "jar",
    "python",
    "cmd",
    "exe",
    "vbs",
    "bat",
    "app",
    "http",
    "https",
    "ftp",
    "file",
    "sql",
    "api",
    "md5",
    "linux",
    "java",
    "web",
    "cs",
    "x",
}
CATEGORY_COLORS = {
    "WebShell管理工具": ("#2563EB", "#67E8F9"),
    "抓包与代理工具": ("#7C3AED", "#C4B5FD"),
    "信息收集工具": ("#0891B2", "#A7F3D0"),
    "后渗透工具": ("#BE123C", "#FDBA74"),
    "漏洞扫描与利用工具": ("#EA580C", "#FDE68A"),
    "免杀工具": ("#4F46E5", "#F0ABFC"),
    "爆破工具": ("#9333EA", "#F9A8D4"),
    "网页工具": ("#0F766E", "#99F6E4"),
    "其他工具": ("#475569", "#CBD5E1"),
}


def load_tools(json_path: Path):
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else payload.get("tools", [])


def normalize_key(value: str) -> str:
    text = str(value or "").strip().casefold()
    text = os.path.basename(text.replace("\\", "/"))
    text = os.path.splitext(text)[0]
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def score_key(key: str) -> int:
    if not key:
        return -10_000
    if key in STOP_KEYS:
        return -500
    if re.fullmatch(r"\d+", key):
        return -500
    if len(key) < 3:
        return -200

    score = len(key)
    if "_" in key:
        score += 2
    if re.search(r"_(v?\d+(_\d+)*)$", key):
        score -= 3
    if key.endswith(("gui", "tool", "tools", "scan")):
        score -= 1
    return score


def choose_icon_key(service: ToolConfigExchangeService, tool: dict, fallback_index: int) -> str:
    candidates = list(service._build_tianhu_icon_library_keys(tool, tool.get("path", ""), False))
    best_key = ""
    best_score = -10_000

    for candidate in candidates:
        key = normalize_key(candidate)
        if not key:
            continue
        score = score_key(key)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key:
        return best_key

    name_key = normalize_key(tool.get("name", ""))
    if name_key and score_key(name_key) > -500:
        return name_key

    return f"tool_{fallback_index:03d}"


def pick_existing_source(tool: dict, service: ToolConfigExchangeService):
    seen = set()
    for candidate in iter_tianhu_icon_names(tool):
        candidate = str(candidate or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        resolved = resolve_icon_path_value(candidate)
        if resolved and resolved.exists():
            return resolved

    key_candidates = list(service._build_tianhu_icon_library_keys(tool, tool.get("path", ""), False))
    for candidate in key_candidates:
        candidate = str(candidate or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        for maybe in (
            candidate,
            f"tianhu/common/{candidate}",
            f"tianhu/3.0/{candidate}",
            f"tianhu/2.0/{candidate}",
        ):
            resolved = resolve_icon_path_value(maybe)
            if resolved and resolved.exists():
                return resolved
    return None


def pick_source_url(tool: dict, service: ToolConfigExchangeService, key: str) -> str:
    seen = set()
    for candidate in iter_tianhu_icon_source_urls(tool):
        candidate = str(candidate or "").strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            return candidate

    raw_url = str(tool.get("url", "") or "").strip()
    if raw_url.startswith(("http://", "https://")) and raw_url not in seen:
        return raw_url

    if not ENABLE_SEARCH:
        return ""

    for query in (key, tool.get("name", "")):
        text = str(query or "").strip()
        if not text:
            continue
        service._tianhu_icon_online_search_count = 0
        search_url = service._search_tianhu_icon_source_url(text)
        if search_url and search_url not in seen:
            seen.add(search_url)
            return search_url

    return ""


def copy_local_icon(source: Path, target_dir: Path, target_key: str) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{target_key}{source.suffix.lower()}"
    shutil.copy2(source, target)
    if is_generic_extracted_icon(target):
        target.unlink(missing_ok=True)
        return copy_github_fallback_icon(target_dir, target_key)
    return target.name


def copy_github_fallback_icon(target_dir: Path, target_key: str) -> str:
    if not GITHUB_FALLBACK_ICON.exists():
        return create_svg_icon({"name": target_key, "category": "其他工具"}, target_dir, target_key)
    return copy_local_icon(GITHUB_FALLBACK_ICON, target_dir, target_key)


def is_generic_extracted_icon(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        digest = hashlib.sha1(path.read_bytes()).hexdigest()
    except OSError:
        return False
    return digest in GENERIC_EXTRACTED_ICON_SHA1S


def resolve_tool_path(tool: dict) -> Path | None:
    raw_path = str(tool.get("path", "") or "").strip()
    if not raw_path:
        return None
    normalized = raw_path.replace("/", os.sep).replace("\\", os.sep)
    candidate = Path(normalized)
    if candidate.exists():
        return candidate

    relative_text = normalized.lstrip("\\/")
    if relative_text:
        for root in DEFAULT_TOOL_ROOTS:
            rooted = root / relative_text
            if rooted.exists():
                return rooted
    return None


def extract_file_icon(tool_path: Path, target_dir: Path, target_key: str) -> str:
    if tool_path is None or not tool_path.exists():
        return ""
    if tool_path.suffix.casefold() not in {".exe", ".jar", ".bat", ".cmd", ".vbs", ".ps1", ".py"}:
        return ""
    try:
        from PyQt5.QtCore import QFileInfo, QSize
        from PyQt5.QtWidgets import QApplication, QFileIconProvider
    except Exception:
        return ""

    app = QApplication.instance() or QApplication([])
    provider = QFileIconProvider()
    icon = provider.icon(QFileInfo(str(tool_path)))
    if icon.isNull():
        return ""

    sizes = icon.availableSizes()
    if sizes:
        size = max(sizes, key=lambda item: item.width() * item.height())
    else:
        size = QSize(96, 96)

    pixmap = icon.pixmap(size)
    if pixmap.isNull():
        return ""

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{target_key}.png"
    if pixmap.save(str(target), "PNG"):
        if is_generic_extracted_icon(target):
            target.unlink(missing_ok=True)
            return copy_github_fallback_icon(target_dir, target_key)
        return target.name
    return ""


def initials_for_name(name: str, key: str) -> str:
    text = str(name or "").strip()
    ascii_parts = re.findall(r"[A-Za-z0-9]+", text)
    if ascii_parts:
        value = "".join(part[0] for part in ascii_parts[:3]).upper()
        return value[:3]
    chinese_chars = [char for char in text if "\u4e00" <= char <= "\u9fff"]
    if chinese_chars:
        return "".join(chinese_chars[:2])
    return str(key or "TH")[:2].upper()


def create_svg_icon(tool: dict, target_dir: Path, target_key: str) -> str:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{target_key}.svg"
    name = str(tool.get("name", "") or target_key).strip()
    category = str(tool.get("category", "") or "其他工具").strip()
    color1, color2 = CATEGORY_COLORS.get(category, CATEGORY_COLORS["其他工具"])
    initials = initials_for_name(name, target_key)
    safe_title = (
        name.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    svg = f'''<svg width="128" height="128" viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg">
  <title>{safe_title}</title>
  <defs>
    <linearGradient id="g" x1="20" y1="14" x2="108" y2="116" gradientUnits="userSpaceOnUse">
      <stop stop-color="{color2}"/>
      <stop offset="1" stop-color="{color1}"/>
    </linearGradient>
  </defs>
  <rect x="14" y="14" width="100" height="100" rx="24" fill="url(#g)"/>
  <path d="M36 82h56M36 64h56M36 46h56" stroke="#FFFFFF" stroke-opacity=".24" stroke-width="8" stroke-linecap="round"/>
  <circle cx="94" cy="34" r="10" fill="#FFFFFF" fill-opacity=".85"/>
  <text x="64" y="76" text-anchor="middle" font-family="Arial, 'Microsoft YaHei', sans-serif" font-size="32" font-weight="700" fill="#FFFFFF">{initials}</text>
</svg>
'''
    target.write_text(svg, encoding="utf-8")
    return target.name


def main():
    if SOURCE_JSON is None:
        print("Usage: python scripts/refresh_tianhu_icon_library.py <tianhu-tools.json> [2.0|3.0]")
        print("Optional: set TIANHU_TOOL_ROOTS to search local tool directories for executable icons.")
        return 2

    tools = load_tools(SOURCE_JSON)
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    service = ToolConfigExchangeService(DataManager(config_dir=str(PROJECT_ROOT / ".runtime")))

    summary = {"copied": 0, "downloaded": 0, "extracted": 0, "generated": 0, "skipped": 0, "failed": 0}
    seen_keys = set()

    for index, tool in enumerate(tools, start=1):
        name = str(tool.get("name", "") or "").strip()
        key = choose_icon_key(service, tool, index)
        if key in seen_keys:
            summary["skipped"] += 1
            continue
        seen_keys.add(key)

        target_files = list(TARGET_DIR.glob(f"{key}.*"))
        generic_existing = [item for item in target_files if is_generic_extracted_icon(item)]
        if generic_existing:
            for item in generic_existing:
                item.unlink(missing_ok=True)
            fallback_name = copy_github_fallback_icon(TARGET_DIR, key)
            summary["copied"] += 1
            print(f"[fallback] {name} -> {fallback_name}")
            continue
        if target_files:
            summary["skipped"] += 1
            continue

        local_source = pick_existing_source(tool, service)
        if local_source:
            copy_local_icon(local_source, TARGET_DIR, key)
            summary["copied"] += 1
            print(f"[copy] {name} -> {key}")
            continue

        source_url = pick_source_url(tool, service, key)
        if not source_url:
            tool_path = resolve_tool_path(tool)
            extracted_name = extract_file_icon(tool_path, TARGET_DIR, key)
            if extracted_name:
                summary["extracted"] += 1
                print(f"[extract] {name} -> {extracted_name}")
                continue

            generated_name = create_svg_icon(tool, TARGET_DIR, key)
            if generated_name:
                summary["generated"] += 1
                print(f"[generate] {name} -> {generated_name}")
            else:
                summary["failed"] += 1
                print(f"[fail] {name} -> {key} (no source url)")
            continue

        downloaded_name = service._download_tianhu_web_icon(
            source_url,
            icon_dir=str(TARGET_DIR),
            target_name=key,
        )
        if downloaded_name:
            summary["downloaded"] += 1
            print(f"[download] {name} -> {downloaded_name} from {source_url}")
            continue

        tool_path = resolve_tool_path(tool)
        extracted_name = extract_file_icon(tool_path, TARGET_DIR, key)
        if extracted_name:
            summary["extracted"] += 1
            print(f"[extract] {name} -> {extracted_name}")
            continue

        generated_name = create_svg_icon(tool, TARGET_DIR, key)
        if generated_name:
            summary["generated"] += 1
            print(f"[generate] {name} -> {generated_name}")
        else:
            summary["failed"] += 1
            print(f"[fail] {name} -> {key} ({source_url})")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())

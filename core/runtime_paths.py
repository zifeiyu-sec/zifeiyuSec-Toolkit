from __future__ import annotations

import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_STATE_DIRNAME = ".runtime"
ICON_EXTENSIONS = (".svg", ".png", ".ico", ".jpg", ".jpeg")


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_bundle_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    return Path(bundle_root).resolve() if bundle_root else PROJECT_ROOT


def get_runtime_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def get_runtime_state_root() -> Path:
    return get_runtime_root().joinpath(RUNTIME_STATE_DIRNAME)


def get_bundle_path(*parts: str) -> Path:
    return get_bundle_root().joinpath(*parts)


def get_runtime_path(*parts: str) -> Path:
    return get_runtime_state_root().joinpath(*parts)


def ensure_runtime_dir(*parts: str) -> Path:
    path = get_runtime_path(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _copy_file_if_missing(source: Path, target: Path) -> Path:
    if not source.exists() or source == target or target.exists():
        return target

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target


def _copy_tree_if_missing(source_root: Path, target_root: Path) -> Path:
    target_root.mkdir(parents=True, exist_ok=True)
    if not source_root.exists() or source_root == target_root:
        return target_root

    for source in source_root.rglob("*"):
        relative_path = source.relative_to(source_root)
        target = target_root / relative_path
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    return target_root


def resolve_preferred_path(*parts: str) -> Path:
    runtime_path = get_runtime_path(*parts)
    if runtime_path.exists():
        return runtime_path

    bundle_path = get_bundle_path(*parts)
    if bundle_path.exists():
        return bundle_path

    return runtime_path


def copy_bundle_file_if_missing(*parts: str) -> Path:
    target = get_runtime_path(*parts)
    if target.exists():
        return target

    source = get_bundle_path(*parts)
    return _copy_file_if_missing(source, target)


def copy_bundle_tree_if_missing(*parts: str) -> Path:
    target_root = ensure_runtime_dir(*parts)
    source_root = get_bundle_path(*parts)
    return _copy_tree_if_missing(source_root, target_root)


def migrate_legacy_runtime_layout() -> Path:
    legacy_root = get_runtime_root()
    state_root = get_runtime_state_root()
    if legacy_root == state_root:
        return state_root

    state_root.mkdir(parents=True, exist_ok=True)

    for relative_parts in (
        ("settings.ini",),
        ("image.ico",),
        ("image.png",),
        ("favicon.ico",),
    ):
        _copy_file_if_missing(
            legacy_root.joinpath(*relative_parts),
            state_root.joinpath(*relative_parts),
        )

    for relative_parts in (
        ("data",),
        ("images",),
        ("resources", "icons"),
        ("resources", "notes"),
    ):
        _copy_tree_if_missing(
            legacy_root.joinpath(*relative_parts),
            state_root.joinpath(*relative_parts),
        )

    return state_root


def resolve_resource_file(relative_dir: tuple[str, ...], value: str, extensions=()) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None

    candidate = Path(text)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    names = [text]
    if extensions and not candidate.suffix:
        names.extend(f"{text}{ext}" for ext in extensions)

    seen_roots = set()
    for root in (get_runtime_path(*relative_dir), get_bundle_path(*relative_dir)):
        root_key = str(root)
        if root_key in seen_roots:
            continue
        seen_roots.add(root_key)

        for name in names:
            resource_path = root / name
            if resource_path.exists():
                return resource_path

    if candidate.exists():
        return candidate.resolve()

    return None


def resolve_icon_path_value(value: str) -> Path | None:
    return resolve_resource_file(("resources", "icons"), value, ICON_EXTENSIONS)


def bootstrap_runtime_layout() -> None:
    migrate_legacy_runtime_layout()
    ensure_runtime_dir("data")
    ensure_runtime_dir("logs")
    ensure_runtime_dir("resources", "notes", "_attachments")
    copy_bundle_tree_if_missing("resources", "icons")
    copy_bundle_tree_if_missing("resources", "notes")
    copy_bundle_tree_if_missing("images")

    for file_name in ("image.ico", "image.png", "favicon.ico", "settings.example.ini"):
        copy_bundle_file_if_missing(file_name)

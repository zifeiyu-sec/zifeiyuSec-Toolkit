from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


class RuntimeBackupError(RuntimeError):
    pass


class RuntimeBackupArchiveError(RuntimeBackupError):
    pass


class RuntimeBackupService:
    BACKUP_SCHEMA = "zifeiyu-runtime-backup"
    BACKUP_VERSION = 1
    MANIFEST_NAME = "backup_manifest.json"
    DEFAULT_INCLUDE_PATHS = (
        "settings.ini",
        "data",
        "resources/icons",
        "resources/notes",
        "images",
    )

    def __init__(self, runtime_root):
        self.runtime_root = Path(runtime_root).resolve()
        self.backup_root = self.runtime_root / "backups" / "manual"
        self.safety_backup_root = self.runtime_root / "backups" / "safety"
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.safety_backup_root.mkdir(parents=True, exist_ok=True)

    def get_default_backup_path(self, at=None):
        moment = at or datetime.now()
        timestamp = moment.strftime("%Y%m%d_%H%M%S")
        return self.backup_root / f"runtime_backup_{timestamp}.zip"

    def get_default_safety_backup_path(self, at=None):
        moment = at or datetime.now()
        timestamp = moment.strftime("%Y%m%d_%H%M%S")
        return self.safety_backup_root / f"restore_before_{timestamp}.zip"

    def create_backup(self, destination_path=None, include_paths=None):
        include_specs = self._build_include_specs(include_paths or self.DEFAULT_INCLUDE_PATHS)
        backup_path = Path(destination_path) if destination_path else self.get_default_backup_path()
        if backup_path.suffix.lower() != ".zip":
            backup_path = backup_path.with_suffix(".zip")
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        entries = self._collect_backup_entries(include_specs)
        manifest = self._build_manifest(include_specs, len(entries))

        with zipfile.ZipFile(backup_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                self.MANIFEST_NAME,
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            for source_path, arcname in entries:
                archive.write(source_path, arcname.as_posix())

        return {
            "backup_path": str(backup_path),
            "file_count": len(entries),
            "include_paths": [spec["path"].as_posix() for spec in include_specs],
            "manifest_path": self.MANIFEST_NAME,
        }

    def restore_backup(self, archive_path, create_safety_backup=True):
        backup_path = Path(archive_path).resolve()
        if not backup_path.is_file():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        with zipfile.ZipFile(backup_path, "r") as archive:
            manifest = self._read_manifest(archive)
            include_specs = self._normalize_manifest_include_specs(manifest)
            entries = self._collect_restore_entries(archive, include_specs)
            if not entries:
                raise RuntimeBackupArchiveError("备份文件中没有可恢复的数据。")

            safety_backup_path = ""
            if create_safety_backup:
                safety_backup_path = str(self.get_default_safety_backup_path())
                self.create_backup(
                    safety_backup_path,
                    include_paths=[spec["path"].as_posix() for spec in include_specs],
                )

            with tempfile.TemporaryDirectory(prefix="runtime_restore_", dir=str(self.backup_root)) as tmp_dir:
                staging_root = Path(tmp_dir)
                self._extract_entries_to_staging(archive, entries, staging_root)
                self._clear_include_roots(include_specs)
                self._copy_staging_to_runtime(staging_root)

        return {
            "backup_path": str(backup_path),
            "restored_files": len(entries),
            "include_paths": [spec["path"].as_posix() for spec in include_specs],
            "safety_backup_path": safety_backup_path,
        }

    def _normalize_include_paths(self, include_paths):
        normalized = []
        seen = set()
        for relative_path in include_paths or []:
            path = self._normalize_relative_path(relative_path)
            key = path.as_posix()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(path)
        return tuple(normalized)

    def _build_include_specs(self, include_paths):
        specs = []
        for relative_path in self._normalize_include_paths(include_paths or []):
            source_root = self.runtime_root / relative_path
            kind = "dir"
            if relative_path.as_posix() == "settings.ini":
                kind = "file"
            elif source_root.exists() and source_root.is_file():
                kind = "file"
            specs.append({
                "path": relative_path,
                "kind": kind,
            })
        return tuple(specs)

    def _normalize_manifest_include_specs(self, manifest):
        include_items = manifest.get("include_items")
        if isinstance(include_items, list) and include_items:
            specs = []
            for item in include_items:
                if not isinstance(item, dict):
                    continue
                path_value = item.get("path")
                kind = str(item.get("kind", "") or "").strip().lower()
                specs.append({
                    "path": self._normalize_relative_path(path_value),
                    "kind": "file" if kind == "file" else "dir",
                })
            if specs:
                return tuple(specs)

        include_paths = manifest.get("include_paths") or self.DEFAULT_INCLUDE_PATHS
        fallback_specs = []
        for relative_path in self._normalize_include_paths(include_paths):
            kind = "file" if relative_path.as_posix() == "settings.ini" else "dir"
            fallback_specs.append({
                "path": relative_path,
                "kind": kind,
            })
        return tuple(fallback_specs)

    def _normalize_relative_path(self, relative_path):
        text = str(relative_path or "").strip().replace("\\", "/")
        if not text:
            raise ValueError("路径不能为空。")

        path = PurePosixPath(text)
        if path.is_absolute() or not path.parts:
            raise ValueError(f"无效的相对路径: {relative_path}")
        if any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError(f"无效的相对路径: {relative_path}")
        if path.parts[0].endswith(":"):
            raise ValueError(f"无效的相对路径: {relative_path}")

        return Path(*path.parts)

    def _normalize_archive_member(self, member_name):
        text = str(member_name or "").strip().replace("\\", "/")
        if not text:
            raise RuntimeBackupArchiveError("备份文件包含空路径条目。")

        member = PurePosixPath(text)
        if member.is_absolute() or not member.parts:
            raise RuntimeBackupArchiveError(f"备份文件包含无效路径: {member_name}")
        if any(part in {"", ".", ".."} for part in member.parts):
            raise RuntimeBackupArchiveError(f"备份文件包含无效路径: {member_name}")
        if member.parts[0].endswith(":"):
            raise RuntimeBackupArchiveError(f"备份文件包含无效路径: {member_name}")
        return member

    def _is_member_allowed(self, member, include_specs):
        for spec in include_specs:
            root = spec["path"]
            kind = spec["kind"]
            root_text = root.as_posix()
            member_text = member.as_posix()
            if kind == "file":
                if member_text == root_text:
                    return True
                continue

            root_parts = root.parts
            member_parts = member.parts
            if len(member_parts) < len(root_parts):
                continue
            if member_parts[: len(root_parts)] == root_parts:
                return True
        return False

    def _collect_backup_entries(self, include_specs):
        entries = []
        seen = set()
        for spec in include_specs:
            relative_root = spec["path"]
            kind = spec["kind"]
            source_root = self.runtime_root / relative_root
            if not source_root.exists():
                continue

            if kind == "file" or source_root.is_file():
                arcname = PurePosixPath(relative_root.as_posix())
                key = arcname.as_posix()
                if key not in seen:
                    entries.append((source_root, arcname))
                    seen.add(key)
                continue

            if not source_root.is_dir():
                continue

            for source_path in sorted(source_root.rglob("*")):
                if not source_path.is_file():
                    continue
                arcname = PurePosixPath(source_path.relative_to(self.runtime_root).as_posix())
                key = arcname.as_posix()
                if key in seen:
                    continue
                entries.append((source_path, arcname))
                seen.add(key)

        entries.sort(key=lambda item: item[1].as_posix())
        return entries

    def _build_manifest(self, include_specs, file_count):
        return {
            "schema": self.BACKUP_SCHEMA,
            "version": self.BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "runtime_root": str(self.runtime_root),
            "include_paths": [spec["path"].as_posix() for spec in include_specs],
            "include_items": [
                {
                    "path": spec["path"].as_posix(),
                    "kind": spec["kind"],
                }
                for spec in include_specs
            ],
            "file_count": int(file_count or 0),
        }

    def _read_manifest(self, archive):
        try:
            raw_manifest = archive.read(self.MANIFEST_NAME).decode("utf-8-sig")
        except KeyError as exc:
            raise RuntimeBackupArchiveError("备份文件缺少清单。") from exc
        except UnicodeDecodeError as exc:
            raise RuntimeBackupArchiveError("备份文件清单编码无效。") from exc

        try:
            manifest = json.loads(raw_manifest)
        except (TypeError, ValueError) as exc:
            raise RuntimeBackupArchiveError("备份文件清单格式无效。") from exc

        if not isinstance(manifest, dict):
            raise RuntimeBackupArchiveError("备份文件清单格式无效。")
        if str(manifest.get("schema", "") or "").strip() != self.BACKUP_SCHEMA:
            raise RuntimeBackupArchiveError("备份文件不是当前工具支持的备份格式。")
        return manifest

    def _collect_restore_entries(self, archive, include_specs):
        entries = []
        for info in archive.infolist():
            if info.is_dir():
                continue

            member = self._normalize_archive_member(info.filename)
            if member.as_posix() == self.MANIFEST_NAME:
                continue
            if not self._is_member_allowed(member, include_specs):
                raise RuntimeBackupArchiveError(f"备份文件包含不允许恢复的路径: {member.as_posix()}")
            entries.append(member)
        entries.sort(key=lambda item: item.as_posix())
        return entries

    def _extract_entries_to_staging(self, archive, entries, staging_root):
        for member in entries:
            target = staging_root / Path(*member.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member.as_posix(), "r") as source, target.open("wb") as target_file:
                shutil.copyfileobj(source, target_file)

    def _clear_include_roots(self, include_specs):
        for spec in include_specs:
            target = self.runtime_root / spec["path"]
            self._remove_target_path(target)

    def _remove_target_path(self, target):
        try:
            if not target.exists() and not target.is_symlink():
                return
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
        except FileNotFoundError:
            return

    def _copy_staging_to_runtime(self, staging_root):
        for source_path in sorted(staging_root.rglob("*")):
            if source_path.is_dir():
                continue
            relative_path = source_path.relative_to(staging_root)
            target_path = self.runtime_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            self._remove_target_path(target_path)
            shutil.copy2(source_path, target_path)

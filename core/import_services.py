from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizedTool:
    data: dict[str, Any]
    source: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImportReport:
    total: int = 0
    imported: int = 0
    skipped: int = 0
    updated: int = 0
    unknown_categories: int = 0
    icon_failures: int = 0
    placeholder_paths: int = 0
    source_path: str = ""
    source_url: str = ""
    detected_version: str = ""
    backup_path: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy_result(cls, result: dict | None) -> "ImportReport":
        result = dict(result or {})
        return cls(
            total=int(result.get("total", 0) or 0),
            imported=int(result.get("imported", 0) or 0),
            skipped=int(result.get("skipped", 0) or 0),
            updated=int(result.get("updated", 0) or 0),
            source_path=str(result.get("source_path", "") or ""),
            source_url=str(result.get("source_url", "") or ""),
            detected_version=str(result.get("detected_version", "") or ""),
            backup_path=str(result.get("backup_path", "") or ""),
            details=result,
        )

    def to_legacy_result(self) -> dict:
        payload = dict(self.details or {})
        payload.setdefault("total", self.total)
        payload.setdefault("imported", self.imported)
        payload.setdefault("skipped", self.skipped)
        if self.updated:
            payload.setdefault("updated", self.updated)
        if self.source_path:
            payload.setdefault("source_path", self.source_path)
        if self.source_url:
            payload.setdefault("source_url", self.source_url)
        if self.detected_version:
            payload.setdefault("detected_version", self.detected_version)
        if self.backup_path:
            payload.setdefault("backup_path", self.backup_path)
        payload.setdefault("unknown_categories", self.unknown_categories)
        payload.setdefault("icon_failures", self.icon_failures)
        payload.setdefault("placeholder_paths", self.placeholder_paths)
        return payload


class CategoryMapper:
    def __init__(self, legacy_exchange):
        self.legacy_exchange = legacy_exchange

    def resolve_assignment(self, categories, category_name, subcategory_name):
        return self.legacy_exchange._resolve_category_assignment(
            categories,
            category_name,
            subcategory_name,
        )


class ImportIconResolver:
    def __init__(self, legacy_exchange):
        self.legacy_exchange = legacy_exchange

    def resolve_tianhu_icon(self, raw_tool, final_path, is_web_tool, detected_version, allow_online_lookup=False):
        return self.legacy_exchange._resolve_tianhu_icon(
            raw_tool,
            final_path,
            is_web_tool,
            detected_version,
            allow_online_lookup=allow_online_lookup,
        )


class NativeConfigImporter:
    def __init__(self, legacy_exchange):
        self.legacy_exchange = legacy_exchange

    def import_file(self, file_path) -> ImportReport:
        return ImportReport.from_legacy_result(self.legacy_exchange._import_native_tools_legacy(file_path))


class OfficialSyncService:
    def __init__(self, legacy_exchange):
        self.legacy_exchange = legacy_exchange

    def sync_from_url(self, source_url, update_existing=True, cancel_requested=None, progress_callback=None) -> ImportReport:
        return ImportReport.from_legacy_result(
            self.legacy_exchange._sync_official_tools_from_url_legacy(
                source_url,
                update_existing=update_existing,
                cancel_requested=cancel_requested,
                progress_callback=progress_callback,
            )
        )


class TianhuImporter:
    def __init__(self, legacy_exchange, category_mapper=None, icon_resolver=None):
        self.legacy_exchange = legacy_exchange
        self.category_mapper = category_mapper or CategoryMapper(legacy_exchange)
        self.icon_resolver = icon_resolver or ImportIconResolver(legacy_exchange)

    def import_file(
        self,
        source_path,
        cancel_requested=None,
        progress_callback=None,
        download_missing_icons=False,
    ) -> ImportReport:
        return ImportReport.from_legacy_result(
            self.legacy_exchange._import_tianhu_tools_legacy(
                source_path,
                cancel_requested=cancel_requested,
                progress_callback=progress_callback,
                download_missing_icons=download_missing_icons,
            )
        )

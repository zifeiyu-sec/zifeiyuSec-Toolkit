from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.runtime_paths import get_runtime_root, is_frozen
from core.task_control import iter_response_chunks, raise_if_cancelled


class UpdateServiceError(RuntimeError):
    """Raised when update operations fail."""


class NoPublishedReleaseError(UpdateServiceError):
    """Raised when the configured release source has no published release yet."""


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    download_url: str
    asset_name: str = ""
    notes: str = ""
    release_url: str = ""
    published_at: str = ""
    sha256: str = ""
    source: str = "github"


def _normalize_version(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith(("v", "V")):
        text = text[1:]
    return text


def _version_tuple(value: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", _normalize_version(value))
    if not nums:
        return (0,)
    return tuple(int(item) for item in nums[:6])


def is_version_newer(latest: str, current: str) -> bool:
    left = _version_tuple(latest)
    right = _version_tuple(current)
    size = max(len(left), len(right))
    left = left + (0,) * (size - len(left))
    right = right + (0,) * (size - len(right))
    return left > right


def _format_asset_name_template(template: str, latest_version: str = "") -> str:
    text = str(template or "").strip()
    if not text:
        return ""

    version = _normalize_version(latest_version)
    version_with_v = f"v{version}" if version else ""
    return (
        text.replace("{version}", version)
        .replace("{version_with_v}", version_with_v)
        .replace("{latest_version}", version)
    ).strip()


def _is_zip_asset(asset: dict) -> bool:
    name = str(asset.get("name") or "").strip().casefold()
    download_url = str(asset.get("browser_download_url") or "").strip().casefold()
    return name.endswith(".zip") or download_url.endswith(".zip")


def _safe_zip_member_parts(name: str) -> list[str] | None:
    normalized = str(name or "").replace("\\", "/").strip()
    if not normalized or normalized.endswith("/"):
        return None
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:", normalized):
        raise UpdateServiceError(f"更新包包含不安全路径：{name}")

    parts = [part for part in normalized.split("/") if part]
    if not parts:
        return None
    if any(part in {".", ".."} for part in parts):
        raise UpdateServiceError(f"更新包包含不安全路径：{name}")
    if ":" in parts[0]:
        raise UpdateServiceError(f"更新包包含不安全路径：{name}")
    return parts


def _archive_payload_relative_names(member_names: list[str]) -> list[str]:
    payload_parts = []
    for member_name in member_names:
        parts = _safe_zip_member_parts(member_name)
        if not parts or parts[0] == "__MACOSX":
            continue
        payload_parts.append(parts)

    if not payload_parts:
        return []

    top_levels = {parts[0] for parts in payload_parts}
    strip_root = len(top_levels) == 1
    relative_names = []
    for parts in payload_parts:
        relative_parts = parts[1:] if strip_root else parts
        if relative_parts:
            relative_names.append("/".join(relative_parts))
    return relative_names


class UpdateService:
    DEFAULT_GITHUB_REPO = "zifeiyu-sec/zifeiyuSec-Toolkit"
    DEFAULT_GITEE_REPO = "zifeiyu-sec/zifeiyu-sec-toolkit"
    DEFAULT_ASSET_NAME_TEMPLATE = "ZifeiyuSec-win64-v{version}.zip"
    SOURCE_ENTRY_FILE = "main.py"
    REQUEST_TIMEOUT_SECONDS = 15
    DOWNLOAD_TIMEOUT_SECONDS = 120
    JSON_CHUNK_SIZE = 64 * 1024
    DOWNLOAD_CHUNK_SIZE = 256 * 1024

    def __init__(self, app_name: str, current_version: str, settings: Any, config_dir: str):
        self.app_name = str(app_name or "zifeiyu-toolkit")
        self.current_version = str(current_version or "0.0.0")
        self.settings = settings
        self.config_dir = Path(config_dir).resolve()
        self.update_root = self.config_dir / "updates"
        self.update_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def select_release_asset(
        assets: list[dict],
        preferred_name: str = "",
        latest_version: str = "",
        name_regex: str = "",
    ) -> dict | None:
        if not isinstance(assets, list):
            return None

        normalized_preferred = _format_asset_name_template(preferred_name, latest_version).casefold()
        if normalized_preferred:
            for asset in assets:
                if not _is_zip_asset(asset):
                    continue
                name = str(asset.get("name") or "").strip().casefold()
                if name == normalized_preferred:
                    return asset

        if name_regex:
            try:
                pattern = re.compile(str(name_regex), re.IGNORECASE)
            except re.error:
                pattern = None
            if pattern is not None:
                for asset in assets:
                    if not _is_zip_asset(asset):
                        continue
                    name = str(asset.get("name") or "").strip()
                    download_url = str(asset.get("browser_download_url") or "").strip()
                    if pattern.search(name) or pattern.search(download_url):
                        return asset

        zip_assets = []
        for asset in assets:
            if _is_zip_asset(asset):
                zip_assets.append(asset)

        if len(zip_assets) == 1:
            return zip_assets[0]
        return None

    def can_self_update(self) -> bool:
        return bool(self._get_update_mode())

    def get_update_mode(self) -> str:
        return self._get_update_mode()

    def _resolve_source_entry_path(self) -> Path | None:
        source_entry = get_runtime_root().resolve() / self.SOURCE_ENTRY_FILE
        if source_entry.is_file():
            return source_entry
        return None

    def _get_update_mode(self) -> str:
        if is_frozen():
            return "frozen"
        return ""

    def _report_progress(self, progress_callback, message: str) -> None:
        if callable(progress_callback):
            try:
                progress_callback(str(message or "").strip())
            except Exception:
                return

    def check_for_updates(self, cancel_requested=None, progress_callback=None) -> tuple[UpdateInfo | None, str]:
        raise_if_cancelled(cancel_requested, "已取消检查更新。")
        provider = self._get_update_provider()
        if provider == "manifest":
            manifest_url = self._setting("update/manifest_url", "").strip()
            self._report_progress(progress_callback, "正在获取更新清单...")
            info = self._check_with_manifest(
                manifest_url,
                cancel_requested=cancel_requested,
                progress_callback=progress_callback,
            )
        else:
            provider_label = "Gitee" if provider == "gitee" else "GitHub"
            self._report_progress(progress_callback, f"正在获取 {provider_label} Release 信息...")
            info = self._check_with_release_provider(
                provider,
                cancel_requested=cancel_requested,
                progress_callback=progress_callback,
            )

        raise_if_cancelled(cancel_requested, "已取消检查更新。")
        if not is_version_newer(info.latest_version, info.current_version):
            return None, f"当前已是最新版本（v{info.current_version}）。"

        return info, f"检测到新版本 v{info.latest_version}（当前 v{info.current_version}）。"

    def start_one_click_update(self, info: UpdateInfo, cancel_requested=None, progress_callback=None) -> str:
        raise_if_cancelled(cancel_requested, "已取消一键更新。")
        update_mode = self._get_update_mode()
        if not update_mode:
            raise UpdateServiceError("当前运行环境不支持一键更新：请使用打包发布版，源码运行请手动更新。")

        self._report_progress(progress_callback, "正在下载更新包...")
        zip_path, file_sha256 = self._download_update_archive(
            info,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )
        raise_if_cancelled(cancel_requested, "已取消一键更新。")
        self._report_progress(progress_callback, "正在校验更新包...")
        self._validate_update_archive(zip_path, update_mode)
        raise_if_cancelled(cancel_requested, "已取消一键更新。")
        self._report_progress(progress_callback, "正在准备更新会话...")
        session_path = self._prepare_session_file(info, zip_path, file_sha256, update_mode)
        helper_cmd = self._build_helper_command(session_path, update_mode)
        raise_if_cancelled(cancel_requested, "已取消一键更新。")
        self._report_progress(progress_callback, "正在启动更新器...")
        self._spawn_helper(helper_cmd)
        return (
            f"更新包已下载并启动更新器：{zip_path.name}\n"
            f"目标版本：v{info.latest_version}\n"
            "更新模式：打包模式\n"
            "程序将在关闭后自动更新并重启。"
        )

    def get_release_page_url(self) -> str:
        try:
            provider = self._get_update_provider()
        except UpdateServiceError:
            provider = self._setting("update/provider", "github").strip().casefold()
        if provider == "gitee":
            repo = self._get_repo_for_provider("gitee")
            return f"https://gitee.com/{repo}/releases"
        if provider == "manifest":
            release_page_url = self._setting("update/release_page_url", "").strip()
            if release_page_url:
                return release_page_url
        repo = self._get_repo_for_provider("github")
        return f"https://github.com/{repo}/releases"

    def _setting(self, key: str, default: Any) -> str:
        if self.settings is None:
            return str(default)
        try:
            value = self.settings.value(key, default)
            if value is None:
                return str(default)
            return str(value)
        except Exception:
            return str(default)

    def _build_user_agent(self) -> str:
        app_token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(self.app_name or "").strip()).strip("-")
        if not app_token:
            app_token = "zifeiyu-toolkit"

        version_token = re.sub(r"[^A-Za-z0-9._-]+", "-", _normalize_version(self.current_version)).strip("-")
        if not version_token:
            version_token = "0.0.0"
        return f"{app_token}/{version_token}"

    def _get_update_provider(self) -> str:
        provider = self._setting("update/provider", "").strip().casefold()
        manifest_url = self._setting("update/manifest_url", "").strip()
        if manifest_url and provider in {"", "manifest"}:
            return "manifest"
        if not provider:
            return "github"
        if provider not in {"github", "gitee", "manifest"}:
            raise UpdateServiceError("更新源配置无效：provider 只能是 github、gitee 或 manifest。")
        if provider == "manifest" and not manifest_url:
            raise UpdateServiceError("更新源配置无效：provider=manifest 时必须配置 manifest_url。")
        return provider

    def _get_repo_for_provider(self, provider: str) -> str:
        if provider == "gitee":
            repo = self._setting("update/gitee_repo", self.DEFAULT_GITEE_REPO).strip()
            return repo or self.DEFAULT_GITEE_REPO
        repo = self._setting("update/github_repo", self.DEFAULT_GITHUB_REPO).strip()
        return repo or self.DEFAULT_GITHUB_REPO

    def _get_release_api_url_for_provider(self, provider: str, repo: str) -> str:
        if provider == "gitee":
            return self._setting(
                "update/gitee_release_api_url",
                f"https://gitee.com/api/v5/repos/{repo}/releases/latest",
            ).strip()

        return (
            self._setting("update/github_release_api_url", "").strip()
            or self._setting(
                "update/release_api_url",
                f"https://api.github.com/repos/{repo}/releases/latest",
            ).strip()
        )

    def _select_update_asset(self, assets: list[dict], latest_version: str) -> dict | None:
        preferred_asset_name = self._setting("update/asset_name", "").strip()
        if not preferred_asset_name:
            preferred_asset_name = self.DEFAULT_ASSET_NAME_TEMPLATE
        asset_name_regex = self._setting("update/asset_name_regex", "").strip()
        return self.select_release_asset(
            assets,
            preferred_name=preferred_asset_name,
            latest_version=latest_version,
            name_regex=asset_name_regex,
        )

    def _check_with_manifest(self, manifest_url: str, cancel_requested=None, progress_callback=None) -> UpdateInfo:
        payload = self._fetch_json(
            manifest_url,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )
        if not isinstance(payload, dict):
            raise UpdateServiceError("更新清单格式错误：根对象必须为 JSON object。")

        candidate = payload
        platforms = payload.get("platforms")
        if isinstance(platforms, dict):
            candidate = (
                platforms.get("windows")
                or platforms.get("win")
                or platforms.get("win64")
                or payload
            )
            if not isinstance(candidate, dict):
                raise UpdateServiceError("更新清单格式错误：platforms.windows 必须为 object。")

        latest = _normalize_version(candidate.get("version") or payload.get("version"))
        download_url = str(
            candidate.get("url")
            or candidate.get("download_url")
            or payload.get("url")
            or payload.get("download_url")
            or ""
        ).strip()
        if not latest or not download_url:
            raise UpdateServiceError("更新清单缺少 version 或 download_url。")

        return UpdateInfo(
            current_version=self.current_version,
            latest_version=latest,
            download_url=download_url,
            asset_name=Path(urlparse(download_url).path).name,
            notes=str(candidate.get("notes") or payload.get("notes") or ""),
            release_url=str(candidate.get("release_url") or payload.get("release_url") or ""),
            published_at=str(candidate.get("published_at") or payload.get("published_at") or ""),
            sha256=str(candidate.get("sha256") or payload.get("sha256") or "").strip(),
            source="manifest",
        )

    def _check_with_github_release(self, cancel_requested=None, progress_callback=None) -> UpdateInfo:
        return self._check_with_release_provider(
            "github",
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )

    def _check_with_gitee_release(self, cancel_requested=None, progress_callback=None) -> UpdateInfo:
        return self._check_with_release_provider(
            "gitee",
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )

    def _check_with_release_provider(self, provider: str, cancel_requested=None, progress_callback=None) -> UpdateInfo:
        repo = self._get_repo_for_provider(provider)
        release_api_url = self._get_release_api_url_for_provider(provider, repo)
        if not release_api_url:
            raise UpdateServiceError("更新源配置无效：release_api_url 为空。")

        payload = self._fetch_json(
            release_api_url,
            cancel_requested=cancel_requested,
            progress_callback=progress_callback,
        )
        if not isinstance(payload, dict):
            raise UpdateServiceError("Release API 返回格式错误。")

        raw_tag = str(payload.get("tag_name") or payload.get("name") or "").strip()
        latest = _normalize_version(raw_tag)
        if not latest:
            raise UpdateServiceError("未从 Release 获取到可用版本号。")

        asset = self._select_update_asset(payload.get("assets") or [], latest)
        if not asset:
            raise UpdateServiceError("发现新版本，但未找到匹配的 zip 更新包。请检查 asset_name 或 asset_name_regex 配置。")

        download_url = str(asset.get("browser_download_url") or "").strip()
        asset_name = str(asset.get("name") or "").strip() or Path(urlparse(download_url).path).name
        if not download_url:
            raise UpdateServiceError("更新包下载地址无效。")

        release_url = str(payload.get("html_url") or "").strip()
        if not release_url and provider == "gitee":
            tag_for_url = raw_tag or f"v{latest}"
            release_url = f"https://gitee.com/{repo}/releases/tag/{tag_for_url}"

        return UpdateInfo(
            current_version=self.current_version,
            latest_version=latest,
            download_url=download_url,
            asset_name=asset_name,
            notes=str(payload.get("body") or ""),
            release_url=release_url,
            published_at=str(payload.get("published_at") or payload.get("created_at") or ""),
            source=provider,
        )

    def _fetch_json(self, url: str, cancel_requested=None, progress_callback=None) -> Any:
        raise_if_cancelled(cancel_requested, "已取消检查更新。")
        user_agent = self._build_user_agent()
        req = Request(
            url,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/vnd.github+json, application/json",
            },
        )
        try:
            with urlopen(req, timeout=self.REQUEST_TIMEOUT_SECONDS) as resp:
                self._report_progress(progress_callback, "正在读取更新响应...")
                raw = b"".join(
                    iter_response_chunks(
                        resp,
                        cancel_requested=cancel_requested,
                        chunk_size=self.JSON_CHUNK_SIZE,
                    )
                )
        except UnicodeEncodeError as exc:
            raise UpdateServiceError("更新请求头编码失败，请检查更新配置。") from exc
        except HTTPError as exc:
            if exc.code == 404 and "/releases/latest" in str(url):
                raise NoPublishedReleaseError("当前仓库还没有发布可用版本。请先在 GitHub Releases 发布版本，或配置 manifest 更新源。") from exc
            raise UpdateServiceError(f"更新请求失败（HTTP {exc.code}）：{url}") from exc
        except URLError as exc:
            raise UpdateServiceError(f"更新请求失败：{exc.reason}") from exc
        except OSError as exc:
            raise UpdateServiceError(f"更新请求失败：{exc}") from exc

        try:
            self._report_progress(progress_callback, "正在解析更新响应...")
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateServiceError("更新接口返回内容不是有效 JSON。") from exc

    def _download_update_archive(self, info: UpdateInfo, cancel_requested=None, progress_callback=None) -> tuple[Path, str]:
        raise_if_cancelled(cancel_requested, "已取消一键更新。")
        parsed_name = Path(urlparse(info.download_url).path).name
        filename = Path(info.asset_name or parsed_name or f"update_{info.latest_version}.zip").name
        target_path = self.update_root / f"{info.latest_version}_{filename}"
        temp_path = target_path.with_suffix(target_path.suffix + ".download")

        user_agent = self._build_user_agent()
        req = Request(
            info.download_url,
            headers={"User-Agent": user_agent},
        )
        sha256 = hashlib.sha256()
        try:
            with urlopen(req, timeout=self.DOWNLOAD_TIMEOUT_SECONDS) as resp:
                total_bytes = 0
                try:
                    total_bytes = int(resp.headers.get("Content-Length") or 0)
                except (TypeError, ValueError):
                    total_bytes = 0
                downloaded_bytes = 0
                last_report_bytes = -1
                with temp_path.open("wb") as f:
                    for chunk in iter_response_chunks(
                        resp,
                        cancel_requested=cancel_requested,
                        chunk_size=self.DOWNLOAD_CHUNK_SIZE,
                    ):
                        f.write(chunk)
                        sha256.update(chunk)
                        downloaded_bytes += len(chunk)
                        if downloaded_bytes == last_report_bytes:
                            continue
                        last_report_bytes = downloaded_bytes
                        downloaded_mb = downloaded_bytes / (1024 * 1024)
                        if total_bytes > 0:
                            total_mb = total_bytes / (1024 * 1024)
                            percent = min(downloaded_bytes / max(total_bytes, 1) * 100, 100.0)
                            self._report_progress(
                                progress_callback,
                                f"正在下载更新包... {percent:.0f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)",
                            )
                        else:
                            self._report_progress(
                                progress_callback,
                                f"正在下载更新包... {downloaded_mb:.1f} MB",
                            )
        except UnicodeEncodeError as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise UpdateServiceError("更新请求头编码失败，请检查更新配置。") from exc
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            if isinstance(exc, TimeoutError) or "timed out" in str(exc).lower():
                raise UpdateServiceError(
                    "下载更新包超时：GitHub Release 文件下载较慢，请检查网络或稍后重试。"
                ) from exc
            raise UpdateServiceError(f"下载更新包失败：{exc}") from exc
        except Exception:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise

        digest = sha256.hexdigest()
        if info.sha256 and digest.casefold() != info.sha256.casefold():
            temp_path.unlink(missing_ok=True)
            raise UpdateServiceError("更新包校验失败：SHA256 不匹配。")

        temp_path.replace(target_path)
        return target_path, digest

    def _validate_update_archive(self, zip_path: Path, update_mode: str) -> None:
        if update_mode != "frozen":
            raise UpdateServiceError("当前运行环境不支持一键更新：请使用打包发布版，源码运行请手动更新。")

        expected_executable = Path(sys.executable or "").name
        if not expected_executable:
            raise UpdateServiceError("更新包校验失败：无法识别当前程序入口。")

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                relative_names = _archive_payload_relative_names(zf.namelist())
        except zipfile.BadZipFile as exc:
            raise UpdateServiceError("更新包校验失败：zip 文件损坏或格式无效。") from exc

        if not relative_names:
            raise UpdateServiceError("更新包校验失败：更新包为空。")

        if any(part.casefold() == ".runtime" for name in relative_names for part in name.split("/")):
            raise UpdateServiceError("更新包校验失败：发布包不能包含 .runtime 用户数据目录。")

        expected = expected_executable.casefold()
        has_expected_executable = any(Path(name).name.casefold() == expected for name in relative_names)
        if not has_expected_executable:
            raise UpdateServiceError(f"更新包校验失败：未找到程序入口 {expected_executable}。")

    def _prepare_session_file(
        self,
        info: UpdateInfo,
        zip_path: Path,
        downloaded_sha256: str,
        update_mode: str,
    ) -> Path:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        app_root = get_runtime_root().resolve()
        session_path = self.update_root / f"session_{timestamp}.json"

        if update_mode != "frozen":
            raise UpdateServiceError("当前运行环境不支持一键更新：请使用打包发布版，源码运行请手动更新。")
        restart_cmd = [sys.executable]

        session = {
            "session_created_at": timestamp,
            "app_name": self.app_name,
            "current_version": info.current_version,
            "target_version": info.latest_version,
            "parent_pid": os.getpid(),
            "app_root": os.fspath(app_root),
            "zip_path": os.fspath(zip_path),
            "staging_dir": os.fspath(self.update_root / f"staging_{timestamp}"),
            "backup_dir": os.fspath(self.update_root / f"backup_{timestamp}"),
            "preserve_paths": [".runtime"],
            "restart_cmd": restart_cmd,
            "restart_cwd": os.fspath(app_root),
            "log_file": os.fspath(self.update_root / "update_worker.log"),
            "downloaded_sha256": downloaded_sha256,
            "expected_executable": Path(sys.executable or "").name,
            "package_format": update_mode,
        }
        with session_path.open("w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return session_path

    def _build_helper_command(self, session_path: Path, update_mode: str) -> list[str]:
        if update_mode != "frozen":
            raise UpdateServiceError("当前运行环境不支持一键更新：请使用打包发布版，源码运行请手动更新。")

        helper_dir = self.update_root / "helper"
        self._prepare_frozen_helper_runtime(helper_dir)
        helper_exe = helper_dir / "updater_helper.exe"
        return [os.fspath(helper_exe), "--run-updater", "--session", os.fspath(session_path)]

    def _prepare_frozen_helper_runtime(self, helper_dir: Path) -> None:
        update_root = self.update_root.resolve()
        helper_dir = helper_dir.resolve()
        try:
            if not helper_dir.is_relative_to(update_root):
                raise UpdateServiceError("打包模式一键更新失败：更新助手目录不在 updates 目录内。")
        except AttributeError:
            if update_root not in helper_dir.parents and helper_dir != update_root:
                raise UpdateServiceError("打包模式一键更新失败：更新助手目录不在 updates 目录内。")

        if helper_dir.exists():
            shutil.rmtree(helper_dir, ignore_errors=False)
        helper_dir.mkdir(parents=True, exist_ok=True)

        source_exe = Path(sys.executable or "").resolve()
        if not source_exe.is_file():
            raise UpdateServiceError("打包模式一键更新失败：未找到当前程序入口。")

        helper_exe = helper_dir / "updater_helper.exe"
        shutil.copy2(source_exe, helper_exe)

        source_internal = source_exe.parent / "_internal"
        if source_internal.is_dir():
            shutil.copytree(source_internal, helper_dir / "_internal", dirs_exist_ok=True)

    def _spawn_helper(self, command: list[str]) -> None:
        creationflags = 0
        if os.name == "nt":
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        try:
            subprocess.Popen(
                command,
                cwd=os.fspath(get_runtime_root()),
                close_fds=True,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise UpdateServiceError(f"启动更新器失败：{exc}") from exc

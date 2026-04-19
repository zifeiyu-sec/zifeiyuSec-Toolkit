import hashlib
import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from core.update_service import NoPublishedReleaseError, UpdateService, is_version_newer


class _FakeSettings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, default=None):
        return self.values.get(key, default)


class _FakeResponse:
    def __init__(self, chunks, headers=None, final_url="https://example.com/api"):
        self._chunks = list(chunks)
        self.headers = dict(headers or {})
        self._final_url = final_url

    def read(self, _size=-1):
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

    def geturl(self):
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class UpdateServiceHelperTests(unittest.TestCase):
    def test_is_version_newer_supports_v_prefix_and_padding(self):
        self.assertTrue(is_version_newer("v3.1.1", "3.1.0"))
        self.assertTrue(is_version_newer("3.2", "3.1.9"))
        self.assertFalse(is_version_newer("3.1.0", "v3.1"))
        self.assertFalse(is_version_newer("3.1.0", "3.1.0"))

    def test_is_version_newer_handles_non_numeric_text(self):
        self.assertTrue(is_version_newer("release-2026.4.2", "release-2026.4.1"))
        self.assertFalse(is_version_newer("stable", "stable"))

    def test_select_release_asset_prefers_explicit_name(self):
        assets = [
            {"name": "toolkit-linux.zip", "browser_download_url": "https://example.com/toolkit-linux.zip"},
            {"name": "toolkit-win.zip", "browser_download_url": "https://example.com/toolkit-win.zip"},
        ]
        picked = UpdateService.select_release_asset(assets, preferred_name="toolkit-win.zip")
        self.assertIsNotNone(picked)
        self.assertEqual("toolkit-win.zip", picked.get("name"))

    def test_select_release_asset_fallbacks_to_first_zip(self):
        assets = [
            {"name": "notes.txt", "browser_download_url": "https://example.com/notes.txt"},
            {"name": "toolkit-portable.zip", "browser_download_url": "https://example.com/toolkit-portable.zip"},
            {"name": "toolkit-src.tar.gz", "browser_download_url": "https://example.com/toolkit-src.tar.gz"},
        ]
        picked = UpdateService.select_release_asset(assets)
        self.assertIsNotNone(picked)
        self.assertEqual("toolkit-portable.zip", picked.get("name"))

    def test_select_release_asset_returns_none_when_zip_missing(self):
        assets = [
            {"name": "readme.md", "browser_download_url": "https://example.com/readme.md"},
        ]
        picked = UpdateService.select_release_asset(assets)
        self.assertIsNone(picked)

    def test_can_self_update_true_for_source_mode_with_main_entry(self):
        temp_path = make_test_dir("update_service_source_mode")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        with patch("core.update_service.is_frozen", return_value=False), patch(
            "core.update_service.get_runtime_root", return_value=temp_path
        ):
            (temp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
            service = UpdateService("toolkit", "3.1.0", settings=None, config_dir=str(temp_path))
            self.assertTrue(service.can_self_update())
            self.assertEqual("source", service.get_update_mode())

    def test_build_helper_command_for_source_mode_uses_python_and_main(self):
        temp_path = make_test_dir("update_service_helper")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        main_path = temp_path / "main.py"
        main_path.write_text("print('ok')\n", encoding="utf-8")
        service = UpdateService("toolkit", "3.1.0", settings=None, config_dir=str(temp_path))
        session_path = temp_path / "session.json"

        with patch("core.update_service.is_frozen", return_value=False), patch(
            "core.update_service.get_runtime_root", return_value=temp_path
        ):
            cmd = service._build_helper_command(session_path, "source")
            self.assertGreaterEqual(len(cmd), 5)
            self.assertEqual(Path(cmd[0]).resolve(), Path(sys.executable).resolve())
            self.assertEqual(Path(cmd[1]).resolve(), main_path.resolve())
            self.assertIn("--run-updater", cmd)
            self.assertIn("--session", cmd)
            self.assertEqual(cmd[-1], str(session_path))

    def test_prepare_session_file_source_mode_sets_python_restart_command(self):
        temp_path = make_test_dir("update_service_session")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        main_path = temp_path / "main.py"
        main_path.write_text("print('ok')\n", encoding="utf-8")
        zip_path = temp_path / "update.zip"
        zip_path.write_bytes(b"dummy")
        service = UpdateService("toolkit", "3.1.0", settings=None, config_dir=str(temp_path))

        info = type(
            "Info",
            (),
            {"current_version": "3.1.0", "latest_version": "3.1.1"},
        )()

        with patch("core.update_service.is_frozen", return_value=False), patch(
            "core.update_service.get_runtime_root", return_value=temp_path
        ):
            session_path = service._prepare_session_file(info, zip_path, "abc123", "source")
            payload = json.loads(session_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("restart_cmd"), [sys.executable, str(main_path)])

    def test_check_for_updates_reads_manifest_via_urlopen(self):
        temp_path = make_test_dir("update_service_manifest")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        settings = _FakeSettings({"update/manifest_url": "https://example.com/manifest.json"})
        service = UpdateService("toolkit", "3.1.0", settings=settings, config_dir=str(temp_path))

        payload = {
            "version": "3.1.1",
            "download_url": "https://example.com/toolkit.zip",
            "notes": "hello",
            "release_url": "https://example.com/release",
        }
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        with patch("core.update_service.urlopen", return_value=_FakeResponse([raw])):
            info, message = service.check_for_updates()

        self.assertEqual("3.1.1", info.latest_version)
        self.assertEqual("https://example.com/toolkit.zip", info.download_url)
        self.assertIn("检测到新版本", message)

    def test_check_for_updates_raises_for_invalid_json_response(self):
        temp_path = make_test_dir("update_service_invalid_json")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        settings = _FakeSettings({"update/manifest_url": "https://example.com/manifest.json"})
        service = UpdateService("toolkit", "3.1.0", settings=settings, config_dir=str(temp_path))

        with patch("core.update_service.urlopen", return_value=_FakeResponse([b"{not-json"])):  # type: ignore[arg-type]
            with self.assertRaisesRegex(RuntimeError, "有效 JSON"):
                service.check_for_updates()

    def test_check_for_updates_reports_no_published_release_clearly(self):
        temp_path = make_test_dir("update_service_no_release")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        service = UpdateService("toolkit", "3.1.0", settings=None, config_dir=str(temp_path))
        error = HTTPError(
            "https://api.github.com/repos/example/toolkit/releases/latest",
            404,
            "Not Found",
            hdrs=None,
            fp=None,
        )

        with patch("core.update_service.urlopen", side_effect=error):
            with self.assertRaisesRegex(NoPublishedReleaseError, "还没有发布可用版本"):
                service.check_for_updates()

    def test_download_update_archive_streams_payload_and_reports_progress(self):
        temp_path = make_test_dir("update_service_download")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        service = UpdateService("toolkit", "3.1.0", settings=None, config_dir=str(temp_path))
        info = type(
            "Info",
            (),
            {
                "download_url": "https://example.com/toolkit.zip",
                "asset_name": "toolkit.zip",
                "latest_version": "3.1.1",
                "sha256": "",
            },
        )()

        progress_messages = []
        with patch(
            "core.update_service.urlopen",
            return_value=_FakeResponse([b"abc", b"def"], headers={"Content-Length": "6"}),
        ):
            zip_path, digest = service._download_update_archive(
                info,
                progress_callback=progress_messages.append,
            )

        self.assertTrue(zip_path.exists())
        self.assertEqual(b"abcdef", zip_path.read_bytes())
        self.assertEqual(hashlib.sha256(b"abcdef").hexdigest(), digest)
        self.assertTrue(any("下载更新包" in message for message in progress_messages))

    def test_download_update_archive_cleans_temp_file_when_request_fails(self):
        temp_path = make_test_dir("update_service_download_fail")
        self.addCleanup(lambda: cleanup_test_dir(temp_path))
        service = UpdateService("toolkit", "3.1.0", settings=None, config_dir=str(temp_path))
        info = type(
            "Info",
            (),
            {
                "download_url": "https://example.com/toolkit.zip",
                "asset_name": "toolkit.zip",
                "latest_version": "3.1.1",
                "sha256": "",
            },
        )()

        with patch("core.update_service.urlopen", side_effect=URLError("offline")):
            with self.assertRaisesRegex(RuntimeError, "下载更新包失败"):
                service._download_update_archive(info)

        self.assertEqual([], list((temp_path / "updates").glob("*.download")))


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import Mock, patch

from PyQt5.QtCore import QCoreApplication

from _support import cleanup_test_dir, make_test_dir
from core.path_status_service import (
    PathStatus,
    PathStatusResult,
    PathStatusService,
    build_path_status_cache_key,
    is_placeholder_path,
    resolve_path_status,
)


class PathStatusServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.workspace = make_test_dir(f"path_status_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.workspace))

    def test_placeholder_path_reports_unconfigured(self):
        result = resolve_path_status({"path": "CHANGE_ME_LOCAL_PATH"}, base_dir=self.workspace)

        self.assertTrue(is_placeholder_path("CHANGE_ME_LOCAL_PATH"))
        self.assertEqual(PathStatus.UNCONFIGURED, result.status)
        self.assertIsNone(result.available)

    def test_existing_relative_path_reports_available(self):
        tool_path = self.workspace / "tools" / "demo.exe"
        tool_path.parent.mkdir(parents=True, exist_ok=True)
        tool_path.write_text("stub", encoding="utf-8")

        result = resolve_path_status({"path": "tools/demo.exe"}, base_dir=self.workspace)

        self.assertEqual(PathStatus.AVAILABLE, result.status)
        self.assertTrue(result.available)
        self.assertEqual(os.fspath(tool_path), result.resolved_path)

    def test_path_command_uses_resolver_result(self):
        command_path = self.workspace / "bin" / "nmap.exe"
        command_path.parent.mkdir(parents=True, exist_ok=True)
        command_path.write_text("stub", encoding="utf-8")

        with patch("core.path_status_service.resolve_accessible_path_value", return_value=command_path):
            result = resolve_path_status({"path": "nmap"}, base_dir=self.workspace)

        self.assertEqual(PathStatus.AVAILABLE, result.status)
        self.assertTrue(result.available)

    def test_inaccessible_drive_or_path_error_reports_missing(self):
        def failing_resolver(_path, base_dir=None):
            raise OSError("drive is not accessible")

        result = resolve_path_status(
            {"path": r"Z:\missing\tool.exe"},
            base_dir=self.workspace,
            path_resolver=failing_resolver,
        )

        self.assertEqual(PathStatus.MISSING, result.status)
        self.assertFalse(result.available)
        self.assertIn("drive", result.error)

    def test_network_unc_path_is_deferred_without_resolver_call(self):
        resolver = Mock(side_effect=AssertionError("resolver should not be called"))

        result = resolve_path_status(
            {"path": r"\\unavailable-host\share\tool.exe"},
            base_dir=self.workspace,
            path_resolver=resolver,
        )

        resolver.assert_not_called()
        self.assertEqual(PathStatus.MISSING, result.status)
        self.assertFalse(result.available)

    def test_timeout_status_is_reported_when_resolver_exceeds_budget(self):
        tool_path = self.workspace / "slow.exe"
        tool_path.write_text("stub", encoding="utf-8")
        clock_values = iter([0.0, 1.0])

        result = resolve_path_status(
            {"path": "slow.exe"},
            base_dir=self.workspace,
            timeout_seconds=0.01,
            path_resolver=lambda _path, base_dir=None: tool_path,
            clock=lambda: next(clock_values),
        )

        self.assertEqual(PathStatus.TIMEOUT, result.status)
        self.assertIsNone(result.available)

    def test_cache_and_cancelled_generation_do_not_publish_stale_result(self):
        service = PathStatusService(ttl_seconds=30.0)
        cache_key = build_path_status_cache_key({"path": "missing.exe"}, self.workspace)
        stale = PathStatusResult(
            cache_key=cache_key,
            status=PathStatus.MISSING,
            available=False,
            request_id=7,
        )

        service.cancel_generation(7)
        service._on_worker_resolved(stale)

        self.assertIsNone(service.get_cached(cache_key))

        fresh = PathStatusResult(
            cache_key=cache_key,
            status=PathStatus.AVAILABLE,
            available=True,
            request_id=8,
        )
        service._on_worker_resolved(fresh)

        self.assertEqual(fresh, service.get_cached(cache_key))


if __name__ == "__main__":
    unittest.main()

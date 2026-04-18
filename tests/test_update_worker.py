import json
import sys
import unittest
import zipfile
from unittest.mock import ANY, patch

from _support import cleanup_test_dir, make_test_dir
from core.update_worker import run_updater_session


class UpdateWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp_path = make_test_dir(f"update_worker_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.temp_path))

    def _build_update_zip(self, payload_root):
        zip_path = self.temp_path / "update.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for path in payload_root.rglob("*"):
                zf.write(path, path.relative_to(self.temp_path / "payload"))
        return zip_path

    def test_run_updater_session_removes_obsolete_top_level_entries_and_preserves_runtime(self):
        app_root = self.temp_path / "app"
        app_root.mkdir()
        (app_root / "main.py").write_text('print("old")\n', encoding="utf-8")
        (app_root / "old.txt").write_text("obsolete\n", encoding="utf-8")
        (app_root / ".runtime").mkdir()
        (app_root / ".runtime" / "keep.txt").write_text("keep\n", encoding="utf-8")

        payload_root = self.temp_path / "payload" / "release"
        payload_root.mkdir(parents=True)
        (payload_root / "main.py").write_text('print("new")\n', encoding="utf-8")
        (payload_root / "new.txt").write_text("fresh\n", encoding="utf-8")
        zip_path = self._build_update_zip(payload_root)

        session_path = self.temp_path / "session.json"
        session_payload = {
            "app_root": str(app_root.resolve()),
            "zip_path": str(zip_path.resolve()),
            "staging_dir": str((self.temp_path / "staging").resolve()),
            "backup_dir": str((self.temp_path / "backup").resolve()),
            "log_file": str((self.temp_path / "update.log").resolve()),
            "parent_pid": 0,
            "preserve_paths": [".runtime"],
            "restart_cmd": [sys.executable, "-c", "print('restart')"],
            "restart_cwd": str(app_root.resolve()),
        }
        session_path.write_text(json.dumps(session_payload, ensure_ascii=False), encoding="utf-8")

        with patch("core.update_worker.subprocess.Popen") as popen_mock:
            exit_code = run_updater_session(session_path)

        self.assertEqual(0, exit_code)
        self.assertEqual('print("new")\n', (app_root / "main.py").read_text(encoding="utf-8"))
        self.assertTrue((app_root / "new.txt").exists())
        self.assertFalse((app_root / "old.txt").exists())
        self.assertEqual("keep\n", (app_root / ".runtime" / "keep.txt").read_text(encoding="utf-8"))
        self.assertTrue((self.temp_path / "backup" / "old.txt").exists())
        popen_mock.assert_called_once_with(
            [sys.executable, "-c", "print('restart')"],
            cwd=str(app_root.resolve()),
            close_fds=True,
            creationflags=ANY,
        )


if __name__ == "__main__":
    unittest.main()

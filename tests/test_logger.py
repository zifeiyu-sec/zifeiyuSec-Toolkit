import os
import unittest
from datetime import datetime

from _support import cleanup_test_dir, make_test_dir
from core.logger import get_current_log_file_path, get_latest_log_file_path, list_log_files


class LoggerHelperTests(unittest.TestCase):
    def setUp(self):
        self.log_dir = make_test_dir(f"logger_helpers_{self._testMethodName}") / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: cleanup_test_dir(self.log_dir.parent))

    def test_current_and_latest_log_path_helpers(self):
        current_path = get_current_log_file_path(log_dir=self.log_dir, at=datetime(2026, 5, 1, 12, 0, 0))
        self.assertEqual("zifeiyuSec_20260501.log", current_path.name)

        older = self.log_dir / "zifeiyuSec_20260501.log"
        newer = self.log_dir / "zifeiyuSec_20260502.log"
        older.write_text("older", encoding="utf-8")
        newer.write_text("newer", encoding="utf-8")
        os.utime(older, (1_700_000_000, 1_700_000_000))
        os.utime(newer, (1_800_000_000, 1_800_000_000))

        self.assertEqual([newer, older], list_log_files(log_dir=self.log_dir))
        self.assertEqual(newer, get_latest_log_file_path(log_dir=self.log_dir))


if __name__ == "__main__":
    unittest.main()

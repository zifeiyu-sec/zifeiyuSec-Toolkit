import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "repo_sanity_check.py"
SPEC = importlib.util.spec_from_file_location("repo_sanity_check", SCRIPT_PATH)
repo_sanity_check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repo_sanity_check)


class RepoSanityCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = make_test_dir(f"repo_sanity_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.temp_root))

    def test_shipped_tool_data_rejects_runtime_state(self):
        data_dir = self.temp_root / "data"
        data_dir.mkdir(parents=True)
        (data_dir / "tools.json").write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "id": 1,
                            "name": "Runtime Tool",
                            "is_favorite": True,
                            "usage_count": 7,
                            "last_used": "2026-05-01T00:00:00Z",
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        errors = []
        with patch.object(repo_sanity_check, "ROOT", self.temp_root):
            repo_sanity_check.check_shipped_tool_data(errors)

        self.assertEqual(1, len(errors))
        self.assertIn("包含运行时状态", errors[0])
        self.assertIn("1:Runtime Tool", errors[0])

    def test_text_encoding_artifacts_reports_mojibake(self):
        docs_dir = self.temp_root / "docs"
        docs_dir.mkdir(parents=True)
        bad_text = "category_name: " + "\u93af\u5440\u6beb\u59e4\u6e1a\ufe79\u7642\n"
        (docs_dir / "bad.md").write_text(bad_text, encoding="utf-8")

        errors = []
        with patch.object(repo_sanity_check, "ROOT", self.temp_root):
            repo_sanity_check.check_text_encoding_artifacts(errors)

        self.assertEqual(1, len(errors))
        self.assertIn("疑似乱码", errors[0])
        self.assertIn("docs", errors[0])


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path

from _support import cleanup_test_dir, make_test_dir
from core.data_manager_qt import ToolsLoadWorker


class ToolsLoadWorkerTests(unittest.TestCase):
    def setUp(self):
        self.workspace = make_test_dir(f"tools_load_worker_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.workspace))

    def test_run_prefers_aggregate_tools_file_over_split_files(self):
        tools_file = self.workspace / "tools.json"
        split_dir = self.workspace / "tools"
        split_dir.mkdir(parents=True, exist_ok=True)

        tools_file.write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "id": 1,
                            "name": "Aggregate Tool",
                            "path": "tools/aggregate.exe",
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (split_dir / "99_uncategorized.json").write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "id": 2,
                            "name": "Split Tool",
                            "path": "tools/split.exe",
                        }
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        results = []
        errors = []
        worker = ToolsLoadWorker(str(tools_file), str(split_dir), None, None)
        worker.finished.connect(results.append)
        worker.error.connect(errors.append)

        worker.run()

        self.assertEqual([], errors)
        self.assertEqual(1, len(results))
        self.assertEqual(["Aggregate Tool"], [tool["name"] for tool in results[0]])


if __name__ == "__main__":
    unittest.main()

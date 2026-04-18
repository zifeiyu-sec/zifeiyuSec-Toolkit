import json
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from core import runtime_paths


class RuntimePathsTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = make_test_dir(f"runtime_paths_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.temp_root))

    def test_migrate_legacy_runtime_layout_copies_mutable_files(self):
        (self.temp_root / "data").mkdir(parents=True, exist_ok=True)
        (self.temp_root / "data" / "tools.json").write_text('{"tools": [{"name": "demo"}]}', encoding="utf-8")
        (self.temp_root / "resources" / "notes").mkdir(parents=True, exist_ok=True)
        (self.temp_root / "resources" / "notes" / "demo.md").write_text("# demo\n", encoding="utf-8")

        with patch("core.runtime_paths.get_runtime_root", return_value=self.temp_root):
            state_root = runtime_paths.migrate_legacy_runtime_layout()

        self.assertEqual(self.temp_root / ".runtime", state_root)
        self.assertTrue((state_root / "data" / "tools.json").exists())
        self.assertTrue((state_root / "resources" / "notes" / "demo.md").exists())

    def test_template_category_icons_resolve_for_file_based_entries(self):
        repo_root = Path(__file__).resolve().parents[1]
        payload = json.loads((repo_root / "data" / "categories.json").read_text(encoding="utf-8"))

        missing = []
        for category in payload.get("categories", []):
            icon_value = str(category.get("icon") or "").strip()
            if not icon_value or "." not in icon_value:
                continue
            if runtime_paths.resolve_icon_path_value(icon_value) is None:
                missing.append(f"{category.get('id')}:{icon_value}")

        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()

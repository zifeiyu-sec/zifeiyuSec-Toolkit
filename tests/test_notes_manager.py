import shutil
import tempfile
import unittest
from pathlib import Path

from core.notes_manager import NotesManager


class TestNotesManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="notes-manager-test-"))
        self.manager = NotesManager(repo_root=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_note_uses_tool_id_based_path(self):
        saved = self.manager.save_note("hello", tool_id=123, tool_name="Nuclei")
        self.assertTrue(saved)
        self.assertTrue((self.temp_dir / "resources" / "notes" / "tool_123.md").exists())
        self.assertEqual("hello", self.manager.load_note(tool_id=123, tool_name="Nuclei"))

    def test_legacy_note_is_migrated_to_tool_id_path(self):
        legacy_path = self.temp_dir / "resources" / "notes" / "Nuclei.md"
        legacy_path.write_text("legacy", encoding="utf-8")

        content = self.manager.load_note(tool_id=123, tool_name="Nuclei")
        self.assertEqual("legacy", content)
        self.assertTrue((self.temp_dir / "resources" / "notes" / "tool_123.md").exists())
        self.assertEqual("legacy", (self.temp_dir / "resources" / "notes" / "tool_123.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

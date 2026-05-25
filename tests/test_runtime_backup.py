import json
import os
import zipfile
import unittest
from pathlib import Path

from _support import cleanup_test_dir, make_test_dir
from core.runtime_backup import RuntimeBackupArchiveError, RuntimeBackupService


class RuntimeBackupServiceTests(unittest.TestCase):
    def setUp(self):
        self.runtime_root = make_test_dir(f"runtime_backup_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.runtime_root))
        self._seed_runtime_state()
        self.service = RuntimeBackupService(self.runtime_root)

    def _seed_runtime_state(self):
        (self.runtime_root / "settings.ini").write_text(
            "[General]\ntheme=dark_green\n",
            encoding="utf-8",
        )

        data_dir = self.runtime_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "tools.json").write_text(
            json.dumps({"tools": [{"id": 1, "name": "Demo Tool"}]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        notes_dir = self.runtime_root / "resources" / "notes"
        (notes_dir / "_attachments" / "tool_1").mkdir(parents=True, exist_ok=True)
        (notes_dir / "tool_1.md").write_text("# Demo Note\n", encoding="utf-8")
        (notes_dir / "_attachments" / "tool_1" / "attachment.txt").write_text("attachment", encoding="utf-8")

        images_dir = self.runtime_root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "bg.png").write_text("image-bytes", encoding="utf-8")

        logs_dir = self.runtime_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        (logs_dir / "ignored.log").write_text("ignore me", encoding="utf-8")

        updates_dir = self.runtime_root / "updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        (updates_dir / "ignored.txt").write_text("ignore me", encoding="utf-8")

    def test_create_backup_only_includes_runtime_data(self):
        backup_path = self.runtime_root / "backups" / "manual" / "snapshot.zip"
        result = self.service.create_backup(str(backup_path))

        self.assertEqual(str(backup_path), result["backup_path"])
        self.assertEqual(5, result["file_count"])

        with zipfile.ZipFile(backup_path, "r") as archive:
            names = set(archive.namelist())

        self.assertIn("backup_manifest.json", names)
        self.assertIn("settings.ini", names)
        self.assertIn("data/tools.json", names)
        self.assertIn("resources/notes/tool_1.md", names)
        self.assertIn("resources/notes/_attachments/tool_1/attachment.txt", names)
        self.assertIn("images/bg.png", names)
        self.assertFalse(any(name.startswith("logs/") for name in names))
        self.assertFalse(any(name.startswith("updates/") for name in names))

    def test_restore_backup_replaces_runtime_scope_and_keeps_safety_copy(self):
        backup_path = self.runtime_root / "backups" / "manual" / "snapshot.zip"
        self.service.create_backup(str(backup_path))

        original_settings = (self.runtime_root / "settings.ini").read_text(encoding="utf-8")
        original_tool_payload = (self.runtime_root / "data" / "tools.json").read_text(encoding="utf-8")
        original_note = (self.runtime_root / "resources" / "notes" / "tool_1.md").read_text(encoding="utf-8")

        (self.runtime_root / "settings.ini").write_text("[General]\ntheme=red_orange\n", encoding="utf-8")
        (self.runtime_root / "data" / "tools.json").write_text(
            json.dumps({"tools": [{"id": 1, "name": "Mutated"}]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        stale_file = self.runtime_root / "data" / "tools" / "stale.json"
        stale_file.parent.mkdir(parents=True, exist_ok=True)
        stale_file.write_text("stale", encoding="utf-8")
        (self.runtime_root / "resources" / "notes" / "tool_1.md").write_text("# Mutated\n", encoding="utf-8")

        result = self.service.restore_backup(str(backup_path))

        self.assertEqual(str(backup_path), result["backup_path"])
        self.assertEqual(5, result["restored_files"])
        self.assertTrue(Path(result["safety_backup_path"]).exists())
        self.assertEqual(original_settings, (self.runtime_root / "settings.ini").read_text(encoding="utf-8"))
        self.assertEqual(original_tool_payload, (self.runtime_root / "data" / "tools.json").read_text(encoding="utf-8"))
        self.assertEqual(original_note, (self.runtime_root / "resources" / "notes" / "tool_1.md").read_text(encoding="utf-8"))
        self.assertFalse(stale_file.exists())
        self.assertTrue((self.runtime_root / "logs" / "ignored.log").exists())
        self.assertTrue((self.runtime_root / "updates" / "ignored.txt").exists())

    def test_restore_backup_rejects_unsafe_paths(self):
        bad_backup = self.runtime_root / "bad.zip"
        manifest = {
            "schema": self.service.BACKUP_SCHEMA,
            "version": self.service.BACKUP_VERSION,
            "include_paths": ["data"],
            "file_count": 1,
        }
        with zipfile.ZipFile(bad_backup, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("backup_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("../evil.txt", "evil")

        with self.assertRaises(RuntimeBackupArchiveError):
            self.service.restore_backup(str(bad_backup), create_safety_backup=False)


if __name__ == "__main__":
    unittest.main()

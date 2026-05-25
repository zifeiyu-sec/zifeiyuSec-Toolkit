import unittest
from unittest.mock import Mock

from core.import_services import (
    CategoryMapper,
    ImportIconResolver,
    ImportReport,
    NativeConfigImporter,
    NormalizedTool,
    OfficialSyncService,
    TianhuImporter,
)


class ImportServiceTests(unittest.TestCase):
    def test_import_report_round_trips_legacy_result(self):
        report = ImportReport.from_legacy_result(
            {
                "total": 3,
                "imported": 2,
                "skipped": 1,
                "source_path": "tools.json",
                "detected_version": "2.0",
            }
        )

        payload = report.to_legacy_result()

        self.assertEqual(3, report.total)
        self.assertEqual(2, payload["imported"])
        self.assertEqual("2.0", payload["detected_version"])
        self.assertIn("unknown_categories", payload)

    def test_normalized_tool_holds_data_and_warnings(self):
        normalized = NormalizedTool({"name": "Demo"}, source="native", warnings=["missing icon"])

        self.assertEqual("Demo", normalized.data["name"])
        self.assertEqual(["missing icon"], normalized.warnings)

    def test_native_importer_delegates_to_legacy_engine(self):
        legacy = Mock()
        legacy._import_native_tools_legacy.return_value = {"total": 1, "imported": 1}

        report = NativeConfigImporter(legacy).import_file("native.json")

        self.assertEqual(1, report.imported)
        legacy._import_native_tools_legacy.assert_called_once_with("native.json")

    def test_official_sync_service_delegates_to_legacy_engine(self):
        legacy = Mock()
        legacy._sync_official_tools_from_url_legacy.return_value = {"total": 1, "updated": 1}

        report = OfficialSyncService(legacy).sync_from_url("https://example.com/tools.json", update_existing=False)

        self.assertEqual(1, report.updated)
        legacy._sync_official_tools_from_url_legacy.assert_called_once()

    def test_tianhu_importer_delegates_to_legacy_engine(self):
        legacy = Mock()
        legacy._import_tianhu_tools_legacy.return_value = {"total": 2, "imported": 2, "detected_version": "3.0"}

        report = TianhuImporter(legacy).import_file("tianhu.json", download_missing_icons=True)

        self.assertEqual("3.0", report.detected_version)
        legacy._import_tianhu_tools_legacy.assert_called_once()

    def test_mapper_and_icon_resolver_delegate_specific_boundaries(self):
        legacy = Mock()
        legacy._resolve_category_assignment.return_value = (1, 101, "Category", "Sub")
        legacy._resolve_tianhu_icon.return_value = "icon.png"

        self.assertEqual(
            (1, 101, "Category", "Sub"),
            CategoryMapper(legacy).resolve_assignment([], "Category", "Sub"),
        )
        self.assertEqual(
            "icon.png",
            ImportIconResolver(legacy).resolve_tianhu_icon({}, "path", False, "2.0"),
        )


if __name__ == "__main__":
    unittest.main()

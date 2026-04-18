import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "create_desktop_shortcut.py"
SPEC = importlib.util.spec_from_file_location("create_desktop_shortcut", SCRIPT_PATH)
create_desktop_shortcut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(create_desktop_shortcut)


class CreateDesktopShortcutTests(unittest.TestCase):
    def setUp(self):
        self.temp_root = make_test_dir("shortcut_tests")
        self.addCleanup(lambda: cleanup_test_dir(self.temp_root))

    def test_build_shortcut_arguments_quotes_path_with_spaces(self):
        main_py = Path(r"S:\code\Tools\zifeiyuSec2.0 - 副本\main.py")

        arguments = create_desktop_shortcut.build_shortcut_arguments(main_py)

        self.assertEqual(arguments, f'"{main_py}"')

    def test_resolve_icon_prefers_ico_over_png(self):
        root = self.temp_root / "icons"
        root.mkdir(parents=True, exist_ok=True)
        (root / "image.png").write_bytes(b"png")
        (root / "image.ico").write_bytes(b"ico")
        (root / "favicon.ico").write_bytes(b"fav")

        icon = create_desktop_shortcut.resolve_icon(root)

        self.assertEqual(icon, root / "image.ico")

    def test_get_desktop_path_prefers_windows_shell_directory(self):
        shell_dir = self.temp_root / "shell_desktop"
        home_dir = self.temp_root / "home"
        shell_dir.mkdir(parents=True, exist_ok=True)
        (home_dir / "Desktop").mkdir(parents=True, exist_ok=True)

        with patch.object(
            create_desktop_shortcut,
            "_get_windows_desktop_directory",
            return_value=str(shell_dir),
        ), patch.dict(
            "os.environ",
            {"USERPROFILE": str(home_dir)},
            clear=False,
        ):
            desktop = create_desktop_shortcut.get_desktop_path()

        self.assertEqual(desktop, str(shell_dir))

import unittest
from unittest.mock import Mock

from _support import cleanup_test_dir, make_test_dir
from ui.tool_card_actions_mixin import ToolCardActionsMixin


class _DummyWindow:
    def __init__(self, config_dir):
        self.config_dir = str(config_dir)


class _DummyMixin(ToolCardActionsMixin):
    def __init__(self, window):
        self._window = window

    def window(self):
        return self._window


class ToolCardActionsMixinTests(unittest.TestCase):
    def setUp(self):
        self.workspace = make_test_dir(f"tool_card_actions_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.workspace))

    def test_open_command_line_resolves_relative_working_directory_against_config_dir(self):
        tools_dir = self.workspace / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        mixin = _DummyMixin(_DummyWindow(self.workspace))
        service_mock = Mock()
        mixin._get_tool_launch_service = Mock(return_value=service_mock)

        mixin.open_command_line(tool_data={"path": "nmap", "working_directory": "tools"})

        service_mock.open_terminal.assert_called_once_with(
            working_dir=str(tools_dir),
            base_dir=str(self.workspace),
        )


if __name__ == "__main__":
    unittest.main()

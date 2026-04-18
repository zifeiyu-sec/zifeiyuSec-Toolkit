from PyQt5.QtCore import QObject, QThread, pyqtSignal

from core.data_manager import _get_tools_state_token, _load_tools_from_storage


class ToolsLoadWorker(QObject):
    """Qt worker for async tool loading."""

    finished = pyqtSignal(list)
    error = pyqtSignal(Exception)

    def __init__(self, tools_file, tools_split_dir, tools_cache, last_tools_modified):
        super().__init__()
        self.tools_file = tools_file
        self.tools_split_dir = tools_split_dir
        self.tools_cache = tools_cache
        self.last_tools_modified = last_tools_modified

    def run(self):
        try:
            current_modified = _get_tools_state_token(self.tools_file, self.tools_split_dir)
            if self.tools_cache is not None and self.last_tools_modified == current_modified:
                self.finished.emit(self.tools_cache)
                return

            if not current_modified:
                self.finished.emit([])
                return

            self.finished.emit(_load_tools_from_storage(self.tools_file, self.tools_split_dir))
        except Exception as e:
            self.error.emit(e)

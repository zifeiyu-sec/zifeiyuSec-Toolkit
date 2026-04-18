from __future__ import annotations
import inspect
import threading

from PyQt5.QtCore import QObject, pyqtSignal

from core.task_control import OperationCancelledError


class CallableWorker(QObject):
    """Run a callable inside a QThread and emit its result."""

    finished = pyqtSignal(object)
    error = pyqtSignal(object)
    progress = pyqtSignal(str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._cancel_event = threading.Event()

    def request_cancellation(self):
        self._cancel_event.set()

    def is_cancellation_requested(self) -> bool:
        return self._cancel_event.is_set()

    def _supports_parameter(self, parameter_name: str) -> bool:
        try:
            signature = inspect.signature(self._func)
        except (TypeError, ValueError):
            return False

        for parameter in signature.parameters.values():
            if parameter.kind == inspect.Parameter.VAR_KEYWORD:
                return True
            if parameter.name == parameter_name:
                return True
        return False

    def run(self):
        if self.is_cancellation_requested():
            self.error.emit(OperationCancelledError("操作已取消。"))
            return

        call_kwargs = dict(self._kwargs)
        if "cancel_requested" not in call_kwargs and self._supports_parameter("cancel_requested"):
            call_kwargs["cancel_requested"] = self.is_cancellation_requested
        if "progress_callback" not in call_kwargs and self._supports_parameter("progress_callback"):
            call_kwargs["progress_callback"] = self.progress.emit

        try:
            result = self._func(*self._args, **call_kwargs)
        except Exception as exc:
            self.error.emit(exc)
            return

        self.finished.emit(result)

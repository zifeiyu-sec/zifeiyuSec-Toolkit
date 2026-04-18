from __future__ import annotations


class OperationCancelledError(RuntimeError):
    """Raised when a cooperative background task is cancelled."""


def is_cancel_requested(cancel_requested=None) -> bool:
    if cancel_requested is None:
        return False
    if not callable(cancel_requested):
        return bool(cancel_requested)
    try:
        return bool(cancel_requested())
    except Exception:
        return True


def raise_if_cancelled(cancel_requested=None, message: str = "操作已取消。") -> None:
    if is_cancel_requested(cancel_requested):
        raise OperationCancelledError(message)


def iter_response_chunks(response, cancel_requested=None, chunk_size: int = 64 * 1024):
    size = max(int(chunk_size or 0), 1)
    while True:
        raise_if_cancelled(cancel_requested)
        chunk = response.read(size)
        if not chunk:
            break
        yield chunk
    raise_if_cancelled(cancel_requested)

import shutil
import uuid
from pathlib import Path


TEST_WORKSPACE_ROOT = Path(__file__).resolve().parents[1] / "test_workspace_local"


def make_test_dir(prefix: str) -> Path:
    TEST_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_WORKSPACE_ROOT / f"{prefix}_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def cleanup_test_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)

"""Version management."""
import sys
from pathlib import Path


def _get_base_path() -> Path:
    """Get base path for bundled or development environment."""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent


def get_version() -> str:
    """Get version from VERSION file or fallback."""
    version_file = _get_base_path() / "VERSION"
    try:
        return version_file.read_text().strip()
    except FileNotFoundError:
        return "0.0.0"

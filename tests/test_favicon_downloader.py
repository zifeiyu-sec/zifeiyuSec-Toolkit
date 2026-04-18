import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from _support import cleanup_test_dir, make_test_dir
from ui.favicon_downloader import FaviconDownloader


class _FakeResponse:
    def __init__(self, data, content_type, final_url):
        self._data = data
        self._content_type = content_type
        self._final_url = final_url
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._data

    def geturl(self):
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FaviconDownloaderTests(unittest.TestCase):
    def setUp(self):
        self.icon_dir = make_test_dir(f"favicon_downloader_{self._testMethodName}")
        self.addCleanup(lambda: cleanup_test_dir(self.icon_dir))

    def test_direct_image_url_is_downloaded_into_icon_dir(self):
        downloader = FaviconDownloader(None, "https://avatars.githubusercontent.com/u/13752566?s=48&v=4", str(self.icon_dir))
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

        with patch(
            "ui.favicon_downloader.urllib.request.urlopen",
            return_value=_FakeResponse(
                fake_png,
                "image/png",
                "https://avatars.githubusercontent.com/u/13752566?s=48&v=4",
            ),
        ):
            file_name = downloader._download_favicon_logic("https://avatars.githubusercontent.com/u/13752566?s=48&v=4")

        self.assertTrue(file_name.endswith(".png"))
        self.assertTrue((self.icon_dir / file_name).is_file())


if __name__ == "__main__":
    unittest.main()

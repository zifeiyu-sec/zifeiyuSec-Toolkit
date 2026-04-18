import os
import re
import urllib.request
from urllib.parse import urljoin, urlparse

from PyQt5.QtCore import QThread, pyqtSignal

from core.logger import logger


class FaviconDownloader(QThread):
    """后台下载 favicon 的线程。"""

    download_finished = pyqtSignal(str)

    def __init__(self, parent, url, icon_dir):
        super().__init__(parent)
        self.url = url
        self.icon_dir = icon_dir

    def run(self):
        try:
            if self.isInterruptionRequested():
                self.download_finished.emit("")
                return
            favicon_name = self._download_favicon_logic(self.url)
            self.download_finished.emit(favicon_name)
        except Exception as exc:
            logger.warning("下载 favicon 失败 %s: %s", self.url, exc)
            self.download_finished.emit("")

    def _download_favicon_logic(self, url: str, timeout: float = 5.0) -> str:
        if not url:
            return ""
        if self.isInterruptionRequested():
            return ""

        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ""
        except Exception:
            return ""

        domain = parsed.netloc
        base = f"{parsed.scheme}://{domain}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        }

        try:
            os.makedirs(self.icon_dir, exist_ok=True)
        except OSError:
            return ""

        direct_icon_name = self._download_direct_icon(url, domain, headers, timeout)
        if direct_icon_name:
            return direct_icon_name
        if self.isInterruptionRequested():
            return ""

        candidates = [
            f"{base}/favicon.ico",
            f"{base}/favicon.png",
            f"{base}/favicon.svg",
            f"{base}/apple-touch-icon.png",
            f"{base}/apple-touch-icon-precomposed.png",
            f"{base}/favicon.jpg",
            f"{base}/favicon.jpeg",
            f"https://{domain}/favicon.ico",
            f"http://{domain}/favicon.ico",
        ]

        for candidate in candidates:
            if self.isInterruptionRequested():
                return ""
            icon_name = self._download_icon_candidate(candidate, domain, headers, timeout)
            if icon_name:
                return icon_name

        page_urls = [url]
        homepage = f"{parsed.scheme}://{domain}/"
        if homepage not in page_urls:
            page_urls.append(homepage)

        seen_icon_urls = set()
        for page_url in page_urls:
            if self.isInterruptionRequested():
                return ""
            html, final_url = self._fetch_html(page_url, headers, timeout)
            if not html:
                continue

            for icon_url in self._extract_icon_links(html, final_url):
                if self.isInterruptionRequested():
                    return ""
                if not icon_url or icon_url in seen_icon_urls:
                    continue
                seen_icon_urls.add(icon_url)
                icon_name = self._download_icon_candidate(icon_url, domain, headers, timeout)
                if icon_name:
                    return icon_name

        return ""

    def _download_direct_icon(self, source_url, domain, headers, timeout):
        if self.isInterruptionRequested():
            return ""
        try:
            req = urllib.request.Request(source_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if self.isInterruptionRequested():
                    return ""
                final_url = resp.geturl()
                content_type = (resp.headers.get('Content-Type', '') or '').lower()
                if not self._looks_like_supported_image(final_url or source_url, content_type):
                    return ""

                data = resp.read()
                if not data or len(data) < 10:
                    return ""

                ext = self._detect_extension(final_url or source_url, content_type)
                return self._save_icon(data, domain, ext)
        except Exception:
            return ""

    def _fetch_html(self, page_url, headers, timeout):
        if self.isInterruptionRequested():
            return "", page_url
        try:
            req = urllib.request.Request(page_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if self.isInterruptionRequested():
                    return "", resp.geturl()
                content_type = (resp.headers.get('Content-Type', '') or '').lower()
                if 'html' not in content_type and content_type:
                    return "", resp.geturl()
                html = resp.read().decode('utf-8', errors='ignore')
                return html, resp.geturl()
        except Exception:
            return "", page_url

    def _extract_icon_links(self, html, base_url):
        icon_links = []
        for tag in re.findall(r'<link\b[^>]*>', html, flags=re.I):
            rel_match = re.search(r'rel=[\'\"]([^\'\"]+)[\'\"]', tag, flags=re.I)
            href_match = re.search(r'href=[\'\"]([^\'\"]+)[\'\"]', tag, flags=re.I)
            if not rel_match or not href_match:
                continue

            rel_value = rel_match.group(1).lower()
            rel_tokens = {token for token in re.split(r'\s+', rel_value) if token}
            if not ({'icon', 'shortcut', 'apple-touch-icon', 'mask-icon', 'fluid-icon'} & rel_tokens or 'apple-touch-icon' in rel_value):
                continue

            href = href_match.group(1).strip()
            if not href or href.startswith('data:'):
                continue
            icon_links.append(urljoin(base_url, href))

        return icon_links

    def _download_icon_candidate(self, candidate, domain, headers, timeout):
        if self.isInterruptionRequested():
            return ""
        try:
            req = urllib.request.Request(candidate, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if self.isInterruptionRequested():
                    return ""
                data = resp.read()
                if not data or len(data) < 10:
                    return ""

                ext = self._detect_extension(candidate, resp.headers.get('Content-Type', ''))
                return self._save_icon(data, domain, ext)
        except Exception:
            return ""

    def _detect_extension(self, source_url, content_type):
        content_type = (content_type or '').lower()
        if 'png' in content_type:
            return '.png'
        if 'svg' in content_type:
            return '.svg'
        if 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        if 'ico' in content_type or 'icon' in content_type:
            return '.ico'

        path = urlparse(source_url).path.lower()
        for ext in ('.svg', '.png', '.ico', '.jpg', '.jpeg'):
            if path.endswith(ext):
                return '.jpg' if ext == '.jpeg' else ext
        return '.ico'

    def _looks_like_supported_image(self, source_url, content_type):
        content_type = (content_type or '').lower()
        if any(token in content_type for token in ('image/', 'icon', 'svg')):
            return True

        path = urlparse(source_url).path.lower()
        return any(path.endswith(ext) for ext in ('.svg', '.png', '.ico', '.jpg', '.jpeg'))

    def _save_icon(self, data, domain, ext):
        safe_domain = domain.replace(':', '_').replace('/', '_')
        filename = f"{safe_domain}_favicon{ext}"
        path = os.path.join(self.icon_dir, filename)

        counter = 1
        while os.path.exists(path):
            filename = f"{safe_domain}_favicon_{counter}{ext}"
            path = os.path.join(self.icon_dir, filename)
            counter += 1

        try:
            with open(path, 'wb') as f:
                f.write(data)
            return filename
        except Exception:
            return ""

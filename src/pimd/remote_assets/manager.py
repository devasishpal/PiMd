"""Remote asset download, caching, and offline management."""

from __future__ import annotations

import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pimd.attachments import AttachmentType, detect_attachment_type, detect_mime_type

logger = logging.getLogger(__name__)

_EXTERNAL_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_SVG_MIME = re.compile(r"image/svg\+xml", re.IGNORECASE)


@dataclass
class RemoteAssetConfig:
    cache_dir: str | Path = ""
    cache_ttl_seconds: int = 86400
    timeout_seconds: float = 30.0
    max_file_size: int = 50 * 1024 * 1024
    user_agent: str = "PiMD/1.0"
    offline_mode: bool = False
    follow_redirects: bool = True
    max_redirects: int = 5
    allowed_domains: list[str] = field(default_factory=list)
    verify_ssl: bool = True


@dataclass
class RemoteAsset:
    url: str
    fetched_path: Path | None = None
    mime_type: str = ""
    attachment_type: AttachmentType = AttachmentType.OTHER
    size: int = 0
    sha256: str = ""
    fetch_time: float = 0.0
    error: str | None = None
    cached: bool = False


@dataclass
class AssetFetchResult:
    success: bool
    assets: list[RemoteAsset] = field(default_factory=list)
    total_bytes: int = 0
    errors: list[str] = field(default_factory=list)
    duration: float = 0.0


class RemoteAssetManager:
    """Download, cache, and manage remote assets (images, SVGs, fonts, etc.).

    Supports:
    - HTTP/HTTPS asset downloads with timeouts
    - Content-addressable SHA256 caching
    - Offline mode (use cached versions only)
    - SVG asset detection
    - Configurable TTL and domain allowlists
    """

    def __init__(self, config: RemoteAssetConfig | None = None) -> None:
        self.config = config or RemoteAssetConfig()
        if not self.config.cache_dir:
            self.config.cache_dir = Path.home() / ".pimd" / "remote-assets"
        self._cache_dir = Path(self.config.cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._session: Any = None

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def is_remote_url(self, url: str) -> bool:
        return bool(_EXTERNAL_URL_RE.match(url))

    def fetch(self, urls: list[str]) -> AssetFetchResult:
        start = time.monotonic()
        assets: list[RemoteAsset] = []
        errors: list[str] = []

        for url in urls:
            if not self.is_remote_url(url):
                errors.append(f"Not a remote URL: {url}")
                continue
            if self.config.allowed_domains:
                parsed = urllib.parse.urlparse(url)
                if parsed.hostname not in self.config.allowed_domains:
                    errors.append(f"Domain not allowed: {parsed.hostname}")
                    continue
            try:
                asset = self._fetch_single(url)
                assets.append(asset)
            except Exception as exc:
                logger.warning("Failed to fetch %s: %s", url, exc)
                errors.append(f"{url}: {exc}")
                assets.append(
                    RemoteAsset(url=url, error=str(exc), cached=False)
                )

        duration = time.monotonic() - start
        total_bytes = sum(a.size for a in assets)
        return AssetFetchResult(
            success=len(errors) == 0,
            assets=assets,
            total_bytes=total_bytes,
            errors=errors,
            duration=duration,
        )

    def _fetch_single(self, url: str) -> RemoteAsset:
        cache_key = self._url_to_cache_key(url)
        cache_path = self._cache_dir / cache_key
        sha_path = cache_path.with_suffix(".sha256")

        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < self.config.cache_ttl_seconds:
                sha = sha_path.read_text().strip() if sha_path.exists() else ""
                mime = detect_mime_type(cache_path)
                att_type = detect_attachment_type(cache_path)
                return RemoteAsset(
                    url=url,
                    fetched_path=cache_path,
                    mime_type=mime,
                    attachment_type=att_type,
                    size=cache_path.stat().st_size,
                    sha256=sha,
                    fetch_time=age,
                    cached=True,
                )

        if self.config.offline_mode:
            if cache_path.exists():
                sha = sha_path.read_text().strip() if sha_path.exists() else ""
                mime = detect_mime_type(cache_path)
                att_type = detect_attachment_type(cache_path)
                return RemoteAsset(
                    url=url,
                    fetched_path=cache_path,
                    mime_type=mime,
                    attachment_type=att_type,
                    size=cache_path.stat().st_size,
                    sha256=sha,
                    fetch_time=time.time() - cache_path.stat().st_mtime,
                    cached=True,
                )
            return RemoteAsset(
                url=url, error="Offline mode — no cached version available", cached=False
            )

        import hashlib
        import urllib.request

        req = urllib.request.Request(
            url,
            headers={"User-Agent": self.config.user_agent},
        )
        with urllib.request.urlopen(
            req, timeout=self.config.timeout_seconds
        ) as response:
            data = response.read()

        if self.config.max_file_size > 0 and len(data) > self.config.max_file_size:
            return RemoteAsset(
                url=url,
                error=f"File too large: {len(data)} bytes (max {self.config.max_file_size})",
                cached=False,
            )

        mime = response.headers.get("Content-Type", "").split(";")[0].strip()
        ext = self._mime_to_extension(mime, url)
        cache_path = self._cache_dir / f"{cache_key}{ext}"
        cache_path.write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        sha_path.write_text(sha)

        att_type = detect_attachment_type(cache_path)
        if att_type == AttachmentType.OTHER and _SVG_MIME.search(mime):
            att_type = AttachmentType.SVG

        return RemoteAsset(
            url=url,
            fetched_path=cache_path,
            mime_type=mime,
            attachment_type=att_type,
            size=len(data),
            sha256=sha,
            fetch_time=0.0,
            cached=False,
        )

    def extract_urls(self, text: str) -> list[str]:
        urls: set[str] = set()
        img_re = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        link_re = re.compile(r'(?<!!)\[([^\]]*)\]\(([^)]+)\)')
        for match in img_re.finditer(text):
            url = match.group(2).split(" ")[0].strip()
            if self.is_remote_url(url):
                urls.add(url)
        for match in link_re.finditer(text):
            url = match.group(2).split(" ")[0].strip()
            if self.is_remote_url(url):
                ext = Path(url).suffix.lower()
                if ext in self._ASSET_EXTENSIONS:
                    urls.add(url)
        html_attr_re = re.compile(
            r'(?:src|href|data|poster)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE
        )
        for match in html_attr_re.finditer(text):
            url = match.group(1).split("?")[0].strip()
            if self.is_remote_url(url):
                urls.add(url)
        return sorted(urls)

    def clear_cache(self) -> None:
        import shutil
        for child in self._cache_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def cache_size(self) -> int:
        total = 0
        for child in self._cache_dir.rglob("*"):
            if child.is_file():
                total += 1
        return total

    @staticmethod
    def _url_to_cache_key(url: str) -> str:
        import hashlib
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _mime_to_extension(mime: str, url: str) -> str:
        mime_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "image/avif": ".avif",
            "image/bmp": ".bmp",
            "image/tiff": ".tiff",
            "image/x-icon": ".ico",
            "application/pdf": ".pdf",
            "font/ttf": ".ttf",
            "font/otf": ".otf",
            "font/woff": ".woff",
            "font/woff2": ".woff2",
        }
        if mime in mime_map:
            return mime_map[mime]
        parsed = urllib.parse.urlparse(url)
        ext = Path(parsed.path).suffix.lower()
        if ext:
            return ext
        return ".bin"

    _ASSET_EXTENSIONS: set[str] = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".avif",
        ".svg", ".svgz", ".pdf", ".ico",
        ".ttf", ".otf", ".woff", ".woff2", ".eot",
    }

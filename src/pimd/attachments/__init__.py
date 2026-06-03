"""Document attachment handling (images, SVG, PDF, embedded assets)."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import re
import shutil
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class AttachmentType(str, Enum):
    IMAGE = "image"
    SVG = "svg"
    PDF = "pdf"
    ARCHIVE = "archive"
    FONT = "font"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    DATA = "data"
    OTHER = "other"


@dataclass
class AttachmentConfig:
    copy_to_output: bool = True
    embed_in_docx: bool = True
    max_image_width: int = 600
    svg_to_png: bool = True
    missing_file_action: str = "warn"
    allowed_extensions: set[str] | None = None
    max_file_size: int = 50 * 1024 * 1024
    extra_mime_types: dict[str, str] = field(default_factory=dict)


@dataclass
class Attachment:
    source_path: Path
    resolved_path: Path | None = None
    attachment_type: AttachmentType = AttachmentType.OTHER
    mime_type: str = ""
    size: int = 0
    relative_path: str = ""
    destination: Path | None = None
    embedded: bool = False
    error: str | None = None


_MIME_EXTRA: dict[str, str] = {
    ".svg": "image/svg+xml",
    ".svgz": "image/svg+xml",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".eps": "application/postscript",
    ".psd": "image/vnd.adobe.photoshop",
    ".ai": "application/postscript",
    ".djvu": "image/vnd.djvu",
    ".cbz": "application/x-cbz",
    ".cbr": "application/x-cbr",
    ".7z": "application/x-7z-compressed",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
    ".zip": "application/zip",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".eot": "application/vnd.ms-fontobject",
}

_IMAGE_EXTENSIONS: set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif",
    ".webp", ".avif", ".heic", ".heif", ".ico",
}

_SVG_EXTENSIONS: set[str] = {".svg", ".svgz"}

_PDF_EXTENSIONS: set[str] = {".pdf"}

_ARCHIVE_EXTENSIONS: set[str] = {
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
}

_FONT_EXTENSIONS: set[str] = {
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
}

_STYLESHEET_EXTENSIONS: set[str] = {".css", ".scss", ".sass", ".less"}

_SCRIPT_EXTENSIONS: set[str] = {".js", ".mjs", ".cjs"}

_DATA_EXTENSIONS: set[str] = {
    ".json", ".yaml", ".yml", ".xml", ".csv", ".tsv", ".toml",
    ".ini", ".cfg", ".conf",
}


_SVG_HEADER_RE = re.compile(rb'<svg[\s>]', re.IGNORECASE)
_SVG_XML_HEADER_RE = re.compile(rb'<\?xml\s+version[^>]*\?>[\s]*<svg[\s>]', re.IGNORECASE)


def _ensure_mime_extra(config: AttachmentConfig | None = None) -> None:
    if config and config.extra_mime_types:
        for ext, mime in config.extra_mime_types.items():
            if ext not in mimetypes.types_map:
                mimetypes.add_type(mime, ext)


def detect_attachment_type(path: str | Path) -> AttachmentType:
    path_str = str(path)
    p = Path(path_str)
    suffix = p.suffix.lower()

    if suffix in _IMAGE_EXTENSIONS:
        return AttachmentType.IMAGE
    if suffix in _SVG_EXTENSIONS:
        return AttachmentType.SVG
    if suffix in _PDF_EXTENSIONS:
        return AttachmentType.PDF
    if suffix in _ARCHIVE_EXTENSIONS:
        return AttachmentType.ARCHIVE
    if suffix in _FONT_EXTENSIONS:
        return AttachmentType.FONT
    if suffix in _STYLESHEET_EXTENSIONS:
        return AttachmentType.STYLESHEET
    if suffix in _SCRIPT_EXTENSIONS:
        return AttachmentType.SCRIPT
    if suffix in _DATA_EXTENSIONS:
        return AttachmentType.DATA

    return AttachmentType.OTHER


def detect_mime_type(path: str | Path, config: AttachmentConfig | None = None) -> str:
    _ensure_mime_extra(config)
    path_str = str(path)
    mime, _ = mimetypes.guess_type(path_str)
    if mime:
        return mime

    ext = Path(path_str).suffix.lower()
    return _MIME_EXTRA.get(ext, "application/octet-stream")


def _detect_svg_by_content(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        header = path.read_bytes()[:512]
        if _SVG_HEADER_RE.search(header):
            return True
        if _SVG_XML_HEADER_RE.search(header):
            return True
        return False
    except OSError:
        return False


def resolve_attachment_path(
    source_path: str | Path,
    source_document: Path,
) -> Path | None:
    src = Path(source_path)
    if src.is_absolute():
        resolved = src.resolve()
        if resolved.exists():
            return resolved
        return None

    doc_dir = source_document.resolve().parent
    candidates = [
        doc_dir / src,
        doc_dir / src.name,
    ]

    if not src.parent.name == "." and str(src.parent) != "":
        candidates.append(doc_dir / src.parent / src.name)

    base = doc_dir
    parts = src.parts
    for i in range(len(parts), 0, -1):
        sub = base.joinpath(*parts[:i])
        if sub.exists():
            return sub.resolve()

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if resolved.exists():
                return resolved
        except (OSError, RuntimeError):
            continue

    return None


def resolve_attachments(
    refs: list[str],
    source_document: Path,
    config: AttachmentConfig | None = None,
) -> list[Attachment]:
    results: list[Attachment] = []
    cfg = config or AttachmentConfig()

    for ref in refs:
        src = Path(ref)
        resolved = resolve_attachment_path(src, source_document)
        att_type = detect_attachment_type(src)

        if resolved is None:
            missing_action = cfg.missing_file_action
            if missing_action == "error":
                raise FileNotFoundError(
                    f"Attachment not found: {ref} (resolved from {source_document})"
                )
            if missing_action == "skip":
                continue

            attachment = Attachment(
                source_path=src,
                resolved_path=None,
                attachment_type=att_type,
                mime_type=detect_mime_type(src, cfg),
                size=0,
                relative_path=str(src),
                error=f"File not found: {ref}",
            )
            results.append(attachment)
            continue

        mime = detect_mime_type(resolved, cfg)
        size = resolved.stat().st_size

        if cfg.max_file_size > 0 and size > cfg.max_file_size:
            attachment = Attachment(
                source_path=src,
                resolved_path=resolved,
                attachment_type=att_type,
                mime_type=mime,
                size=size,
                relative_path=str(src),
                error=f"File too large: {size} bytes (max {cfg.max_file_size})",
            )
            results.append(attachment)
            continue

        attachment = Attachment(
            source_path=src,
            resolved_path=resolved,
            attachment_type=att_type,
            mime_type=mime,
            size=size,
            relative_path=str(src),
        )
        results.append(attachment)

    return results


_MARKDOWN_IMAGE_RE = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\((?P<url>[^)]+)\)'
)
_MARKDOWN_LINK_RE = re.compile(
    r'(?<!!)\[(?P<text>[^\]]*)\]\((?P<url>[^)]+)\)'
)
_HTML_IMG_RE = re.compile(
    r'<img\s[^>]*src\s*=\s*["\'](?P<url>[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
_HTML_LINK_RE = re.compile(
    r'<link\s[^>]*href\s*=\s*["\'](?P<url>[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
_HTML_SCRIPT_RE = re.compile(
    r'<script\s[^>]*src\s*=\s*["\'](?P<url>[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
_HTML_OBJECT_RE = re.compile(
    r'<object\s[^>]*data\s*=\s*["\'](?P<url>[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
_HTML_EMBED_RE = re.compile(
    r'<embed\s[^>]*src\s*=\s*["\'](?P<url>[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
_HTML_SOURCE_RE = re.compile(
    r'<source\s[^>]*src\s*=\s*["\'](?P<url>[^"\']+)["\'][^>]*>',
    re.IGNORECASE,
)
_REFERENCE_IMAGE_RE = re.compile(
    r'!\[(?P<alt>[^\]]*)\]\[(?P<refid>[^\]]*)\]'
)
_REFERENCE_LINK_RE = re.compile(
    r'(?<!!)\[(?P<text>[^\]]*)\]\[(?P<refid>[^\]]*)\]'
)

_EXTERNAL_PROTOCOLS = re.compile(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://')


def _is_external_url(url: str) -> bool:
    return bool(_EXTERNAL_PROTOCOLS.match(url))


def _is_data_uri(url: str) -> bool:
    return url.startswith("data:")


def _extract_urls_from_text(text: str) -> list[str]:
    urls: set[str] = set()

    for match in _MARKDOWN_IMAGE_RE.finditer(text):
        url = match.group("url").split(" ")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _MARKDOWN_LINK_RE.finditer(text):
        url = match.group("url").split(" ")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            ext = Path(url).suffix.lower()
            if ext in _IMAGE_EXTENSIONS | _SVG_EXTENSIONS | _PDF_EXTENSIONS | _ARCHIVE_EXTENSIONS:
                urls.add(url)

    for match in _HTML_IMG_RE.finditer(text):
        url = match.group("url").split("?")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _HTML_LINK_RE.finditer(text):
        url = match.group("url").split("?")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _HTML_SCRIPT_RE.finditer(text):
        url = match.group("url").split("?")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _HTML_OBJECT_RE.finditer(text):
        url = match.group("url").split("?")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _HTML_EMBED_RE.finditer(text):
        url = match.group("url").split("?")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _HTML_SOURCE_RE.finditer(text):
        url = match.group("url").split("?")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _REFERENCE_IMAGE_RE.finditer(text):
        url = match.group("refid").strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    for match in _REFERENCE_LINK_RE.finditer(text):
        url = match.group("refid").strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    attr_re = re.compile(
        r'(?:src|href|data|poster|srcset)\s*=\s*["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    for match in attr_re.finditer(text):
        url = match.group(1).split("?")[0].strip()
        if not _is_external_url(url) and not _is_data_uri(url):
            urls.add(url)

    return sorted(urls)


def find_attachments_in_text(
    text: str,
    source_document: Path,
    config: AttachmentConfig | None = None,
) -> list[Attachment]:
    urls = _extract_urls_from_text(text)
    return resolve_attachments(urls, source_document, config)


def copy_attachment(
    attachment: Attachment,
    output_dir: Path,
    config: AttachmentConfig | None = None,
) -> Attachment:
    if attachment.resolved_path is None:
        attachment.error = attachment.error or "Cannot copy: unresolved path"
        return attachment

    if attachment.error:
        return attachment

    rel = attachment.relative_path or attachment.resolved_path.name
    dest = (output_dir / rel).resolve()

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(attachment.resolved_path), str(dest))
        attachment.destination = dest
    except OSError as exc:
        attachment.error = f"Copy failed: {exc}"

    return attachment


def embed_attachment(
    attachment: Attachment,
    config: AttachmentConfig | None = None,
) -> tuple[str, str]:
    if attachment.resolved_path is None:
        raise FileNotFoundError(
            f"Cannot embed unresolved attachment: {attachment.source_path}"
        )
    mime = attachment.mime_type or detect_mime_type(attachment.resolved_path, config)
    data = attachment.resolved_path.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")
    return (mime, encoded)


def svg_to_png(
    svg_path: Path,
    output_path: Path,
    width: int = 800,
    height: int | None = None,
) -> bool:
    if not svg_path.exists():
        return False

    try:
        import cairosvg
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(output_path),
            output_width=width,
            output_height=height,
        )
        return True
    except ImportError:
        pass
    except Exception:
        logger.exception("cairosvg conversion failed for %s", svg_path)

    try:
        svg_data = svg_path.read_bytes()

        try:
            import cairosvg
            png_data = cairosvg.svg2png(
                bytestring=svg_data,
                output_width=width,
                output_height=height,
            )
            output_path.write_bytes(png_data)
            return True
        except ImportError:
            pass

        try:
            from reportlab.graphics import renderPM
            from svglib.svglib import svg2rlg

            drawing = svg2rlg(svg_path)
            renderPM.drawToFile(drawing, str(output_path), fmt="PNG")
            return True
        except ImportError:
            pass

        try:
            import cairocffi
            import cairocffi.svg as cairosvg_mod

            surface = cairosvg_mod.SVGSurface(
                svg_data,
                None,
                output_width=width,
                output_height=height,
            )
            png_surface = cairocffi.ImageSurface(
                cairocffi.FORMAT_ARGB32,
                surface.get_width(),
                surface.get_height(),
            )
            ctx = cairocffi.Context(png_surface)
            ctx.set_source_surface(surface, 0, 0)
            ctx.paint()
            png_surface.write_to_png(str(output_path))
            surface.finish()
            png_surface.finish()
            return True
        except ImportError:
            pass

        try:
            import subprocess
            result = subprocess.run(
                ["rsvg-convert", "-w", str(width), "-o", str(output_path), str(svg_path)],
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        try:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
                f.write(f'<html><body><img src="data:image/svg+xml;base64,'
                        f'{base64.b64encode(svg_data).decode()}" '
                        f'width="{width}"></body></html>')
                html_path = f.name
            try:
                import subprocess
                result = subprocess.run(
                    ["wkhtmltoimage", "--width", str(width), html_path, str(output_path)],
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            finally:
                try:
                    os.unlink(html_path)
                except OSError:
                    pass
        except Exception:
            pass

        logger.warning("No SVG-to-PNG renderer available for %s", svg_path)
        return False
    except Exception:
        logger.exception("SVG-to-PNG conversion failed for %s", svg_path)
        return False


def image_to_docx_xml(
    attachment: Attachment,
    max_width: int = 600,
    config: AttachmentConfig | None = None,
) -> str:
    if attachment.resolved_path is None:
        raise FileNotFoundError(
            f"Cannot generate XML for unresolved attachment: {attachment.source_path}"
        )

    path = attachment.resolved_path
    cfg = config or AttachmentConfig()
    width = min(max_width, cfg.max_image_width)

    try:
        from PIL import Image
        with Image.open(path) as img:
            img_width, img_height = img.size
    except Exception:
        img_width = width
        img_height = int(width * 0.75)

    aspect = img_height / img_width if img_width > 0 else 0.75
    emu_width = int(width * 914400)
    emu_height = int(emu_width * aspect)

    if attachment.mime_type == "image/svg+xml" and cfg.svg_to_png:
        tmp_png = path.with_suffix(".png")
        if svg_to_png(path, tmp_png, width=img_width):
            try:
                tmp_png.unlink()
            except OSError:
                pass

    img_id = str(hash(str(path)) & 0x7FFFFFFFFFFFFFFF)

    return (
        f'<w:drawing xmlns:wp="{_NS_WP}" xmlns:a="{_NS_A}" xmlns:r="{_NS_R}">'
        f'<wp:inline distT="0" distB="0" distL="0" distR="0">'
        f'<wp:extent cx="{emu_width}" cy="{emu_height}"/>'
        f'<wp:effectExtent l="0" t="0" r="0" b="0"/>'
        f'<wp:docPr id="{img_id}" name="Image {img_id}"'
        f' descr="{attachment.relative_path or path.name}"/>'
        f'<wp:cNvGraphicFramePr>'
        f'<a:graphicFrameLocks xmlns:a="{_NS_A}" noChangeAspect="1"/>'
        f'</wp:cNvGraphicFramePr>'
        f'<a:graphic xmlns:a="{_NS_A}">'
        f'<a:graphicData uri="{_NS_PIC}">'
        f'<pic:pic xmlns:pic="{_NS_PIC}">'
        f'<pic:nvPicPr>'
        f'<pic:cNvPr id="{img_id}" name="{path.name}"/>'
        f'<pic:cNvPicPr/>'
        f'</pic:nvPicPr>'
        f'<pic:blipFill>'
        f'<a:blip r:embed="rId{img_id}">'
        f'<a:extLst>'
        f'<a:ext uri="{{28A0092B-C50C-407E-A947-70E740481C1C}}">'
        f'<a14:useLocalDpi xmlns:a14="http://schemas.microsoft.com/office/drawing/2010/main" val="0"/>'
        f'</a:ext>'
        f'</a:extLst>'
        f'</a:blip>'
        f'<a:srcRect/>'
        f'<a:stretch>'
        f'<a:fillRect/>'
        f'</a:stretch>'
        f'</pic:blipFill>'
        f'<pic:spPr>'
        f'<a:xfrm>'
        f'<a:off x="0" y="0"/>'
        f'<a:ext cx="{emu_width}" cy="{emu_height}"/>'
        f'</a:xfrm>'
        f'<a:prstGeom prst="rect">'
        f'<a:avLst/>'
        f'</a:prstGeom>'
        f'</pic:spPr>'
        f'</pic:pic>'
        f'</a:graphicData>'
        f'</a:graphic>'
        f'</wp:inline>'
        f'</w:drawing>'
    )


_NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
_NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"


def collect_assets(
    directory: Path,
    patterns: list[str] | None = None,
    config: AttachmentConfig | None = None,
) -> list[Attachment]:
    cfg = config or AttachmentConfig()
    assets: list[Attachment] = []

    if not directory.exists() or not directory.is_dir():
        return assets

    if patterns:
        for pattern in patterns:
            for path in directory.rglob(pattern):
                if not path.is_file():
                    continue
                att_type = detect_attachment_type(path)
                mime = detect_mime_type(path, cfg)
                size = path.stat().st_size
                rel = path.relative_to(directory)
                assets.append(
                    Attachment(
                        source_path=path,
                        resolved_path=path,
                        attachment_type=att_type,
                        mime_type=mime,
                        size=size,
                        relative_path=str(rel),
                    )
                )
    else:
        allowed = cfg.allowed_extensions
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if allowed and path.suffix.lower() not in allowed:
                continue
            att_type = detect_attachment_type(path)
            mime = detect_mime_type(path, cfg)
            size = path.stat().st_size
            try:
                rel = path.relative_to(directory)
            except ValueError:
                rel = path.name
            assets.append(
                Attachment(
                    source_path=path,
                    resolved_path=path,
                    attachment_type=att_type,
                    mime_type=mime,
                    size=size,
                    relative_path=str(rel),
                )
            )

    if cfg.max_file_size > 0:
        filtered: list[Attachment] = []
        for att in assets:
            if att.size > cfg.max_file_size:
                att.error = f"File too large: {att.size} bytes (max {cfg.max_file_size})"
            filtered.append(att)
        assets = filtered

    return assets


def process_attachments(
    text: str,
    source_document: Path,
    config: AttachmentConfig | None = None,
) -> tuple[str, list[Attachment]]:
    cfg = config or AttachmentConfig()
    attachments = find_attachments_in_text(text, source_document, cfg)

    output_dir: Path | None = None
    if cfg.copy_to_output:
        doc_dir = source_document.resolve().parent
        output_dir = doc_dir / f"{source_document.stem}_assets"
        output_dir.mkdir(parents=True, exist_ok=True)

    for att in attachments:
        if att.error:
            continue

        if att.resolved_path is None:
            continue

        if cfg.copy_to_output and output_dir is not None:
            copy_attachment(att, output_dir, cfg)

        if cfg.embed_in_docx and att.attachment_type in (
            AttachmentType.IMAGE,
            AttachmentType.SVG,
            AttachmentType.PDF,
        ):
            if att.resolved_path and att.resolved_path.exists():
                try:
                    embed_attachment(att, cfg)
                    att.embedded = True
                except Exception as exc:
                    att.error = f"Embedding failed: {exc}"

    updated_text = text

    processed_refs: dict[str, str] = {}
    for att in attachments:
        if att.resolved_path and att.error is None:
            if cfg.copy_to_output and att.destination:
                processed_refs[att.relative_path] = str(att.destination)
            else:
                processed_refs[att.relative_path] = str(att.resolved_path)

    def _replace_md_image(match: re.Match) -> str:
        url = match.group("url").split(" ")[0].strip()
        if url in processed_refs:
            new_url = processed_refs[url]
            alt = match.group("alt")
            return f"![{alt}]({new_url})"
        return match.group(0)

    updated_text = _MARKDOWN_IMAGE_RE.sub(_replace_md_image, updated_text)

    return (updated_text, attachments)
